from threading import Thread
import logging
import time
import datetime
import os
import re
import io
import random
import asyncio
import copy
import base64
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


class GoBang:

    def __init__(self, game: games, message: Message):
        self.game = game
        self.message = message
        self.bot = game.bot
        self.name = '五子棋'
        # 人数
        self.nums = 2
        # 玩家
        self.player_dict = {}
        self.gid = message.sender.group_id
        # 棋盘
        self.canvas = game.select_canvas()
        # 画图对象
        self.draw = ImageDraw.Draw(self.canvas)
        # 棋盘大小 15 * 15
        self.size = 15
        # 明细
        self.detailed = [[None for _ in range(15)] for _ in range(15)]

        # 日志路径
        self.path = ''

        self._gobang()

    def _gobang(self):
        # 启用群消息监听
        self.game.group_msg_context(self.gid, self.name)

        # 匹配玩家
        res = self.game.matching_players(self.message, self.name, self.nums)
        if res is None:
            return res
        host, (player,), timestamp = res

        self.player_dict = dict((host, player))

        # 开始游戏
        self.start(host, player, timestamp)

        # 结束游戏 发送gif记录
        self.send_details()

    def start(self, _host, _player, _dt):
        """开始游戏"""
        # 轮序表
        active_list = list(self.player_dict.keys())

        # 开局宣言
        back_msg = '\n先手(黑)："%s"选手，后手(白)："%s"选手' % (self.player_dict.get(active_list[1]),
                                                    self.player_dict.get(active_list[0]))
        # 届, 日志路径
        season, self.path = self.game.start_manifesto(self.gid, self.name, _dt, _host, [_player], back_msg)

        # 准备棋盘
        self.prepare_canvas(season)

        # 开始游戏
        winner = self._start(active_list)

        if winner is None:
            end_msg = '天尊之间的大战，直到到最后也没有分出胜负，对局结束！'
        else:
            end_msg = '"%s"使出了决胜的一击，对局结束！' % self.player_dict.get(winner)
        # 结束宣言
        self.game.send_group_msg(self.gid, end_msg)

    def _start(self, _active):
        # 设置开始时间
        _, dt, _ = self.bot.group_msg_context.last(self.gid)
        # 轮次
        _turn = 1
        # 发送棋谱
        self.send_image()

        while True:
            context = self.bot.group_msg_context.get(self.gid, dt)
            for user, dt, msg in context:
                # 后手0 先手1
                if msg in ['认输', '投降'] and user in _active:
                    return list(set(_active) - {user})[0]

                _who = _turn % self.nums
                if user != _active[_who]:
                    continue

                # 校验指令
                _command = self.command_format(msg, _who)
                if not _command:
                    continue

                # 绘制指令
                self.command_draw(_command, _who, _turn)

                # 发送棋谱
                self.send_image(_turn)

                # 检测对局
                winner = self.check_detailed(_command, _who)
                if winner is not None:
                    return _active[winner]

                _turn += 1

                # 超出轮次 平局
                if _turn > 15 * 15:
                    return None

            time.sleep(1)

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
        __x_start, __x_end = _x - 4, _x + 4 + 1
        __y_start, __y_end = _y - 4, _y + 4 + 1
        if _x < 4:
            __x_start = 0
        elif _x > 10:
            __x_end = _len
        if _y < 4:
            __y_start = 0
        elif _y > 10:
            __y_end = _len

        if _who != _detailed[_y][_x] or _detailed[_y][_x] is False:
            # 异常
            return None

        def func_xx():
            """检查水平方向"""
            return _detailed[_y][__x_start:__x_end]

        def func_yy():
            """检查垂直方向"""
            return (cells[_x] for cells in _detailed[__y_start:__y_end])

        def func_xy():
            """检查正斜线方向"""
            return (cells[__x_start + __i] for __i, cells in enumerate(_detailed[__y_start:__y_end]))

        def func_yx():
            """检查反斜线方向"""
            for __y in range(__y_start, __y_end):
                __x = _y - __y + _x
                if __x < 0 or __x > 14:
                    continue
                yield _detailed[__y][__x]

        for func in [func_xx, func_yy, func_xy, func_yx]:
            str_detailed = ''.join('_' if x is False else str(x) for x in func())
            if str(_who) * 5 in str_detailed:
                return _who

        return None

    def command_format(self, _command, _who):
        """读取指令"""
        # 使用正则表达式匹配数字
        numbers = re.findall(r'\d+', _command)
        letters = re.findall(r'[a-zA-Z]+', _command)

        if len(numbers) == 1 and len(letters) == 1:
            x, y = letters[0].upper(), numbers[0]
            _x, _y = HORIZONTAL_MAPPING.get(x, None), VERTICAL_MAPPING.get(y, None)

            if _x is not None and _y is not None:
                # 指令计入明细
                if self.detailed[_y][_x] is None:
                    self.detailed[_y][_x] = _who
                    return _x, _y
            self.game.send_group_msg(self.gid, '坐标(%s, %s)无法落子！' % (x, y))

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
        # 颜色 先黑后红
        _color = (0, 0, 0) if _who else (255, 0, 0)

        # 落子
        x1, y1 = _x * _margin - _piece, _y * _margin - _piece
        x2, y2 = _x * _margin + _piece, _y * _margin + _piece
        _draw.ellipse([(x1, y1), (x2, y2)], fill=_color, outline=_color)

        # 写头信息
        self.draw_msg(site=(_side * 0.5, 0), msg='%s' % _turn, color=_color)

    def draw_msg(self, site, msg, color):
        """写入信息"""
        # 创建一个绘图对象
        _draw = self.draw
        # 指定字体
        _font = ImageFont.truetype('arial.ttf', 20)
        _draw.text(site, msg, font=_font, fill=color)

    def send_details(self):
        file_path = self.game.match_details(self.gid, self.name, self.path)
        # 发送文件
        self.game.send_group_msg(self.gid, image('file:///%s/%s' % (LOCAL_PATH, file_path)))

    def send_image(self, _turn=0):
        if not self.path:
            return
        path = '%s/%s.%s' % (self.path, '{:0>3}'.format(_turn), IMAGE_TYPE)
        file = copy.copy(self.canvas)

        # 永久储存
        self.game.cqapi.add_task(self.game.download(file, path, IMAGE_TYPE))

        # 发送文件
        self.game.send_group_msg(self.gid, image('file:///%s/%s' % (LOCAL_PATH, path)))
