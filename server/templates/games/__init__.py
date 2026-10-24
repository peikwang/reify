from __future__ import annotations

from typing import Any, Callable

from . import breakout, shooter, snake, tetris

GENRES = ("snake", "tetris", "shooter", "breakout")

DEFAULTS: dict[str, dict[str, Any]] = {
    "snake": {
        "title": "霓虹贪吃蛇",
        "tagline": "在霓虹网格里收集能量，别撞上自己的轨迹。",
        "paragraph": "一个足够小、足够快的浏览器街机，打开就能玩。",
        "highlights": ["键盘 / 触控双操作", "连击加速", "本地最高分", "零依赖单文件"],
        "accent": "#b8ff5a",
    },
    "tetris": {
        "title": "俄罗斯方块",
        "tagline": "把每一块，放进该在的位置。",
        "paragraph": "一个足够小、足够快的方块消除街机，消行、升级、再来一局。",
        "highlights": ["七种方块", "消行升级", "触控操作", "本地最高分"],
        "accent": "#8b9dff",
    },
    "shooter": {
        "title": "星际航线",
        "tagline": "在弹幕里，找到一条缝。",
        "paragraph": "一个纵向卷轴射击街机，移动、开火、活下去。",
        "highlights": ["连续射击", "敌机波次", "生命值", "本地最高分"],
        "accent": "#ff8a65",
    },
    "breakout": {
        "title": "打砖块",
        "tagline": "让每一块砖，都消失。",
        "paragraph": "一个经典打砖块街机，接住弹球，清空屏幕。",
        "highlights": ["多行砖块", "挡板反弹", "关卡升级", "本地最高分"],
        "accent": "#5ee0ff",
    },
    "custom": {
        "title": "长尾小游戏",
        "tagline": "把你描述的玩法，做成一个真正能玩的页面。",
        "paragraph": "根据你的描述生成一个单文件 Canvas 街机，打开就能玩。",
        "highlights": ["自定义玩法", "键盘 / 触控", "计分与重开", "离线单文件"],
        "accent": "#b8ff5a",
    },
}

_TETRIS_WORDS = ("俄罗斯方块", "tetris", "方块消除", "方块消除游戏")
_SHOOTER_WORDS = ("飞机大战", "弹幕", "射击", "shooter", "space shooter", "飞机", "飞碟")
_BREAKOUT_WORDS = ("打砖块", "砖块", "breakout", "弹球", "brick")
_SNAKE_WORDS = ("贪吃蛇", "snake", "蛇")

RENDERERS: dict[str, Callable[[dict, str], str]] = {
    "snake": snake.render,
    "tetris": tetris.render,
    "shooter": shooter.render,
    "breakout": breakout.render,
}


def detect_genre(prompt: str) -> str:
    text = (prompt or "").lower()
    if any(word in text for word in _TETRIS_WORDS):
        return "tetris"
    if any(word in text for word in _SHOOTER_WORDS):
        return "shooter"
    if any(word in text for word in _BREAKOUT_WORDS):
        return "breakout"
    if any(word in text for word in _SNAKE_WORDS):
        return "snake"
    return "custom"


def defaults(prompt: str) -> dict[str, Any]:
    return dict(DEFAULTS[detect_genre(prompt)])


def render(brief: dict[str, Any], prompt: str = "") -> str:
    genre = detect_genre(prompt)
    renderer = RENDERERS.get(genre, snake.render)
    return renderer(brief, prompt)
