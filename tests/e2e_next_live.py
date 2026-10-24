#!/usr/bin/env python3
"""Live Next.js runtime UI E2E: build -> start -> 12889 iframe -> server API.

Usage:
    VIBEFORGE_E2E_BASE=https://117.148.166.55:12888 .venv/bin/python tests/e2e_next_live.py
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("VIBEFORGE_E2E_BASE", "").rstrip("/")
if not BASE:
    raise SystemExit("VIBEFORGE_E2E_BASE is required")
ARTIFACTS = Path(tempfile.mkdtemp(prefix="vibeforge-next-live-"))


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"  ok  {message}")


def post_json(request, path: str, payload: dict):
    return request.post(
        BASE + path,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )


def main() -> int:
    username = "next_ui_" + str(int(time.time()))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 960}, ignore_https_errors=True
        )
        request = context.request
        registered = post_json(
            request,
            "/api/auth/register",
            {"username": username, "password": "next-ui-password", "display_name": "Next UI E2E"},
        )
        check(registered.status == 200, "register live user")

        created = post_json(
            request,
            "/api/projects",
            {
                "prompt": "用 Next.js 15 App Router 和 SSR 做一个带服务端留言板的官网，需要 /api/notes 接口",
                "capability": "website",
            },
        )
        check(created.status == 200, "create Next project")
        task = created.json()["task"]
        check(task["stack"] == "next", "prompt routed to Next automatically")
        project_id = task["id"]

        deadline = time.time() + 480
        events: list[dict] = []
        while time.time() < deadline:
            detail = request.get(BASE + f"/api/projects/{project_id}").json()
            task = detail["task"]
            events = detail.get("events", [])
            if task["status"] == "error":
                raise AssertionError(f"Next build failed: {task.get('error')}")
            if task["status"] == "done":
                break
            time.sleep(1)
        check(task.get("status") == "done", "Next build completed")
        build_logs = [event for event in events if event.get("type") == "build_log"]
        check(bool(build_logs), "build logs streamed")

        page = context.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(BASE + f"/projects/{project_id}", wait_until="networkidle")
        page.get_by_role("button", name="启动应用").click()
        page.get_by_role("button", name="停止应用").wait_for(timeout=180_000)
        check("APP RUNNING" in page.locator(".workspace-actions").inner_text(), "runtime running")

        iframe = page.locator("iframe[title='生成结果预览']")
        src = iframe.get_attribute("src") or ""
        check(":12889/apps/" in src, f"iframe uses the SSR origin ({src})")
        frame = page.frame_locator("iframe[title='生成结果预览']")
        frame.get_by_role("heading", name=re.compile("不是模板")).wait_for(timeout=60_000)
        frame.locator(".notes").wait_for(timeout=60_000)
        page.wait_for_timeout(800)  # let the client component hydrate before typing
        board = frame.get_by_label("留言")
        board.fill("来自 12889 iframe 的留言")
        frame.get_by_role("button", name="发送").click()
        frame.get_by_text("来自 12889 iframe 的留言").wait_for(timeout=30_000)
        check(True, "Next server route works inside the sandboxed iframe")
        check(not errors, f"no page errors ({errors[:2]})")
        page.screenshot(path=str(ARTIFACTS / "next-ui.png"), full_page=True)

        page.get_by_role("button", name="停止应用").click()
        page.get_by_role("button", name="启动应用").wait_for(timeout=60_000)
        check(True, "runtime stopped")
        browser.close()

    print(f"\nNEXT UI E2E PASSED\nartifacts: {ARTIFACTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
