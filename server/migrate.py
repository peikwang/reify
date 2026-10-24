from __future__ import annotations

import json
import logging
import re
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DATA_DIR, PROJECTS_DIR, USERS_DIR
from .db import db

logger = logging.getLogger("reify.migrate")

_TEXT_SUFFIXES = {".html", ".json", ".js", ".css", ".md", ".txt"}


def _rewrite_asset_urls(workspace: Path, project_id: str, asset_key: str) -> None:
    pattern = re.compile(
        r"(/media/" + re.escape(project_id) + r"/[^\"'\s?]+)(\?[^\"'\s]*)?"
    )

    def replace(match: re.Match[str]) -> str:
        base, query = match.group(1), match.group(2) or ""
        if "k=" in query:
            query = re.sub(r"([?&])k=[^&]*", lambda item: item.group(1) + "k=" + asset_key, query)
            return base + query
        return base + query + ("&" if query else "?") + "k=" + asset_key

    for path in workspace.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        updated = pattern.sub(replace, text)
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def _read_meta(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _mtime(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(
            timespec="seconds"
        )
    except OSError:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")


def migrate_legacy(admin_id: str, *, dry_run: bool = False) -> dict[str, Any]:
    legacy_tasks = DATA_DIR / "tasks"
    report: dict[str, Any] = {"migrated": [], "skipped": [], "errors": []}
    ids: set[str] = set()
    if legacy_tasks.exists():
        for path in legacy_tasks.iterdir():
            if path.is_dir():
                ids.add(path.name)
    if PROJECTS_DIR.exists():
        for path in PROJECTS_DIR.iterdir():
            if path.is_dir() and not path.name.startswith("."):
                ids.add(path.name)

    for project_id in sorted(ids):
        task_dir = legacy_tasks / project_id
        workspace_dir = PROJECTS_DIR / project_id
        meta_path = task_dir / "meta.json"
        if db.get_project(project_id):
            report["skipped"].append(project_id)
            continue
        meta = _read_meta(meta_path)
        if not meta and not workspace_dir.exists():
            continue
        target = USERS_DIR / admin_id / "projects" / project_id
        previous_meta = _read_meta(target / "meta.json")
        asset_key = str(
            meta.get("asset_key") or previous_meta.get("asset_key") or secrets.token_hex(16)
        )
        if dry_run:
            report["migrated"].append({"id": project_id, "target": str(target), "dry_run": True})
            continue
        try:
            target.mkdir(parents=True, exist_ok=True)
            if meta_path.exists():
                shutil.copy2(meta_path, target / "meta.json")
            events_path = task_dir / "events.jsonl"
            if events_path.exists():
                events_text = events_path.read_text(encoding="utf-8")
                events_text = events_text.replace(f'"/tasks/{project_id}/', f'"/p/{project_id}/')
                (target / "events.jsonl").write_text(events_text, encoding="utf-8")
            if workspace_dir.exists():
                shutil.copytree(workspace_dir, target / "workspace", dirs_exist_ok=True)
            else:
                (target / "workspace").mkdir(parents=True, exist_ok=True)
            _rewrite_asset_urls(target / "workspace", project_id, asset_key)
            created = str(meta.get("created_at") or _mtime(workspace_dir if workspace_dir.exists() else target))
            updated = str(meta.get("updated_at") or created)
            result = meta.get("result")
            if isinstance(result, dict) and isinstance(result.get("url"), str):
                result = {**result, "url": result["url"].replace(f"/tasks/{project_id}/", f"/p/{project_id}/")}
            record = {
                "id": project_id,
                "owner_id": admin_id,
                "capability": str(meta.get("capability") or "website"),
                "stack": str(meta.get("stack") or "static"),
                "title": str(meta.get("title") or "Legacy project"),
                "status": str(meta.get("status") or "done"),
                "revision": int(meta.get("revision") or 0),
                "visibility": str(meta.get("visibility") or "private"),
                "share_token": meta.get("share_token"),
                "asset_key": asset_key,
                "prompt": str(meta.get("prompt") or ""),
                "source": str(meta.get("source") or "director"),
                "error": meta.get("error"),
                "result": result,
                "created_at": created,
                "updated_at": updated,
            }
            merged = {
                **meta,
                "id": project_id,
                "owner_id": admin_id,
                "asset_key": record["asset_key"],
                "stack": record["stack"],
                "result": result,
            }
            (target / "meta.json").write_text(
                json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            db.save_project(record)
            if task_dir.exists():
                (task_dir / ".migrated").write_text(created, encoding="utf-8")
            report["migrated"].append({"id": project_id, "target": str(target)})
        except Exception as exc:  # noqa: BLE001 - report and keep legacy data intact
            logger.exception("legacy migration failed for %s", project_id)
            report["errors"].append({"id": project_id, "error": str(exc)})

    return report
