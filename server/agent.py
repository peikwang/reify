from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from .config import STEP_DELAY
from .events import Task, store
from .llm import design_brief, enabled as llm_enabled, refine_html
from .templates.library import (
    CAPABILITIES,
    PLANS,
    THINKING,
    defaults,
    extra_files,
    html_checks,
    render_html,
    safe_brief,
    scaffold_html,
)
from .tools import Workspace

logger = logging.getLogger("vibeforge.agent")


async def _pause(multiplier: float = 1.0) -> None:
    await asyncio.sleep(max(0.05, STEP_DELAY * multiplier))


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

            # Step 1 — understand and set the creative direction.
            await task.emit("step_started", index=0, title=plan[0])
            await task.emit("thinking", step=plan[0], summary=thinking[0])
            await _pause(0.8)
            brief = await design_brief(capability, task.prompt, brief)
            brief = safe_brief(capability, brief)
            task.source = "llm" if brief.get("source") == "llm" else "director"
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

            # Step 2 — scaffold. This is the first real file snapshot.
            await task.emit("step_started", index=1, title=plan[1])
            await task.emit("thinking", step=plan[1], summary=thinking[1])
            await _pause(0.9)
            await workspace.write_file(
                "index.html", scaffold_html(capability, brief), "先搭一个可运行的页面骨架"
            )
            await task.emit("step_done", index=1, summary="骨架已落盘")

            # Step 3 — build the real artifact (and code file for the Code Lab).
            await task.emit("step_started", index=2, title=plan[2])
            await task.emit("thinking", step=plan[2], summary=thinking[2])
            await _pause(0.9)
            if capability == "code":
                extras = extra_files(capability, brief, task.prompt, task.id)
                await workspace.write_file("main.py", extras["main.py"], "生成算法主体")
                html = render_html(capability, brief)
                await workspace.write_file("index.html", html, "把算法过程做成可交互页面")
            else:
                html = render_html(capability, brief)
                await workspace.write_file("index.html", html, "完成页面结构、视觉与交互")
            await task.emit("preview_ready", url=task.url, title=task.title)
            await task.emit("step_done", index=2, summary="核心产物已生成")

            # Step 4 — supporting files, data, and documentation.
            await task.emit("step_started", index=3, title=plan[3])
            await task.emit("thinking", step=plan[3], summary=thinking[3])
            await _pause(0.9)
            extras = extra_files(capability, brief, task.prompt, task.id)
            for path, content in extras.items():
                await workspace.write_file(path, content, "补齐结构化数据与交付说明")
                await _pause(0.4)
            await task.emit("step_done", index=3, summary="交付文件已补齐")

            # Step 5 — verify and deploy.
            await task.emit("step_started", index=4, title=plan[4])
            await task.emit("thinking", step=plan[4], summary=thinking[4])
            await _pause(0.8)
            current = (task.workspace / "index.html").read_text(encoding="utf-8")
            checks = html_checks(current, capability)
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
            task.save_meta()
            await task.emit(
                "done",
                url=manifest["url"],
                title=task.title,
                summary=f"{task.title} 已完成，并通过结构与交互自检。",
                elapsed_ms=elapsed,
                source=task.source,
                capability=capability,
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
