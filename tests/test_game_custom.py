from __future__ import annotations

import asyncio

import pytest

from server.templates.games import detect_genre
from server.templates.games import custom
from server.templates.games.spec import build_spec
from server.templates.library import classify, defaults, render_html

BRIEF = {
    "title": "2048",
    "tagline": "合并数字，别让棋盘满掉。",
    "paragraph": "一个根据用户描述生成的数字合并游戏。",
    "highlights": ["方向键", "触控", "计分", "重开"],
    "accent": "#f4b860",
}


def _valid_game() -> str:
    padding = "/*" + ("canvas-layout " * 320) + "*/"
    return (
        "<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"UTF-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
        "<title>2048</title><style>" + padding + "</style></head><body>"
        "<canvas id=\"game\" width=\"480\" height=\"480\"></canvas>"
        "<script>"
        "const canvas=document.getElementById('game');"
        "const ctx=canvas.getContext('2d');"
        "let score=0;"
        "function draw(){ctx.clearRect(0,0,480,480);ctx.fillText(String(score),20,20);}"
        "function loop(){draw();requestAnimationFrame(loop);}"
        "document.addEventListener('keydown',()=>{score+=1;});"
        "canvas.addEventListener('touchstart',()=>{score+=1;});"
        "loop();"
        "</script></body></html>"
    )


def test_unknown_game_uses_custom_spec():
    assert detect_genre("做一个 2048 数字合并小游戏") == "custom"
    assert classify("做一个 2048 数字合并小游戏") == "game"
    assert defaults("game", "做一个 2048 数字合并小游戏")["title"] == "长尾小游戏"
    spec = build_spec(BRIEF, "做一个 2048 数字合并小游戏")
    assert spec.genre == "custom"
    assert spec.title == "2048"
    assert any("canvas" in item.lower() for item in spec.constraints)
    assert any("触控" in item for item in spec.controls)


def test_validator_accepts_a_self_contained_game():
    assert custom.validate_game_html(_valid_game()) == []


def test_validator_rejects_external_and_network_code():
    external = _valid_game().replace("</head>", '<script src="https://cdn.example/game.js"></script></head>')
    problems = custom.validate_game_html(external)
    assert any("外部资源" in item for item in problems)

    networked = _valid_game().replace("loop();", "fetch('https://example.test');loop();")
    problems = custom.validate_game_html(networked)
    assert any("网络请求" in item for item in problems)


def test_validator_rejects_incomplete_documents():
    problems = custom.validate_game_html("<html><body>not a game</body></html>")
    assert any("<canvas>" in item for item in problems)
    assert any("脚本" in item for item in problems)
    assert any("过短" in item for item in problems)


def test_custom_render_stamps_and_returns_llm_game(monkeypatch):
    calls = []

    async def fake_generate(spec, prompt, feedback=""):
        calls.append((spec, prompt, feedback))
        return _valid_game()

    monkeypatch.setattr(custom, "llm_enabled", lambda: True)
    monkeypatch.setattr(custom, "generate_game_page", fake_generate)
    html = asyncio.run(custom.render(BRIEF, "做一个 2048 数字合并小游戏"))
    assert html is not None
    assert '<meta name="reify-game" content="custom">' in html
    assert len(calls) == 1
    assert calls[0][0]["genre"] == "custom"


def test_custom_render_repairs_once(monkeypatch):
    responses = iter(["<html><body>broken</body></html>", _valid_game()])
    calls = []

    async def fake_generate(spec, prompt, feedback=""):
        calls.append(feedback)
        return next(responses)

    monkeypatch.setattr(custom, "llm_enabled", lambda: True)
    monkeypatch.setattr(custom, "generate_game_page", fake_generate)
    html = asyncio.run(custom.render(BRIEF, "做一个 2048 数字合并小游戏"))
    assert html is not None
    assert len(calls) == 2
    assert "canvas" in calls[1]


def test_custom_render_falls_back_when_llm_is_unavailable(monkeypatch):
    monkeypatch.setattr(custom, "llm_enabled", lambda: False)
    assert asyncio.run(custom.render(BRIEF, "做一个 2048 数字合并小游戏")) is None

    html = render_html("game", BRIEF, "做一个 2048 数字合并小游戏")
    assert "reify-snake-best" in html
    assert "<canvas" in html


@pytest.mark.parametrize("prompt", ["做一个数独游戏", "做一个五子棋小游戏", "做一个跑酷游戏"])
def test_more_long_tail_game_prompts_classify_as_game(prompt: str):
    assert classify(prompt) == "game"
    assert detect_genre(prompt) == "custom"
