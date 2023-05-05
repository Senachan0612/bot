import sys
import os
import json
import logging
import datetime
import csv

from pycqBot import cqBot, cqHttpApi, Plugin, Message
from pycqBot.cqCode import node_list, node_list_alter

DOWNLOAD_PATH = r'../info/download/chatgpt'
LOCAL_PATH = sys.path[0].replace('\\', '/')
# 回复切割符
SPLIT_SIGN = '|||：'
# 失效话题标识
FAIL_SIGN = '_f_'

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
        }).command(self.query_chat, '查看会话', {
            'help': [
                '#查看会话 - 携带参数时则为查看会话详情',
                '   格式: #查看会话 [会话名称(可选)]'
            ]
        }).command(self.normal_chat, 'Q', {
            'help': [
                '#Q - ChatGpt聊天，会话名称不存在时为临时对话',
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
        _path = self.format_path(_title, message.sender.group_id)

        if os.path.isfile(_path):
            # 回复消息
            message.reply('会话[%s]已存在，无法重新创建！' % _title)

        self.cqapi.add_task(self._new_chat(_title, message))

    async def _new_chat(self, title, message):
        await self.download(title, message.sender.group_id, new=True)
        message.reply('会话[%s]已成功创建！' % title)

    def clear_chat(self, commandData, message: Message):
        """
            删除会话
        """
        if not commandData:
            # 回复消息
            message.reply('删除会话命令有误，指令例子："#删除会话 测试会话"。')
        _title = commandData[0]
        _path = self.format_path(_title, message.sender.group_id)

        if not os.path.isfile(_path):
            # 回复消息
            message.reply('会话[%s]不存在，删除失败！' % _title)

        self.cqapi.add_task(self._clear_chat(_title, _path, message))

    async def _clear_chat(self, title, _path, message):
        old_path = _path
        _time = self.format_time().replace(':', '-')
        _title = f'{FAIL_SIGN}%s_%s_%s' % (title, message.sender.id, _time)
        new_path = self.format_path(_title, message.sender.group_id)

        os.rename(old_path, new_path)
        message.reply('会话[%s]已成功删除！' % title)

    def query_chat(self, commandData, message: Message):
        """
            查看会话
        """
        _title = commandData and commandData[0] or None

        self.cqapi.add_task(self._query_chat(_title, message))

    async def _query_chat(self, _title, message):
        _group_id = message.sender.group_id
        _path = self.format_path(_title, _group_id)

        if _title:
            # 查询明细
            if not os.path.isfile(_path):
                # 回复消息
                message.reply('会话[%s]不存在，查询失败！' % _title)

            with open(_path, 'r', encoding='utf8') as file:
                reader = csv.DictReader(file)
                # 格式化处理内容
                _context = (('[%s]%s' % (row['date'], row['info']), row['name'], row['uid']) for row in reader)
                reply_list = node_list_alter(_context)
        else:
            # 查询话题
            if os.path.isdir(_path):
                file_names = os.listdir(_path)
                if not file_names:
                    return message.reply('当前不存在任何会话！')

                def __func(_list):
                    for __file in _list:
                        __name, __type = __file.split('.', maxsplit=1)
                        if __type == 'csv':
                            yield __name

                reply_list = node_list(__func(file_names), self.cqapi.bot_name, self.cqapi.bot_qq)

        self.cqapi.send_group_forward_msg(message.sender.group_id, reply_list)

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
        analyze_dict = [SPLIT_SIGN, '<OPENAI>：', '<OPENAI>回答：']
        res = response['choices'][0]['message']['content']

        for flag in analyze_dict:
            if flag in res:
                return res.split(flag, maxsplit=1)[-1]

        return res

    def format_path(self, title, group_id, user_id=None):
        _group_id = str(group_id)

        # 创建该群组文件路径
        self.check_dir(_group_id)

        if title:
            if user_id:
                _time = self.format_time().replace(':', '-')
                return os.path.join(self._path, _group_id, '_f_%s_%s_%s.csv' % (title, user_id, _time))

            return os.path.join(self._path, _group_id, '%s.csv' % title)

        return os.path.join(self._path, _group_id)

    def check_dir(self, _group_id):
        _group_id = str(_group_id)

        path = os.path.join(self._path, _group_id)
        if not os.path.exists(path):
            os.makedirs(path)

    async def download(self, _title, _group_id, _info=[], new=False):
        _path = self.format_path(_title, _group_id)
        _row = ('date', 'uid', 'name', 'info')

        if new or not os.path.isfile(_path):
            new = True
            self.check_dir(_group_id)

        with open(_path, 'a', encoding='utf8', newline='') as file:
            writer = csv.writer(file)
            # 写头信息
            if new:
                writer.writerow(_row)
            for info in _info:
                writer.writerow(info)

    async def format_message(self, data, message):
        _data = [x for x in data if x]

        _title = _data[0]
        _group_id = message.sender.group_id
        context_path = self.format_path(_title, _group_id)

        if len(_data) > 1 and os.path.isfile(context_path):
            # 上下文对话
            _time = self.format_time()
            _text = '，'.join(_data[1:])
            _data = _time, message.sender.id, message.sender.nickname, _text

            with open(context_path, 'r', encoding='utf8') as file:
                reader = csv.DictReader(file)
                _context = (f'[%s]<%s>{SPLIT_SIGN}%s' % (row['date'], row['name'], row['info']) for row in reader)

                text = f'''
对话上下文(格式为"[时间]<用户>：消息内容"，用户"OPENAI"代表的是你的回复，回复以"[时间]<OPENAI>{SPLIT_SIGN}"的格式开头)：\n
%s \n
[%s]<%s>提问：%s
''' % ('\n'.join(_context), _data[0], _data[2], _data[3])

            # 写入最新的上下文
            await self.download(_title, _group_id, _info=[_data])

        else:
            # 临时对话
            _title = ''
            text = '，'.join(_data)

        return _title, _group_id, json.dumps({
            "model": self._model,
            "messages": [
                {"role": 'user', "content": text}
            ]
        })

    async def _normal_chat(self, data, message):
        try:
            # 格式化处理消息
            title, group_id, message_context = await self.format_message(data, message)

            # 请求gpt 格式化处理返回数据
            _reply = self.format_response(await self._link_gpt(message_context))

            # 回复消息
            message.reply(_reply)
            # 回复消息写入日志
            if title:
                _time = self.format_time()
                save_reply = _time, self.cqapi.bot_qq, self.cqapi.bot_name, _reply
                await self.download(title, group_id, _info=[save_reply])

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
