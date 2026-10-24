from __future__ import annotations

import logging
import re
from typing import Any

from .spec import build_spec

logger = logging.getLogger("reify.games")

_EXTERNAL_RESOURCE = re.compile(
    r"""(?:(?:src|href)\s*=\s*["']?\s*(?:https?:)?//|url\(\s*["']?https?://|@import\s+["']?https?://|import\s*\(\s*["']https?://)""",
    re.IGNORECASE,
)
_NETWORK_CALL = re.compile(
    r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon)\s*\(",
    re.IGNORECASE,
)
_MIN_BYTES = 3200


def llm_enabled() -> bool:
    from ...llm import enabled

    return enabled()


async def generate_game_page(
    spec: dict[str, Any], prompt: str, feedback: str = ""
) -> str | None:
    from ...llm import generate_game_page as generate

    return await generate(spec, prompt, feedback)


def validate_game_html(html: str) -> list[str]:
    problems: list[str] = []
    lowered = html.lower()
    if not lowered.lstrip().startswith("<!doctype html>"):
        problems.append("必须以 <!DOCTYPE html> 开头")
    if "</html>" not in lowered:
        problems.append("缺少 </html> 闭合标签")
    if "<title" not in lowered:
        problems.append("缺少 <title>")
    if 'name="viewport"' not in lowered:
        problems.append("缺少移动端 viewport")
    if "<canvas" not in lowered:
        problems.append("缺少 <canvas>")
    if "<script" not in lowered:
        problems.append("缺少内联脚本")
    if "addeventlistener" not in lowered and "onkeydown" not in lowered and "ontouchstart" not in lowered:
        problems.append("缺少键盘或触控输入")
    if "requestanimationframe" not in lowered and "setinterval" not in lowered:
        problems.append("缺少游戏循环")
    if len(html.encode("utf-8")) < _MIN_BYTES:
        problems.append(f"文档过短（至少 {_MIN_BYTES} 字节）")
    if re.search(r"\{\{[A-Za-z_][A-Za-z0-9_]*\}\}", html):
        problems.append("包含未渲染的模板占位符")
    if _EXTERNAL_RESOURCE.search(html):
        problems.append("引用了外部资源")
    if _NETWORK_CALL.search(html):
        problems.append("包含网络请求调用")
    return problems


def _stamp(html: str) -> str:
    tag = '<meta name="reify-game" content="custom">'
    if tag in html:
        return html
    head = re.search(r"<head[^>]*>", html, re.IGNORECASE)
    if head:
        index = head.end()
        return html[:index] + "\n" + tag + html[index:]
    return html


async def render(brief: dict[str, Any], prompt: str) -> str | None:
    if not llm_enabled():
        return None
    spec = build_spec(brief, prompt)
    feedback = ""
    for attempt in range(2):
        html = await generate_game_page(spec.as_dict(), prompt, feedback)
        if not html:
            feedback = (
                "上一次没有返回完整 HTML 文档。请直接输出从 <!DOCTYPE html> 开始、"
                "以 </html> 结束的完整单文件游戏，不要解释，也不要在 HTML 前后输出任何文字。"
            )
            continue
        problems = validate_game_html(html)
        if not problems:
            return _stamp(html)
        logger.info("custom game validation attempt %s: %s", attempt + 1, problems)
        feedback = "上一次输出未通过自检，请完整重写并修复：\n" + "\n".join(
            f"- {item}" for item in problems
        )
    logger.info("custom game generation fell back after two attempts")
    return None
