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
)
from .db import db
from .events import Task, store
from .sandbox import SandboxError, sandbox_runner

logger = logging.getLogger("reify.runtime")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


class RuntimeManager:
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock(self, project_id: str) -> asyncio.Lock:
        if project_id not in self._locks:
            self._locks[project_id] = asyncio.Lock()
        return self._locks[project_id]

    def status(self, task: Task) -> dict[str, Any]:
        record = db.get_runtime(task.id)
        if not record:
            return {"status": "stopped", "preview": SSR_PREVIEW_ENABLED}
        return {
            "status": record["status"],
            "revision": record.get("revision"),
            "started_at": record.get("started_at"),
            "last_active_at": record.get("last_active_at"),
            "preview": SSR_PREVIEW_ENABLED,
            "url": f"/apps/{task.id}/" if SSR_PREVIEW_ENABLED and record["status"] == "running" else None,
            "error": record.get("error"),
        }

    def _validate(self, task: Task) -> None:
        if task.stack != "next":
            raise SandboxError("只有 Next.js SSR 项目可以启动运行时")
        if not sandbox_runner.enabled:
            raise SandboxError("沙箱未启用，无法启动 SSR 运行时")
        if not (task.runtime_dir / "server.js").is_file():
            raise SandboxError("运行时产物缺失：server.js")

    async def start(self, task: Task) -> dict[str, Any]:
        self._validate(task)
        async with self._lock(task.id):
            existing = db.get_runtime(task.id)
            if existing and existing["status"] == "running" and existing.get("sandbox_id"):
                if await self._healthy(task, existing):
                    return self.status(task)
                await self._kill(existing)
            return await self._launch(task, swap=False)

    async def deploy(self, task: Task) -> dict[str, Any]:
        """Start a new runtime from the current artifact, then retire the old one."""
        self._validate(task)
        async with self._lock(task.id):
            old = db.get_runtime(task.id)
            keep_old = bool(old and old["status"] == "running" and old.get("sandbox_id"))
            result = await self._launch(task, swap=keep_old)
            if keep_old and old and old.get("sandbox_id") != db.get_runtime(task.id).get("sandbox_id"):
                await self._kill(old)
            return result

    async def _launch(self, task: Task, *, swap: bool) -> dict[str, Any]:
        from opensandbox.models.execd import RunCommandOpts
        from opensandbox.models.filesystem import WriteEntry
        from opensandbox.models.sandboxes import Host, NetworkPolicy, Volume
        from opensandbox.sandbox import Sandbox

        await task.emit("runtime_starting", image=SANDBOX_IMAGE, port=RUNTIME_PORT)
        sandbox = None
        volumes = None
        if SANDBOX_HOST_DATA_ROOT:
            task.data_dir.mkdir(parents=True, exist_ok=True)
            host_path = (
                f"{SANDBOX_HOST_DATA_ROOT.rstrip('/')}/{task.owner_id}/projects/{task.id}/runtime-data"
            )
            volumes = [Volume(name="data", host=Host(path=host_path), mountPath="/data")]
        network_policy = None
        if SANDBOX_EGRESS != "open":
            network_policy = NetworkPolicy(defaultAction="deny", egress=[])
        try:
            sandbox = await Sandbox.create(
                SANDBOX_IMAGE,
                connection_config=sandbox_runner._connection_config(),
                timeout=timedelta(seconds=RUNTIME_TTL_SECONDS),
                ready_timeout=timedelta(seconds=60),
                resource={"cpu": SANDBOX_CPU, "memory": SANDBOX_MEMORY},
                env={
                    "PORT": str(RUNTIME_PORT),
                    "HOSTNAME": "0.0.0.0",
                    "NODE_ENV": "production",
                    "DATA_DIR": "/data",
                },
                metadata={"project": task.id, "stack": "next"},
                network_policy=network_policy,
                volumes=volumes,
            )
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
            endpoint = await self._wait_ready(sandbox, task)
            record = {
                "project_id": task.id,
                "revision": task.revision,
                "backend": "opensandbox",
                "sandbox_id": sandbox.id,
                "endpoint": _endpoint_base(endpoint.endpoint),
                "status": "running",
                "image": SANDBOX_IMAGE,
                "process_id": execution.id,
                "port": RUNTIME_PORT,
                "started_at": _now(),
                "last_active_at": _now(),
                "error": None,
            }
            db.save_runtime(record)
            task.result = {**(task.result or {}), "runtime": self.status(task)}
            task.save_meta()
            await task.emit(
                "runtime_ready",
                url=f"/apps/{task.id}/" if SSR_PREVIEW_ENABLED else None,
                sandbox_id=sandbox.id,
                port=RUNTIME_PORT,
                message="SSR 运行时已更新" if swap else "SSR 运行时已启动",
            )
            return self.status(task)
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
                        "revision": task.revision,
                        "backend": "opensandbox",
                        "status": "error",
                        "image": SANDBOX_IMAGE,
                        "port": RUNTIME_PORT,
                        "last_active_at": _now(),
                        "error": message,
                    }
                )
            await task.emit("runtime_error", message=message)
            if isinstance(exc, SandboxError):
                raise
            raise SandboxError(message) from exc

    async def stop(self, task: Task, reason: str = "manual") -> dict[str, Any]:
        async with self._lock(task.id):
            record = db.get_runtime(task.id)
            if record:
                await self._kill(record)
            db.save_runtime(
                {
                    "project_id": task.id,
                    "revision": task.revision,
                    "backend": "opensandbox",
                    "status": "stopped",
                    "image": SANDBOX_IMAGE,
                    "port": RUNTIME_PORT,
                    "last_active_at": _now(),
                    "error": None,
                }
            )
            task.result = {**(task.result or {}), "runtime": self.status(task)}
            task.save_meta()
            await task.emit("runtime_stopped", reason=reason, message="SSR 运行时已停止")
            return self.status(task)

    def touch(self, task: Task) -> None:
        record = db.get_runtime(task.id)
        if record and record["status"] == "running":
            record["last_active_at"] = _now()
            db.save_runtime(record)

    async def monitor_idle(self) -> None:
        while True:
            await asyncio.sleep(60)
            cutoff = datetime.now(timezone.utc).timestamp() - RUNTIME_IDLE_SECONDS
            for record in db.list_runtimes():
                if record["status"] != "running":
                    continue
                try:
                    last = datetime.fromisoformat(record["last_active_at"] or record["started_at"]).timestamp()
                except (TypeError, ValueError):
                    last = 0
                if last < cutoff:
                    task = store.get_any(record["project_id"])
                    if task:
                        logger.info("stopping idle runtime for %s", task.id)
                        try:
                            await self.stop(task, reason="idle")
                        except Exception:  # noqa: BLE001 - monitor must continue
                            logger.warning("idle stop failed for %s", task.id, exc_info=True)

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

    async def _healthy(self, task: Task, record: dict[str, Any]) -> bool:
        endpoint = record.get("endpoint")
        if not endpoint:
            return False
        try:
            async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
                response = await client.get(
                    _endpoint_base(endpoint).rstrip("/") + f"/apps/{task.id}/",
                )
            return response.status_code < 500
        except httpx.HTTPError:
            return False

    async def _wait_ready(self, sandbox, task: Task):
        deadline = time.monotonic() + RUNTIME_READY_TIMEOUT
        last_error = "runtime not ready"
        while time.monotonic() < deadline:
            try:
                endpoint = await sandbox.get_endpoint(RUNTIME_PORT)
                async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
                    response = await client.get(
                        _endpoint_base(endpoint.endpoint).rstrip("/") + f"/apps/{task.id}/",
                        headers=endpoint.headers,
                    )
                if response.status_code < 500:
                    return endpoint
                last_error = f"HTTP {response.status_code}"
            except Exception as exc:  # noqa: BLE001 - readiness polling
                last_error = str(exc)
            await asyncio.sleep(1)
        raise SandboxError(f"SSR 运行时健康检查超时：{last_error}")


runtime_manager = RuntimeManager()
