from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DATA_DIR, MAX_CONCURRENT_TASKS, PROJECTS_DIR


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Task:
    id: str
    prompt: str
    capability: str
    status: str = "queued"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    events: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None
    source: str = "director"
    title: str = ""
    revision: int = 0
    refine_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _seq: int = 0
    _subscribers: set[asyncio.Queue] = field(default_factory=set)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def dir(self) -> Path:
        return DATA_DIR / "tasks" / self.id

    @property
    def workspace(self) -> Path:
        return PROJECTS_DIR / self.id

    @property
    def url(self) -> str:
        return f"/tasks/{self.id}/"

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
            "url": self.url,
            "event_count": len(self.events),
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
        target = self.dir / "meta.json"
        temp = self.dir / "meta.json.tmp"
        temp.write_text(json.dumps(self.meta(), ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, target)

    @classmethod
    def from_disk(cls, path: Path) -> "Task | None":
        try:
            meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        task = cls(
            id=meta["id"],
            prompt=meta.get("prompt", ""),
            capability=meta.get("capability", "website"),
            status=meta.get("status", "done"),
            created_at=meta.get("created_at", _now()),
            updated_at=meta.get("updated_at", _now()),
            result=meta.get("result"),
            error=meta.get("error"),
            source=meta.get("source", "director"),
            title=meta.get("title", ""),
            revision=int(meta.get("revision", 0)),
        )
        events_path = path / "events.jsonl"
        if events_path.exists():
            for line in events_path.read_text(encoding="utf-8").splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                task.events.append(event)
                task._seq = max(task._seq, int(event.get("seq", 0)))
        if task.status in {"queued", "running", "deploying"}:
            task.status = "interrupted"
        return task


class TaskStore:
    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
        self._load()

    def _load(self) -> None:
        root = DATA_DIR / "tasks"
        for path in sorted(root.iterdir(), reverse=True):
            if path.is_dir():
                task = Task.from_disk(path)
                if task:
                    self.tasks[task.id] = task

    def create(self, prompt: str, capability: str, title: str = "") -> Task:
        task_id = uuid.uuid4().hex[:10]
        task = Task(id=task_id, prompt=prompt, capability=capability, title=title)
        task.workspace.mkdir(parents=True, exist_ok=True)
        task.dir.mkdir(parents=True, exist_ok=True)
        self.tasks[task.id] = task
        task.save_meta()
        return task

    def get(self, task_id: str) -> Task | None:
        return self.tasks.get(task_id)

    def list(self) -> list[dict[str, Any]]:
        tasks = sorted(self.tasks.values(), key=lambda t: t.created_at, reverse=True)
        return [t.meta() for t in tasks]

    def semaphore(self) -> asyncio.Semaphore:
        return self._semaphore


store = TaskStore()
