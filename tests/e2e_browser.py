#!/usr/bin/env python3
"""Phase 4-6 browser E2E: real uvicorn + real Chrome + mock LLM, no sandbox required."""
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
from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
APP_PORT = 18190
LLM_PORT = 18210
BASE = f"http://127.0.0.1:{APP_PORT}"
WORK = Path(tempfile.mkdtemp(prefix="vibeforge-browser-e2e-"))
ARTIFACTS = Path(tempfile.mkdtemp(prefix="vibeforge-browser-artifacts-"))


class MockLLM(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        messages = payload.get("messages") or []
        system = "\n".join(
            str(item.get("content", "")) for item in messages if item.get("role") == "system"
        )
        user = "\n".join(
            str(item.get("content", "")) for item in messages if item.get("role") == "user"
        )
        if "创意导演" in system:
            content = json.dumps(
                {
                    "title": "E2E Static",
                    "tagline": "BROWSER CHECK",
                    "paragraph": "一个用于端到端验证的静态页面。",
                    "highlights": ["结构", "样式", "交互", "构建"],
                    "accent": "#1e5c40",
                },
                ensure_ascii=False,
            )
        elif "页面编辑 Agent" in system:
            match = re.search(r"<title>.*?</title>", user)
            find = match.group(0) if match else ""
            patches = (
                [{"find": find, "replace": "<title>E2E Refined</title>", "note": "更新标题"}]
                if find
                else []
            )
            content = json.dumps(
                {"summary": "已更新页面标题", "patches": patches}, ensure_ascii=False
            )
        else:
            content = json.dumps({"summary": "noop", "patches": []}, ensure_ascii=False)
        body = json.dumps({"choices": [{"message": {"content": content}}]}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:
        return


def server_env() -> dict[str, str]:
    return {
        **os.environ,
        "VIBEFORGE_DATA": str(WORK / "data"),
        "VIBEFORGE_PROJECTS": str(WORK / "legacy"),
        "VIBEFORGE_COOKIE_SECURE": "0",
        "VIBEFORGE_UI": "legacy",  # must be ignored after Phase 6 cutover
        "VIBEFORGE_LLM_ENABLED": "1",
        "VIBEFORGE_LLM_BASE_URL": f"http://127.0.0.1:{LLM_PORT}/v1",
        "VIBEFORGE_LLM_MODEL": "mock",
        "VIBEFORGE_LLM_TIMEOUT": "20",
        "VIBEFORGE_STEP_DELAY": "0.02",
        "VIBEFORGE_SANDBOX": "off",
        "VIBEFORGE_ADMIN_PASSWORD": "browser-e2e-admin",
        "VIBEFORGE_REGISTRATION": "open",
    }


def start_server(log_path: Path) -> subprocess.Popen:
    handle = log_path.open("ab")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.main:app", "--host", "127.0.0.1", "--port", str(APP_PORT)],
        cwd=ROOT,
        env=server_env(),
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


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"  ok  {message}")


def wait_project(page: Page, project_id: str, revision: int = 0) -> dict:
    deadline = time.time() + 90
    last: dict = {}
    while time.time() < deadline:
        response = page.request.get(BASE + f"/api/projects/{project_id}")
        if response.ok:
            last = response.json()["task"]
            if last["status"] == "error":
                raise AssertionError(f"project failed: {last.get('error')}")
            if last["status"] == "done" and int(last.get("revision", 0)) >= revision:
                return last
        time.sleep(0.25)
    raise AssertionError(f"project timeout: {last}")


def main() -> int:
    mock = ThreadingHTTPServer(("127.0.0.1", LLM_PORT), MockLLM)
    threading.Thread(target=mock.serve_forever, daemon=True).start()
    log_path = WORK / "server.log"
    process = start_server(log_path)
    username = "e2e_browser"
    target = "e2e_target"
    password = "browser-password-123"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 960})
            page = context.new_page()

            print("1. register through the React login page")
            page.goto(BASE + "/login", wait_until="networkidle")
            expect(page.get_by_role("heading", name="进入工作台。")).to_be_visible()
            page.get_by_role("button", name="注册").click()
            page.locator("#username").fill(username)
            page.locator("#password").fill(password)
            page.get_by_role("button", name="创建本地账号").click()
            page.wait_for_url(BASE + "/")
            expect(page.get_by_role("region", name="模板库")).to_be_visible()
            check(page.locator(".template-card").count() == 7, "seven templates rendered")

            print("2. template fills the single generic composer")
            page.locator(".template-card").filter(has_text="网站").click()
            textarea = page.locator(".generic-composer textarea")
            expect(textarea).to_have_value(re.compile("独立设计工作室"))
            check(page.locator(".generic-composer").count() == 1, "composer is generic")
            check(page.locator(".template-card").filter(has_text="已填入").count() == 1, "template active")

            print("3. create and deploy a static project")
            page.get_by_role("button", name="开始生成").click()
            page.wait_for_url(re.compile(r"/projects$"))
            expect(page.locator(".public-link-banner")).to_be_visible()
            page.locator(".project-card-main").first.click()
            page.wait_for_url(re.compile(r"/projects/[0-9a-f]+$"))
            project_id = page.url.rsplit("/", 1)[-1]
            task = wait_project(page, project_id, 0)
            check(task["title"] == "E2E Static", "mock LLM brief applied")
            expect(page.get_by_text("DEPLOYED").first).to_be_visible()
            expect(page.locator(".browser-frame iframe")).to_be_visible()
            expect(page.get_by_role("link", name=re.compile("公开页"))).to_be_visible()
            page.screenshot(path=str(ARTIFACTS / "project.png"), full_page=True)

            print("4. refine through the UI and rebuild")
            page.get_by_label("修改指令").fill("把页面标题改成 E2E Refined")
            page.get_by_role("button", name="发送修改").click()
            page.get_by_text("修改已提交").wait_for()
            refined = wait_project(page, project_id, 1)
            check(refined["revision"] == 1, "revision incremented")
            html = page.request.get(BASE + f"/p/{project_id}/").text()
            check("E2E Refined" in html, "refined title is deployed")
            expect(page.get_by_text("DEPLOYED").first).to_be_visible()

            print("5. coding mode diff, terminal and replay")
            page.get_by_role("tab", name="编程").click()
            page.locator("#diffPath").wait_for()
            check(page.locator("#diffPath").inner_text().endswith(".html"), "diff shows generated file")
            check(page.locator(".diff-line.add").count() > 0, "diff has additions")
            check("TERMINAL" in page.locator(".stage-panel").inner_text(), "terminal rendered")
            page.get_by_role("button", name="重播").click()
            page.get_by_text("重播中").wait_for()
            page.wait_for_timeout(600)
            page.get_by_role("tab", name="交付").click()

            print("6. deploy, share and export")
            page.get_by_role("button", name="重新部署").click()
            page.get_by_text("项目已重新部署").wait_for()
            page.get_by_role("button", name="取消分享").click()
            page.get_by_text("已关闭分享").wait_for()
            page.get_by_role("button", name="分享").click()
            page.get_by_text("分享链接已复制").wait_for()
            share_href = page.get_by_role("link", name=re.compile("公开页")).get_attribute("href")
            check(bool(share_href and share_href.startswith("/s/")), "public link created")
            with page.expect_download() as download_info:
                page.get_by_role("link", name="导出源码").click()
            download = download_info.value
            check(download.suggested_filename.endswith(".zip"), "bundle export downloads a zip")

            print("7. anonymous public page")
            anonymous = browser.new_context(viewport={"width": 1280, "height": 900})
            public = anonymous.new_page()
            response = public.goto(BASE + str(share_href), wait_until="networkidle")
            check(response is not None and response.status == 200, "public page opens without login")
            check("E2E Refined" in public.content(), "public page shows refined content")
            public.screenshot(path=str(ARTIFACTS / "public.png"), full_page=True)

            print("8. project library stats and filter")
            page.get_by_role("link", name="项目库").click()
            page.wait_for_url(BASE + "/projects")
            expect(page.locator(".project-card").first).to_be_visible()
            stats_text = page.locator(".project-stats").inner_text()
            check(
                bool(re.search(r"1\s*个项目", stats_text)),
                f"stats count projects ({stats_text!r})",
            )
            page.get_by_role("button", name=re.compile("网站")).click()
            check(page.locator(".project-card").count() == 1, "capability filter keeps the card")

            print("9. admin users and audit")
            anonymous.request.post(
                BASE + "/api/auth/register",
                data={"username": target, "password": password, "display_name": "Target User"},
            )
            admin = browser.new_context(viewport={"width": 1440, "height": 960})
            login = admin.request.post(
                BASE + "/api/auth/login",
                data={"username": "admin", "password": "browser-e2e-admin"},
            )
            check(login.ok, "admin logs in")
            admin_page = admin.new_page()
            admin_page.goto(BASE + "/admin", wait_until="networkidle")
            expect(admin_page.get_by_text("@e2e_browser")).to_be_visible()
            row = admin_page.locator(".admin-row").filter(has_text="@e2e_target")
            expect(row).to_be_visible()
            row.get_by_role("button", name="禁用").click()
            admin_page.get_by_text("用户已禁用").wait_for()
            expect(row).to_contain_text("DISABLED")
            row.get_by_role("button", name="启用").click()
            admin_page.get_by_text("用户已启用").wait_for()
            row.get_by_role("button", name="下线").click()
            admin_page.get_by_text("会话已全部撤销").wait_for()
            expect(admin_page.locator(".audit-list")).to_contain_text("admin.user.disable")
            admin_page.screenshot(path=str(ARTIFACTS / "admin.png"), full_page=True)

            print("10. logout and login again")
            page.get_by_role("button", name="退出登录").click()
            page.wait_for_url(re.compile(r"/login"))
            page.locator("#username").fill(username)
            page.locator("#password").fill(password)
            page.get_by_role("button", name="进入 VibeForge").click()
            page.wait_for_url(BASE + "/")

            print("11. mobile smoke")
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(BASE + "/", wait_until="networkidle")
            expect(page.locator(".generic-composer textarea")).to_be_visible()
            expect(page.locator(".run-btn")).to_be_visible()
            page.screenshot(path=str(ARTIFACTS / "mobile-home.png"), full_page=True)
            page.goto(BASE + f"/projects/{project_id}", wait_until="networkidle")
            expect(page.get_by_text("DEPLOYED").first).to_be_visible()
            page.screenshot(path=str(ARTIFACTS / "mobile-project.png"), full_page=True)

            browser.close()

        print(f"\nBROWSER E2E PASSED\nartifacts: {ARTIFACTS}")
        return 0
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        mock.shutdown()
        shutil.rmtree(WORK, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
