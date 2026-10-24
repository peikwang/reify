from __future__ import annotations

import asyncio
import json
import os
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DATA_DIR, MAX_CONCURRENT_TASKS
from .db import db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Task:
    id: str
    prompt: str
    capability: str
    owner_id: str
    status: str = "queued"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    events: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None
    source: str = "director"
    title: str = ""
    revision: int = 0
    stack: str = "static"
    asset_key: str = ""
    visibility: str = "private"
    share_token: str | None = None
    refine_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _seq: int = 0
    _subscribers: set[asyncio.Queue] = field(default_factory=set)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def dir(self) -> Path:
        return DATA_DIR / "users" / self.owner_id / "projects" / self.id

    @property
    def workspace(self) -> Path:
        return self.dir / "workspace"

    @property
    def artifact_dir(self) -> Path:
        if self.stack == "react":
            return self.workspace / "dist"
        if self.stack == "next":
            return self.workspace / "runtime"
        return self.workspace

    @property
    def runtime_dir(self) -> Path:
        return self.workspace / "runtime"

    @property
    def data_dir(self) -> Path:
        return self.dir / "runtime-data"

    @property
    def url(self) -> str:
        return f"/p/{self.id}/"

    def meta(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "capability": self.capability,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "result": self.result,
            "error": self.error,
            "source": self.source,
            "title": self.title,
            "revision": self.revision,
            "stack": self.stack,
            "url": self.url,
            "shared": bool(self.share_token),
            "share_url": f"/s/{self.share_token}/" if self.share_token else None,
            "event_count": len(self.events),
        }

    def to_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "capability": self.capability,
            "stack": self.stack,
            "title": self.title,
            "status": self.status,
            "revision": self.revision,
            "visibility": self.visibility,
            "share_token": self.share_token,
            "asset_key": self.asset_key,
            "prompt": self.prompt,
            "source": self.source,
            "error": self.error,
            "result": self.result,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    async def emit(self, event_type: str, **payload: Any) -> dict[str, Any]:
        async with self._lock:
            self._seq += 1
            seq = self._seq
        event = {"seq": seq, "type": event_type, "ts": _now(), **payload}
        self.events.append(event)
        self.updated_at = _now()
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            with (self.dir / "events.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError:
            pass
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass
        return event

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    def save_meta(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        payload = {**self.meta(), "owner_id": self.owner_id, "asset_key": self.asset_key}
        target = self.dir / "meta.json"
        temp = self.dir / "meta.json.tmp"
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, target)
        db.save_project(self.to_record())


class TaskStore:
    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
        self._loaded = False

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        for record in db.list_all_projects():
            task = self._from_record(record)
            if task:
                if task.status in {"queued", "running", "deploying"}:
                    task.status = "interrupted"
                    task.save_meta()
                self.tasks[task.id] = task

    def reload(self) -> None:
        self.tasks.clear()
        self._loaded = False
        self.ensure_loaded()

    def _from_record(self, record: dict[str, Any]) -> Task | None:
        try:
            task = Task(
                id=record["id"],
                prompt=record.get("prompt", ""),
                capability=record.get("capability", "website"),
                owner_id=record["owner_id"],
                status=record.get("status", "done"),
                created_at=record.get("created_at", _now()),
                updated_at=record.get("updated_at", _now()),
                result=record.get("result"),
                error=record.get("error"),
                source=record.get("source", "director"),
                title=record.get("title", ""),
                revision=int(record.get("revision", 0)),
                stack=record.get("stack", "static"),
                asset_key=record.get("asset_key", ""),
                visibility=record.get("visibility", "private"),
                share_token=record.get("share_token"),
            )
        except (KeyError, TypeError, ValueError):
            return None
        events_path = task.dir / "events.jsonl"
        if events_path.exists():
            try:
                lines = events_path.read_text(encoding="utf-8").splitlines()
            except OSError:
                lines = []
            for line in lines:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                task.events.append(event)
                task._seq = max(task._seq, int(event.get("seq", 0)))
        return task

    def create(
        self,
        prompt: str,
        capability: str,
        title: str = "",
        owner_id: str = "",
        stack: str = "static",
    ) -> Task:
        if not owner_id:
            raise ValueError("owner_id is required")
        task_id = uuid.uuid4().hex[:10]
        share_token = secrets.token_urlsafe(24) if stack != "next" else None
        task = Task(
            id=task_id,
            prompt=prompt,
            capability=capability,
            title=title,
            owner_id=owner_id,
            stack=stack,
            asset_key=secrets.token_hex(16),
            share_token=share_token,
            visibility="share" if share_token else "private",
        )
        task.workspace.mkdir(parents=True, exist_ok=True)
        task.dir.mkdir(parents=True, exist_ok=True)
        task.save_meta()
        self.tasks[task.id] = task
        return task

    def get(self, task_id: str, owner_id: str | None = None) -> Task | None:
        self.ensure_loaded()
        task = self.tasks.get(task_id)
        if task and owner_id is not None and task.owner_id != owner_id:
            return None
        return task

    def get_any(self, task_id: str) -> Task | None:
        self.ensure_loaded()
        return self.tasks.get(task_id)

    def remove(self, task_id: str) -> None:
        self.ensure_loaded()
        self.tasks.pop(task_id, None)

    def list(self, owner_id: str) -> list[dict[str, Any]]:
        self.ensure_loaded()
        tasks = sorted(
            (task for task in self.tasks.values() if task.owner_id == owner_id),
            key=lambda task: task.created_at,
            reverse=True,
        )
        return [task.meta() for task in tasks]

    def semaphore(self) -> asyncio.Semaphore:
        return self._semaphore


store = TaskStore()
