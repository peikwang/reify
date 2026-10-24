from __future__ import annotations

import asyncio
import logging
import mimetypes
import time
from typing import Any, Awaitable, Callable

import httpx

from .config import (
    IMAGE_COUNT,
    IMAGE_MODEL,
    LLM_API_KEY,
    LLM_BASE_URL,
    MEDIA_API_BASE,
    MEDIA_API_KEY,
    MEDIA_TIMEOUT,
    VIDEO_DURATION,
    VIDEO_MODEL,
    VIDEO_POLL_INTERVAL,
    VIDEO_RESOLUTION,
)

logger = logging.getLogger("reify.media")

ProgressCallback = Callable[[dict[str, Any]], Awaitable[None]]


class MediaError(Exception):
    pass


def api_root() -> str:
    return MEDIA_API_BASE or LLM_BASE_URL


def _headers(async_video: bool = False) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if MEDIA_API_KEY:
        headers["Authorization"] = f"Bearer {MEDIA_API_KEY}"
    if async_video:
        headers["X-DashScope-Async"] = "enable"
    return headers


def _error(data: dict[str, Any], status: int) -> str:
    error = data.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or f"HTTP {status}")[:500]
    return str(data.get("message") or data.get("code") or f"HTTP {status}")[:500]


async def generate_images(prompt: str, count: int = IMAGE_COUNT, size: str = "1024*1024") -> list[str]:
    url = f"{api_root()}/api/v1/services/aigc/multimodal-generation/generation"
    payload = {
        "model": IMAGE_MODEL,
        "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
        "parameters": {
            "size": size,
            "n": count,
            "prompt_extend": True,
            "watermark": False,
        },
    }
    async with httpx.AsyncClient(timeout=MEDIA_TIMEOUT, follow_redirects=True) as client:
        response = await client.post(url, json=payload, headers=_headers())
    try:
        data = response.json()
    except ValueError as exc:
        raise MediaError(f"图片接口返回非 JSON：{response.text[:200]}") from exc
    if response.status_code >= 400:
        raise MediaError("图片生成失败：" + _error(data, response.status_code))
    urls: list[str] = []
    for choice in (data.get("output") or {}).get("choices", []):
        for item in (choice.get("message") or {}).get("content", []):
            image_url = item.get("image")
            if image_url:
                urls.append(str(image_url))
    if not urls:
        raise MediaError("图片接口没有返回图片 URL")
    return urls[:count]


async def download_asset(url: str) -> tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=MEDIA_TIMEOUT, follow_redirects=True) as client:
        response = await client.get(url)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if not content_type or content_type == "application/octet-stream":
        content_type = mimetypes.guess_type(url.split("?", 1)[0])[0] or "application/octet-stream"
    if not response.content:
        raise MediaError("下载的媒体文件为空")
    return response.content, content_type


async def create_video(
    prompt: str,
    duration: int = VIDEO_DURATION,
    resolution: str = VIDEO_RESOLUTION,
) -> str:
    url = f"{api_root()}/api/v1/services/aigc/video-generation/video-synthesis"
    payload = {
        "model": VIDEO_MODEL,
        "input": {"prompt": prompt},
        "parameters": {
            "resolution": resolution,
            "ratio": "16:9",
            "duration": duration,
            "audio": False,
            "prompt_extend": True,
            "watermark": False,
        },
    }
    async with httpx.AsyncClient(timeout=90, follow_redirects=True) as client:
        response = await client.post(url, json=payload, headers=_headers(async_video=True))
    try:
        data = response.json()
    except ValueError as exc:
        raise MediaError(f"视频接口返回非 JSON：{response.text[:200]}") from exc
    if response.status_code >= 400:
        raise MediaError("视频任务创建失败：" + _error(data, response.status_code))
    task_id = (data.get("output") or {}).get("task_id")
    if not task_id:
        raise MediaError("视频接口没有返回 task_id")
    return str(task_id)


async def wait_video(task_id: str, on_progress: ProgressCallback | None = None) -> dict[str, Any]:
    url = f"{api_root()}/api/v1/tasks/{task_id}"
    started = time.monotonic()
    while True:
        remaining = MEDIA_TIMEOUT - (time.monotonic() - started)
        if remaining <= 0:
            raise MediaError("视频生成超时，请稍后重试")
        async with httpx.AsyncClient(timeout=min(45, remaining), follow_redirects=True) as client:
            response = await client.get(url, headers=_headers())
        try:
            data = response.json()
        except ValueError as exc:
            raise MediaError(f"视频状态接口返回非 JSON：{response.text[:200]}") from exc
        if response.status_code >= 400:
            raise MediaError("视频状态查询失败：" + _error(data, response.status_code))
        output = data.get("output") or {}
        status = str(output.get("task_status", "")).upper()
        elapsed = round(time.monotonic() - started)
        if on_progress:
            await on_progress({"status": status, "elapsed": elapsed, "task_id": task_id})
        if status == "SUCCEEDED":
            if not output.get("video_url"):
                raise MediaError("视频任务完成但没有返回 video_url")
            return output
        if status == "FAILED":
            raise MediaError(str(output.get("message") or "视频生成失败"))
        await asyncio.sleep(VIDEO_POLL_INTERVAL)
