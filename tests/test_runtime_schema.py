from __future__ import annotations

import sqlite3

from server.db import Database


def test_old_runtimes_table_is_migrated(tmp_path):
    path = tmp_path / "old.db"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE projects (id TEXT PRIMARY KEY, owner_id TEXT, created_at TEXT);
        CREATE TABLE runtimes (
          project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
          revision INTEGER NOT NULL,
          backend TEXT NOT NULL,
          sandbox_id TEXT,
          endpoint TEXT,
          status TEXT NOT NULL,
          image TEXT NOT NULL,
          last_active_at TEXT,
          error TEXT
        );
        INSERT INTO projects(id, owner_id, created_at) VALUES ('p1', 'u1', '2026-01-01');
        INSERT INTO runtimes(project_id, revision, backend, status, image)
          VALUES ('p1', 1, 'opensandbox', 'stopped', 'node:24');
        """
    )
    connection.commit()
    connection.close()

    db = Database(path)
    record = db.get_runtime("p1")
    assert record is not None
    assert record["kind"] == "next"
    columns = {row["name"] for row in db._conn.execute("PRAGMA table_info(runtimes)")}
    assert {"kind", "expires_at", "stopped_at", "stop_reason"} <= columns
    indexes = {row[1] for row in db._conn.execute("PRAGMA index_list(runtimes)")}
    assert {
        "idx_runtimes_status_activity",
        "idx_runtimes_expiry",
        "idx_runtimes_kind_status",
    } <= indexes
