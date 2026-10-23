from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .events import Task

LANGUAGES = {
    ".html": "html",
    ".css": "css",
    ".js": "javascript",
    ".json": "json",
    ".md": "markdown",
    ".py": "python",
    ".txt": "text",
}


class Workspace:
    def __init__(self, task: Task) -> None:
        self.task = task
        self.root = task.workspace.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _atomic_write(target: Path, content: str) -> None:
        temp = target.with_name(target.name + ".tmp")
        temp.write_text(content, encoding="utf-8")
        os.replace(temp, target)

    def _safe_path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError(f"path escapes workspace: {relative}") from exc
        return candidate

    async def write_file(self, path: str, content: str, reason: str = "") -> dict[str, Any]:
        target = self._safe_path(path)
        before = target.read_text(encoding="utf-8") if target.exists() else ""
        if before == content:
            await self.task.emit(
                "tool_result", name="write_file", ok=True, summary=f"{path} 无变化，跳过写入"
            )
            return {"ok": True, "path": path, "noop": True, "lines": len(content.splitlines())}
        target.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write(target, content)
        language = LANGUAGES.get(target.suffix.lower(), "text")
        await self.task.emit(
            "tool_call",
            name="write_file",
            args={"path": path, "reason": reason},
            summary=f"{'更新' if before else '创建'} {path}",
        )
        await self.task.emit(
            "file_diff",
            path=path,
            language=language,
            before=before,
            after=content,
            created=not before,
            reason=reason,
            stats={"before_lines": len(before.splitlines()), "after_lines": len(content.splitlines())},
        )
        await self.task.emit(
            "tool_result",
            name="write_file",
            ok=True,
            summary=f"{path} 已写入 · {len(content.splitlines())} 行",
        )
        return {"ok": True, "path": path, "lines": len(content.splitlines())}

    async def restore_file(self, path: str, content: str) -> None:
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write(target, content)

    async def save_asset(self, path: str, data: bytes, mime: str, label: str = "") -> dict[str, Any]:
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + ".tmp")
        temp.write_bytes(data)
        os.replace(temp, target)
        await self.task.emit(
            "asset_created",
            path=path,
            mime=mime,
            bytes=len(data),
            url=f"/media/{self.task.id}/{path}",
            summary=label or path,
        )
        return {"path": path, "url": f"/media/{self.task.id}/{path}", "mime": mime, "bytes": len(data)}

    async def edit_file(self, path: str, old: str, new: str, reason: str = "") -> dict[str, Any]:
        target = self._safe_path(path)
        if not target.exists():
            raise ValueError(f"file not found: {path}")
        content = target.read_text(encoding="utf-8")
        if old not in content:
            raise ValueError(f"edit anchor not found in {path}")
        return await self.write_file(path, content.replace(old, new, 1), reason)

    async def run_python(self, path: str) -> dict[str, Any]:
        target = self._safe_path(path)
        await self.task.emit(
            "tool_call", name="python_execute", args={"path": path}, summary=f"运行 {path} 自检"
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "py_compile",
                str(target),
                cwd=str(self.root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=12)
            ok = proc.returncode == 0
            detail = (stderr or stdout).decode("utf-8", errors="replace")[-1200:]
        except Exception as exc:  # noqa: BLE001 - surface tool failure as an event
            ok = False
            detail = str(exc)
        await self.task.emit(
            "tool_result",
            name="python_execute",
            ok=ok,
            summary="Python 语法检查通过" if ok else "Python 语法检查失败",
            detail=detail,
        )
        return {"ok": ok, "detail": detail}

    async def deploy(self, title: str) -> dict[str, Any]:
        index = self._safe_path("index.html")
        if not index.exists():
            raise ValueError("index.html is missing")
        await self.task.emit(
            "tool_call", name="deploy_local", args={"path": "/"}, summary="写入部署清单并发布"
        )
        manifest = {
            "task_id": self.task.id,
            "title": title,
            "url": self.task.url,
            "entry": "index.html",
            "capability": self.task.capability,
            "deployed_at": self.task.updated_at,
        }
        self._atomic_write(
            self.root / "deploy.json",
            json.dumps(manifest, ensure_ascii=False, indent=2),
        )
        await self.task.emit(
            "tool_result", name="deploy_local", ok=True, summary="静态路由已生效"
        )
        await self.task.emit(
            "deployed",
            url=self.task.url,
            title=title,
            entry="index.html",
            message="已部署到本地 Agent Server",
        )
        return manifest
