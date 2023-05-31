import time
import re
import random
import copy
import sys
from PIL import Image, ImageDraw, ImageFont

from pycqBot import cqBot, cqHttpApi, Plugin, Message
from pycqBot.cqCode import image
from plugin.games import games

# 图片默认存储类型
IMAGE_TYPE = 'JPEG'
# 插件路径
LOCAL_PATH = sys.path[0].replace('\\', '/')
# 横轴
HORIZONTAL = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O']
# 纵轴
VERTICAL = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15']
# 横轴映射
HORIZONTAL_MAPPING = {_k: _i for _i, _k in enumerate(HORIZONTAL)}
# 纵轴映射
VERTICAL_MAPPING = {_k: _i for _i, _k in enumerate(VERTICAL)}

# 先手颜色 - 黑
FIRST_COLOR = (0, 0, 0)
# 后手颜色 - 白
SECOND_COLOR = (255, 255, 255)


class GoBang:

    def __init__(self, game: games, message: Message, canvas: Image or None = None):
        self.game = game
        self.message = message
        self.bot = game.bot

        self.gid = message.sender.group_id
        self.name = '五子棋'
        # 人数
        self.nums = 2
        # 玩家信息
        self.player_dict = {}
        # 轮序表
        self.active_list = []
        # 游戏拥有者
        self.owner = str(self.message.sender.id)

        # 棋盘
        self.canvas = canvas if canvas else game.select_canvas()
        # 画图对象
        self.draw = ImageDraw.Draw(self.canvas)
        # 棋盘大小 15 * 15
        self.size = 15
        # 明细表
        self.detailed_dict = {0: [[None for _ in range(15)] for _ in range(15)]}
        # 明细
        self.detailed = self.detailed_dict[0]

        # 日志路径
        self.path = ''

        self._gobang()

    def _gobang(self):
        # 启用群消息监听
        self.game.group_msg_context(self.gid, self.name)

        # 匹配玩家
        players_info = self.game.matching_players(self.message, self.name, self.nums)
        if players_info is None:
            return None
        host, (player,), timestamp = players_info

        # 玩家信息
        self.player_dict = dict((host, player))
        self.active_list = list(self.player_dict.keys())

        # 开始游戏
        self.start(host, player, timestamp)

        # 结束游戏 发送gif记录
        self.send_details(before_msg='>>>本局精彩回顾<<<')

    def start(self, _host, _player, _dt):
        """开始游戏"""
        # 轮序表 随机顺序
        random.shuffle(self.active_list)

        # 开局宣言
        back_msg = '\n先手(黑)："%s"选手！ \n后手(白)："%s"选手！' \
                   % (self.player_dict[self.active_list[-1]], self.player_dict[self.active_list[0]])
        # 届, 日志路径
        season, self.path = self.game.start_manifesto(self.gid, self.name, _dt, _host, [_player], back_msg)

        # 准备棋盘
        self.prepare_canvas(season)

        # 开始游戏
        winner = self._start()

        if winner is None:
            end_msg = '天尊之间的大战，直到到最后也没有分出胜负，对局结束！'
        else:
            end_msg = '"%s"使出了决胜的一击，对局结束！' % self.player_dict.get(winner)
        # 结束宣言
        self.game.send_group_msg(self.gid, end_msg)

    def _start(self):
        # 设置开始时间
        _, dt, _ = self.bot.group_msg_context.last(self.gid)
        # 轮次
        _turn = 1
        # 发送棋谱
        self.send_image()
        # 写入日志
        self.game_logs('创建游戏', self.owner, dt, 0)

        while True:
            context = self.bot.group_msg_context.get(self.gid, dt)
            # todo
            # context = [('1074545686', dt + 10, 'A1')]
            for user, dt, msg in context:
                # 后手0 先手1
                _who = _turn % self.nums

                if msg == '掀桌' and self.game.check_user_limit(user, []):
                    self.game.send_group_msg(self.gid, '有内鬼，终止交易！"bot的管理员"把牌桌给扬了！')
                    self.active_list = []
                    return None

                if user not in self.active_list:
                    continue

                # 校验指令
                _command = self.command_format(user, msg, _who, _turn)

                if _command is None:
                    continue

                # 写入日志
                self.game_logs(_command, user, dt, _turn)

                if isinstance(_command, str):
                    return self.active_list and self.active_list[0] or None

                # 执行指令
                _new_turn = self.command_exec(_command, _who, _turn)

                if _new_turn is None:
                    continue

                if _new_turn == _turn and isinstance(_command, tuple):
                    # 检测对局
                    winner = self.check_detailed(_command, _who)
                    if winner is not None:
                        return winner

                _turn = _new_turn + 1
                # 超出轮次 平局
                if _turn > 15 * 15:
                    return None

            time.sleep(self.game.sleep_time)

    def prepare_canvas(self, _season):
        """准备棋盘"""
        # 创建一个绘图对象
        _draw = self.draw
        # 指定字体
        _font = ImageFont.truetype('arial.ttf', 18)
        # 边长
        _side = self.canvas.size[0]
        # 宫格分布 15 * 15
        _split = 14
        # 间距 = 宫格 15 + 上下边距 2
        _margin = _side / (_split + 2)
        # 黑点大小 半径0.15间距
        _point = _margin * 0.15

        # 绘制田字格
        for _i in range(_split + 2):
            if _i == 0:
                continue

            # 横轴（左-右+）
            _draw.text((_margin * (0.85 + _i - 1), _side * 0.94),
                       HORIZONTAL[_i - 1], font=_font, fill=(0, 0, 0))
            # # 纵轴（上+下-）
            _draw.text((_margin * 0.35, _margin * (0.65 + _split + 2 - _i - 1)),
                       VERTICAL[_i - 1], font=_font, fill=(0, 0, 0))

            _x = _y = _i * _margin
            # 绘制垂直线
            _draw.line([(_x, _side - _margin), (_x, _margin)], fill='black')
            # 绘制水平线
            _draw.line([(_side - _margin, _y), (_margin, _y)], fill='black')

        # 创建棋盘黑点
        for _x, _y in [(4, 4), (4, 12), (8, 8), (12, 4), (12, 12)]:
            x1, y1 = _x * _margin - _point, _y * _margin - _point
            x2, y2 = _x * _margin + _point, _y * _margin + _point
            _draw.ellipse([(x1, y1), (x2, y2)],
                          fill=(0, 0, 0), outline=(0, 0, 0))

    def check_detailed(self, _command, _who):
        """分析棋谱"""
        _detailed = self.detailed
        _len = len(_detailed)
        # 坐标
        _x, _y = _command

        # 以_x, _y为中心，半径为4的正方形
        x_start, x_end = _x - 4, _x + 4 + 1
        y_start, y_end = _y - 4, _y + 4 + 1
        if _x < 4:
            x_start = 0
        elif _x > 10:
            x_end = _len
        if _y < 4:
            y_start = 0
        elif _y > 10:
            y_end = _len

        if _who != _detailed[_y][_x] or _detailed[_y][_x] is False:
            # 异常
            return None

        def func_xx():
            """检查水平方向"""
            return _detailed[_y][x_start:x_end]

        def func_yy():
            """检查垂直方向"""
            return (cells[_x] for cells in _detailed[y_start:y_end])

        def func_xy():
            """检查正斜线方向"""
            for __y in range(y_start, y_end):
                __x = _x - (_y - __y)
                if __x < 0 or __x > 14:
                    continue
                yield _detailed[__y][__x]

        def func_yx():
            """检查反斜线方向"""
            for __y in range(y_start, y_end):
                __x = _x + (_y - __y)
                if __x < 0 or __x > 14:
                    continue
                yield _detailed[__y][__x]

        for func in [func_xx, func_yy, func_xy, func_yx]:
            str_detailed = ''.join('_' if _info is False else str(_info) for _info in func())
            if str(_who) * 5 in str_detailed:
                return self.active_list[_who]

        return None

    def command_format(self, _user, _command, _who, _turn):
        """读取指令"""

        def find_user(user_list, user):
            # 寻找用户下标
            for _i, _u in enumerate(user_list):
                if _u == user:
                    return _i

        # 投降
        if _command in ['认输', '投降', '我输了', '你赢了', '寄了', '法国军礼']:
            user_index = find_user(self.active_list, _user)
            self.active_list.pop(user_index)
            return '投降'

        # 悔棋
        if _command in ['悔棋', '撤回', '下错了']:
            self.game.send_group_msg(self.gid, '要记住，落子无悔哦！')

            new_turn = _turn - self.nums
            if _user == self.active_list[_who]:
                new_turn -= 1
            return new_turn

        # 结束对局
        if _command in ['结束对局', '不玩了', '掀桌']:
            self.game.send_group_msg(self.gid, '"%s"把牌桌给扬了！' % self.player_dict[_user])
            self.active_list = []
            return '掀桌'

        # 读取坐标指令(仅当前轮次用户)
        if _user != self.active_list[_who]:
            return None

        numbers = re.findall(r'\d+', _command)
        letters = re.findall(r'[a-zA-Z]+', _command)
        if len(numbers) == 1 and len(letters) == 1:
            x, y = letters[0].upper(), numbers[0]
            _x, _y = HORIZONTAL_MAPPING.get(x, None), VERTICAL_MAPPING.get(y, None)

            if _x is not None and _y is not None:
                # 指令计入明细
                if self.detailed[_y][_x] is None:
                    return _x, _y
            self.game.send_group_msg(self.gid, '坐标(%s, %s)无法落子！' % (x, y))

        return None

    def command_exec(self, _command, _who, _turn):
        # 覆盖写入棋谱
        is_reload = True
        if isinstance(_command, tuple):
            # 下棋
            self.detailed = copy.deepcopy(self.detailed)
            _y, _x = _command
            self.detailed[_x][_y] = _who

            # 记录棋谱
            self.detailed_dict[_turn] = self.detailed

            # 绘制棋谱
            self.command_draw(_command, _who, _turn)
            new_turn = _turn
        elif isinstance(_command, int):
            # 悔棋 轮次-1轮
            new_turn = _command

            if _command < 0:
                self.game.send_group_msg(self.gid, '你当前没有棋可以反悔！')
                return _turn
            else:
                self.detailed = copy.deepcopy(self.detailed_dict[new_turn])
                self.canvas = Image.open('%s/%s.%s' % (self.path, self.format_file_name(new_turn), IMAGE_TYPE))
                self.draw = ImageDraw.Draw(self.canvas)
                is_reload = False
        else:
            return _turn

        # 发送棋谱
        self.send_image(new_turn, is_reload)

        return new_turn

    def command_draw(self, _command, _who, _turn):
        """绘制指令"""
        # 创建一个绘图对象
        _draw = self.draw
        # 边长
        _side = self.canvas.size[0]
        # 宫格分布 15 * 15
        _split = 14
        # 间距 = 宫格 15 + 上下边距 2
        _margin = _side / (_split + 2)
        # 棋子半径
        _piece = _margin * 0.35

        # 坐标
        _x, _y = _command[0] + 1, _split + 2 - _command[1] - 1
        # 颜色 先1后0
        _color = FIRST_COLOR if _who else SECOND_COLOR

        # 落子
        x1, y1 = _x * _margin - _piece, _y * _margin - _piece
        x2, y2 = _x * _margin + _piece, _y * _margin + _piece
        _draw.ellipse([(x1, y1), (x2, y2)], fill=_color, outline=_color)

        # 写头信息
        # self.draw_msg(site=(_side * 0.5, 0), msg='%s' % _turn, color=_color)

    def draw_msg(self, site, msg, color):
        """写入信息"""
        # 创建一个绘图对象
        _draw = self.draw
        # 指定字体
        _font = ImageFont.truetype('arial.ttf', 20)
        _draw.text(site, msg, font=_font, fill=color)

    def send_details(self, before_msg='', after_msg=''):
        file_path = self.game.match_details(self.gid, self.name, self.path)
        # 发送文件

        self.game.send_group_msg(self.gid, '%s%s%s' % (before_msg,
                                                       image('file:///%s/%s' % (LOCAL_PATH, file_path)),
                                                       after_msg))

    def send_image(self, _turn=0, is_reload=True):
        if not self.path:
            return
        path = '%s/%s.%s' % (self.path, self.format_file_name(_turn), IMAGE_TYPE)

        if is_reload:
            file = copy.copy(self.canvas)
            # 永久储存
            self.game.cqapi.add_task(self.game.download(file, path, IMAGE_TYPE))

        # 发送文件
        self.game.send_group_msg(self.gid, image('file:///%s/%s' % (LOCAL_PATH, path)))

    @staticmethod
    def format_file_name(_turn):
        return '' if _turn is None else '{:0>3}'.format(_turn)

    def game_logs(self, _command, _user, _dt, _turn=None):
        """生成日志信息"""
        if isinstance(_command, int):
            _turn = None
            _command = '撤回'

        file_name = self.format_file_name(_turn)

        self.game.cqapi.add_task(self.game.game_logs(self.path, _command, _user, _dt, file_name))
