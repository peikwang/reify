from __future__ import annotations

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
REACT_DIST_DIR = WEB_DIR / "dist"
PROJECTS_DIR = Path(os.getenv("REIFY_PROJECTS", str(ROOT / "projects"))).resolve()
DATA_DIR = Path(os.getenv("REIFY_DATA", str(ROOT / "data"))).resolve()
USERS_DIR = DATA_DIR / "users"
DB_PATH = Path(os.getenv("REIFY_DB", str(DATA_DIR / "reify.db"))).resolve()

PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
USERS_DIR.mkdir(parents=True, exist_ok=True)

HOST = os.getenv("REIFY_HOST", "0.0.0.0")
PORT = int(os.getenv("REIFY_PORT", "12888"))

LLM_BASE_URL = os.getenv("REIFY_LLM_BASE_URL", "").rstrip("/")
LLM_API_KEY = os.getenv("REIFY_LLM_API_KEY", "")
LLM_MODEL = os.getenv("REIFY_LLM_MODEL", "")
LLM_TIMEOUT = float(os.getenv("REIFY_LLM_TIMEOUT", "45"))
LLM_MAX_TOKENS = int(os.getenv("REIFY_LLM_MAX_TOKENS", "1200"))
LLM_REFINE_MAX_TOKENS = int(os.getenv("REIFY_LLM_REFINE_MAX_TOKENS", "3000"))
LLM_LONGTAIL_MAX_TOKENS = int(os.getenv("REIFY_LLM_LONGTAIL_MAX_TOKENS", "24000"))
LLM_LONGTAIL_TIMEOUT = float(os.getenv("REIFY_LLM_LONGTAIL_TIMEOUT", "240"))
LLM_LONGTAIL_DISABLE_THINKING = os.getenv(
    "REIFY_LLM_LONGTAIL_DISABLE_THINKING", "1"
) not in {"0", "false", "False", "off"}
LLM_ENABLED = os.getenv("REIFY_LLM_ENABLED", "1") not in {"0", "false", "False", "off"}

MEDIA_API_BASE = os.getenv("REIFY_MEDIA_API_BASE", "").rstrip("/")
if not MEDIA_API_BASE:
    MEDIA_API_BASE = LLM_BASE_URL
    for suffix in ("/compatible-mode/v1", "/v1"):
        if MEDIA_API_BASE.endswith(suffix):
            MEDIA_API_BASE = MEDIA_API_BASE[: -len(suffix)]
            break
MEDIA_API_KEY = os.getenv("REIFY_MEDIA_API_KEY", "") or LLM_API_KEY
IMAGE_MODEL = os.getenv("REIFY_IMAGE_MODEL", "qwen-image-3.0-pro")
VIDEO_MODEL = os.getenv("REIFY_VIDEO_MODEL", "wan3.0-video")
IMAGE_COUNT = max(1, min(int(os.getenv("REIFY_IMAGE_COUNT", "4")), 6))
VIDEO_DURATION = max(2, min(int(os.getenv("REIFY_VIDEO_DURATION", "5")), 30))
VIDEO_RESOLUTION = os.getenv("REIFY_VIDEO_RESOLUTION", "720P")
MEDIA_TIMEOUT = float(os.getenv("REIFY_MEDIA_TIMEOUT", "900"))
VIDEO_POLL_INTERVAL = float(os.getenv("REIFY_VIDEO_POLL_INTERVAL", "10"))

STEP_DELAY = float(os.getenv("REIFY_STEP_DELAY", "0.55"))
MAX_CONCURRENT_TASKS = int(os.getenv("REIFY_MAX_CONCURRENT", "4"))
MAX_PROJECTS_PER_USER = int(os.getenv("REIFY_MAX_PROJECTS_PER_USER", "50"))
MAX_ACTIVE_TASKS_PER_USER = int(os.getenv("REIFY_MAX_ACTIVE_PER_USER", "2"))
MAX_ACTIVE_REACT_PER_USER = int(os.getenv("REIFY_MAX_ACTIVE_REACT_PER_USER", "1"))
MAX_RUNTIME_PER_USER = int(os.getenv("REIFY_MAX_RUNTIME_PER_USER", "2"))
MAX_STORAGE_PER_USER = int(os.getenv("REIFY_MAX_STORAGE_PER_USER", str(1024 * 1024 * 1024)))

# Execution sandbox (OpenSandbox server with Docker runtime).
SANDBOX_BACKEND = os.getenv("REIFY_SANDBOX", "off").strip().lower()
SANDBOX_DOMAIN = os.getenv("REIFY_SANDBOX_DOMAIN", "127.0.0.1:8080").strip()
SANDBOX_API_KEY = os.getenv("REIFY_SANDBOX_API_KEY", "").strip()
SANDBOX_PROTOCOL = os.getenv("REIFY_SANDBOX_PROTOCOL", "http").strip()
SANDBOX_USE_SERVER_PROXY = os.getenv("REIFY_SANDBOX_SERVER_PROXY", "1") not in {"0", "false", "False", "off"}
SANDBOX_IMAGE = os.getenv("REIFY_SANDBOX_IMAGE", "node:24-bookworm-slim")
SANDBOX_CPU = os.getenv("REIFY_SANDBOX_CPU", "1")
SANDBOX_MEMORY = os.getenv("REIFY_SANDBOX_MEMORY", "1Gi")
SANDBOX_BUILD_MEMORY = os.getenv("REIFY_SANDBOX_BUILD_MEMORY", "2Gi")
SANDBOX_TTL_SECONDS = int(os.getenv("REIFY_SANDBOX_TTL", "900"))
SANDBOX_READY_TIMEOUT = int(os.getenv("REIFY_SANDBOX_READY_TIMEOUT", "120"))
SANDBOX_REQUEST_TIMEOUT = int(os.getenv("REIFY_SANDBOX_REQUEST_TIMEOUT", "600"))
SANDBOX_CONCURRENCY = max(1, int(os.getenv("REIFY_SANDBOX_CONCURRENCY", "2")))
SANDBOX_EGRESS = os.getenv("REIFY_SANDBOX_EGRESS", "allowlist").strip().lower()
SANDBOX_EGRESS_ALLOW = [
    item.strip()
    for item in os.getenv(
        "REIFY_SANDBOX_EGRESS_ALLOW",
        "*.npmmirror.com,registry.npmjs.org,*.npmjs.org",
    ).split(",")
    if item.strip()
]
NPM_REGISTRY = os.getenv("REIFY_NPM_REGISTRY", "https://registry.npmmirror.com").strip()
NPM_INSTALL_TIMEOUT = int(os.getenv("REIFY_NPM_INSTALL_TIMEOUT", "600"))
NPM_BUILD_TIMEOUT = int(os.getenv("REIFY_NPM_BUILD_TIMEOUT", "600"))
REACT_DIST_MAX_BYTES = int(os.getenv("REIFY_REACT_DIST_MAX_BYTES", str(30 * 1024 * 1024)))
NEXT_ARTIFACT_MAX_BYTES = int(os.getenv("REIFY_NEXT_ARTIFACT_MAX_BYTES", str(120 * 1024 * 1024)))
RUNTIME_TTL_SECONDS = int(os.getenv("REIFY_RUNTIME_TTL", "3600"))
RUNTIME_IDLE_SECONDS = int(os.getenv("REIFY_RUNTIME_IDLE", "600"))
RUNTIME_READY_TIMEOUT = int(os.getenv("REIFY_RUNTIME_READY_TIMEOUT", "90"))
RUNTIME_PORT = int(os.getenv("REIFY_RUNTIME_PORT", "3000"))
SSR_PREVIEW_ENABLED = os.getenv("REIFY_SSR_PREVIEW", "0") not in {"0", "false", "False", "off"}
SSR_PORT = int(os.getenv("REIFY_SSR_PORT", "12889"))
SANDBOX_HOST_DATA_ROOT = os.getenv("REIFY_SANDBOX_HOST_DATA_ROOT", "").strip()

AUTH_COOKIE_NAME = "reify_session"
AUTH_TTL_SECONDS = int(os.getenv("REIFY_AUTH_TTL", str(7 * 24 * 3600)))
AUTH_COOKIE_SECURE = os.getenv("REIFY_COOKIE_SECURE", "0") not in {"0", "false", "False", "off"}
AUTH_MAX_ATTEMPTS = int(os.getenv("REIFY_AUTH_MAX_ATTEMPTS", "8"))
AUTH_WINDOW_SECONDS = int(os.getenv("REIFY_AUTH_WINDOW", "60"))

REGISTRATION_MODE = os.getenv("REIFY_REGISTRATION", "open").strip().lower()
REGISTRATION_ENABLED = REGISTRATION_MODE not in {"closed", "off", "0", "false"}
REGISTRATION_MAX_PER_HOUR = int(os.getenv("REIFY_REGISTRATION_MAX_PER_HOUR", "5"))
SESSION_TOUCH_SECONDS = int(os.getenv("REIFY_SESSION_TOUCH", "300"))

ADMIN_USERNAME = os.getenv("REIFY_ADMIN_USER", "admin").strip() or "admin"
ADMIN_PASSWORD = os.getenv("REIFY_ADMIN_PASSWORD", "").strip()
AUTH_PASSWORD = os.getenv("REIFY_PASSWORD", "").strip()
AUTH_PASSWORD_GENERATED = False
if not ADMIN_PASSWORD:
    if not AUTH_PASSWORD:
        AUTH_PASSWORD = secrets.token_urlsafe(12)
        AUTH_PASSWORD_GENERATED = True
    ADMIN_PASSWORD = AUTH_PASSWORD

AUTO_MIGRATE_LEGACY = os.getenv("REIFY_AUTO_MIGRATE", "1") not in {"0", "false", "False", "off"}

APP_NAME = "Reify"
APP_VERSION = "2.0.0"
