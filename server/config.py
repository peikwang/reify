from __future__ import annotations

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
PROJECTS_DIR = Path(os.getenv("VIBEFORGE_PROJECTS", str(ROOT / "projects"))).resolve()
DATA_DIR = Path(os.getenv("VIBEFORGE_DATA", str(ROOT / "data"))).resolve()

PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "tasks").mkdir(parents=True, exist_ok=True)

HOST = os.getenv("VIBEFORGE_HOST", "0.0.0.0")
PORT = int(os.getenv("VIBEFORGE_PORT", "12888"))

LLM_BASE_URL = os.getenv("VIBEFORGE_LLM_BASE_URL", "").rstrip("/")
LLM_API_KEY = os.getenv("VIBEFORGE_LLM_API_KEY", "")
LLM_MODEL = os.getenv("VIBEFORGE_LLM_MODEL", "")
LLM_TIMEOUT = float(os.getenv("VIBEFORGE_LLM_TIMEOUT", "45"))
LLM_MAX_TOKENS = int(os.getenv("VIBEFORGE_LLM_MAX_TOKENS", "1200"))
LLM_REFINE_MAX_TOKENS = int(os.getenv("VIBEFORGE_LLM_REFINE_MAX_TOKENS", "3000"))
LLM_ENABLED = os.getenv("VIBEFORGE_LLM_ENABLED", "1") not in {"0", "false", "False", "off"}

MEDIA_API_BASE = os.getenv("VIBEFORGE_MEDIA_API_BASE", "").rstrip("/")
if not MEDIA_API_BASE:
    MEDIA_API_BASE = LLM_BASE_URL
    if MEDIA_API_BASE.endswith("/compatible-mode/v1"):
        MEDIA_API_BASE = MEDIA_API_BASE[: -len("/compatible-mode/v1")]
IMAGE_MODEL = os.getenv("VIBEFORGE_IMAGE_MODEL", "qwen-image-3.0-pro")
VIDEO_MODEL = os.getenv("VIBEFORGE_VIDEO_MODEL", "wan3.0-video")
IMAGE_COUNT = max(1, min(int(os.getenv("VIBEFORGE_IMAGE_COUNT", "4")), 6))
VIDEO_DURATION = max(2, min(int(os.getenv("VIBEFORGE_VIDEO_DURATION", "5")), 30))
VIDEO_RESOLUTION = os.getenv("VIBEFORGE_VIDEO_RESOLUTION", "720P")
MEDIA_TIMEOUT = float(os.getenv("VIBEFORGE_MEDIA_TIMEOUT", "900"))
VIDEO_POLL_INTERVAL = float(os.getenv("VIBEFORGE_VIDEO_POLL_INTERVAL", "10"))

STEP_DELAY = float(os.getenv("VIBEFORGE_STEP_DELAY", "0.55"))
MAX_CONCURRENT_TASKS = int(os.getenv("VIBEFORGE_MAX_CONCURRENT", "4"))

AUTH_PASSWORD = os.getenv("VIBEFORGE_PASSWORD", "").strip()
AUTH_PASSWORD_GENERATED = False
if not AUTH_PASSWORD:
    AUTH_PASSWORD = secrets.token_urlsafe(12)
    AUTH_PASSWORD_GENERATED = True
AUTH_SECRET = os.getenv("VIBEFORGE_SECRET", "").strip() or secrets.token_hex(32)
AUTH_COOKIE_NAME = "vibeforge_session"
AUTH_TTL_SECONDS = int(os.getenv("VIBEFORGE_AUTH_TTL", str(7 * 24 * 3600)))
AUTH_COOKIE_SECURE = os.getenv("VIBEFORGE_COOKIE_SECURE", "0") not in {"0", "false", "False", "off"}
AUTH_MAX_ATTEMPTS = int(os.getenv("VIBEFORGE_AUTH_MAX_ATTEMPTS", "8"))
AUTH_WINDOW_SECONDS = int(os.getenv("VIBEFORGE_AUTH_WINDOW", "60"))

APP_NAME = "VibeForge"
APP_VERSION = "1.0.0"
