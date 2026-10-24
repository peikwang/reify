#!/usr/bin/env python3
"""Live generic-template E2E: website / resume / travel / code against a deployment."""
from __future__ import annotations

import io
import json
import os
import tempfile
import time
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("REIFY_E2E_BASE", "").rstrip("/")
if not BASE:
    raise SystemExit("REIFY_E2E_BASE is required")
ARTIFACTS = Path(tempfile.mkdtemp(prefix="reify-longtail-live-"))


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


def wait_project(request, project_id: str) -> dict:
    deadline = time.time() + 600
    last: dict = {}
    while time.time() < deadline:
        detail = request.get(BASE + f"/api/projects/{project_id}").json()
        task = detail["task"]
        last = task
        if task["status"] == "error":
            raise AssertionError(f"project failed: {task.get('error')}")
        if task["status"] == "done":
            return task
        time.sleep(1)
    raise AssertionError(f"project timeout: {last}")


def main() -> int:
    username = "longtail_" + str(int(time.time()))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 960}, ignore_https_errors=True
        )
        request = context.request
        registered = post_json(
            request,
            "/api/auth/register",
            {"username": username, "password": "longtail-password", "display_name": "Longtail E2E"},
        )
        check(registered.status == 200, "register live user")

        only = {
            item.strip()
            for item in os.environ.get("REIFY_E2E_CASES", "").split(",")
            if item.strip()
        }
        cases = [
            ("website", "做一个街角咖啡店官网，要有菜单和到店信息", ("咖啡", "coffee")),
            ("resume", "做一份学术科研简历，强调论文和田野调查", ("学术", "研究", "research")),
            ("travel", "做一份海岛露营攻略，两天一夜", ("海岛", "露营", "camp")),
            ("code", "写一个二分查找并做一个可视化页面", ("二分", "binary")),
        ]
        for capability, prompt, markers in cases:
            if only and capability not in only:
                continue
            print(f"{capability}: {prompt}")
            created = post_json(
                request,
                "/api/projects",
                {"prompt": prompt, "capability": capability},
            )
            check(created.status == 200, f"create {capability}")
            project_id = created.json()["task"]["id"]
            task = wait_project(request, project_id)
            check(task["status"] == "done", f"{capability} completed")
            html = request.get(BASE + f"/p/{project_id}/").text()
            check('name="reify-longtail"' in html, f"{capability} used generic generation")
            lowered = html.lower()
            check(any(marker.lower() in lowered for marker in markers), f"{capability} follows the prompt")
            checks = (task.get("result") or {}).get("checks") or []
            check(bool(checks) and all(item["ok"] for item in checks), f"{capability} checks passed")
            if capability == "code":
                bundle = request.get(BASE + f"/api/projects/{project_id}/bundle")
                with zipfile.ZipFile(io.BytesIO(bundle.body())) as archive:
                    source = archive.read("main.py").decode("utf-8")
                check("def " in source and ("binary" in source.lower() or "二分" in source), "custom main.py bundled")
            page = context.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(BASE + f"/p/{project_id}/", wait_until="networkidle")
            check(page.locator("body").inner_text() != "", f"{capability} renders in Chrome")
            check(not errors, f"{capability} has no page errors")
            page.screenshot(path=str(ARTIFACTS / f"{capability}.png"), full_page=True)
            page.close()

        browser.close()

    print(f"\nLONGTAIL LIVE E2E PASSED\nartifacts: {ARTIFACTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
