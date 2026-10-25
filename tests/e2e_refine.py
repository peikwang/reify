#!/usr/bin/env python3
"""Refine E2E using a local OpenAI-compatible mock (no real model/credential)."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
APP_PORT = 18160
LLM_PORT = 18200
BASE = f"http://127.0.0.1:{APP_PORT}"
WORK = Path(tempfile.mkdtemp(prefix="reify-refine-e2e-"))


class MockLLM(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        messages = payload.get("messages") or []
        system = "\n".join(str(item.get("content", "")) for item in messages if item.get("role") == "system")
        user = "\n".join(str(item.get("content", "")) for item in messages if item.get("role") == "user")
        if "创意导演" in system:
            content = json.dumps(
                {
                    "title": "Mock Studio",
                    "tagline": "MOCK TAGLINE",
                    "paragraph": "一个用于验证源码修改链路的本地页面。",
                    "highlights": ["结构", "样式", "交互", "构建"],
                    "accent": "#1e5c40",
                },
                ensure_ascii=False,
            )
        elif "源码编辑" in system:
            source = user.split("当前源码：", 1)[-1].split("用户的修改要求：", 1)[0]
            match = re.search(r"const tagline(?:\s*:\s*string)?\s*=\s*.*?;", source)
            find = match.group(0) if match else ""
            patches = (
                [{"find": find, "replace": 'const tagline: string = "REFINED TAGLINE";', "note": "更新标语"}]
                if find
                else []
            )
            content = json.dumps(
                {"summary": "已更新页面标语", "patches": patches}, ensure_ascii=False
            )
        else:
            content = json.dumps({"summary": "noop", "patches": []}, ensure_ascii=False)
        body = json.dumps({"choices": [{"message": {"content": content}}]}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


def env() -> dict[str, str]:
    return {
        **os.environ,
        "REIFY_DATA": str(WORK / "data"),
        "REIFY_PROJECTS": str(WORK / "legacy"),
        "REIFY_COOKIE_SECURE": "0",
        "REIFY_LLM_ENABLED": "1",
        "REIFY_LLM_BASE_URL": f"http://127.0.0.1:{LLM_PORT}/v1",
        "REIFY_LLM_MODEL": "mock",
        "REIFY_LLM_TIMEOUT": "20",
        "REIFY_STEP_DELAY": "0.02",
        "REIFY_ADMIN_PASSWORD": "e2e-admin-password",
        "REIFY_SANDBOX": "opensandbox",
        "REIFY_SANDBOX_DOMAIN": os.getenv("REIFY_SANDBOX_DOMAIN", "127.0.0.1:8080"),
        "REIFY_SANDBOX_API_KEY": os.getenv("REIFY_SANDBOX_API_KEY", "reify-local-key"),
        "REIFY_SANDBOX_SERVER_PROXY": "1",
        "REIFY_SSR_PREVIEW": "1",
        "REIFY_SSR_PORT": "0",
    }


def start_app(log_path: Path) -> subprocess.Popen:
    handle = log_path.open("ab")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.main:app", "--host", "127.0.0.1", "--port", str(APP_PORT)],
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
    raise RuntimeError(f"app failed to start:\n{log_path.read_text(errors='replace')[-4000:]}")


def stop_process(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"  ok  {message}")


def wait_task(client: httpx.Client, project_id: str, *, revision: int = 0) -> dict:
    deadline = time.time() + 600
    last = {}
    while time.time() < deadline:
        last = client.get(f"/api/projects/{project_id}").json()
        task = last["task"]
        if task["status"] == "error":
            raise AssertionError(f"task error: {task.get('error')}")
        if task["status"] == "done" and int(task.get("revision", 0)) >= revision:
            return last
        failures = [e for e in last.get("events", []) if e.get("type") in {"refine_failed", "error"}]
        if task["status"] == "done" and failures:
            raise AssertionError(f"refine failed: {failures[-1]}")
        time.sleep(0.5)
    raise AssertionError(
        f"task timeout: {last.get('task', {}).get('status')} revision={last.get('task', {}).get('revision')} "
        f"error={last.get('task', {}).get('error')} events={[e for e in last.get('events', []) if e.get('type') in {'error','refine_failed','done','build_failed','runtime_error'}][-8:]}"
    )


def main() -> int:
    mock = ThreadingHTTPServer(("127.0.0.1", LLM_PORT), MockLLM)
    thread = threading.Thread(target=mock.serve_forever, daemon=True)
    thread.start()
    log_path = WORK / "server.log"
    app = start_app(log_path)
    client = httpx.Client(base_url=BASE, follow_redirects=False, timeout=90)
    project_ids: list[str] = []
    try:
        check(
            client.post("/api/auth/register", json={"username": "refine_e2e", "password": "password123"}).status_code
            == 200,
            "register",
        )

        print("1. React source refine")
        created = client.post(
            "/api/projects",
            json={"prompt": "做一个 React 官网", "capability": "website", "stack": "react"},
        )
        check(created.status_code == 200, "create react project")
        react_id = created.json()["task"]["id"]
        project_ids.append(react_id)
        wait_task(client, react_id)
        source = WORK / "data" / "users" / client.get("/api/auth/me").json()["user"]["id"] / "projects" / react_id / "workspace" / "src" / "App.tsx"
        check("MOCK TAGLINE" in source.read_text(encoding="utf-8"), "initial source uses mock brief")
        refined = client.post(f"/api/projects/{react_id}/refine", json={"instruction": "把标语改掉"})
        check(refined.status_code == 200, "react refine accepted")
        detail = wait_task(client, react_id, revision=1)
        check(detail["task"]["revision"] == 1, "react revision incremented")
        check("REFINED TAGLINE" in source.read_text(encoding="utf-8"), "react source patched")
        check(client.get(f"/p/{react_id}/").status_code == 200, "react preview still works")

        print("2. Next source refine + blue-green runtime")
        created = client.post(
            "/api/projects",
            json={"prompt": "做一个 Next 官网", "capability": "website", "stack": "next"},
        )
        check(created.status_code == 200, "create next project")
        next_id = created.json()["task"]["id"]
        project_ids.append(next_id)
        wait_task(client, next_id)
        check(client.post(f"/api/projects/{next_id}/runtime/start").status_code == 200, "runtime started")
        page = client.get(f"/apps/{next_id}/")
        check(page.status_code == 200 and "MOCK TAGLINE" in page.text, "initial SSR page uses mock brief")
        refined = client.post(f"/api/projects/{next_id}/refine", json={"instruction": "把标语改掉"})
        check(refined.status_code == 200, "next refine accepted")
        detail = wait_task(client, next_id, revision=1)
        check(detail["task"]["revision"] == 1, "next revision incremented")
        runtime = client.get(f"/api/projects/{next_id}/runtime").json()["runtime"]
        check(runtime["status"] == "running", "new runtime is running after blue-green")
        page = client.get(f"/apps/{next_id}/")
        check(page.status_code == 200 and "REFINED TAGLINE" in page.text, "SSR page switched to refined build")

        print("\nREFINE E2E PASSED")
        return 0
    finally:
        for project_id in project_ids:
            try:
                client.post(f"/api/projects/{project_id}/runtime/stop")
            except Exception:
                pass
        stop_process(app)
        mock.shutdown()
        shutil.rmtree(WORK, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
