from threading import Thread
import logging
import time
import datetime
import os
import requests
import io
import random
import copy
import csv
from PIL import Image, ImageDraw, ImageFont

from pycqBot import cqBot, cqHttpApi, Plugin, Message
from pycqBot.cqCode import node_list, node_list_alter

# 导入附加游戏
from plugin.games import _gobang

# 参与指令
JOIN_TAG = '参战'
# 日志路径
DOWNLOAD_PATH = r'../info/download/games'
# 背景图片大小
IMAGE_SIZE = 500


class games(Plugin):
    """
    games

    插件配置
    ---------------------------
    """

    def __init__(self, bot: cqBot, cqapi: cqHttpApi, plugin_config) -> None:
        super().__init__(bot, cqapi, plugin_config)

        self.game_mapping = {
            '五子棋': _gobang.GoBang
        }

        self.game_dict = {_g: _f for _g, _f in self.game_mapping.items() if _g in plugin_config.get('list', [])}

        def _format_canvas(_canvas_list, _size):
            _l = []
            for _path in _canvas_list[:5]:
                try:
                    # 打开图像
                    _img = Image.open(_path)
                except Exception:
                    continue

                # 添加处理后的图片
                _l.append(self.format_canvas(_img))

            if not _l:
                # 绘制一张默认背景
                _l.append(Image.new('RGB', (_size, _size), (210, 180, 140)))

            return _l

        self.canvas = _format_canvas(plugin_config.get('canvas', []), IMAGE_SIZE)

        # 消息监听时间(s)
        self.sleep_time = 2

        bot.command(self.play_game, 'G', {
            'help': [
                '#G - 开始Van♂游戏',
                '   格式: #G 游戏名'
            ]
        })

    # 发送群消息
    def send_group_msg(self, gid, msg: str, auto_escape: bool = False) -> None:
        self.cqapi.send_group_msg(int(gid), msg, auto_escape)

    @staticmethod
    def get_command(commandData, index_list):
        """
            取第n条有效命令
        """
        if isinstance(index_list, int):
            index_list = [index_list]

        res_list = []
        i = 0
        for command in commandData:
            if not command:
                continue
            i += 1
            if i in index_list:
                res_list.append(command)
        return tuple(res_list)

    def play_game(self, commandData, message: Message):
        commandData = [_msg for _msg in commandData if _msg]

        _name = ''
        # 是否替换背景图片
        is_canvas = False
        if len(commandData):
            _name = commandData[0]
            if len(commandData) > 1:
                is_canvas = True

        self.game_create(_name, message, is_canvas)

    def game_create(self, game_name, message: Message, is_canvas):
        name, func = game_name, self.game_dict.get(game_name)

        if not func:
            return message.reply('小游戏"%s"不存在！' % name)

        # 获取背景壁纸
        canvas = self.select_canvas(is_canvas, name, message)

        # 创建线程启动小游戏
        thread = Thread(target=func, args=(self, message, canvas), name=name)
        thread.setDaemon(True)
        thread.start()

        logging.info("创建小游戏任务 %s 用户 %s" % (name, []))

    def group_msg_context(self, _gid, _name):
        """启用群消息监听"""
        self.bot.group_msg_context.monitor(_gid, _name)

    def matching_players(self, message: Message, game_name, players_nums):
        """
            匹配玩家
        """
        # 群
        gid = message.sender.group_id
        # 所有群成员
        group_users = {str(u['user_id']): u['nickname']
                       for u in self.cqapi.get_group_member_list(gid).get('data', [])}

        if len(group_users) < players_nums:
            return message.reply('人数不足%s人，"%s"对局无法开始！' % (players_nums, game_name))

        # 对决发起者
        host_id, host_name = str(message.sender.id), message.sender.nickname

        self.send_group_msg(gid, '天下无敌的"%s"向愚蠢的群友们发起了"%s"对决邀请，回复"%s"与之一战！'
                            % (host_name, game_name, JOIN_TAG))

        dt = message._message_data['time']
        # 匹配人数
        matching_nums = players_nums - 1
        # 对决接受者
        player_ids = set()
        while True:
            context = self.bot.group_msg_context.get(gid, dt)
            _dt = dt
            # # todo
            # context = [('1074545686', _dt, '参战')]
            for _uid, _dt, _msg in context:
                _uname = group_users[_uid]
                _player = (_uid, _uname)

                if _msg == '取消' and self.check_user_limit(_uid, host_id):
                    self.send_group_msg(gid, '本次对局已取消！')
                    return None

                if JOIN_TAG in _msg and _uid != host_id and _player not in player_ids:
                    player_ids.add(_player)
                    self.send_group_msg(gid, '愚蠢的"%s"接受了这场"%s"巅峰对决，这时的TA还没有意识到TA将会面临什么。'
                                             '没错！一场血流成河的厮杀即将拉开帷幕！' % (_uname, game_name))
                    if len(player_ids) >= matching_nums:
                        break
            dt = _dt

            if len(player_ids) >= matching_nums:
                break
            time.sleep(self.sleep_time)
        return (host_id, host_name), player_ids, dt

    def select_canvas(self, is_custom=False, name='', message=None):
        """挑选画布"""
        if is_custom and name and isinstance(message, Message):
            gid = message.sender.group_id
            dt = message._message_data['time']
            user = str(message.sender.id)

            self.send_group_msg(gid, '请发送一张图片作为默认壁纸！')
            # 监听群消息
            self.bot.group_msg_context.monitor(gid, name)

            _canvas = None
            while True:
                context = self.bot.group_msg_context.get(gid, dt)
                _dt = dt
                for _uid, _dt, _msg in context:
                    if _msg == '取消' and self.check_user_limit(_uid, user):
                        self.send_group_msg(gid, '取消个性化认壁纸，使用默认壁纸！')
                        return copy.copy(self.canvas[int(len(self.canvas) * random.random() // 1)])

                    if _uid == user:
                        # 获取文件url
                        url = _msg.split('url=')
                        if len(url) < 2:
                            continue
                        url = url[-1].split(']')[0]
                        if url:
                            try:
                                byte_file = requests.get(url).content
                                _img = Image.open(io.BytesIO(byte_file))
                                _canvas = self.format_canvas(_img)
                            except Exception:
                                _canvas = copy.copy(self.canvas[int(len(self.canvas) * random.random() // 1)])
                                self.send_group_msg(gid, '未知错误，将使用默认壁纸！')
                        break
                dt = _dt

                if _canvas:
                    break
                time.sleep(self.sleep_time)
        else:
            _canvas = copy.copy(self.canvas[int(len(self.canvas) * random.random() // 1)])

        return _canvas

    def start_manifesto(self, _gid, _name, timestamp, host, player, back_msg='', path=DOWNLOAD_PATH):
        """开始宣言"""
        dt_object = datetime.datetime.fromtimestamp(timestamp)
        format_time = dt_object.strftime("%Y-%m-%d %H:%M:%S")
        host_name = '"%s"' % host[1]
        player_name = '、'.join(('"%s"' % x[1] for x in player))

        root_path = r'%s/%s/%s' % (path, _name, _gid)
        if not os.path.exists(root_path):
            os.makedirs(root_path)

        # 计算多少届
        season = len(os.listdir(root_path)) + 1
        while True:
            file_path = r'%s/%s' % (root_path, season)
            if not os.path.exists(file_path):
                os.makedirs(file_path)
                break
            season += 1

        self.send_group_msg(_gid, '服务器时间[%s]\n'
                                  '第%s届%s对决现在开始！'
                                  '%s'
                            % (format_time, season, _name, back_msg))

        return season, file_path

    def match_details(self, _gid, _game_name, _path):
        """对局详情，生成git"""
        # 获取图像文件夹中的所有图像文件
        images = []

        if os.path.exists(_path):
            for filename in sorted(os.listdir(_path)):
                if filename.endswith('.JPEG'):
                    file_path = r'%s/%s' % (_path, filename)
                    images.append(Image.open(file_path))
        if not images:
            return None

        file_name = r'%s/%s' % (_path, '__.gif')
        images[0].save(file_name, save_all=True, append_images=images[1:], optimize=False, duration=1000, loop=0)

        # 永久储存
        return file_name

    def check_user_limit(self, check_uid, uid_list):
        """检测用户是否用有权限"""
        if isinstance(uid_list, (int, str)):
            uid_list = [uid_list]

        _uid_list = [int(_u) for _u in uid_list] + self.bot.admin
        return int(check_uid) in _uid_list

    @staticmethod
    def format_canvas(image: Image, size=IMAGE_SIZE):
        width, height = image.size
        # 取长宽最小的边
        small_size = min(width, height) or 1
        # 计算和size的占比
        rate = size / small_size
        # 等比例调正图像大小
        new_width, new_height = int(width * rate), int(height * rate)
        # 等比例调正图像大小
        image = image.resize((new_width, new_height))

        # 从中心裁剪为输出大小
        # 计算裁剪的边界
        left = (new_width - size) // 2
        upper = (new_height - size) // 2
        right = left + size
        lower = upper + size
        # 裁剪图像
        image = image.crop((left, upper, right, lower))

        # 创建一个内存文件对象
        temp_file = io.BytesIO()
        # 将图像以指定格式保存到内存文件对象中
        image.save(temp_file, format='jpeg')
        # 将内存文件对象的内容作为新的Image对象打开
        return Image.open(temp_file)

    async def download(self, _file, _path, _type):
        """
            图片文件存储
        """
        _file.save(_path, _type)

    async def game_logs(self, path, msg, user, dt, file):
        """生成日志文件"""
        _path = '%s/%s' % (path, 'logs.csv')
        _row = ('datetime', 'user_id', 'message', 'file_name')

        # 文件路径
        file_path = '%s/%s' % (path, 'logs.csv')
        # 写入模式：如果文件存在则追加写入，否则创建新文件并写入
        mode = 'a' if os.path.exists(file_path) else 'w'

        # 打开 CSV 文件，使用指定的写入模式
        with open(file_path, mode, encoding='utf-8', newline='') as f:
            writer = csv.writer(f)

            # 如果是新文件，则写入表头
            if mode == 'w':
                writer.writerow(_row)

            # 写入数据
            writer.writerow([dt, user, msg, file])
