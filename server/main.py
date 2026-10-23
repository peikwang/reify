from __future__ import annotations

import asyncio
import hmac
import io
import json
import logging
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import auth
from .agent import run_media_refine, run_refine, run_task
from .config import (
    ADMIN_PASSWORD,
    APP_NAME,
    APP_VERSION,
    AUTH_COOKIE_NAME,
    AUTH_COOKIE_SECURE,
    AUTH_PASSWORD_GENERATED,
    AUTH_TTL_SECONDS,
    AUTO_MIGRATE_LEGACY,
    HOST,
    LLM_ENABLED,
    MAX_ACTIVE_REACT_PER_USER,
    MAX_ACTIVE_TASKS_PER_USER,
    MAX_PROJECTS_PER_USER,
    PORT,
    SSR_PREVIEW_ENABLED,
    WEB_DIR,
)
from .db import User, db
from .events import Task, store
from .llm import enabled as llm_enabled
from .migrate import migrate_legacy
from .runtime import runtime_manager
from .sandbox import SandboxError, sandbox_runner
from .templates.library import CAPABILITIES, classify, defaults
from .tools import Workspace

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("vibeforge")

app = FastAPI(title=APP_NAME, version=APP_VERSION)
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

_background: set[asyncio.Task] = set()
MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".webm"}
ACTIVE_STATUSES = {"queued", "running", "deploying"}

PUBLIC_PATHS = {
    "/login",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/me",
    "/api/health",
}


class CreateTaskRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    capability: str | None = None
    stack: str = "static"

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=40)
    email: str = Field(default="", max_length=254)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class RefineRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=2000)


class PasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


def _secured(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    return response


def _json_error(status: int, detail: str) -> JSONResponse:
    return _secured(JSONResponse(status_code=status, content={"ok": False, "detail": detail}))


def _current_user(request: Request) -> User | None:
    return getattr(request.state, "user", None)


def _require_user(request: Request) -> User:
    user = _current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="authentication required")
    return user


def _project_for(request: Request, project_id: str) -> Task:
    user = _require_user(request)
    task = store.get(project_id, user.id)
    if not task:
        raise HTTPException(status_code=404, detail="project not found")
    return task


def _enforce_react_quota(user: User) -> None:
    active = [
        item
        for item in store.list(user.id)
        if item.get("stack") in {"react", "next"} and item["status"] in ACTIVE_STATUSES
    ]
    if len(active) >= MAX_ACTIVE_REACT_PER_USER:
        raise HTTPException(status_code=429, detail="已有源码构建在运行，请等待完成")


def _enforce_user_quota(user: User, *, exclude_project_id: str | None = None) -> None:
    items = store.list(user.id)
    if exclude_project_id is None and len(items) >= MAX_PROJECTS_PER_USER:
        raise HTTPException(status_code=429, detail="项目数量已达上限")
    active = [
        item
        for item in items
        if item["status"] in ACTIVE_STATUSES and item["id"] != exclude_project_id
    ]
    if len(active) >= MAX_ACTIVE_TASKS_PER_USER:
        raise HTTPException(status_code=429, detail="当前运行中的任务过多，请稍后再试")


def _set_session_cookie(response, token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=AUTH_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=AUTH_COOKIE_SECURE,
        path="/",
    )


def _clear_session_cookie(response) -> None:
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")


def _format_sse(event: dict[str, Any]) -> str:
    return f"id: {event.get('seq', 0)}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


def _terminal(task: Task) -> bool:
    return task.status in {"done", "error", "interrupted"}


def _safe_file(root: Path, relative: str) -> Path | None:
    try:
        target = (root / relative).resolve()
        target.relative_to(root.resolve())
    except (ValueError, OSError):
        return None
    if target.is_dir():
        target = target / "index.html"
    return target if target.is_file() else None


@app.middleware("http")
async def auth_guard(request: Request, call_next):
    path = request.url.path
    asset_request = path.startswith(("/static/", "/media/"))
    user = None if asset_request else auth.resolve_session(request.cookies.get(AUTH_COOKIE_NAME))
    request.state.user = user
    public = (
        path in PUBLIC_PATHS
        or asset_request
        or (path.startswith("/p/") and bool(request.query_params.get("k")))
    )

    if path == "/login" and user:
        return _secured(RedirectResponse("/", status_code=303))
    if not public and not user:
        if path.startswith("/api/"):
            return _json_error(401, "authentication required")
        target = request.url.path
        if request.url.query:
            target += "?" + request.url.query
        return _secured(RedirectResponse("/login?next=" + quote(target, safe=""), status_code=303))
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and path.startswith("/api/"):
        if not auth.same_origin(request):
            return _json_error(403, "origin rejected")

    response = await call_next(request)
    if path.startswith(("/api/", "/login", "/p/")):
        response.headers["Cache-Control"] = "no-store, max-age=0"
    if path == "/p" or path.startswith(("/p/", "/media/")):
        response.headers["Content-Security-Policy"] = (
            "sandbox allow-scripts allow-forms allow-popups allow-modals allow-downloads"
        )
    if path == "/p" or path.startswith("/p/"):
        # Vite emits module scripts with crossorigin; the CSP sandbox gives the page
        # an opaque origin, so its own assets need a CORS-permitted response.
        response.headers["Access-Control-Allow-Origin"] = "*"
    return _secured(response)


@app.get("/login")
async def login_page() -> FileResponse:
    return FileResponse(WEB_DIR / "login.html")


@app.post("/api/auth/register")
async def register(payload: RegisterRequest, request: Request) -> JSONResponse:
    try:
        user, token = await asyncio.to_thread(
            auth.register,
            username=payload.username,
            password=payload.password,
            display_name=payload.display_name,
            email=payload.email,
            request=request,
        )
    except auth.AuthError as exc:
        return _json_error(exc.status, exc.detail)
    response = JSONResponse({"ok": True, "user": user.public()})
    _set_session_cookie(response, token)
    return _secured(response)


@app.post("/api/auth/login")
async def login(payload: LoginRequest, request: Request) -> JSONResponse:
    try:
        user, token = await asyncio.to_thread(
            auth.login, username=payload.username, password=payload.password, request=request
        )
    except auth.AuthError as exc:
        return _json_error(exc.status, exc.detail)
    response = JSONResponse({"ok": True, "user": user.public()})
    _set_session_cookie(response, token)
    return _secured(response)


@app.post("/api/auth/logout")
async def logout(request: Request) -> JSONResponse:
    auth.revoke_session(request.cookies.get(AUTH_COOKIE_NAME))
    response = JSONResponse({"ok": True})
    _clear_session_cookie(response)
    return _secured(response)


@app.post("/api/auth/logout-all")
async def logout_all(request: Request) -> JSONResponse:
    user = _require_user(request)
    auth.revoke_all_sessions(user.id)
    response = JSONResponse({"ok": True})
    _clear_session_cookie(response)
    return _secured(response)


@app.get("/api/auth/me")
async def auth_me(request: Request) -> dict[str, Any]:
    user = _current_user(request)
    return {"authenticated": bool(user), "user": user.public() if user else None}


@app.post("/api/auth/password")
async def change_password(payload: PasswordRequest, request: Request) -> JSONResponse:
    user = _require_user(request)
    try:
        await asyncio.to_thread(
            auth.change_password, user, payload.current_password, payload.new_password
        )
    except auth.AuthError as exc:
        return _json_error(exc.status, exc.detail)
    response = JSONResponse({"ok": True, "relogin": True})
    _clear_session_cookie(response)
    return _secured(response)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/projects")
async def projects_index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/projects/{project_id}")
async def project_page(project_id: str) -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/p/{project_id}")
async def project_preview_redirect(project_id: str) -> RedirectResponse:
    return RedirectResponse(f"/p/{project_id}/", status_code=307)


@app.get("/p/{project_id}/")
async def project_preview_index(project_id: str, request: Request) -> FileResponse:
    task = _project_for(request, project_id)
    target = _safe_file(task.artifact_dir, "index.html")
    if not target:
        raise HTTPException(status_code=404, detail="project file not found")
    return FileResponse(target)


@app.get("/p/{project_id}/{filename:path}")
async def project_preview_file(
    project_id: str, filename: str, request: Request, k: str = ""
) -> FileResponse:
    task = store.get_any(project_id)
    if not task:
        raise HTTPException(status_code=404, detail="project file not found")
    user = _current_user(request)
    allowed = bool(user and user.id == task.owner_id)
    if not allowed:
        if not task.asset_key or not k:
            raise HTTPException(status_code=404, detail="project file not found")
        if not hmac.compare_digest(k.encode("utf-8"), task.asset_key.encode("utf-8")):
            raise HTTPException(status_code=404, detail="project file not found")
    target = _safe_file(task.artifact_dir, filename)
    if not target:
        raise HTTPException(status_code=404, detail="project file not found")
    return FileResponse(target)


@app.get("/media/{project_id}/{filename:path}")
async def media_asset(project_id: str, filename: str, k: str = "") -> FileResponse:
    task = store.get_any(project_id)
    if not task or not task.asset_key or not k:
        raise HTTPException(status_code=404, detail="asset not found")
    if not hmac.compare_digest(k.encode("utf-8"), task.asset_key.encode("utf-8")):
        raise HTTPException(status_code=404, detail="asset not found")
    if not filename.startswith("assets/"):
        raise HTTPException(status_code=404, detail="asset not found")
    assets_root = (task.workspace / "assets").resolve()
    target = (task.workspace / filename).resolve()
    try:
        target.relative_to(assets_root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="asset not found") from exc
    if not target.is_file() or target.suffix.lower() not in MEDIA_SUFFIXES:
        raise HTTPException(status_code=404, detail="asset not found")
    return FileResponse(target, headers={"Cache-Control": "private, max-age=3600"})


@app.get("/api/health")
async def health() -> dict[str, Any]:
    sandbox = sandbox_runner.status()
    if sandbox["backend"] != "off":
        sandbox["reachable"] = await sandbox_runner.reachable()
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
        "llm": bool(llm_enabled()),
        "sandbox": sandbox,
    }


@app.get("/api/capabilities")
async def capabilities() -> dict[str, Any]:
    return {
        "items": [{"key": key, **value} for key, value in CAPABILITIES.items()],
        "sandbox": sandbox_runner.status(),
        "ssr_preview": SSR_PREVIEW_ENABLED,
        "stacks": ["static", "react", "next"],
    }


@app.get("/api/projects")
async def list_projects(request: Request) -> dict[str, Any]:
    user = _require_user(request)
    return {"items": store.list(user.id)}


@app.post("/api/projects")
async def create_project(payload: CreateTaskRequest, request: Request) -> dict[str, Any]:
    user = _require_user(request)
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is empty")
    capability = payload.capability or classify(prompt)
    if capability not in CAPABILITIES:
        capability = classify(prompt)
    stack = payload.stack if payload.stack in {"static", "react", "next"} else "static"
    if stack in {"react", "next"}:
        if not sandbox_runner.enabled:
            raise HTTPException(status_code=503, detail="构建沙箱未启用")
        if not await sandbox_runner.reachable():
            raise HTTPException(status_code=503, detail="构建沙箱暂不可达")
        if capability != "website":
            raise HTTPException(status_code=400, detail="源码工程当前只支持网站能力")
    _enforce_user_quota(user)
    if stack in {"react", "next"}:
        _enforce_react_quota(user)
    if not auth.limiter.hit(f"create:{user.id}", 10, 60):
        raise HTTPException(status_code=429, detail="创建过于频繁，请稍后再试")
    default_title = str(defaults(capability, prompt).get("title", ""))
    task = store.create(
        prompt=prompt,
        capability=capability,
        title=default_title,
        owner_id=user.id,
        stack=stack,
    )
    background = asyncio.create_task(run_task(task))
    _background.add(background)
    background.add_done_callback(_background.discard)
    logger.info("project created id=%s owner=%s capability=%s", task.id, user.id, capability)
    return {"task": task.meta(), "events": []}


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str, request: Request) -> dict[str, Any]:
    task = _project_for(request, project_id)
    return {"task": task.meta(), "events": task.events}


@app.get("/api/projects/{project_id}/events")
async def project_events(project_id: str, request: Request, after: int = 0) -> StreamingResponse:
    task = _project_for(request, project_id)
    header_last = request.headers.get("last-event-id", "")
    try:
        cursor = max(after, int(header_last) if header_last else 0)
    except ValueError:
        cursor = after

    async def stream():
        queue = task.subscribe()
        last_seq = cursor
        try:
            yield "retry: 2500\n\n"
            for event in list(task.events):
                seq = int(event.get("seq", 0))
                if seq > last_seq:
                    last_seq = seq
                    yield _format_sse(event)
            if task.status == "interrupted":
                yield _format_sse(
                    {
                        "seq": task._seq + 1,
                        "type": "interrupted",
                        "message": "任务在服务重启前中断，原产物已保留。",
                    }
                )
                return
            if _terminal(task):
                return
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                seq = int(event.get("seq", 0))
                if seq <= last_seq:
                    continue
                last_seq = seq
                yield _format_sse(event)
                if event.get("type") in {"done", "error"}:
                    return
        finally:
            task.unsubscribe(queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/projects/{project_id}/refine")
async def refine_project(project_id: str, payload: RefineRequest, request: Request) -> dict[str, Any]:
    task = _project_for(request, project_id)
    user = _require_user(request)
    if task.stack == "react":
        raise HTTPException(status_code=400, detail="React 源码工程的二次修改将在下一阶段接入")
    if task.stack == "next":
        raise HTTPException(status_code=400, detail="Next.js 源码的二次修改将在后续阶段接入")
    _enforce_user_quota(user, exclude_project_id=task.id)
    async with task.refine_lock:
        if task.status in {"queued", "running", "deploying"}:
            raise HTTPException(status_code=409, detail="task is still running")
        index = task.workspace / "index.html"
        if not index.exists():
            raise HTTPException(status_code=400, detail="index.html is missing")
        instruction = payload.instruction.strip()
        if not instruction:
            raise HTTPException(status_code=400, detail="instruction is empty")
        task.status = "queued"
        task.save_meta()
    runner = run_media_refine if task.capability in {"image", "video"} else run_refine
    background = asyncio.create_task(runner(task, instruction))
    _background.add(background)
    background.add_done_callback(_background.discard)
    logger.info("refine queued id=%s revision=%s capability=%s", task.id, task.revision + 1, task.capability)
    return {"task": task.meta()}


@app.post("/api/projects/{project_id}/deploy")
async def deploy_project(project_id: str, request: Request) -> dict[str, Any]:
    task = _project_for(request, project_id)
    if task.stack == "next":
        raise HTTPException(status_code=400, detail="SSR 项目请启动运行时，而不是静态部署")
    async with task.refine_lock:
        if task.status in {"queued", "running", "deploying"}:
            raise HTTPException(status_code=409, detail="task is still running")
        index = task.artifact_dir / "index.html"
        if not index.exists():
            raise HTTPException(status_code=400, detail="index.html is missing")
        manifest = await Workspace(task).deploy(task.title or "VibeForge project")
        task.status = "done"
        task.result = {**(task.result or {}), "url": manifest["url"]}
        task.save_meta()
    return {"ok": True, "url": manifest["url"], "manifest": manifest}


@app.get("/api/projects/{project_id}/bundle")
async def bundle_project(project_id: str, request: Request):
    task = _project_for(request, project_id)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in task.workspace.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(task.workspace))
    buffer.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="vibeforge-{task.id}.zip"'}
    return StreamingResponse(buffer, media_type="application/zip", headers=headers)


@app.get("/api/projects/{project_id}/runtime")
async def get_runtime(project_id: str, request: Request) -> dict[str, Any]:
    task = _project_for(request, project_id)
    if task.stack != "next":
        raise HTTPException(status_code=400, detail="该项目不是 SSR 运行时项目")
    return {"runtime": runtime_manager.status(task)}


@app.post("/api/projects/{project_id}/runtime/start")
async def start_runtime(project_id: str, request: Request) -> dict[str, Any]:
    task = _project_for(request, project_id)
    if task.stack != "next":
        raise HTTPException(status_code=400, detail="该项目不是 SSR 运行时项目")
    try:
        state = await runtime_manager.start(task)
    except SandboxError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"ok": True, "runtime": state}


@app.post("/api/projects/{project_id}/runtime/stop")
async def stop_runtime(project_id: str, request: Request) -> dict[str, Any]:
    task = _project_for(request, project_id)
    if task.stack != "next":
        raise HTTPException(status_code=400, detail="该项目不是 SSR 运行时项目")
    state = await runtime_manager.stop(task)
    return {"ok": True, "runtime": state}


async def _proxy_ssr(task: Task, request: Request, suffix: str) -> Response:
    if not SSR_PREVIEW_ENABLED:
        raise HTTPException(status_code=404, detail="SSR preview is disabled")
    record = db.get_runtime(task.id)
    if not record or record["status"] != "running" or not record.get("endpoint"):
        raise HTTPException(status_code=503, detail="SSR runtime is not running")
    path = f"/apps/{task.id}/{suffix}"
    if request.url.query:
        path += "?" + request.url.query
    url = record["endpoint"].rstrip("/") + path
    headers = {}
    for name in ("accept", "content-type", "range"):
        value = request.headers.get(name)
        if value:
            headers[name] = value
    body = await request.body() if request.method in {"POST", "PUT", "PATCH"} else None
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.request(request.method, url, headers=headers, content=body)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"SSR runtime proxy failed: {exc}") from exc
    runtime_manager.touch(task)
    response_headers = {}
    for name in ("content-type", "cache-control", "etag", "last-modified", "location"):
        value = response.headers.get(name)
        if value:
            response_headers[name] = value
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers,
    )


@app.api_route("/apps/{project_id}", methods=["GET", "HEAD"])
async def ssr_root_redirect(project_id: str) -> RedirectResponse:
    return RedirectResponse(f"/apps/{project_id}/", status_code=307)


@app.api_route(
    "/apps/{project_id}/",
    methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"],
)
async def ssr_root(project_id: str, request: Request) -> Response:
    task = _project_for(request, project_id)
    if task.stack != "next":
        raise HTTPException(status_code=404, detail="not an SSR project")
    return await _proxy_ssr(task, request, "")


@app.api_route(
    "/apps/{project_id}/{filename:path}",
    methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"],
)
async def ssr_file(project_id: str, filename: str, request: Request) -> Response:
    task = _project_for(request, project_id)
    if task.stack != "next":
        raise HTTPException(status_code=404, detail="not an SSR project")
    return await _proxy_ssr(task, request, filename)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return _json_error(exc.status_code, str(exc.detail))


@app.on_event("startup")
async def startup() -> None:
    admin = auth.bootstrap_admin()
    if AUTH_PASSWORD_GENERATED:
        logger.warning("VIBEFORGE_ADMIN_PASSWORD is not set; generated admin password: %s", ADMIN_PASSWORD)
    if AUTO_MIGRATE_LEGACY:
        report = migrate_legacy(admin.id)
        if report["migrated"]:
            logger.info("legacy projects migrated: %s", len(report["migrated"]))
        for item in report["errors"]:
            logger.warning("legacy migration error %s: %s", item["id"], item["error"])
    store.ensure_loaded()
    db.cleanup_sessions()
    monitor = asyncio.create_task(runtime_manager.monitor_idle())
    _background.add(monitor)
    monitor.add_done_callback(_background.discard)
    logger.info(
        "%s %s ready · data=%s · users=%s · llm=%s · auth=on",
        APP_NAME,
        APP_VERSION,
        db.path.parent,
        db.count_users(),
        LLM_ENABLED,
    )


if __name__ == "__main__":
    uvicorn.run("server.main:app", host=HOST, port=PORT, reload=False)
