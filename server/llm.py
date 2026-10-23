from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from .config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_ENABLED,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_REFINE_MAX_TOKENS,
    LLM_TIMEOUT,
)

logger = logging.getLogger("vibeforge.llm")


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
        "你是 VibeForge 的创意导演。根据用户需求，输出一个 JSON 对象，不要 markdown，不要解释。"
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
        "你是 VibeForge 的源码编辑 Agent。用户要求在现有前端源码上做二次修改。"
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
        "你是 VibeForge 的页面编辑 Agent。用户要求在现有页面上做二次修改。"
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
