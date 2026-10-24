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

GAME_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>E2E 2048</title>
<style>
:root{--bg:#0a0f0c;--panel:#131c16;--ink:#eaf7ef;--accent:#f4b860}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:grid;place-items:center;background:radial-gradient(circle at 50% 20%,#1b2a20,var(--bg));color:var(--ink);font-family:ui-sans-serif,system-ui,sans-serif}
.shell{width:min(560px,calc(100vw - 32px));padding:20px}
.hud{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;font:700 12px/1.4 ui-monospace,monospace;letter-spacing:.12em}
.hud b{color:var(--accent);font-size:22px}
.board{border:1px solid rgba(244,184,96,.24);border-radius:20px;padding:12px;background:var(--panel)}
canvas{width:100%;aspect-ratio:1;display:block;border-radius:12px;background:#0b120e}
.actions{display:flex;gap:8px;margin-top:12px}
button{flex:1;border:1px solid rgba(244,184,96,.3);border-radius:10px;padding:11px;background:transparent;color:var(--ink);font:700 12px/1 ui-monospace,monospace}
button:hover{background:var(--accent);color:#1b1408}
.hint{margin-top:10px;color:#8fa39a;font:11px/1.6 ui-monospace,monospace;text-align:center}
/* layout-guard-000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 */
</style>
</head>
<body>
<div class="shell">
  <header class="hud"><span>SCORE <b id="score">0</b></span><span>2048 / E2E</span></header>
  <div class="board"><canvas id="game" width="512" height="512" aria-label="数字合并棋盘"></canvas></div>
  <div class="actions"><button id="start" type="button">开始</button><button id="pause" type="button">暂停</button><button id="reset" type="button">重开</button></div>
  <p class="hint">方向键 / WASD 移动 · 手机滑动或点按方向按钮</p>
</div>
<script>
const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');
const scoreEl = document.getElementById('score');
const size = 4, cell = 116, gap = 12, origin = 22;
let grid = [], score = 0, paused = false, running = false;
function reset() {
  grid = Array.from({ length: size }, () => Array(size).fill(0));
  score = 0; paused = false; running = true;
  addTile(); addTile(); paint();
}
function addTile() {
  const empty = [];
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) if (!grid[y][x]) empty.push([x, y]);
  if (!empty.length) return;
  const [x, y] = empty[Math.floor(Math.random() * empty.length)];
  grid[y][x] = Math.random() < 0.9 ? 2 : 4;
}
function compress(line) {
  const values = line.filter(Boolean);
  const merged = [];
  for (let i = 0; i < values.length; i++) {
    if (values[i] === values[i + 1]) { merged.push(values[i] * 2); score += values[i] * 2; i++; }
    else merged.push(values[i]);
  }
  while (merged.length < size) merged.push(0);
  return merged;
}
function move(dx, dy) {
  if (!running || paused) return;
  const before = JSON.stringify(grid);
  if (dx) {
    for (let y = 0; y < size; y++) {
      const row = grid[y].slice();
      if (dx > 0) grid[y] = compress(row.reverse()).reverse();
      else grid[y] = compress(row);
    }
  } else {
    for (let x = 0; x < size; x++) {
      const column = grid.map((row) => row[x]);
      const moved = dy > 0 ? compress(column.reverse()).reverse() : compress(column);
      for (let y = 0; y < size; y++) grid[y][x] = moved[y];
    }
  }
  if (JSON.stringify(grid) !== before) { addTile(); paint(); }
}
function color(value) {
  const table = { 2: '#2d3a31', 4: '#3b4c40', 8: '#8a6a32', 16: '#c58a38', 32: '#f4b860', 64: '#ff9d5c', 128: '#ff7a59', 256: '#f45d48', 512: '#d6423b', 1024: '#a92f36', 2048: '#7a2030' };
  return table[value] || '#202b24';
}
function paint() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#0b120e'; ctx.fillRect(0, 0, canvas.width, canvas.height);
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const value = grid[y][x];
    const px = origin + x * (cell + gap), py = origin + y * (cell + gap);
    ctx.fillStyle = color(value);
    ctx.beginPath(); ctx.roundRect(px, py, cell, cell, 12); ctx.fill();
    if (value) {
      ctx.fillStyle = value >= 8 ? '#fff8ea' : '#dcebe0';
      ctx.font = '700 ' + (value >= 1000 ? 30 : 38) + 'px ui-monospace, monospace';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(String(value), px + cell / 2, py + cell / 2);
    }
  }
  scoreEl.textContent = String(score);
}
function togglePause() { if (!running) return; paused = !paused; }
function handleKey(event) {
  const key = event.key.toLowerCase();
  if (['arrowup', 'w'].includes(key)) { event.preventDefault(); move(0, -1); }
  if (['arrowdown', 's'].includes(key)) { event.preventDefault(); move(0, 1); }
  if (['arrowleft', 'a'].includes(key)) { event.preventDefault(); move(-1, 0); }
  if (['arrowright', 'd'].includes(key)) { event.preventDefault(); move(1, 0); }
  if (key === 'p') togglePause();
}
let touchStart = null;
document.addEventListener('keydown', handleKey);
canvas.addEventListener('touchstart', (event) => { touchStart = event.touches[0]; }, { passive: true });
canvas.addEventListener('touchend', (event) => {
  if (!touchStart) return;
  const touch = event.changedTouches[0];
  const dx = touch.clientX - touchStart.clientX, dy = touch.clientY - touchStart.clientY;
  if (Math.max(Math.abs(dx), Math.abs(dy)) < 18) return;
  if (Math.abs(dx) > Math.abs(dy)) move(dx > 0 ? 1 : -1, 0); else move(0, dy > 0 ? 1 : -1);
  touchStart = null;
}, { passive: true });
document.getElementById('start').addEventListener('click', reset);
document.getElementById('pause').addEventListener('click', togglePause);
document.getElementById('reset').addEventListener('click', reset);
setInterval(() => { if (running && !paused) paint(); }, 160);
reset();
</script>
</body>
</html>"""


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
        elif "独立游戏工程师" in system:
            content = GAME_HTML
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

            print("12. long-tail custom game generation")
            page.set_viewport_size({"width": 1440, "height": 960})
            page.goto(BASE + "/", wait_until="networkidle")
            page.locator(".generic-composer textarea").fill(
                "做一个 2048 数字合并小游戏：支持方向键和触控，显示分数、暂停和重新开始"
            )
            page.get_by_role("button", name="开始生成").click()
            page.wait_for_url(re.compile(r"/projects$"))
            page.locator(".project-card-main").first.click()
            page.wait_for_url(re.compile(r"/projects/[0-9a-f]+$"))
            game_id = page.url.rsplit("/", 1)[-1]
            game_task = wait_project(page, game_id)
            game_html = page.request.get(BASE + f"/p/{game_id}/").text()
            check(game_task["status"] == "done", "custom game project completed")
            check('name="vibeforge-game"' in game_html, "LLM game passed validation")
            check("<canvas" in game_html, "custom game renders with canvas")
            expect(page.get_by_text("DEPLOYED").first).to_be_visible()
            page.screenshot(path=str(ARTIFACTS / "custom-game.png"), full_page=True)

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
