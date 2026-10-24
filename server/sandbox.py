from __future__ import annotations

import asyncio
import base64
import io
import logging
import re
import tarfile
import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import PurePosixPath
from typing import Any, Callable

import httpx

from .config import (
    NPM_BUILD_TIMEOUT,
    NPM_INSTALL_TIMEOUT,
    NPM_REGISTRY,
    NEXT_ARTIFACT_MAX_BYTES,
    REACT_DIST_MAX_BYTES,
    SANDBOX_API_KEY,
    SANDBOX_BACKEND,
    SANDBOX_CONCURRENCY,
    SANDBOX_CPU,
    SANDBOX_DOMAIN,
    SANDBOX_EGRESS,
    SANDBOX_EGRESS_ALLOW,
    SANDBOX_BUILD_MEMORY,
    SANDBOX_IMAGE,
    SANDBOX_MEMORY,
    SANDBOX_PROTOCOL,
    SANDBOX_READY_TIMEOUT,
    SANDBOX_REQUEST_TIMEOUT,
    SANDBOX_TTL_SECONDS,
    SANDBOX_USE_SERVER_PROXY,
)
from .events import Task

logger = logging.getLogger("vibeforge.sandbox")
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


class SandboxError(RuntimeError):
    pass


@dataclass
class BuildResult:
    files: dict[str, bytes]
    total_bytes: int
    duration_ms: int
    sandbox_id: str


def _clean(text: str) -> str:
    return ANSI_RE.sub("", text).rstrip()


def _sign_asset_urls(html: str, asset_key: str) -> str:
    pattern = re.compile(r'((?:src|href)=")([^"]*assets/[^"]+?)(")')

    def replace(match: re.Match[str]) -> str:
        url = match.group(2)
        if url.lower().startswith(("http://", "https://", "//", "data:", "blob:")):
            return match.group(0)
        separator = "&" if "?" in url else "?"
        return f"{match.group(1)}{url}{separator}k={asset_key}{match.group(3)}"

    return pattern.sub(replace, html)


class SandboxRunner:
    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(SANDBOX_CONCURRENCY)
        self._health_cache: tuple[float, bool] = (0.0, False)

    @property
    def enabled(self) -> bool:
        return SANDBOX_BACKEND == "opensandbox" and bool(SANDBOX_API_KEY)

    def status(self) -> dict[str, Any]:
        return {
            "backend": SANDBOX_BACKEND if self.enabled else "off",
            "image": SANDBOX_IMAGE if self.enabled else None,
        }

    async def reachable(self) -> bool:
        if not self.enabled:
            return False
        now = time.monotonic()
        cached_at, cached = self._health_cache
        if now - cached_at < 5:
            return cached
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{SANDBOX_PROTOCOL}://{SANDBOX_DOMAIN}/health")
            result = response.status_code == 200
        except httpx.HTTPError:
            result = False
        self._health_cache = (now, result)
        return result

    def _connection_config(self):
        from opensandbox.config import ConnectionConfig

        return ConnectionConfig(
            domain=SANDBOX_DOMAIN,
            api_key=SANDBOX_API_KEY,
            protocol=SANDBOX_PROTOCOL,
            use_server_proxy=SANDBOX_USE_SERVER_PROXY,
            request_timeout=timedelta(seconds=SANDBOX_REQUEST_TIMEOUT),
        )

    def _network_policy(self):
        if SANDBOX_EGRESS == "open":
            return None
        from opensandbox.models.sandboxes import NetworkPolicy, NetworkRule

        # Empty allowlist still means deny-all; never fall back to open network.
        return NetworkPolicy(
            defaultAction="deny",
            egress=[NetworkRule(action="allow", target=target) for target in SANDBOX_EGRESS_ALLOW],
        )

    async def _run(
        self,
        sandbox,
        command: str,
        task: Task,
        *,
        timeout: int,
    ) -> list[str]:
        from opensandbox.models.execd import ExecutionHandlers, RunCommandOpts

        lines: list[str] = []

        async def on_output(message) -> None:
            text = _clean(str(getattr(message, "text", message)))
            if not text:
                return
            for line in text.splitlines():
                line = line[:800]
                lines.append(line)
                await task.emit("build_log", line=line)

        handlers = ExecutionHandlers(on_stdout=on_output, on_stderr=on_output, skip_accumulation=True)
        execution = await sandbox.commands.run(
            command,
            opts=RunCommandOpts(working_directory="/workspace", timeout=timedelta(seconds=timeout)),
            handlers=handlers,
        )
        if execution.exit_code != 0:
            tail = "\n".join(lines[-12:])[-2000:]
            raise SandboxError(f"命令失败（exit {execution.exit_code}）：{command}\n{tail}")
        return lines

    async def build(
        self,
        task: Task,
        files: dict[str, str],
        validate: Callable[[dict[str, bytes]], list[tuple[str, bool, str]]] | None = None,
    ) -> BuildResult:
        if not self.enabled:
            raise SandboxError("沙箱未启用：请配置 VIBEFORGE_SANDBOX=opensandbox 与 API Key")
        from opensandbox.sandbox import Sandbox
        from opensandbox.models.execd import RunCommandOpts

        async with self._semaphore:
            started = time.monotonic()
            await task.emit("build_started", image=SANDBOX_IMAGE, files=len(files))
            sandbox = None
            try:
                sandbox = await Sandbox.create(
                    SANDBOX_IMAGE,
                    connection_config=self._connection_config(),
                    timeout=timedelta(seconds=SANDBOX_TTL_SECONDS),
                    ready_timeout=timedelta(seconds=SANDBOX_READY_TIMEOUT),
                    resource={"cpu": SANDBOX_CPU, "memory": SANDBOX_BUILD_MEMORY},
                    env={
                        "NPM_CONFIG_REGISTRY": NPM_REGISTRY,
                        "CI": "1",
                        "NEXT_TELEMETRY_DISABLED": "1",
                    },
                    metadata={"project": task.id, "stack": task.stack},
                    network_policy=self._network_policy(),
                )
                await task.emit("build_log", line=f"sandbox ready · {sandbox.id}")

                entries = []
                for path, content in files.items():
                    relative = PurePosixPath(path)
                    if relative.is_absolute() or ".." in relative.parts:
                        raise SandboxError(f"非法的构建文件路径：{path}")
                    entries.append(
                        {
                            "path": f"/workspace/{relative.as_posix()}",
                            "data": content,
                            "mode": 644,
                        }
                    )
                from opensandbox.models.filesystem import WriteEntry

                await sandbox.files.write_files(
                    [WriteEntry(path=entry["path"], data=entry["data"], mode=entry["mode"]) for entry in entries]
                )
                await task.emit("build_log", line=f"uploaded {len(entries)} source files")

                install_cmd = (
                    "npm ci --ignore-scripts --no-audit --no-fund"
                    if files.get("package-lock.json")
                    else "npm install --ignore-scripts --no-audit --no-fund"
                )
                await self._run(
                    sandbox,
                    install_cmd,
                    task,
                    timeout=NPM_INSTALL_TIMEOUT,
                )
                await self._run(sandbox, "npm run build", task, timeout=NPM_BUILD_TIMEOUT)

                is_next = task.stack == "next"
                artifact_max = NEXT_ARTIFACT_MAX_BYTES if is_next else REACT_DIST_MAX_BYTES
                if is_next:
                    artifact_command = (
                        "cp -r .next/static .next/standalone/.next/static && "
                        "if [ -d public ]; then cp -r public .next/standalone/public; fi && "
                        "tar -czf /tmp/dist.tgz -C .next/standalone ."
                    )
                else:
                    artifact_command = "tar -czf /tmp/dist.tgz -C dist ."
                max_encoded = int(artifact_max * 4 / 3) + 16
                archive = await sandbox.commands.run(
                    f"{artifact_command} && base64 -w0 /tmp/dist.tgz > /tmp/dist.b64 && wc -c < /tmp/dist.b64",
                    opts=RunCommandOpts(
                        working_directory="/workspace", timeout=timedelta(seconds=60)
                    ),
                )
                if archive.exit_code != 0:
                    raise SandboxError("构建产物打包失败")
                size_text = "".join(message.text for message in archive.logs.stdout).strip()
                try:
                    encoded_size = int(size_text.splitlines()[-1])
                except (ValueError, IndexError) as exc:
                    raise SandboxError("无法读取构建产物大小") from exc
                if encoded_size > max_encoded:
                    raise SandboxError("构建产物超过大小限制")

                encoded = await sandbox.files.read_file("/tmp/dist.b64")
                encoded = "".join(encoded.split())
                try:
                    compressed = base64.b64decode(encoded, validate=True)
                except ValueError as exc:
                    raise SandboxError("构建产物解码失败") from exc

                artifact_files = self._extract_artifact(compressed, artifact_max)
                if task.stack == "react" and "index.html" in artifact_files:
                    html = artifact_files["index.html"].decode("utf-8", errors="replace")
                    artifact_files["index.html"] = _sign_asset_urls(html, task.asset_key).encode("utf-8")
                total_bytes = sum(len(value) for value in artifact_files.values())
                if not is_next and "index.html" not in artifact_files:
                    raise SandboxError("构建产物缺少 index.html")
                if validate is not None:
                    failed = [name for name, ok, _ in validate(artifact_files) if not ok]
                    if failed:
                        raise SandboxError("构建产物校验失败：" + "、".join(failed))
                duration = round((time.monotonic() - started) * 1000)
                await task.emit(
                    "build_done",
                    files=len(artifact_files),
                    bytes=total_bytes,
                    duration_ms=duration,
                    sandbox_id=sandbox.id,
                )
                return BuildResult(
                    files=artifact_files,
                    total_bytes=total_bytes,
                    duration_ms=duration,
                    sandbox_id=sandbox.id,
                )
            except Exception as exc:
                message = str(exc)[:2000]
                await task.emit("build_failed", message=message)
                if isinstance(exc, SandboxError):
                    raise
                raise SandboxError(message) from exc
            finally:
                if sandbox is not None:
                    try:
                        await sandbox.destroy()
                    except Exception:  # noqa: BLE001 - cleanup must not mask results
                        logger.warning("sandbox destroy failed for %s", task.id, exc_info=True)

    @staticmethod
    def _extract_artifact(compressed: bytes, max_bytes: int) -> dict[str, bytes]:
        files: dict[str, bytes] = {}
        total = 0
        try:
            with tarfile.open(fileobj=io.BytesIO(compressed), mode="r:gz") as archive:
                for member in archive.getmembers():
                    if member.isdir():
                        continue
                    if not member.isfile():
                        raise SandboxError("构建产物包含非普通文件")
                    relative = PurePosixPath(member.name)
                    if relative.is_absolute() or ".." in relative.parts:
                        raise SandboxError("构建产物包含非法路径")
                    if member.size > max_bytes:
                        raise SandboxError("构建产物单文件超过大小限制")
                    total += member.size
                    if total > max_bytes * 2:
                        raise SandboxError("构建产物解压后超过大小限制")
                    handle = archive.extractfile(member)
                    if handle is None:
                        continue
                    files[relative.as_posix()] = handle.read()
        except tarfile.TarError as exc:
            raise SandboxError("构建产物解压失败") from exc
        return files


sandbox_runner = SandboxRunner()
