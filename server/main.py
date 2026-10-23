from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
from typing import Any
from urllib.parse import quote

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agent import run_media_refine, run_refine, run_task
from .config import (
    APP_NAME,
    APP_VERSION,
    AUTH_COOKIE_NAME,
    AUTH_COOKIE_SECURE,
    AUTH_MAX_ATTEMPTS,
    AUTH_PASSWORD,
    AUTH_PASSWORD_GENERATED,
    AUTH_SECRET,
    AUTH_TTL_SECONDS,
    AUTH_WINDOW_SECONDS,
    HOST,
    LLM_ENABLED,
    PORT,
    PROJECTS_DIR,
    WEB_DIR,
)
from .events import store
from .llm import enabled as llm_enabled
from .templates.library import CAPABILITIES, classify, defaults
from .tools import Workspace

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("vibeforge")

app = FastAPI(title=APP_NAME, version=APP_VERSION)
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
app.mount("/tasks", StaticFiles(directory=str(PROJECTS_DIR), html=True), name="tasks")

_background: set[asyncio.Task] = set()


class CreateTaskRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    capability: str | None = None


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class RefineRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=2000)


_attempts: dict[str, list[float]] = {}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limited(ip: str) -> bool:
    now = time.time()
    recent = [stamp for stamp in _attempts.get(ip, []) if now - stamp < AUTH_WINDOW_SECONDS]
    _attempts[ip] = recent
    return len(recent) >= AUTH_MAX_ATTEMPTS


def _record_attempt(ip: str) -> None:
    now = time.time()
    _attempts.setdefault(ip, []).append(now)


def _sign_session(payload: str) -> str:
    return hmac.new(AUTH_SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _issue_session() -> str:
    payload = str(int(time.time()) + AUTH_TTL_SECONDS)
    return f"{payload}.{_sign_session(payload)}"


def _valid_session(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    payload, signature = token.split(".", 1)
    if not hmac.compare_digest(signature, _sign_session(payload)):
        return False
    try:
        return int(payload) >= int(time.time())
    except ValueError:
        return False


def _authenticated(request: Request) -> bool:
    return _valid_session(request.cookies.get(AUTH_COOKIE_NAME))


def _secured(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    return response


def _format_sse(event: dict[str, Any]) -> str:
    return f"id: {event.get('seq', 0)}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


def _terminal(task) -> bool:
    return task.status in {"done", "error", "interrupted"}


@app.middleware("http")
async def auth_guard(request: Request, call_next):
    path = request.url.path
    public = path in {"/login", "/api/auth/login", "/api/health"} or path.startswith(("/static/", "/media/"))
    if path == "/login" and _authenticated(request):
        return _secured(RedirectResponse("/", status_code=303))
    if not public and not _authenticated(request):
        if path.startswith(("/api/", "/tasks/")):
            return _secured(JSONResponse(status_code=401, content={"ok": False, "detail": "authentication required"}))
        target = request.url.path
        if request.url.query:
            target += "?" + request.url.query
        return _secured(RedirectResponse("/login?next=" + quote(target, safe=""), status_code=303))
    response = await call_next(request)
    if path.startswith(("/api/", "/tasks/", "/login", "/static/")):
        response.headers["Cache-Control"] = "no-store, max-age=0"
    if path == "/tasks" or path.startswith("/tasks/"):
        response.headers["Content-Security-Policy"] = (
            "sandbox allow-scripts allow-forms allow-popups allow-modals allow-downloads"
        )
    return _secured(response)


@app.get("/login")
async def login_page() -> FileResponse:
    return FileResponse(WEB_DIR / "login.html")


@app.post("/api/auth/login")
async def login(payload: LoginRequest, request: Request) -> JSONResponse:
    ip = _client_ip(request)
    if _rate_limited(ip):
        return JSONResponse(status_code=429, content={"ok": False, "detail": "too many attempts"})
    if not hmac.compare_digest(payload.password.encode("utf-8"), AUTH_PASSWORD.encode("utf-8")):
        _record_attempt(ip)
        return JSONResponse(status_code=401, content={"ok": False, "detail": "密码不正确"})
    _attempts.pop(ip, None)
    response = JSONResponse({"ok": True})
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=_issue_session(),
        max_age=AUTH_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=AUTH_COOKIE_SECURE,
        path="/",
    )
    return _secured(response)


@app.post("/api/auth/logout")
async def logout() -> JSONResponse:
    response = JSONResponse({"ok": True})
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    return _secured(response)


@app.get("/api/auth/me")
async def auth_me(request: Request) -> dict[str, Any]:
    return {"authenticated": _authenticated(request)}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/projects")
async def projects_index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/projects/{task_id}")
async def project_page(task_id: str) -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/media/{task_id}/{filename:path}")
async def media_asset(task_id: str, filename: str):
    task = store.get(task_id)
    if not task or not filename.startswith("assets/"):
        raise HTTPException(status_code=404, detail="asset not found")
    assets_root = (task.workspace / "assets").resolve()
    target = (task.workspace / filename).resolve()
    try:
        target.relative_to(assets_root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="asset not found") from exc
    if not target.is_file():
        raise HTTPException(status_code=404, detail="asset not found")
    return FileResponse(target)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
        "llm": bool(llm_enabled()),
        "tasks": len(store.tasks),
    }


@app.get("/api/capabilities")
async def capabilities() -> dict[str, Any]:
    return {"items": [{"key": key, **value} for key, value in CAPABILITIES.items()]}


@app.get("/api/tasks")
async def list_tasks() -> dict[str, Any]:
    return {"items": store.list()}


@app.post("/api/tasks")
async def create_task(payload: CreateTaskRequest) -> dict[str, Any]:
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is empty")
    capability = payload.capability or classify(prompt)
    if capability not in CAPABILITIES:
        capability = classify(prompt)
    default_title = str(defaults(capability, prompt).get("title", ""))
    task = store.create(prompt=prompt, capability=capability, title=default_title)
    background = asyncio.create_task(run_task(task))
    _background.add(background)
    background.add_done_callback(_background.discard)
    logger.info("task created id=%s capability=%s", task.id, capability)
    return {"task": task.meta(), "events": []}


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str) -> dict[str, Any]:
    task = store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return {"task": task.meta(), "events": task.events}


@app.get("/api/tasks/{task_id}/events")
async def task_events(task_id: str, request: Request, after: int = 0) -> StreamingResponse:
    task = store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
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


@app.post("/api/tasks/{task_id}/refine")
async def refine_task(task_id: str, payload: RefineRequest) -> dict[str, Any]:
    task = store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
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


@app.post("/api/tasks/{task_id}/deploy")
async def deploy_task(task_id: str) -> dict[str, Any]:
    task = store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    async with task.refine_lock:
        if task.status in {"queued", "running", "deploying"}:
            raise HTTPException(status_code=409, detail="task is still running")
        index = task.workspace / "index.html"
        if not index.exists():
            raise HTTPException(status_code=400, detail="index.html is missing")
        manifest = await Workspace(task).deploy(task.title or "VibeForge project")
        task.status = "done"
        task.result = {**(task.result or {}), "url": manifest["url"]}
        task.save_meta()
    return {"ok": True, "url": manifest["url"], "manifest": manifest}


@app.get("/api/tasks/{task_id}/bundle")
async def bundle_task(task_id: str):
    import io
    import zipfile

    task = store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in task.workspace.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(task.workspace))
    buffer.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="vibeforge-{task.id}.zip"'}
    return StreamingResponse(buffer, media_type="application/zip", headers=headers)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"ok": False, "detail": exc.detail})


@app.on_event("startup")
async def startup() -> None:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    if AUTH_PASSWORD_GENERATED:
        logger.warning("VIBEFORGE_PASSWORD is not set; generated temporary password: %s", AUTH_PASSWORD)
    logger.info("%s %s ready · projects=%s · llm=%s · auth=on", APP_NAME, APP_VERSION, PROJECTS_DIR, LLM_ENABLED)


if __name__ == "__main__":
    uvicorn.run("server.main:app", host=HOST, port=PORT, reload=False)
