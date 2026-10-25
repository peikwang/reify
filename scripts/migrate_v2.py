#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.db import db  # noqa: E402
from server.migrate import migrate_legacy  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy flat Reify projects to per-user storage.")
    parser.add_argument("--dry-run", action="store_true", help="report without copying or writing")
    parser.add_argument("--admin-id", default="", help="owner user id (defaults to the first admin)")
    args = parser.parse_args()

    admin_id = args.admin_id
    if not admin_id:
        admin = next((user for user in db.list_users() if user.role == "admin"), None)
        if not admin:
            print("No admin user found. Start the app once to bootstrap an admin, then retry.", file=sys.stderr)
            return 2
        admin_id = admin.id

    report = migrate_legacy(admin_id, dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
