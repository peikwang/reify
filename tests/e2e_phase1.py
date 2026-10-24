#!/usr/bin/env python3
"""Local Phase 1 end-to-end check: real uvicorn, real cookies, restart persistence."""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
PORT = 18100
BASE = f"http://127.0.0.1:{PORT}"
WORK = Path(tempfile.mkdtemp(prefix="reify-e2e-"))


def env() -> dict[str, str]:
    return {
        **os.environ,
        "REIFY_DATA": str(WORK / "data"),
        "REIFY_PROJECTS": str(WORK / "legacy"),
        "REIFY_COOKIE_SECURE": "0",
        "REIFY_LLM_ENABLED": "0",
        "REIFY_STEP_DELAY": "0.02",
        "REIFY_ADMIN_PASSWORD": "e2e-admin-password",
    }


def start_server(log_path: Path) -> subprocess.Popen:
    handle = log_path.open("ab")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=ROOT,
        env=env(),
        stdout=handle,
        stderr=subprocess.STDOUT,
    )
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            response = httpx.get(BASE + "/api/health", timeout=1)
            if response.status_code == 200:
                return process
        except httpx.HTTPError:
            pass
        if process.poll() is not None:
            break
        time.sleep(0.2)
    process.terminate()
    raise RuntimeError(f"server failed to start:\n{log_path.read_text(errors='replace')[-4000:]}")


def stop_server(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"  ok  {message}")


def main() -> int:
    log_path = WORK / "server.log"
    process = start_server(log_path)
    try:
        anon = httpx.Client(base_url=BASE, follow_redirects=False, timeout=30)
        alice = httpx.Client(base_url=BASE, follow_redirects=False, timeout=30)
        bob = httpx.Client(base_url=BASE, follow_redirects=False, timeout=30)

        print("1. register users")
        alice_reg = alice.post(
            "/api/auth/register",
            json={"username": "e2e_alice", "password": "password123", "display_name": "Alice"},
        )
        check(alice_reg.status_code == 200, "alice registers")
        alice_id = alice_reg.json()["user"]["id"]
        bob_reg = bob.post(
            "/api/auth/register", json={"username": "e2e_bob", "password": "password123"}
        )
        check(bob_reg.status_code == 200, "bob registers")
        duplicate = anon.post(
            "/api/auth/register", json={"username": "E2E_ALICE", "password": "password123"}
        )
        check(duplicate.status_code == 409, "case-insensitive duplicate rejected")

        print("2. create and wait for a project")
        created = alice.post(
            "/api/projects",
            json={"prompt": "做一个极简作品集网站，包含介绍和联系入口", "capability": "website"},
        )
        check(created.status_code == 200, "alice creates a project")
        project_id = created.json()["task"]["id"]
        status = "queued"
        deadline = time.time() + 60
        while time.time() < deadline and status not in {"done", "error"}:
            time.sleep(0.25)
            detail = alice.get(f"/api/projects/{project_id}")
            status = detail.json()["task"]["status"]
        check(status == "done", f"project completed (status={status})")

        print("3. preview and cross-user isolation")
        check(alice.get(f"/p/{project_id}/").status_code == 200, "owner preview 200")
        check(anon.get(f"/p/{project_id}/").status_code == 303, "anonymous preview redirects to login")
        check(bob.get(f"/p/{project_id}/").status_code == 404, "other user preview 404")
        check(bob.get(f"/api/projects/{project_id}").status_code == 404, "other user API 404")
        check(bob.get("/api/projects").json()["items"] == [], "other user list is empty")
        check(
            bob.get(f"/api/projects/{project_id}/bundle").status_code == 404,
            "other user bundle 404",
        )
        check(
            bob.post(
                f"/api/projects/{project_id}/refine", json={"instruction": "改标题"}
            ).status_code
            == 404,
            "other user refine 404",
        )

        print("4. media capability key")
        project_dir = WORK / "data" / "users" / alice_id / "projects" / project_id
        meta = json.loads((project_dir / "meta.json").read_text(encoding="utf-8"))
        assets = project_dir / "workspace" / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        (assets / "e2e.png").write_bytes(b"png-bytes")
        key = meta["asset_key"]
        check(
            anon.get(f"/media/{project_id}/assets/e2e.png?k={key}").status_code == 200,
            "valid media key is public",
        )
        check(
            anon.get(f"/media/{project_id}/assets/e2e.png?k=wrong").status_code == 404,
            "wrong media key 404",
        )

        print("5. restart persistence")
        alice_cookie = alice.cookies.get("reify_session")
        stop_server(process)
        process = start_server(log_path)
        restarted = httpx.Client(base_url=BASE, follow_redirects=False, timeout=30)
        restarted.cookies.set("reify_session", alice_cookie)
        me = restarted.get("/api/auth/me").json()
        check(me["authenticated"] is True and me["user"]["username"] == "e2e_alice", "session survives restart")
        items = restarted.get("/api/projects").json()["items"]
        check(len(items) == 1 and items[0]["id"] == project_id, "project survives restart")
        check(restarted.get(f"/p/{project_id}/").status_code == 200, "preview survives restart")
        check(restarted.get(f"/media/{project_id}/assets/e2e.png?k={key}").status_code == 200, "media survives restart")

        print("6. logout revokes the server-side session")
        check(restarted.post("/api/auth/logout").status_code == 200, "logout")
        stale = httpx.Client(base_url=BASE, follow_redirects=False, timeout=30)
        stale.cookies.set("reify_session", alice_cookie)
        check(stale.get("/api/auth/me").json()["authenticated"] is False, "old session rejected")

        print("\nE2E PASSED")
        return 0
    finally:
        stop_server(process)
        shutil.rmtree(WORK, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
