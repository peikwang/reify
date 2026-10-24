#!/usr/bin/env python3
"""Phase 3 E2E: Next.js source -> sandbox standalone -> runtime -> SSR proxy."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
PORT = 18130
BASE = f"http://127.0.0.1:{PORT}"
WORK = Path(tempfile.mkdtemp(prefix="reify-next-e2e-"))


def env() -> dict[str, str]:
    return {
        **os.environ,
        "REIFY_DATA": str(WORK / "data"),
        "REIFY_PROJECTS": str(WORK / "legacy"),
        "REIFY_COOKIE_SECURE": "0",
        "REIFY_LLM_ENABLED": "0",
        "REIFY_STEP_DELAY": "0.02",
        "REIFY_ADMIN_PASSWORD": "e2e-admin-password",
        "REIFY_SANDBOX": "opensandbox",
        "REIFY_SANDBOX_DOMAIN": os.getenv("REIFY_SANDBOX_DOMAIN", "127.0.0.1:8080"),
        "REIFY_SANDBOX_API_KEY": os.getenv("REIFY_SANDBOX_API_KEY", "reify-local-key"),
        "REIFY_SANDBOX_SERVER_PROXY": "1",
        "REIFY_SSR_PREVIEW": "1",
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
            if httpx.get(BASE + "/api/health", timeout=1).status_code == 200:
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
    client = httpx.Client(base_url=BASE, follow_redirects=False, timeout=90)
    project_id = ""
    try:
        health = httpx.get(BASE + "/api/health", timeout=10).json()
        check(health.get("sandbox", {}).get("reachable") is True, "OpenSandbox reachable")

        register = client.post(
            "/api/auth/register",
            json={"username": "next_e2e", "password": "password123"},
        )
        check(register.status_code == 200, "register")

        created = client.post(
            "/api/projects",
            json={
                "prompt": "做一个带服务端留言板的 Next.js 官网",
                "capability": "website",
                "stack": "next",
            },
        )
        check(created.status_code == 200, "create next project")
        project_id = created.json()["task"]["id"]
        check(created.json()["task"]["stack"] == "next", "stack persisted")

        status = "queued"
        detail = {}
        deadline = time.time() + 600
        while time.time() < deadline and status not in {"done", "error"}:
            time.sleep(0.5)
            detail = client.get(f"/api/projects/{project_id}").json()
            status = detail["task"]["status"]
        check(status == "done", f"next build completed (status={status})")
        result = detail["task"]["result"] or {}
        check(result.get("stack") == "next", "result marks next")
        check(bool(result.get("build", {}).get("files")), "build metadata present")

        started = client.post(f"/api/projects/{project_id}/runtime/start")
        check(started.status_code == 200, "runtime started")
        runtime = started.json()["runtime"]
        check(runtime["status"] == "running", "runtime is running")

        page = client.get(f"/apps/{project_id}/")
        check(page.status_code == 200, "SSR page 200")
        check("<title>Lumen Studio" in page.text, "SSR page rendered on server")
        assets = re.findall(r'/apps/' + project_id + r'/_next/static/[^"]+\.js', page.text)
        check(bool(assets), "SSR page references Next assets")
        check(client.get(assets[0]).status_code == 200, "Next asset loads through proxy")

        before = client.get(f"/apps/{project_id}/api/notes").json()["notes"]
        posted = client.post(f"/apps/{project_id}/api/notes", json={"text": "E2E note"})
        check(posted.status_code == 200, "server route POST works")
        after = posted.json()["notes"]
        check(len(after) == len(before) + 1 and after[-1]["text"] == "E2E note", "server state updated")

        stopped = client.post(f"/api/projects/{project_id}/runtime/stop")
        check(stopped.status_code == 200, "runtime stopped")
        check(stopped.json()["runtime"]["status"] == "stopped", "runtime status stopped")
        check(client.get(f"/apps/{project_id}/").status_code == 503, "proxy refuses stopped runtime")

        print("\nNEXT E2E PASSED")
        return 0
    finally:
        if project_id:
            try:
                client.post(f"/api/projects/{project_id}/runtime/stop")
            except Exception:
                pass
        stop_server(process)
        shutil.rmtree(WORK, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
