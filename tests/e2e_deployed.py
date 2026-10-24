#!/usr/bin/env python3
"""Deployed-environment smoke E2E: real HTTPS deployment, real Chrome, one static project.

Usage:
    REIFY_E2E_BASE=https://117.148.166.55:12888 .venv/bin/python tests/e2e_deployed.py
"""
from __future__ import annotations

import os
import re
import tempfile
import time
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

BASE = os.environ.get("REIFY_E2E_BASE", "").rstrip("/")
if not BASE:
    raise SystemExit("REIFY_E2E_BASE is required")
ARTIFACTS = Path(tempfile.mkdtemp(prefix="reify-deployed-e2e-"))


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"  ok  {message}")


def wait_project(page: Page, project_id: str) -> dict:
    deadline = time.time() + 90
    last: dict = {}
    while time.time() < deadline:
        response = page.request.get(BASE + f"/api/projects/{project_id}")
        if response.ok:
            last = response.json()["task"]
            if last["status"] == "error":
                raise AssertionError(f"project failed: {last.get('error')}")
            if last["status"] == "done":
                return last
        time.sleep(0.3)
    raise AssertionError(f"project timeout: {last}")


def main() -> int:
    username = "deploy_e2e_" + str(int(time.time()))
    password = "deployed-e2e-password"
    print(f"base: {BASE}")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 960},
            ignore_https_errors=True,
        )
        page = context.new_page()

        print("1. login page is served by the React SPA")
        page.goto(BASE + "/login", wait_until="networkidle")
        expect(page.get_by_role("heading", name="进入工作台。")).to_be_visible()
        check("LOCAL ACCOUNTS" in page.content(), "React login page rendered")

        print("2. register a throwaway user and create a static project")
        page.get_by_role("tab", name="注册").click()
        page.locator("#username").fill(username)
        page.locator("#password").fill(password)
        page.get_by_role("button", name="创建本地账号").click()
        page.wait_for_url(re.compile(re.escape(BASE) + r"/$"))
        expect(page.get_by_role("region", name="模板库")).to_be_visible()
        check(page.locator(".template-card").count() == 7, "seven templates on production")
        page.locator(".template-card").filter(has_text="网站").click()
        page.locator(".generic-composer textarea").fill(
            "做一个极简的独立设计工作室官网，包含介绍、服务和联系入口"
        )
        page.get_by_role("button", name="开始生成").click()
        page.wait_for_url(re.compile(r"/projects$"))
        page.locator(".project-card-main").first.click()
        page.wait_for_url(re.compile(r"/projects/[0-9a-f]+$"))
        project_id = page.url.rsplit("/", 1)[-1]
        task = wait_project(page, project_id)
        check(task["id"] == project_id, "project completed")
        expect(page.get_by_text("DEPLOYED").first).to_be_visible()
        expect(page.locator(".browser-frame iframe")).to_be_visible()
        check("/p/" + project_id in page.locator(".browser-url").inner_text(), "preview URL shown")
        page.screenshot(path=str(ARTIFACTS / "deployed-project.png"), full_page=True)

        print("3. public share link opens without a session")
        share_href = page.get_by_role("link", name=re.compile("公开页")).get_attribute("href")
        check(bool(share_href and share_href.startswith("/s/")), "auto public link exists")
        anonymous = browser.new_context(viewport={"width": 1280, "height": 900}, ignore_https_errors=True)
        public = anonymous.new_page()
        response = public.goto(BASE + str(share_href), wait_until="networkidle")
        check(response is not None and response.status == 200, "public page 200 without login")
        public.screenshot(path=str(ARTIFACTS / "deployed-public.png"), full_page=True)

        print("4. coding mode and export")
        page.get_by_role("tab", name="编程").click()
        page.locator("#diffPath").wait_for()
        check(page.locator("#diffPath").inner_text().endswith(".html"), "diff file rendered")
        with page.expect_download() as download_info:
            page.get_by_role("link", name="导出源码").click()
        check(download_info.value.suggested_filename.endswith(".zip"), "source bundle downloads")
        page.get_by_role("tab", name="交付").click()

        print("5. share toggle and project library")
        page.get_by_role("button", name="取消分享").click()
        page.get_by_text("已关闭分享").wait_for()
        page.get_by_role("button", name="分享").click()
        page.get_by_text("分享链接已复制").wait_for()
        page.get_by_role("link", name="项目库").click()
        page.wait_for_url(BASE + "/projects")
        expect(page.locator(".project-card").first).to_be_visible()
        check("个项目" in page.locator(".project-stats").inner_text(), "library stats rendered")

        print("6. mobile smoke")
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(BASE + "/", wait_until="networkidle")
        expect(page.locator(".generic-composer textarea")).to_be_visible()
        page.screenshot(path=str(ARTIFACTS / "deployed-mobile.png"), full_page=True)

        print("7. delete the throwaway project")
        page.set_viewport_size({"width": 1440, "height": 960})
        page.goto(BASE + f"/projects/{project_id}", wait_until="networkidle")
        page.once("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="删除项目").click()
        page.wait_for_url(BASE + "/projects")
        check(
            page.request.get(BASE + f"/api/projects/{project_id}").status == 404,
            "project deletion removes the project and its files",
        )

        browser.close()

    print(f"\nDEPLOYED E2E PASSED\nartifacts: {ARTIFACTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
