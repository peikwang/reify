#!/usr/bin/env python3
"""Phase 2 E2E: React source -> OpenSandbox npm build -> signed dist preview."""
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
PORT = 18120
BASE = f"http://127.0.0.1:{PORT}"
WORK = Path(tempfile.mkdtemp(prefix="reify-react-e2e-"))


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
    try:
        health = httpx.get(BASE + "/api/health", timeout=10).json()
        print("sandbox:", health.get("sandbox"))
        check(health.get("sandbox", {}).get("reachable") is True, "OpenSandbox reachable")

        client = httpx.Client(base_url=BASE, follow_redirects=False, timeout=30)
        register = client.post(
            "/api/auth/register",
            json={"username": "react_e2e", "password": "password123"},
        )
        check(register.status_code == 200, "register")
        user_id = register.json()["user"]["id"]

        created = client.post(
            "/api/projects",
            json={
                "prompt": "为一家独立设计工作室做一个有编辑感的官网",
                "capability": "website",
                "stack": "react",
            },
        )
        check(created.status_code == 200, "create react project")
        project_id = created.json()["task"]["id"]
        check(created.json()["task"]["stack"] == "react", "stack persisted")

        status = "queued"
        detail = {}
        deadline = time.time() + 600
        while time.time() < deadline and status not in {"done", "error"}:
            time.sleep(0.5)
            detail = client.get(f"/api/projects/{project_id}").json()
            status = detail["task"]["status"]
        check(status == "done", f"react build completed (status={status})")
        result = detail["task"]["result"] or {}
        check(result.get("stack") == "react", "result marks react")
        check(bool(result.get("build", {}).get("files")), "build metadata present")

        preview = client.get(f"/p/{project_id}/")
        check(preview.status_code == 200, "react preview 200")
        html = preview.text
        assets = re.findall(r'(?:src|href)="([^"]*assets/[^"]+)"', html)
        check(bool(assets), "built html references hashed assets")
        check(all("k=" in asset for asset in assets), "asset URLs carry capability key")

        anon = httpx.Client(base_url=BASE, follow_redirects=False, timeout=30)
        js_asset = next((asset for asset in assets if asset.endswith(".js") or ".js?" in asset), "")
        check(bool(js_asset), "js asset found")
        asset_path = js_asset[2:] if js_asset.startswith("./") else js_asset
        check(anon.get("/p/" + project_id + "/" + asset_path).status_code == 200, "js asset loads without cookie")
        check(
            anon.get("/p/" + project_id + "/" + asset_path.split("?")[0] + "?k=wrong").status_code == 404,
            "wrong asset key 404",
        )

        dist = WORK / "data" / "users" / user_id / "projects" / project_id / "workspace" / "dist"
        files = [path for path in dist.rglob("*") if path.is_file()] if dist.exists() else []
        check(bool(files), f"dist installed ({len(files)} files)")

        print("\nREACT E2E PASSED")
        return 0
    finally:
        stop_server(process)
        shutil.rmtree(WORK, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
