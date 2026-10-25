from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  username TEXT NOT NULL,
  username_key TEXT NOT NULL,
  email TEXT,
  email_key TEXT,
  display_name TEXT NOT NULL DEFAULT '',
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user',
  token_version INTEGER NOT NULL DEFAULT 0,
  disabled INTEGER NOT NULL DEFAULT 0,
  created_ip TEXT,
  created_at TEXT NOT NULL,
  last_login_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_key ON users(username_key);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_key ON users(email_key) WHERE email_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  token_hash TEXT NOT NULL UNIQUE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  last_seen_at TEXT,
  revoked_at TEXT,
  ip TEXT,
  user_agent TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL REFERENCES users(id),
  capability TEXT NOT NULL,
  stack TEXT NOT NULL DEFAULT 'static',
  title TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'queued',
  revision INTEGER NOT NULL DEFAULT 0,
  visibility TEXT NOT NULL DEFAULT 'private',
  share_token TEXT UNIQUE,
  asset_key TEXT NOT NULL,
  prompt TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT 'director',
  error TEXT,
  result_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_id, created_at DESC);

CREATE TABLE IF NOT EXISTS runtimes (
  project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  revision INTEGER NOT NULL,
  backend TEXT NOT NULL,
  sandbox_id TEXT,
  endpoint TEXT,
  status TEXT NOT NULL,
  image TEXT NOT NULL,
  process_id TEXT,
  port INTEGER,
  started_at TEXT,
  last_active_at TEXT,
  expires_at TEXT,
  stopped_at TEXT,
  stop_reason TEXT,
  error TEXT
);

CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  user_id TEXT,
  action TEXT NOT NULL,
  project_id TEXT,
  ip TEXT,
  detail TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts DESC);
"""

RUNTIME_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_runtimes_status_activity
  ON runtimes(status, last_active_at);
CREATE INDEX IF NOT EXISTS idx_runtimes_expiry
  ON runtimes(status, expires_at);
CREATE INDEX IF NOT EXISTS idx_runtimes_kind_status
  ON runtimes(kind, status);
"""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat(timespec="seconds")


def new_id(prefix: str = "") -> str:
    return prefix + uuid.uuid4().hex[:12]


@dataclass(frozen=True)
class User:
    id: str
    username: str
    display_name: str
    email: str | None
    role: str
    disabled: bool
    created_at: str
    last_login_at: str | None
    token_version: int
    password_hash: str = ""

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at,
        }


def _user_from_row(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        username=row["username"],
        display_name=row["display_name"] or row["username"],
        email=row["email"],
        role=row["role"],
        disabled=bool(row["disabled"]),
        created_at=row["created_at"],
        last_login_at=row["last_login_at"],
        token_version=int(row["token_version"]),
        password_hash=row["password_hash"],
    )


class Database:
    def __init__(self, path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA busy_timeout=5000")
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._ensure_columns()
            self._conn.executescript(RUNTIME_INDEXES)
            self._conn.commit()
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    def _ensure_columns(self) -> None:
        columns = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(runtimes)").fetchall()
        }
        additions = {
            "process_id": "TEXT",
            "port": "INTEGER",
            "started_at": "TEXT",
            "kind": "TEXT NOT NULL DEFAULT 'next'",
            "expires_at": "TEXT",
            "stopped_at": "TEXT",
            "stop_reason": "TEXT",
        }
        for name, sql_type in additions.items():
            if name not in columns:
                self._conn.execute(f"ALTER TABLE runtimes ADD COLUMN {name} {sql_type}")

    # ---- users ---------------------------------------------------------
    def create_user(
        self,
        *,
        username: str,
        username_key: str,
        email: str | None,
        email_key: str | None,
        display_name: str,
        password_hash: str,
        role: str = "user",
        created_ip: str | None = None,
    ) -> User:
        user_id = new_id("u_")
        created_at = iso_utc()
        with self._lock:
            try:
                self._conn.execute(
                    """INSERT INTO users
                       (id, username, username_key, email, email_key, display_name,
                        password_hash, role, created_ip, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user_id,
                        username,
                        username_key,
                        email,
                        email_key,
                        display_name,
                        password_hash,
                        role,
                        created_ip,
                        created_at,
                    ),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
            row = self._conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _user_from_row(row)

    def get_user(self, user_id: str) -> User | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _user_from_row(row) if row else None

    def get_user_by_key(self, username_key: str) -> User | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM users WHERE username_key = ?", (username_key,)
            ).fetchone()
        return _user_from_row(row) if row else None

    def get_user_by_login(self, login_key: str) -> User | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM users WHERE username_key = ? OR email_key = ?",
                (login_key, login_key),
            ).fetchone()
        return _user_from_row(row) if row else None

    def list_users(self) -> list[User]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM users ORDER BY created_at ASC").fetchall()
        return [_user_from_row(row) for row in rows]

    def count_users(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()
        return int(row["n"])

    def count_admins(self) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM users WHERE role = 'admin' AND disabled = 0"
            ).fetchone()
        return int(row["n"])

    def set_user_disabled(self, user_id: str, disabled: bool) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE users SET disabled = ? WHERE id = ?", (1 if disabled else 0, user_id)
            )
            self._conn.commit()

    def set_user_role(self, user_id: str, role: str) -> None:
        with self._lock:
            self._conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
            self._conn.commit()

    def update_password(self, user_id: str, password_hash: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE users SET password_hash = ?, token_version = token_version + 1 WHERE id = ?",
                (password_hash, user_id),
            )
            self._conn.commit()

    def touch_login(self, user_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE users SET last_login_at = ? WHERE id = ?", (iso_utc(), user_id)
            )
            self._conn.commit()

    # ---- sessions ------------------------------------------------------
    def create_session(
        self,
        *,
        user_id: str,
        token_hash: str,
        expires_at: str,
        ip: str | None,
        user_agent: str | None,
    ) -> str:
        session_id = new_id("s_")
        with self._lock:
            self._conn.execute(
                """INSERT INTO sessions
                   (id, token_hash, user_id, created_at, expires_at, ip, user_agent)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, token_hash, user_id, iso_utc(), expires_at, ip, user_agent),
            )
            self._conn.commit()
        return session_id

    def get_session(self, token_hash: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                """SELECT s.id AS session_id, s.expires_at, s.revoked_at, s.last_seen_at,
                          u.*
                   FROM sessions s JOIN users u ON u.id = s.user_id
                   WHERE s.token_hash = ?""",
                (token_hash,),
            ).fetchone()
        if not row:
            return None
        return {
            "session_id": row["session_id"],
            "expires_at": row["expires_at"],
            "revoked_at": row["revoked_at"],
            "last_seen_at": row["last_seen_at"],
            "user": _user_from_row(row),
        }

    def touch_session(self, session_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE sessions SET last_seen_at = ? WHERE id = ?", (iso_utc(), session_id)
            )
            self._conn.commit()

    def revoke_session(self, token_hash: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
                (iso_utc(), token_hash),
            )
            self._conn.commit()

    def revoke_user_sessions(self, user_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
                (iso_utc(), user_id),
            )
            self._conn.commit()

    def cleanup_sessions(self, before: str | None = None) -> int:
        cutoff = before or iso_utc(utc_now() - timedelta(days=1))
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM sessions WHERE expires_at < ? OR (revoked_at IS NOT NULL AND revoked_at < ?)",
                (iso_utc(), cutoff),
            )
            self._conn.commit()
        return cursor.rowcount

    # ---- projects ------------------------------------------------------
    def save_project(self, data: dict[str, Any]) -> None:
        result = data.get("result")
        with self._lock:
            try:
                self._conn.execute(
                    """INSERT INTO projects
                       (id, owner_id, capability, stack, title, status, revision, visibility,
                        share_token, asset_key, prompt, source, error, result_json,
                        created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET
                         owner_id = excluded.owner_id,
                         capability = excluded.capability,
                         stack = excluded.stack,
                         title = excluded.title,
                         status = excluded.status,
                         revision = excluded.revision,
                         visibility = excluded.visibility,
                         share_token = excluded.share_token,
                         asset_key = excluded.asset_key,
                         prompt = excluded.prompt,
                         source = excluded.source,
                         error = excluded.error,
                         result_json = excluded.result_json,
                         updated_at = excluded.updated_at""",
                    (
                        data["id"],
                        data["owner_id"],
                        data.get("capability", "website"),
                        data.get("stack", "static"),
                        data.get("title", ""),
                        data.get("status", "queued"),
                        int(data.get("revision", 0)),
                        data.get("visibility", "private"),
                        data.get("share_token"),
                        data["asset_key"],
                        data.get("prompt", ""),
                        data.get("source", "director"),
                        data.get("error"),
                        json.dumps(result, ensure_ascii=False) if result is not None else None,
                        data.get("created_at", iso_utc()),
                        data.get("updated_at", iso_utc()),
                    ),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    @staticmethod
    def _project_from_row(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        try:
            data["result"] = json.loads(data.pop("result_json")) if data.get("result_json") else None
        except ValueError:
            data["result"] = None
            data.pop("result_json", None)
        return data

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        return self._project_from_row(row) if row else None

    def list_projects(self, owner_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM projects WHERE owner_id = ? ORDER BY created_at DESC",
                (owner_id,),
            ).fetchall()
        return [self._project_from_row(row) for row in rows]

    def list_all_projects(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM projects ORDER BY created_at DESC"
            ).fetchall()
        return [self._project_from_row(row) for row in rows]

    def delete_project(self, project_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM runtimes WHERE project_id = ?", (project_id,))
            self._conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            self._conn.commit()

    # ---- runtimes ------------------------------------------------------
    def save_runtime(self, data: dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO runtimes
                   (project_id, kind, revision, backend, sandbox_id, endpoint, status, image,
                    process_id, port, started_at, last_active_at, expires_at, stopped_at,
                    stop_reason, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(project_id) DO UPDATE SET
                     kind = excluded.kind,
                     revision = excluded.revision,
                     backend = excluded.backend,
                     sandbox_id = excluded.sandbox_id,
                     endpoint = excluded.endpoint,
                     status = excluded.status,
                     image = excluded.image,
                     process_id = excluded.process_id,
                     port = excluded.port,
                     started_at = excluded.started_at,
                     last_active_at = excluded.last_active_at,
                     expires_at = excluded.expires_at,
                     stopped_at = excluded.stopped_at,
                     stop_reason = excluded.stop_reason,
                     error = excluded.error""",
                (
                    data["project_id"],
                    data.get("kind") or "next",
                    int(data.get("revision", 0)),
                    data.get("backend", "opensandbox"),
                    data.get("sandbox_id"),
                    data.get("endpoint"),
                    data.get("status", "stopped"),
                    data.get("image", ""),
                    data.get("process_id"),
                    data.get("port"),
                    data.get("started_at"),
                    data.get("last_active_at"),
                    data.get("expires_at"),
                    data.get("stopped_at"),
                    data.get("stop_reason"),
                    data.get("error"),
                ),
            )
            self._conn.commit()

    def get_runtime(self, project_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM runtimes WHERE project_id = ?", (project_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_runtimes(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM runtimes").fetchall()
        return [dict(row) for row in rows]

    # ---- audit / sharing ----------------------------------------------
    def log_audit(
        self,
        action: str,
        *,
        user_id: str | None = None,
        project_id: str | None = None,
        ip: str | None = None,
        detail: str | None = None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO audit_log (ts, user_id, action, project_id, ip, detail) VALUES (?, ?, ?, ?, ?, ?)",
                (iso_utc(), user_id, action, project_id, ip, detail),
            )
            self._conn.commit()

    def list_audit(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (max(1, min(limit, 500)),)
            ).fetchall()
        return [dict(row) for row in rows]

    def get_project_by_share_token(self, token: str) -> dict[str, Any] | None:
        if not token:
            return None
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM projects WHERE share_token = ? AND visibility = 'share'",
                (token,),
            ).fetchone()
        return self._project_from_row(row) if row else None

    def set_project_share(
        self, project_id: str, token: str | None, visibility: str
    ) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE projects SET share_token = ?, visibility = ?, updated_at = ? WHERE id = ?",
                (token, visibility, iso_utc(), project_id),
            )
            self._conn.commit()


db = Database(DB_PATH)
