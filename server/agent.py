from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from .config import (
    IMAGE_COUNT,
    IMAGE_MODEL,
    STEP_DELAY,
    VIDEO_DURATION,
    VIDEO_MODEL,
    VIDEO_RESOLUTION,
)
from .events import Task, store
from .llm import design_brief, enabled as llm_enabled, refine_html, refine_source
from .media import MediaError, create_video, download_asset, generate_images, wait_video
from .runtime import runtime_manager
from .sandbox import SandboxError, sandbox_runner
from .templates.library import (
    CAPABILITIES,
    PLANS,
    THINKING,
    defaults,
    extra_files,
    html_checks,
    render_html,
    render_media_html,
    safe_brief,
    scaffold_html,
)
from .templates.games import detect_genre
from .templates.games.custom import render as render_custom_game
from .templates.longtail import detect_variant, render_code_page, render_page
from .templates.next_app import build_files as next_build_files
from .templates.next_app import next_checks_files
from .templates.react_app import build_files as react_build_files
from .templates.react_app import react_checks, react_checks_files
from .tools import Workspace

logger = logging.getLogger("reify.agent")
MEDIA_CAPS = {"image", "video"}


async def _render_static_html(
    capability: str, brief: dict[str, Any], prompt: str, task: Task
) -> str:
    if capability == "game" and detect_genre(prompt) == "custom" and llm_enabled():
        await task.emit(
            "thinking",
            step="实现自定义玩法",
            summary="当前玩法不在内置引擎里，正在按 GameSpec 生成单文件 Canvas 游戏。",
            source="llm",
        )
        html = await render_custom_game(brief, prompt)
        if html:
            await task.emit(
                "thinking",
                step="自定义玩法已通过自检",
                summary="生成结果包含 canvas、游戏循环、输入、计分和重开，并且没有外部依赖。",
                source="llm",
            )
            return html
        await task.emit(
            "thinking",
            step="回退内置街机",
            summary="自定义玩法未通过结构或离线自检，已回退到内置引擎，页面仍然可玩。",
            source="fallback",
        )
    if (
        capability in {"website", "resume", "travel"}
        and detect_variant(capability, prompt) == "custom"
        and llm_enabled()
    ):
        await task.emit(
            "thinking",
            step="生成通用页面",
            summary=f"当前需求没有命中内置 {capability} 模板，正在按规格生成一个独特的单文件页面。",
            source="llm",
        )
        html = await render_page(capability, brief, prompt)
        if html:
            task.source = "llm-longtail"
            await task.emit(
                "thinking",
                step="通用页面已通过自检",
                summary="结构、移动端、离网依赖与交互检查通过。",
                source="llm",
            )
            return html
        await task.emit(
            "thinking",
            step="回退内置模板",
            summary="通用页面未通过自检，已回退到内置模板，页面仍然可用。",
            source="fallback",
        )
    return render_html(capability, brief, prompt)


async def _render_custom_code(
    capability: str, brief: dict[str, Any], prompt: str, task: Task
) -> dict[str, str] | None:
    if capability != "code" or detect_variant("code", prompt) != "custom" or not llm_enabled():
        return None
    await task.emit(
        "thinking",
        step="生成自定义算法",
        summary="当前问题不在内置快速排序示例里，正在生成 Python 实现和可视化页面。",
        source="llm",
    )
    result = await render_code_page(brief, prompt)
    if result:
        task.source = "llm-longtail"
        await task.emit(
            "thinking",
            step="算法与页面已通过自检",
            summary="Python 语法、页面结构、交互和离网依赖检查通过。",
            source="llm",
        )
        return result
    await task.emit(
        "thinking",
        step="回退内置算法模板",
        summary="自定义算法未通过自检，已回退到内置快速排序演示。",
        source="fallback",
    )
    return None


async def _pause(multiplier: float = 1.0) -> None:
    await asyncio.sleep(max(0.05, STEP_DELAY * multiplier))


def _media_ext(mime: str) -> str:
    return {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}.get(
        (mime or "").lower(), ".png"
    )


async def _generate_media_assets(
    task: Task, capability: str, prompt: str, version: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    workspace = Workspace(task)
    assets: list[dict[str, Any]] = []
    if capability == "image":
        await task.emit(
            "media_progress",
            status="GENERATING",
            message=f"正在生成 {IMAGE_COUNT} 张图片 · {IMAGE_MODEL}",
        )
        urls = await generate_images(prompt, IMAGE_COUNT)
        for index, url in enumerate(urls, start=1):
            data, mime = await download_asset(url)
            path = f"assets/v{version}/image-{index:02d}{_media_ext(mime)}"
            asset = await workspace.save_asset(path, data, mime, f"图片 {index} 已保存")
            assets.append(asset)
            await task.emit(
                "media_progress",
                status="ASSET_READY",
                message=f"第 {index}/{len(urls)} 张图片已保存",
                progress=index,
                total=len(urls),
            )
        meta = {
            "kind": "image",
            "model": IMAGE_MODEL,
            "count": len(assets),
            "duration": None,
            "resolution": "1024x1024",
        }
        return assets, meta

    await task.emit(
        "media_progress",
        status="SUBMITTING",
        message=f"正在提交视频渲染任务 · {VIDEO_MODEL}",
    )
    upstream_task_id = await create_video(prompt, VIDEO_DURATION, VIDEO_RESOLUTION)

    async def on_progress(info: dict[str, Any]) -> None:
        await task.emit(
            "media_progress",
            status=info.get("status", "RUNNING"),
            message=f"视频渲染中 · {info.get('status', '')} · {info.get('elapsed', 0)}s",
            elapsed=info.get("elapsed", 0),
            upstream_task_id=info.get("task_id", upstream_task_id),
        )

    output = await wait_video(upstream_task_id, on_progress)
    video_url = str(output["video_url"])
    data, mime = await download_asset(video_url)
    asset = await workspace.save_asset(
        f"assets/v{version}/video.mp4",
        data,
        mime or "video/mp4",
        "视频已下载",
    )
    assets.append(asset)
    meta = {
        "kind": "video",
        "model": VIDEO_MODEL,
        "count": 1,
        "duration": VIDEO_DURATION,
        "resolution": VIDEO_RESOLUTION,
        "upstream_task_id": upstream_task_id,
    }
    return assets, meta


def _media_manifest(
    task: Task,
    prompt: str,
    revision: int,
    assets: list[dict[str, Any]],
    meta: dict[str, Any],
    brief: dict[str, Any],
) -> dict[str, Any]:
    return {
        "capability": task.capability,
        "title": task.title,
        "prompt": prompt,
        "revision": revision,
        "assets": assets,
        "meta": meta,
        "brief": brief,
    }


async def run_task(task: Task) -> None:
    started = time.monotonic()
    capability = task.capability
    label = CAPABILITIES.get(capability, CAPABILITIES["website"])["label"]
    plan = PLANS.get(capability, PLANS["website"])
    thinking = THINKING.get(capability, THINKING["website"])
    workspace = Workspace(task)

    async with store.semaphore():
        try:
            task.status = "running"
            task.save_meta()
            await task.emit(
                "task_started",
                prompt=task.prompt,
                capability=capability,
                label=label,
                mode_hint="coding" if any(k in task.prompt for k in ("代码", "算法", "编程")) else "daily",
            )
            await task.emit(
                "intent",
                capability=capability,
                label=label,
                description=CAPABILITIES.get(capability, {}).get("description", ""),
            )
            await task.emit("plan", steps=plan, capability=capability, label=label)

            brief = safe_brief(capability, defaults(capability, task.prompt))
            is_media = capability in MEDIA_CAPS
            is_react = task.stack == "react"
            is_next = task.stack == "next"
            react_source: dict[str, str] = {}
            next_source: dict[str, str] = {}
            build = None
            assets: list[dict[str, Any]] = []
            media_meta: dict[str, Any] = {}
            custom_code: dict[str, str] | None = None
            longtail_variant = detect_variant(capability, task.prompt)

            # Step 1 — understand and set the creative direction.
            await task.emit("step_started", index=0, title=plan[0])
            await task.emit("thinking", step=plan[0], summary=thinking[0])
            await _pause(0.8)
            if is_media:
                task.source = "media"
                if not task.title_locked:
                    task.title = str(brief.get("title", task.title or label))
                task.save_meta()
                await task.emit(
                    "thinking",
                    step=plan[0],
                    summary=f"画面方向：{brief.get('tagline', '')}",
                    detail=task.prompt,
                    source="media",
                )
            else:
                brief = await design_brief(capability, task.prompt, brief)
                brief = safe_brief(capability, brief)
                task.source = "llm" if brief.get("source") == "llm" else "director"
                if not task.title_locked:
                    task.title = str(brief.get("title", task.title or label))
                task.save_meta()
                await task.emit(
                    "thinking",
                    step=plan[0],
                    summary=f"视觉方向：{brief.get('tagline', '')}",
                    detail=brief.get("paragraph", ""),
                    source=task.source,
                )
            await _pause(0.6)
            await task.emit("step_done", index=0, summary="方向已确定", source=task.source)

            # Step 2 — scaffold. For media this is a loading gallery/player page.
            await task.emit("step_started", index=1, title=plan[1])
            await task.emit("thinking", step=plan[1], summary=thinking[1])
            await _pause(0.9)
            if is_next:
                next_source = next_build_files(brief, task.prompt, task.id)
                for path, content in next_source.items():
                    await workspace.write_file(path, content, "生成 Next.js App Router 源码")
                    await _pause(0.06)
            elif is_react:
                react_source = react_build_files(brief, task.prompt)
                for path, content in react_source.items():
                    await workspace.write_file(path, content, "生成 React 源码工程")
                    await _pause(0.08)
            else:
                await workspace.write_file(
                    "index.html", scaffold_html(capability, brief), "先搭一个可运行的页面骨架"
                )
            if is_media:
                assets, media_meta = await _generate_media_assets(
                    task, capability, task.prompt, 1
                )
            await task.emit(
                "step_done",
                index=1,
                summary="Next 源码已落盘" if is_next else ("React 源码已落盘" if is_react else ("素材已落盘" if is_media else "骨架已落盘")),
            )

            # Step 3 — build the real artifact (and code file for the Code Lab).
            await task.emit("step_started", index=2, title=plan[2])
            await task.emit("thinking", step=plan[2], summary=thinking[2])
            await _pause(0.9)
            if is_next:
                try:
                    build = await sandbox_runner.build(task, next_source, validate=next_checks_files)
                    await workspace.install_runtime(build.files)
                except SandboxError as exc:
                    task.status = "error"
                    task.error = str(exc)
                    task.save_meta()
                    await task.emit(
                        "error",
                        message=f"Next.js 构建失败：{exc}",
                        recoverable=True,
                        hint="检查 Sandbox 服务与 npm 出网白名单，或改用静态模板。",
                    )
                    return
            elif is_react:
                try:
                    build = await sandbox_runner.build(task, react_source, validate=react_checks_files)
                    await workspace.install_artifact(build.files)
                except SandboxError as exc:
                    task.status = "error"
                    task.error = str(exc)
                    task.save_meta()
                    await task.emit(
                        "error",
                        message=f"React 构建失败：{exc}",
                        recoverable=True,
                        hint="检查 Sandbox 服务与 npm 出网白名单，或改用静态模板。",
                    )
                    return
            elif is_media:
                html = render_media_html(capability, brief, assets, 1, task.prompt, media_meta)
                await workspace.write_file("index.html", html, "组装媒体画廊页面")
            elif capability == "code":
                custom_code = await _render_custom_code(capability, brief, task.prompt, task)
                if custom_code:
                    await workspace.write_file("main.py", custom_code["python"], "生成自定义算法主体")
                    html = custom_code["html"]
                    await workspace.write_file("index.html", html, "把算法过程做成可交互页面")
                else:
                    extras = extra_files(capability, brief, task.prompt, task.id)
                    await workspace.write_file("main.py", extras["main.py"], "生成算法主体")
                    html = render_html(capability, brief, task.prompt)
                    await workspace.write_file("index.html", html, "把算法过程做成可交互页面")
            else:
                html = await _render_static_html(capability, brief, task.prompt, task)
                await workspace.write_file("index.html", html, "完成页面结构、视觉与交互")
            if is_next:
                await task.emit(
                    "runtime_built",
                    files=len(build.files) if build else 0,
                    bytes=build.total_bytes if build else 0,
                    message="standalone 构建完成，SSR 运行时可按需启动",
                )
            else:
                await task.emit("preview_ready", url=task.url, title=task.title)
            await task.emit(
                "step_done",
                index=2,
                summary="standalone 构建产物已生成" if is_next else ("构建产物已生成" if is_react else "核心产物已生成"),
            )

            # Step 4 — supporting files, data, and documentation.
            await task.emit("step_started", index=3, title=plan[3])
            await task.emit("thinking", step=plan[3], summary=thinking[3])
            await _pause(0.9)
            if is_media:
                media_manifest = _media_manifest(task, task.prompt, 1, assets, media_meta, brief)
                await workspace.write_file(
                    "media.json", json.dumps(media_manifest, ensure_ascii=False, indent=2), "写入媒体元数据"
                )
            if is_react and build:
                await workspace.write_file(
                    "build.json",
                    json.dumps(
                        {
                            "stack": "react",
                            "files": len(build.files),
                            "bytes": build.total_bytes,
                            "duration_ms": build.duration_ms,
                            "sandbox_id": build.sandbox_id,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    "写入构建信息",
                )
            if is_next and build:
                await workspace.write_file(
                    "build.json",
                    json.dumps(
                        {
                            "stack": "next",
                            "files": len(build.files),
                            "bytes": build.total_bytes,
                            "duration_ms": build.duration_ms,
                            "sandbox_id": build.sandbox_id,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    "写入构建信息",
                )
            if not is_react and not is_next:
                extras = extra_files(capability, brief, task.prompt, task.id)
                if capability == "code" and custom_code:
                    extras["main.py"] = custom_code["python"]
                if longtail_variant == "custom" and capability in {"resume", "travel"}:
                    extras.pop("resume.json", None)
                    extras.pop("itinerary.json", None)
                for path, content in extras.items():
                    if path == "media.json":
                        continue
                    await workspace.write_file(path, content, "补齐结构化数据与交付说明")
                    await _pause(0.4)
            await task.emit("step_done", index=3, summary="交付文件已补齐")

            # Step 5 — verify and deploy.
            await task.emit("step_started", index=4, title=plan[4])
            await task.emit("thinking", step=plan[4], summary=thinking[4])
            await _pause(0.8)
            if is_next:
                checks = next_checks_files(build.files) if build else []
            elif is_react:
                checks = react_checks(task.artifact_dir)
            else:
                current = (task.workspace / "index.html").read_text(encoding="utf-8")
                checks = html_checks(current, capability)
            if is_media:
                checks.append(("素材已生成", bool(assets) and all(a.get("bytes", 0) > 0 for a in assets), f"{len(assets)} 个文件"))
            for name, ok, detail in checks:
                await task.emit("verify", name=name, ok=ok, detail=detail)
                await _pause(0.24)
            if capability == "code":
                result = await workspace.run_python("main.py")
                await task.emit(
                    "verify",
                    name="Python 可执行",
                    ok=bool(result.get("ok")),
                    detail="py_compile 通过" if result.get("ok") else "语法检查失败",
                )
            failed_checks = [name for name, ok, _ in checks if not ok]
            if capability == "code" and not result.get("ok"):
                failed_checks.append("Python 可执行")
            if failed_checks:
                task.status = "error"
                task.error = "自检未通过：" + "、".join(failed_checks)
                task.save_meta()
                await task.emit(
                    "error",
                    message="生成未通过自检，未部署：" + "、".join(failed_checks),
                    recoverable=True,
                )
                return
            if is_next:
                elapsed = round((time.monotonic() - started) * 1000)
                task.status = "done"
                task.result = {
                    "url": None,
                    "title": task.title,
                    "capability": capability,
                    "source": task.source,
                    "elapsed_ms": elapsed,
                    "stack": "next",
                    "runtime": {"status": "stopped"},
                    "checks": [{"name": name, "ok": ok, "detail": detail} for name, ok, detail in checks],
                }
                if build:
                    task.result["build"] = {
                        "files": len(build.files),
                        "bytes": build.total_bytes,
                        "duration_ms": build.duration_ms,
                        "sandbox_id": build.sandbox_id,
                    }
                task.save_meta()
                await task.emit("step_done", index=4, summary="构建完成，SSR 运行时可启动")
                await task.emit(
                    "done",
                    url=None,
                    title=task.title,
                    summary=f"{task.title} 已构建完成；点击启动 SSR 运行时即可访问。",
                    elapsed_ms=elapsed,
                    source=task.source,
                    capability=capability,
                    revision=task.revision,
                )
                return
            task.status = "deploying"
            task.save_meta()
            manifest = await workspace.deploy(task.title)
            await task.emit("step_done", index=4, summary="已通过自检并部署")

            elapsed = round((time.monotonic() - started) * 1000)
            task.status = "done"
            task.result = {
                "url": manifest["url"],
                "title": task.title,
                "capability": capability,
                "source": task.source,
                "elapsed_ms": elapsed,
                "checks": [{"name": name, "ok": ok, "detail": detail} for name, ok, detail in checks],
            }
            if is_media:
                task.revision = 1
                task.result["revision"] = 1
                task.result["assets"] = len(assets)
                task.result["media"] = media_meta
            if is_react and build:
                task.result["stack"] = "react"
                task.result["build"] = {
                    "files": len(build.files),
                    "bytes": build.total_bytes,
                    "duration_ms": build.duration_ms,
                    "sandbox_id": build.sandbox_id,
                }
            task.save_meta()
            await task.emit(
                "done",
                url=manifest["url"],
                title=task.title,
                summary=f"{task.title} 已完成，并通过结构与交互自检。",
                elapsed_ms=elapsed,
                source=task.source,
                capability=capability,
                revision=task.revision,
            )
        except Exception as exc:  # noqa: BLE001 - task failure must be visible in the stream
            logger.exception("task %s failed", task.id)
            task.status = "error"
            task.error = str(exc)
            task.save_meta()
            await task.emit(
                "error",
                message=f"生成中断：{exc}",
                recoverable=True,
                hint="可以重试，或换一种描述让 Agent 重新规划。",
            )


async def _refine_failed(task: Task, message: str) -> None:
    await task.emit("refine_failed", message=message)
    task.status = "done"
    task.save_meta()
    await task.emit(
        "done",
        url=task.url,
        title=task.title,
        summary="本次修改未应用，原页面保持不变。",
        source="refine-failed",
        capability=task.capability,
        revision=task.revision,
    )


async def _run_source_refine(task: Task, instruction: str, revision: int) -> None:
    workspace = Workspace(task)
    is_next = task.stack == "next"
    page_path = (
        next(
            (
                path
                for path in (
                    "app/page.tsx",
                    "app/page.jsx",
                )
                if (task.workspace / path).is_file()
            ),
            "app/page.tsx",
        )
        if is_next
        else next(
            (
                path
                for path in (
                    "src/App.tsx",
                    "src/App.jsx",
                )
                if (task.workspace / path).is_file()
            ),
            "src/App.tsx",
        )
    )
    style_path = "app/globals.css" if is_next else "src/styles.css"
    style_words = ("颜色", "配色", "字体", "字号", "间距", "留白", "样式", "主题", "背景", "css", "style")
    target_path = style_path if any(word in instruction.lower() for word in style_words) else page_path
    target = task.workspace / target_path
    if not target.is_file():
        await _refine_failed(task, f"缺少可修改的源码文件：{target_path}")
        return
    original = target.read_text(encoding="utf-8")
    if not llm_enabled():
        await _refine_failed(task, "当前没有可用的 LLM，无法进行源码修改。")
        return
    if page_path.endswith(".tsx"):
        language = "Next.js App Router TypeScript (TSX/TS)" if is_next else "React TypeScript (TSX)"
    else:
        language = "Next.js App Router JSX" if is_next else "React JSX"
    result = await refine_source(
        original,
        instruction,
        task.capability,
        language,
    )
    if not result:
        await _refine_failed(task, "模型没有返回可应用的源码修改，已保留原运行时。")
        return
    updated = result["source"]
    await task.emit(
        "thinking",
        step="应用源码修改",
        summary=result.get("summary", "已生成局部源码修改。"),
        detail=f"目标文件 {target_path}，应用 {len(result.get('notes', []))} 处 patch。",
        source="llm",
    )
    await workspace.write_file(target_path, updated, "根据对话修改源码：" + instruction[:40])
    source_files = _collect_source_files(task)
    try:
        if is_next:
            build = await sandbox_runner.build(task, source_files, validate=next_checks_files)
            await workspace.install_runtime(build.files)
            checks = next_checks_files(build.files)
            for name, ok, detail in checks:
                await task.emit("verify", name=name, ok=ok, detail=detail)
            old_revision = task.revision
            task.revision = revision
            try:
                await runtime_manager.deploy(task)
            except Exception:
                task.revision = old_revision
                raise
            event_url = None
        else:
            build = await sandbox_runner.build(task, source_files, validate=react_checks_files)
            await workspace.install_artifact(build.files)
            checks = react_checks(task.artifact_dir)
            for name, ok, detail in checks:
                await task.emit("verify", name=name, ok=ok, detail=detail)
            manifest = await Workspace(task).deploy(task.title)
            event_url = manifest["url"]
        task.revision = revision
        task.source = "llm-edit"
        task.error = None
        task.status = "done"
        task.result = {
            "url": event_url,
            "title": task.title,
            "capability": task.capability,
            "source": "llm-edit",
            "revision": revision,
            "stack": task.stack,
            "runtime": runtime_manager.status(task) if is_next else None,
            "build": {
                "files": len(build.files),
                "bytes": build.total_bytes,
                "duration_ms": build.duration_ms,
            },
            "checks": [{"name": name, "ok": ok, "detail": detail} for name, ok, detail in checks],
        }
        task.save_meta()
        await task.emit(
            "done",
            url=event_url,
            title=task.title,
            summary=result.get("summary", "已根据你的要求完成修改。"),
            source="llm-edit",
            capability=task.capability,
            revision=revision,
        )
    except Exception as exc:  # noqa: BLE001 - keep the previous build/runtime intact
        logger.exception("source refine failed for task %s", task.id)
        await workspace.restore_file(target_path, original)
        task.error = str(exc)
        await _refine_failed(task, "源码修改没有通过构建/校验，原版本保持不变。")


def _collect_source_files(task: Task) -> dict[str, str]:
    skip_dirs = {"dist", "runtime", "node_modules", ".next", "assets", ".git", "__pycache__"}
    suffixes = {".js", ".jsx", ".mjs", ".ts", ".tsx", ".json", ".css", ".md", ".html"}
    files: dict[str, str] = {}
    for path in task.workspace.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(task.workspace)
        if any(part in skip_dirs for part in relative.parts):
            continue
        if path.name in {"build.json", "deploy.json"} or path.suffix.lower() not in suffixes:
            continue
        try:
            files[relative.as_posix()] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    return files


async def run_refine(task: Task, instruction: str) -> None:
    started = time.monotonic()
    revision = task.revision + 1
    original_html: str | None = None
    committed = False
    async with store.semaphore():
        try:
            task.status = "running"
            task.save_meta()
            await task.emit(
                "refine_started",
                instruction=instruction,
                capability=task.capability,
                revision=revision,
            )
            await task.emit(
                "thinking",
                step="理解修改要求",
                summary="先读取当前成果，只修改你指定的部分，保留其余结构。",
                source="llm" if llm_enabled() else "director",
            )
            await _pause(0.45)
            if task.stack in {"react", "next"}:
                await _run_source_refine(task, instruction, revision)
                return
            if not llm_enabled():
                await _refine_failed(task, "当前没有可用的 LLM，无法进行语义修改。")
                return
            index = task.workspace / "index.html"
            if not index.exists():
                await _refine_failed(task, "当前项目缺少 index.html，无法修改。")
                return
            current = index.read_text(encoding="utf-8")
            original_html = current
            result = await refine_html(current, instruction, task.capability)
            if not result:
                await _refine_failed(
                    task,
                    "模型没有返回可应用的局部修改，已保留原页面。可以换一种更具体的说法再试。",
                )
                return
            new_html = result["html"]
            checks = html_checks(new_html, task.capability)
            if not all(ok for _, ok, _ in checks):
                await _refine_failed(task, "修改后的页面没有通过结构自检，已保留原页面。")
                return
            await task.emit(
                "thinking",
                step="应用修改",
                summary=result.get("summary", "已生成局部修改。"),
                detail="应用了 " + str(len(result.get("notes", []))) + " 处局部 patch。",
                source="llm",
            )
            workspace = Workspace(task)
            await workspace.write_file(
                "index.html",
                new_html,
                "根据对话修改：" + instruction[:48],
            )
            await task.emit("preview_ready", url=task.url, title=task.title)
            for name, ok, detail in checks:
                await task.emit("verify", name=name, ok=ok, detail=detail)
                await _pause(0.12)
            task.status = "deploying"
            task.save_meta()
            manifest = await workspace.deploy(task.title)
            elapsed = round((time.monotonic() - started) * 1000)
            task.revision = revision
            task.source = "llm-edit"
            task.error = None
            task.status = "done"
            task.result = {
                "url": manifest["url"],
                "title": task.title,
                "capability": task.capability,
                "source": "llm-edit",
                "elapsed_ms": elapsed,
                "revision": revision,
                "summary": result.get("summary", ""),
                "checks": [{"name": name, "ok": ok, "detail": detail} for name, ok, detail in checks],
            }
            task.save_meta()
            committed = True
            await task.emit(
                "done",
                url=manifest["url"],
                title=task.title,
                summary=result.get("summary", "已根据你的要求完成修改。"),
                elapsed_ms=elapsed,
                source="llm-edit",
                capability=task.capability,
                revision=revision,
            )
        except Exception as exc:  # noqa: BLE001 - keep the previous deliverable intact
            logger.exception("refine failed for task %s", task.id)
            task.error = str(exc)
            if not committed and original_html is not None:
                try:
                    await Workspace(task).restore_file("index.html", original_html)
                    await Workspace(task).deploy(task.title)
                except Exception:  # noqa: BLE001 - rollback is best effort; log if it fails
                    logger.exception("refine rollback failed for task %s", task.id)
            if not committed:
                await _refine_failed(task, "修改过程中出现错误，原页面保持不变。")


async def run_media_refine(task: Task, instruction: str) -> None:
    started = time.monotonic()
    revision = task.revision + 1
    original_html: str | None = None
    original_media: str | None = None
    committed = False
    async with store.semaphore():
        try:
            task.status = "running"
            task.save_meta()
            await task.emit(
                "refine_started",
                instruction=instruction,
                capability=task.capability,
                revision=revision,
            )
            await task.emit(
                "thinking",
                step="理解媒体修改要求",
                summary="保留当前项目，只重新生成需要变化的图片或视频。",
                source="media",
            )
            await _pause(0.3)
            index = task.workspace / "index.html"
            media_path = task.workspace / "media.json"
            original_html = index.read_text(encoding="utf-8") if index.exists() else None
            media_data: dict[str, Any] = {}
            if media_path.exists():
                try:
                    media_data = json.loads(media_path.read_text(encoding="utf-8"))
                except ValueError:
                    media_data = {}
                original_media = json.dumps(media_data, ensure_ascii=False, indent=2)
            base_prompt = str(media_data.get("prompt") or task.prompt)
            new_prompt = base_prompt + "\n修改要求：" + instruction
            brief = safe_brief(
                task.capability,
                media_data.get("brief") or defaults(task.capability, task.prompt),
            )
            assets, media_meta = await _generate_media_assets(
                task, task.capability, new_prompt, revision
            )
            html = render_media_html(task.capability, brief, assets, revision, new_prompt, media_meta)
            checks = html_checks(html, task.capability)
            checks.append(
                ("素材已生成", bool(assets) and all(a.get("bytes", 0) > 0 for a in assets), f"{len(assets)} 个文件")
            )
            if not all(ok for _, ok, _ in checks):
                await _refine_failed(task, "修改后的媒体项目没有通过资源自检，已保留原页面。")
                return
            workspace = Workspace(task)
            await workspace.write_file("index.html", html, "重新生成媒体画廊")
            manifest = _media_manifest(task, new_prompt, revision, assets, media_meta, brief)
            await workspace.write_file(
                "media.json", json.dumps(manifest, ensure_ascii=False, indent=2), "更新媒体元数据"
            )
            await task.emit("preview_ready", url=task.url, title=task.title)
            for name, ok, detail in checks:
                await task.emit("verify", name=name, ok=ok, detail=detail)
                await _pause(0.12)
            task.status = "deploying"
            task.save_meta()
            deployed = await workspace.deploy(task.title)
            elapsed = round((time.monotonic() - started) * 1000)
            task.revision = revision
            task.source = "media-edit"
            task.error = None
            task.status = "done"
            task.result = {
                "url": deployed["url"],
                "title": task.title,
                "capability": task.capability,
                "source": "media-edit",
                "elapsed_ms": elapsed,
                "revision": revision,
                "assets": len(assets),
                "media": media_meta,
                "checks": [{"name": name, "ok": ok, "detail": detail} for name, ok, detail in checks],
            }
            task.save_meta()
            committed = True
            summary = (
                f"已重新生成 {len(assets)} 张图片并部署。"
                if task.capability == "image"
                else "已重新生成视频并部署。"
            )
            await task.emit(
                "done",
                url=deployed["url"],
                title=task.title,
                summary=summary,
                elapsed_ms=elapsed,
                source="media-edit",
                capability=task.capability,
                revision=revision,
            )
        except Exception as exc:  # noqa: BLE001 - keep the previous deliverable intact
            logger.exception("media refine failed for task %s", task.id)
            task.error = str(exc)
            if not committed:
                try:
                    if original_html is not None:
                        await Workspace(task).restore_file("index.html", original_html)
                    if original_media is not None:
                        await Workspace(task).restore_file("media.json", original_media)
                    if original_html is not None:
                        await Workspace(task).deploy(task.title)
                except Exception:  # noqa: BLE001 - best-effort rollback
                    logger.exception("media refine rollback failed for task %s", task.id)
                await _refine_failed(task, "媒体修改过程中出现错误，原页面保持不变。")
