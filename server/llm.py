from __future__ import annotations

import html as html_lib
import json
import logging
import re
from typing import Any

import httpx

from .config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_ENABLED,
    LLM_LONGTAIL_DISABLE_THINKING,
    LLM_LONGTAIL_MAX_TOKENS,
    LLM_LONGTAIL_TIMEOUT,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_REFINE_MAX_TOKENS,
    LLM_TIMEOUT,
)

logger = logging.getLogger("reify.llm")


def enabled() -> bool:
    return bool(LLM_ENABLED and LLM_BASE_URL)


async def _resolve_model(client: httpx.AsyncClient) -> str:
    if LLM_MODEL:
        return LLM_MODEL
    try:
        response = await client.get(f"{LLM_BASE_URL}/models")
        response.raise_for_status()
        data = response.json().get("data") or []
        if data:
            return str(data[0].get("id", ""))
    except Exception as exc:  # noqa: BLE001 - model discovery is best effort
        logger.info("model discovery failed: %s", exc)
    return "local-model"


def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


async def design_brief(capability: str, prompt: str, defaults: dict[str, Any]) -> dict[str, Any]:
    if not enabled():
        return defaults
    system = (
        "你是 Reify 的创意导演。根据用户需求，输出一个 JSON 对象，不要 markdown，不要解释。"
        "字段：title(不超过18字)、tagline(不超过36字)、paragraph(不超过90字)、"
        "highlights(4条，每条不超过16字)、accent(十六进制色值)。中文表达，具体、克制、有画面感。"
    )
    payload = {
        "model": "",
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": f"能力类型：{capability}\n用户需求：{prompt}\n请给出创意方向。",
            },
        ],
        "temperature": 0.8,
        "max_tokens": LLM_MAX_TOKENS,
    }
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            payload["model"] = await _resolve_model(client)
            response = await client.post(
                f"{LLM_BASE_URL}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        brief = _extract_json(content)
        if not brief:
            return defaults
        merged = dict(defaults)
        for key in ("title", "tagline", "paragraph", "accent"):
            value = brief.get(key)
            if isinstance(value, str) and value.strip():
                merged[key] = value.strip()[:160]
        highlights = brief.get("highlights")
        if isinstance(highlights, list):
            cleaned = [str(item).strip()[:40] for item in highlights if str(item).strip()]
            if cleaned:
                merged["highlights"] = cleaned[:4]
        merged["source"] = "llm"
        return merged
    except Exception as exc:  # noqa: BLE001 - optional enhancement must not break the run
        logger.info("design brief fallback: %s", exc)
        return defaults


def _apply_patches(current_html: str, patches: list[Any]) -> tuple[str, list[str]] | None:
    updated = current_html
    notes: list[str] = []
    for patch in patches[:8]:
        if not isinstance(patch, dict):
            continue
        find = str(patch.get("find", ""))
        replace = str(patch.get("replace", ""))
        if not find or len(find) > 2000 or len(replace) > 20000:
            continue
        if updated.count(find) != 1:
            continue
        updated = updated.replace(find, replace, 1)
        note = str(patch.get("note", "")).strip()
        notes.append(note[:120] or "已应用局部修改")
    if updated == current_html or not notes:
        return None
    return updated, notes


async def refine_source(
    current_source: str, instruction: str, capability: str, language: str
) -> dict[str, Any] | None:
    if not enabled():
        return None
    system = (
        "你是 Reify 的源码编辑 Agent。用户要求在现有前端源码上做二次修改。"
        "只输出一个 JSON 对象，不要 markdown，不要解释。格式："
        '{"summary":"一句话说明改了什么","patches":[{"find":"当前源码中唯一且连续出现的原文","replace":"替换后的内容","note":"简短说明"}]}。'
        f"当前文件是 {language}。规则：find 必须从当前源码原样复制且唯一出现；优先最小修改；"
        "保留现有组件结构、样式类名、服务端接口和导入；不要引入新依赖或外部链接；1-6 个 patches。"
    )
    user = (
        f"能力类型：{capability}\n当前源码：\n{current_source}\n\n"
        f"用户的修改要求：{instruction}\n只输出 JSON。"
    )
    payload = {
        "model": "",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.35,
        "max_tokens": LLM_REFINE_MAX_TOKENS,
    }
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            payload["model"] = await _resolve_model(client)
            response = await client.post(
                f"{LLM_BASE_URL}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
            message = response.json()["choices"][0]["message"]
        content = message.get("content") or message.get("reasoning_content") or ""
        data = _extract_json(content)
        if not data:
            return None
        patches = data.get("patches")
        if not isinstance(patches, list):
            return None
        applied = _apply_patches(current_source, patches)
        if not applied:
            return None
        updated, notes = applied
        return {
            "source": updated,
            "summary": str(data.get("summary", "已根据你的要求完成修改"))[:200],
            "notes": notes,
        }
    except Exception as exc:  # noqa: BLE001 - failed refinement keeps old source
        logger.info("source refine fallback: %s", exc)
        return None


async def refine_html(current_html: str, instruction: str, capability: str) -> dict[str, Any] | None:
    """Edit an existing page through small, verifiable patches.

    A patch must point at a unique substring of the current document. This keeps
    the model from accidentally replacing the whole page and gives the agent a
    concrete, reviewable diff.
    """
    if not enabled():
        return None
    system = (
        "你是 Reify 的页面编辑 Agent。用户要求在现有页面上做二次修改。"
        "只输出一个 JSON 对象，不要 markdown，不要解释。格式："
        '{"summary":"一句话说明改了什么","patches":[{"find":"当前HTML中唯一且连续出现的原文","replace":"替换后的内容","note":"简短说明"}]}。'
        "规则：find 必须从当前 HTML 原样复制，必须唯一出现，不要使用省略号；优先最小修改；"
        "保留现有页面结构、响应式、脚本和视觉语言；不要引入外部依赖或外链图片；1-6 个 patches。"
    )
    user = (
        f"能力类型：{capability}\n当前页面 HTML：\n{current_html}\n\n"
        f"用户的修改要求：{instruction}\n只输出 JSON。"
    )
    payload = {
        "model": "",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.35,
        "max_tokens": LLM_REFINE_MAX_TOKENS,
    }
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            payload["model"] = await _resolve_model(client)
            response = await client.post(
                f"{LLM_BASE_URL}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
            message = response.json()["choices"][0]["message"]
        content = message.get("content") or ""
        if not content.strip():
            content = message.get("reasoning_content") or ""
        data = _extract_json(content)
        if not data:
            logger.info("refine returned no json")
            return None
        summary = str(data.get("summary", "已根据你的要求完成修改"))[:200]
        html_value = data.get("html")
        if isinstance(html_value, str) and "<html" in html_value and len(html_value) > 1200:
            return {"html": html_value, "summary": summary, "notes": ["整页重写"]}
        patches = data.get("patches")
        if not isinstance(patches, list):
            return None
        applied = _apply_patches(current_html, patches)
        if not applied:
            logger.info("refine patches did not match any unique anchor")
            return None
        updated, notes = applied
        return {"html": updated, "summary": summary, "notes": notes}
    except Exception as exc:  # noqa: BLE001 - surface as a failed refinement, keep old page
        logger.info("refine fallback: %s", exc)
        return None


def _clean_document(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:html)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    if "&lt;" in text and "<html" not in text.lower():
        text = html_lib.unescape(text)
    if text.lstrip().startswith("{"):
        wrapped = _extract_json(text)
        if wrapped and isinstance(wrapped.get("html"), str):
            text = str(wrapped["html"])
    lowered = text.lower()
    start = lowered.find("<!doctype")
    if start < 0:
        start = lowered.find("<html")
    end = lowered.rfind("</html>")
    if start < 0 or end < start:
        return ""
    return text[start : end + len("</html>")]


def _message_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "".join(
            str(part.get("text", "")) if isinstance(part, dict) else str(part)
            for part in content
        )
    else:
        text = ""
    if not text.strip():
        text = str(message.get("reasoning_content") or "")
    return text


async def generate_game_page(
    spec: dict[str, Any], prompt: str, feedback: str = ""
) -> str | None:
    """Generate a complete single-file canvas game for an unknown genre."""
    if not enabled():
        return None
    system = (
        "你是 Reify 的独立游戏工程师。根据规格，输出一个完整可运行的单文件 HTML5 游戏。"
        "只输出 HTML 文档本身，不要 markdown 代码围栏，不要解释。"
        "硬性要求：所有 CSS 和 JavaScript 内联；使用 <canvas> 渲染核心玩法；"
        "包含开始、暂停、失败、重新开始；显示分数或进度；同时支持键盘和触控；"
        "适配手机宽度；不加载任何外部脚本、字体、图片，不发起任何网络请求；"
        "不要使用省略号、TODO 或占位代码。"
    )
    user = (
        "游戏规格：\n"
        + json.dumps(spec, ensure_ascii=False, indent=2)
        + f"\n\n用户需求：{prompt}\n"
    )
    if feedback:
        user += (
            "\n上一次输出未通过自检，问题如下，请完整重写并修复：\n"
            + feedback
            + "\n"
        )
    payload = {
        "model": "",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.65,
        "max_tokens": LLM_LONGTAIL_MAX_TOKENS,
    }
    if LLM_LONGTAIL_DISABLE_THINKING:
        payload["enable_thinking"] = False
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    try:
        async with httpx.AsyncClient(timeout=LLM_LONGTAIL_TIMEOUT) as client:
            payload["model"] = await _resolve_model(client)
            response = await client.post(
                f"{LLM_BASE_URL}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
            choice = response.json()["choices"][0]
            message = choice.get("message") or {}
        text = _message_text(message)
        document = _clean_document(text)
        logger.info(
            "game generation finish=%s content_len=%s reasoning_len=%s usage=%s document=%s",
            choice.get("finish_reason"),
            len(str(message.get("content") or "")),
            len(str(message.get("reasoning_content") or "")),
            response.json().get("usage"),
            len(document),
        )
        if not document:
            logger.info("game generation returned no html document head=%r", text[:160])
            return None
        return document
    except Exception as exc:  # noqa: BLE001 - fallback to a built-in engine
        logger.info("game generation fallback: %s", exc)
        return None


async def _chat_completion(
    system: str,
    user: str,
    *,
    max_tokens: int,
    timeout: float,
    temperature: float = 0.65,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    if not enabled():
        return None
    payload = {
        "model": "",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if LLM_LONGTAIL_DISABLE_THINKING:
        payload["enable_thinking"] = False
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            payload["model"] = await _resolve_model(client)
            response = await client.post(
                f"{LLM_BASE_URL}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
            data = response.json()
            choice = data["choices"][0]
            message = choice.get("message") or {}
        return message, choice, data.get("usage") or {}
    except Exception as exc:  # noqa: BLE001 - fall back to built-in templates
        logger.info("longtail completion fallback: %s", exc)
        return None


async def generate_longtail_page(
    capability: str, spec: dict[str, Any], prompt: str, feedback: str = ""
) -> str | None:
    from .templates.longtail import system_prompt

    user = (
        f"能力类型：{capability}\n规格：\n"
        + json.dumps(spec, ensure_ascii=False, indent=2)
        + f"\n\n用户需求：{prompt}\n"
    )
    if feedback:
        user += "\n上一次输出未通过自检，请完整重写并修复：\n" + feedback + "\n"
    result = await _chat_completion(
        system_prompt(capability), user, max_tokens=LLM_LONGTAIL_MAX_TOKENS, timeout=LLM_LONGTAIL_TIMEOUT
    )
    if not result:
        return None
    message, choice, usage = result
    text = _message_text(message)
    document = _clean_document(text)
    logger.info(
        "longtail page capability=%s finish=%s content_len=%s reasoning_len=%s usage=%s document=%s",
        capability,
        choice.get("finish_reason"),
        len(str(message.get("content") or "")),
        len(str(message.get("reasoning_content") or "")),
        usage,
        len(document),
    )
    if not document:
        logger.info("longtail page returned no html head=%r", text[:160])
        return None
    return document


async def generate_longtail_code(
    spec: dict[str, Any], prompt: str, feedback: str = ""
) -> dict[str, Any] | None:
    system = (
        "你是 Reify 的单文件交付工程师。根据规格生成一个 Python 算法实现和一个可交互可视化页面。"
        "只输出一个 JSON 对象：{summary, python, html}。python 是完整可编译的 Python 代码；"
        "html 是完整单文件 HTML 页面，内联 CSS/JS，展示代码、步骤和结果，适配手机，不加载外部资源、"
        "不发起网络请求，不使用省略号或占位代码。不要输出 markdown，不要解释。"
    )
    user = (
        "规格：\n"
        + json.dumps(spec, ensure_ascii=False, indent=2)
        + f"\n\n用户需求：{prompt}\n"
    )
    if feedback:
        user += "\n上一次输出未通过自检，请完整重写并修复：\n" + feedback + "\n"
    result = await _chat_completion(
        system, user, max_tokens=LLM_LONGTAIL_MAX_TOKENS, timeout=LLM_LONGTAIL_TIMEOUT
    )
    if not result:
        return None
    message, choice, usage = result
    text = _message_text(message)
    data = _extract_json(text)
    logger.info(
        "longtail code finish=%s content_len=%s reasoning_len=%s usage=%s json=%s",
        choice.get("finish_reason"),
        len(str(message.get("content") or "")),
        len(str(message.get("reasoning_content") or "")),
        usage,
        bool(data),
    )
    if not data:
        return None
    python = data.get("python")
    html = data.get("html")
    if not isinstance(python, str) or not isinstance(html, str):
        return None
    html = _clean_document(html)
    if not python.strip() or not html:
        return None
    return {
        "summary": str(data.get("summary") or "已生成算法与可视化页面"),
        "python": python,
        "html": html,
    }
