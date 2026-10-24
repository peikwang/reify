from __future__ import annotations

import pytest

from server.templates.games import detect_genre
from server.templates.library import classify, defaults, html_checks, render_html

BRIEF = {
    "title": "测试游戏",
    "tagline": "一个用于测试的小游戏。",
    "paragraph": "打开就能玩，支持键盘和触控。",
    "highlights": ["键盘", "触控", "计分", "最高分"],
    "accent": "#b8ff5a",
}


@pytest.mark.parametrize(
    ("prompt", "genre"),
    [
        ("做一个霓虹风格的贪吃蛇小游戏", "snake"),
        ("做一个俄罗斯方块小游戏", "tetris"),
        ("做一个飞机大战射击游戏", "shooter"),
        ("做一个打砖块小游戏", "breakout"),
        ("做一个弹球游戏", "breakout"),
        ("做一个小游戏", "snake"),
    ],
)
def test_detect_genre(prompt: str, genre: str):
    assert detect_genre(prompt) == genre


@pytest.mark.parametrize(
    ("prompt", "title"),
    [
        ("做一个贪吃蛇小游戏", "霓虹贪吃蛇"),
        ("做一个俄罗斯方块小游戏", "俄罗斯方块"),
        ("做一个飞机大战小游戏", "星际航线"),
        ("做一个打砖块小游戏", "打砖块"),
    ],
)
def test_genre_defaults(prompt: str, title: str):
    assert defaults("game", prompt)["title"] == title


@pytest.mark.parametrize(
    ("prompt", "marker"),
    [
        ("做一个贪吃蛇小游戏", "vibeforge-snake-best"),
        ("做一个俄罗斯方块小游戏", "vibeforge-tetris-best"),
        ("做一个飞机大战小游戏", "vibeforge-shooter-best"),
        ("做一个打砖块小游戏", "vibeforge-breakout-best"),
    ],
)
def test_each_genre_renders_a_self_contained_game(prompt: str, marker: str):
    html = render_html("game", BRIEF, prompt)
    assert '<canvas id="game"' in html
    assert marker in html
    assert "<script src=" not in html
    checks = html_checks(html, "game")
    assert all(ok for _, ok, _ in checks), checks


@pytest.mark.parametrize(
    "prompt",
    [
        "做一个俄罗斯方块",
        "做一个打砖块",
        "做一个飞机大战射击小游戏",
    ],
)
def test_other_game_prompts_classify_as_game(prompt: str):
    assert classify(prompt) == "game"
