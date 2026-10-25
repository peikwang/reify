from __future__ import annotations

import asyncio
import io
import logging
import tarfile
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from .config import (
    RUNTIME_IDLE_SECONDS,
    RUNTIME_PORT,
    RUNTIME_READY_TIMEOUT,
    RUNTIME_TTL_SECONDS,
    SANDBOX_CPU,
    SANDBOX_EGRESS,
    SANDBOX_HOST_DATA_ROOT,
    SANDBOX_IMAGE,
    SANDBOX_MEMORY,
    SSR_PREVIEW_ENABLED,
    STATIC_RUNTIME_IMAGE,
    STATIC_RUNTIME_MEMORY,
)
from .db import db
from .events import Task, store
from .sandbox import SandboxError, sandbox_runner

logger = logging.getLogger("reify.runtime")

RUNTIME_KINDS = frozenset({"static", "next"})

STATIC_NGINX_CONF = """server {
    listen 3000;
    server_name _;
    root /app;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }
}
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _deadline(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat(timespec="seconds")


def _endpoint_base(value: str) -> str:
    value = value.strip()
    if value.startswith(("http://", "https://")):
        return value
    return "http://" + value.lstrip("/")


def _tar_dir(root) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for path in root.rglob("*"):
            if path.is_file():
                archive.add(path, arcname=path.relative_to(root).as_posix())
    return buffer.getvalue()


def runtime_kind(task: Task) -> str:
    return "next" if task.stack == "next" else "static"


class RuntimeManager:
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock(self, project_id: str) -> asyncio.Lock:
        if project_id not in self._locks:
            self._locks[project_id] = asyncio.Lock()
        return self._locks[project_id]

    def status(self, task: Task, kind: str | None = None) -> dict[str, Any]:
        kind = kind or runtime_kind(task)
        record = db.get_runtime(task.id)
        if not record:
            return {
                "kind": kind,
                "status": "stopped",
                "preview": kind == "static" or SSR_PREVIEW_ENABLED,
            }
        record_kind = record.get("kind") or kind
        url = None
        if record["status"] == "running":
            if record_kind == "static":
                url = f"/p/{task.id}/"
            elif SSR_PREVIEW_ENABLED:
                url = f"/apps/{task.id}/"
        return {
            "kind": record_kind,
            "status": record["status"],
            "revision": record.get("revision"),
            "started_at": record.get("started_at"),
            "last_active_at": record.get("last_active_at"),
            "expires_at": record.get("expires_at"),
            "stopped_at": record.get("stopped_at"),
            "stop_reason": record.get("stop_reason"),
            "preview": record_kind == "static" or SSR_PREVIEW_ENABLED,
            "url": url,
            "error": record.get("error"),
        }

    def _validate(self, task: Task, kind: str) -> None:
        if kind not in RUNTIME_KINDS:
            raise SandboxError(f"未知运行时类型：{kind}")
        if not sandbox_runner.enabled:
            raise SandboxError("沙箱未启用，无法启动运行时")
        if kind == "next":
            if task.stack != "next":
                raise SandboxError("只有 Next.js SSR 项目可以启动 Next 运行时")
            if not (task.runtime_dir / "server.js").is_file():
                raise SandboxError("运行时产物缺失：server.js")
            return
        if task.stack not in {"static", "react"}:
            raise SandboxError("只有静态或 React 项目可以启动静态运行时")
        if not (task.artifact_dir / "index.html").is_file():
            raise SandboxError("运行时产物缺失：index.html")

    async def start(self, task: Task, kind: str | None = None) -> dict[str, Any]:
        kind = kind or runtime_kind(task)
        self._validate(task, kind)
        async with self._lock(task.id):
            existing = db.get_runtime(task.id)
            if existing and existing["status"] == "running" and existing.get("sandbox_id"):
                if await self._healthy(task, existing, kind):
                    return self.status(task, kind)
                await self._kill(existing)
            return await self._launch(task, kind, swap=False)

    async def deploy(self, task: Task, kind: str | None = None) -> dict[str, Any]:
        """Start a new runtime from the current artifact, then retire the old one."""
        kind = kind or runtime_kind(task)
        self._validate(task, kind)
        async with self._lock(task.id):
            return await self._launch_with_swap(task, kind)

    async def ensure(self, task: Task, kind: str | None = None) -> dict[str, Any]:
        """Reuse a healthy runtime for the current revision, otherwise (re)start one."""
        kind = kind or runtime_kind(task)
        self._validate(task, kind)
        async with self._lock(task.id):
            record = db.get_runtime(task.id)
            if (
                record
                and record["status"] == "running"
                and record.get("endpoint")
                and int(record.get("revision") or 0) == task.revision
            ):
                return self.status(task, kind)
            return await self._launch_with_swap(task, kind)

    async def _launch_with_swap(self, task: Task, kind: str) -> dict[str, Any]:
        old = db.get_runtime(task.id)
        keep_old = bool(old and old["status"] == "running" and old.get("sandbox_id"))
        result = await self._launch(task, kind, swap=keep_old)
        current = db.get_runtime(task.id)
        if keep_old and old and current and old.get("sandbox_id") != current.get("sandbox_id"):
            await self._kill(old)
        return result

    async def _launch(self, task: Task, kind: str, *, swap: bool) -> dict[str, Any]:
        from opensandbox.models.execd import RunCommandOpts
        from opensandbox.models.filesystem import WriteEntry
        from opensandbox.models.sandboxes import NetworkPolicy
        from opensandbox.sandbox import Sandbox

        image = STATIC_RUNTIME_IMAGE if kind == "static" else SANDBOX_IMAGE
        memory = STATIC_RUNTIME_MEMORY if kind == "static" else SANDBOX_MEMORY
        label = "站点运行时" if kind == "static" else "SSR 运行时"
        await task.emit("runtime_starting", kind=kind, image=image, port=RUNTIME_PORT)
        sandbox = None
        volumes = None
        if kind == "next" and SANDBOX_HOST_DATA_ROOT:
            task.data_dir.mkdir(parents=True, exist_ok=True)
            host_path = (
                f"{SANDBOX_HOST_DATA_ROOT.rstrip('/')}/{task.owner_id}/projects/{task.id}/runtime-data"
            )
            from opensandbox.models.sandboxes import Host, Volume

            volumes = [Volume(name="data", host=Host(path=host_path), mountPath="/data")]
        network_policy = None
        if SANDBOX_EGRESS != "open":
            network_policy = NetworkPolicy(defaultAction="deny", egress=[])
        try:
            sandbox = await Sandbox.create(
                image,
                connection_config=sandbox_runner._connection_config(),
                timeout=timedelta(seconds=RUNTIME_TTL_SECONDS),
                ready_timeout=timedelta(seconds=60),
                resource={"cpu": SANDBOX_CPU, "memory": memory},
                env={
                    "PORT": str(RUNTIME_PORT),
                    "HOSTNAME": "0.0.0.0",
                    "NODE_ENV": "production",
                    "DATA_DIR": "/data",
                },
                metadata={"project": task.id, "kind": kind},
                network_policy=network_policy,
                volumes=volumes,
            )
            if kind == "static":
                archive = _tar_dir(task.artifact_dir)
                await sandbox.files.write_files(
                    [WriteEntry(path="/tmp/site.tgz", data=archive, mode=644)]
                )
                extract = await sandbox.commands.run(
                    "mkdir -p /app && tar -xzf /tmp/site.tgz -C /app && test -f /app/index.html",
                    opts=RunCommandOpts(working_directory="/", timeout=timedelta(seconds=60)),
                )
                if extract.exit_code != 0:
                    raise SandboxError("站点产物解压失败")
                await sandbox.files.write_files(
                    [
                        WriteEntry(
                            path="/etc/nginx/conf.d/default.conf",
                            data=STATIC_NGINX_CONF.encode("utf-8"),
                            mode=644,
                        )
                    ]
                )
                execution = await sandbox.commands.run(
                    "nginx -g 'daemon off;'",
                    opts=RunCommandOpts(background=True, working_directory="/"),
                )
            else:
                archive = _tar_dir(task.runtime_dir)
                await sandbox.files.write_files(
                    [WriteEntry(path="/tmp/runtime.tgz", data=archive, mode=644)]
                )
                extract = await sandbox.commands.run(
                    "mkdir -p /app && tar -xzf /tmp/runtime.tgz -C /app && test -f /app/server.js",
                    opts=RunCommandOpts(working_directory="/", timeout=timedelta(seconds=60)),
                )
                if extract.exit_code != 0:
                    raise SandboxError("运行时产物解压失败")
                execution = await sandbox.commands.run(
                    "node server.js",
                    opts=RunCommandOpts(
                        background=True,
                        working_directory="/app",
                        envs={
                            "PORT": str(RUNTIME_PORT),
                            "HOSTNAME": "0.0.0.0",
                            "NODE_ENV": "production",
                            "DATA_DIR": "/data",
                        },
                    ),
                )
            endpoint = await self._wait_ready(sandbox, task, kind)
            record = {
                "project_id": task.id,
                "kind": kind,
                "revision": task.revision,
                "backend": "opensandbox",
                "sandbox_id": sandbox.id,
                "endpoint": _endpoint_base(endpoint.endpoint),
                "status": "running",
                "image": image,
                "process_id": execution.id,
                "port": RUNTIME_PORT,
                "started_at": _now(),
                "last_active_at": _now(),
                "expires_at": _deadline(RUNTIME_TTL_SECONDS),
                "stopped_at": None,
                "stop_reason": None,
                "error": None,
            }
            db.save_runtime(record)
            task.result = {**(task.result or {}), "runtime": self.status(task, kind)}
            task.save_meta()
            url = None
            if kind == "static" or SSR_PREVIEW_ENABLED:
                url = f"/p/{task.id}/" if kind == "static" else f"/apps/{task.id}/"
            await task.emit(
                "runtime_ready",
                kind=kind,
                url=url,
                sandbox_id=sandbox.id,
                port=RUNTIME_PORT,
                message=f"{label}已更新" if swap else f"{label}已启动",
            )
            return self.status(task, kind)
        except Exception as exc:
            message = str(exc)[:1200]
            if sandbox is not None:
                try:
                    await sandbox.kill()
                except Exception:  # noqa: BLE001 - best-effort cleanup
                    logger.warning("runtime cleanup failed for %s", task.id, exc_info=True)
            if not swap:
                db.save_runtime(
                    {
                        "project_id": task.id,
                        "kind": kind,
                        "revision": task.revision,
                        "backend": "opensandbox",
                        "status": "error",
                        "image": image,
                        "port": RUNTIME_PORT,
                        "last_active_at": _now(),
                        "stop_reason": "error",
                        "error": message,
                    }
                )
            await task.emit("runtime_error", kind=kind, message=message)
            if isinstance(exc, SandboxError):
                raise
            raise SandboxError(message) from exc

    async def stop(self, task: Task, reason: str = "manual") -> dict[str, Any]:
        async with self._lock(task.id):
            record = db.get_runtime(task.id)
            if record:
                await self._kill(record)
            base = record or {}
            kind = base.get("kind") or runtime_kind(task)
            image = base.get("image") or (
                STATIC_RUNTIME_IMAGE if kind == "static" else SANDBOX_IMAGE
            )
            db.save_runtime(
                {
                    "project_id": task.id,
                    "kind": kind,
                    "revision": base.get("revision", task.revision),
                    "backend": base.get("backend", "opensandbox"),
                    "sandbox_id": None,
                    "endpoint": None,
                    "status": "stopped",
                    "image": image,
                    "process_id": None,
                    "port": base.get("port"),
                    "started_at": base.get("started_at"),
                    "last_active_at": _now(),
                    "expires_at": None,
                    "stopped_at": _now(),
                    "stop_reason": reason,
                    "error": None,
                }
            )
            task.result = {**(task.result or {}), "runtime": self.status(task, kind)}
            task.save_meta()
            await task.emit("runtime_stopped", kind=kind, reason=reason, message="运行时已停止")
            return self.status(task, kind)

    def touch(self, task: Task) -> None:
        record = db.get_runtime(task.id)
        if record and record["status"] == "running":
            record["last_active_at"] = _now()
            db.save_runtime(record)

    async def monitor_idle(self) -> None:
        while True:
            await asyncio.sleep(60)
            now = datetime.now(timezone.utc)
            idle_cutoff = now.timestamp() - RUNTIME_IDLE_SECONDS
            for record in db.list_runtimes():
                if record["status"] != "running":
                    continue
                task = store.get_any(record["project_id"])
                if not task:
                    continue
                reason = None
                expires_at = record.get("expires_at")
                if expires_at:
                    try:
                        if datetime.fromisoformat(expires_at).timestamp() <= now.timestamp():
                            reason = "ttl"
                    except (TypeError, ValueError):
                        reason = None
                if reason is None:
                    try:
                        last = datetime.fromisoformat(
                            record["last_active_at"] or record["started_at"]
                        ).timestamp()
                    except (TypeError, ValueError):
                        last = 0
                    if last < idle_cutoff:
                        reason = "idle"
                if reason is None:
                    continue
                logger.info("stopping %s runtime for %s", reason, task.id)
                try:
                    await self.stop(task, reason=reason)
                except Exception:  # noqa: BLE001 - monitor must continue
                    logger.warning("runtime stop failed for %s", task.id, exc_info=True)

    async def _kill(self, record: dict[str, Any]) -> None:
        sandbox_id = record.get("sandbox_id")
        if not sandbox_id:
            return
        from opensandbox.sandbox import Sandbox

        try:
            sandbox = await Sandbox.connect(
                sandbox_id,
                connection_config=sandbox_runner._connection_config(),
                skip_health_check=True,
            )
            await sandbox.kill()
        except Exception:  # noqa: BLE001 - sandbox may already be gone
            logger.info("runtime sandbox %s already gone", sandbox_id)

    async def _healthy(self, task: Task, record: dict[str, Any], kind: str) -> bool:
        endpoint = record.get("endpoint")
        if not endpoint:
            return False
        path = "/" if kind == "static" else f"/apps/{task.id}/"
        try:
            async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
                response = await client.get(_endpoint_base(endpoint).rstrip("/") + path)
            return response.status_code < 500
        except httpx.HTTPError:
            return False

    async def _wait_ready(self, sandbox, task: Task, kind: str):
        deadline = time.monotonic() + RUNTIME_READY_TIMEOUT
        last_error = "runtime not ready"
        path = "/" if kind == "static" else f"/apps/{task.id}/"
        label = "站点运行时" if kind == "static" else "SSR 运行时"
        while time.monotonic() < deadline:
            try:
                endpoint = await sandbox.get_endpoint(RUNTIME_PORT)
                async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
                    response = await client.get(
                        _endpoint_base(endpoint.endpoint).rstrip("/") + path,
                        headers=endpoint.headers,
                    )
                if response.status_code < 500:
                    return endpoint
                last_error = f"HTTP {response.status_code}"
            except Exception as exc:  # noqa: BLE001 - readiness polling
                last_error = str(exc)
            await asyncio.sleep(1)
        raise SandboxError(f"{label}健康检查超时：{last_error}")


runtime_manager = RuntimeManager()
