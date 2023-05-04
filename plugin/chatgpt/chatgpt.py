import sys
import os
import json
import logging
import datetime
import csv

from pycqBot import cqBot, cqHttpApi, Plugin, Message

DOWNLOAD_PATH = r'../info/download/chatgpt'
LOCAL_PATH = sys.path[0].replace('\\', '/')

URL = 'https://api.openai.com/v1/chat/completions'
MODEL = 'gpt-3.5-turbo'


class chatgpt(Plugin):
    """
    chatgpt

    插件配置
    ---------------------------
    url: 请求链接默认为'https://api.openai.com/v1/chat/completions'
    model: 模型默认为'gpt-3.5-turbo'
    key: 密钥
    proxy: 代理
    """

    def __init__(self, bot: cqBot, cqapi: cqHttpApi, plugin_config) -> None:
        super().__init__(bot, cqapi, plugin_config)

        self._url = plugin_config.get('url', URL)
        self._model = plugin_config.get('model', MODEL)
        self._key = plugin_config['key']
        self._proxy = "http://%s" % plugin_config['proxy']
        # 请求头
        self._headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        # 上下文管理 - 会话名称
        self.titles = set()
        # 上下文管理存放路径
        self._path = plugin_config.get('path', DOWNLOAD_PATH)

        bot.command(self.new_chat, '新建会话', {
            'help': [
                '#新建会话 - 新建一个聊天事件，在单个事件中，上下文可以互相使用',
                '   格式: #新建会话 [会话名称(可选)] [信息]'
            ]
        }).command(self.clear_chat, '删除会话', {
            'help': [
                '#删除会话 - 删除目标会话上下文',
                '   格式: #删除会话 [删除会话]'
            ]
        }).command(self.normal_chat, 'Q', {
            'help': [
                '#Q - ChatGpt聊天，会话名称不存在或为"-"时为临时对话',
                '   格式: #Q [会话名称(可选)] [信息]'
            ]
        })

    def new_chat(self, commandData, message: Message):
        """
            新建会话
        """
        if not commandData:
            # 回复消息
            message.reply('新建会话命令有误，指令例子："#新建会话 测试会话"。')

        _title = commandData[0]
        _path = os.path.join(self._path, '%s.csv' % _title)

        if os.path.isfile(_path):
            # 回复消息
            message.reply('会话[%s]已存在，无法重新创建！' % _title)

        self.cqapi.add_task(self._new_chat(_title, _path, message))

    async def _new_chat(self, title, path, message):
        await self.download(title, path=path, new=True)
        message.reply('会话[%s]已成功创建！' % title)

    def clear_chat(self, commandData, message: Message):
        """
            删除会话
        """
        if not commandData:
            # 回复消息
            message.reply('删除会话命令有误，指令例子："#删除会话 测试会话"。')
        _title = commandData[0]
        _path = os.path.join(self._path, '%s.csv' % _title)

        if not os.path.isfile(_path):
            # 回复消息
            message.reply('会话[%s]不存在，删除失败！' % _title)

        self.cqapi.add_task(self._clear_chat(_title, _path, message))

    async def _clear_chat(self, title, _path, message):
        _time = self.format_time().replace(':', '-')
        new_path = os.path.join(self._path, '_f_%s_%s_%s.csv' % (title, message.sender.id, _time))
        os.rename(_path, new_path)
        message.reply('会话[%s]已成功删除！' % title)

    def normal_chat(self, commandData, message: Message):
        """
            聊天
        """
        self.cqapi.add_task(self._normal_chat(commandData, message))

    @staticmethod
    def request_error(self, err):
        """
        请求ChatGTP时发生错误
        """
        logging.error("请求ChatGTP时发生错误! Error: %s " % err)
        logging.exception(err)

    @staticmethod
    def format_time(date=datetime.datetime.now()):
        return date.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def format_response(response):
        # 解析响应
        return response['choices'][0]['message']['content'].split('：', maxsplit=1)[-1]

    async def download(self, _title, _info=[], new=False, path=''):
        _path = path or os.path.join(self._path, '%s.csv' % _title)
        _row = ('date', 'user', 'info')

        if new or not os.path.isfile(_path):
            new = True

        with open(_path, 'a', encoding='utf8', newline='') as file:
            writer = csv.writer(file)
            # 写头信息
            if new:
                writer.writerow(_row)
            for info in _info:
                writer.writerow(info)

    async def format_message(self, data, message):
        title = data[0]
        context_path = os.path.join(self._path, '%s.csv' % title)

        if len(data) > 1 and os.path.isfile(context_path):
            # 上下文对话
            _time = self.format_time()
            _text = '，'.join(data[1:])
            _data = _time, message.sender.id, _text

            with open(context_path, 'r', encoding='utf8') as file:
                reader = csv.DictReader(file)
                _context = ('[%s]<%s>：%s' % (row['date'], row['user'], row['info']) for row in reader)

                text = '''
对话上下文(格式为"[时间]<用户>：消息内容"，用户"OPENAI"代表的是你的回复)：\n
%s \n
[%s]<%s>提问：%s
''' % ('\n'.join(_context), _data[0], _data[1], _data[2])

            # 写入最新的上下文
            await self.download(title, [_data])

        else:
            # 临时对话
            text = '，'.join(data)

        return json.dumps({
            "model": self._model,
            "messages": [
                {"role": 'user', "content": text}
            ]
        })

    async def _normal_chat(self, data, message):
        try:
            # 格式化处理消息
            message_context = await self.format_message(data, message)

            # 请求gpt 格式化处理返回数据
            res = self.format_response(await self._link_gpt(message_context))

            # 回复消息
            message.reply(res)

        except Exception as err:
            self.request_error(err)
            return False

    async def _link_gpt(self, message):
        """
            请求gpt响应
        """
        try:
            return await self.cqapi.link(url=self._url, mod='post', data=message, json=True,
                                         proxy=self._proxy, headers=self._headers)

        except Exception as err:
            self.request_error(err)
            return False
