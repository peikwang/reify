from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from . import db
from .config import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    AUTH_MAX_ATTEMPTS,
    AUTH_TTL_SECONDS,
    AUTH_WINDOW_SECONDS,
    REGISTRATION_ENABLED,
    REGISTRATION_MAX_PER_HOUR,
    SESSION_TOUCH_SECONDS,
)
from .db import User, iso_utc, utc_now

USERNAME_RE = re.compile(r"^[\w.\-]{3,32}$", re.UNICODE)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SCRYPT_N = 2**15
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
SCRYPT_MAXMEM = 128 * 1024 * 1024


class AuthError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


class RateLimiter:
    PRUNE_SECONDS = 3600

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()
        self._last_prune = time.time()

    def _prune(self, now: float) -> None:
        if now - self._last_prune < 300:
            return
        cutoff = now - self.PRUNE_SECONDS
        for key in list(self._hits):
            hits = [stamp for stamp in self._hits[key] if stamp >= cutoff]
            if hits:
                self._hits[key] = hits
            else:
                self._hits.pop(key, None)
        self._last_prune = now

    def hit(self, key: str, limit: int, window: int) -> bool:
        now = time.time()
        with self._lock:
            self._prune(now)
            hits = [stamp for stamp in self._hits.get(key, []) if now - stamp < window]
            if len(hits) >= limit:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True

    def clear(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)


limiter = RateLimiter()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
        maxmem=SCRYPT_MAXMEM,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
            maxmem=SCRYPT_MAXMEM,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


_DUMMY_HASH = hash_password("reify-dummy-password")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _client_ip(request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        parts = [part.strip() for part in forwarded.split(",") if part.strip()]
        if parts:
            # Caddy appends the immediate peer; the leftmost value is client-controlled.
            return parts[-1]
    return request.client.host if request.client else "unknown"


def create_session(user: User, request) -> str:
    token = secrets.token_urlsafe(32)
    db.db.create_session(
        user_id=user.id,
        token_hash=_hash_token(token),
        expires_at=iso_utc(utc_now() + timedelta(seconds=AUTH_TTL_SECONDS)),
        ip=_client_ip(request),
        user_agent=(request.headers.get("user-agent", "") or "")[:200],
    )
    return token


def resolve_session(token: str | None) -> User | None:
    if not token:
        return None
    row = db.db.get_session(_hash_token(token))
    if not row:
        return None
    if row["revoked_at"]:
        return None
    try:
        expires = datetime.fromisoformat(row["expires_at"])
    except ValueError:
        return None
    if expires <= utc_now():
        return None
    user: User = row["user"]
    if user.disabled:
        return None
    last_seen = row["last_seen_at"]
    if not last_seen or (utc_now() - datetime.fromisoformat(last_seen)).total_seconds() > SESSION_TOUCH_SECONDS:
        db.db.touch_session(row["session_id"])
    return user


def revoke_session(token: str | None) -> None:
    if token:
        db.db.revoke_session(_hash_token(token))


def revoke_all_sessions(user_id: str) -> None:
    db.db.revoke_user_sessions(user_id)


def _validate_username(username: str) -> str:
    username = (username or "").strip()
    if not USERNAME_RE.fullmatch(username):
        raise AuthError(400, "用户名需为 3~32 个字符，可使用中英文、数字、下划线、点或短横线")
    return username


def _validate_password(password: str) -> None:
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        raise AuthError(400, "密码长度需为 8~128 位")
    if "\x00" in password:
        raise AuthError(400, "密码包含非法字符")


def register(
    *,
    username: str,
    password: str,
    display_name: str = "",
    email: str = "",
    request,
) -> tuple[User, str]:
    if not REGISTRATION_ENABLED:
        raise AuthError(403, "当前已关闭自助注册")
    username = _validate_username(username)
    _validate_password(password)
    display_name = (display_name or "").strip()[:40] or username
    email = (email or "").strip()[:254]
    email_key = email.casefold() if email else None
    if email and not EMAIL_RE.fullmatch(email):
        raise AuthError(400, "邮箱格式不正确")

    ip = _client_ip(request)
    if not limiter.hit(f"register:{ip}", REGISTRATION_MAX_PER_HOUR, 3600):
        raise AuthError(429, "注册过于频繁，请稍后再试")

    try:
        user = db.db.create_user(
            username=username,
            username_key=username.casefold(),
            email=email or None,
            email_key=email_key,
            display_name=display_name,
            password_hash=hash_password(password),
            role="user",
            created_ip=ip,
        )
    except sqlite3.IntegrityError as exc:
        raise AuthError(409, "用户名或邮箱已被使用") from exc

    db.db.touch_login(user.id)
    user = db.db.get_user(user.id) or user
    token = create_session(user, request)
    return user, token


def login(*, username: str, password: str, request) -> tuple[User, str]:
    login_key = (username or "").strip().casefold()
    if not login_key:
        raise AuthError(400, "请输入用户名或邮箱")
    ip = _client_ip(request)
    if not limiter.hit(f"login-ip:{ip}", 20, AUTH_WINDOW_SECONDS):
        raise AuthError(429, "尝试次数过多，请稍后再试")
    if not limiter.hit(f"login-user:{login_key}", AUTH_MAX_ATTEMPTS, AUTH_WINDOW_SECONDS):
        raise AuthError(429, "尝试次数过多，请稍后再试")

    user = db.db.get_user_by_login(login_key)
    stored = user.password_hash if user else _DUMMY_HASH
    valid = verify_password(password, stored) and user is not None and not user.disabled
    if not valid:
        raise AuthError(401, "用户名或密码不正确")

    limiter.clear(f"login-user:{login_key}")
    limiter.clear(f"login-ip:{ip}")
    db.db.touch_login(user.id)
    user = db.db.get_user(user.id) or user
    token = create_session(user, request)
    return user, token


def change_password(user: User, current: str, new: str) -> None:
    fresh = db.db.get_user(user.id)
    if not fresh or not verify_password(current, fresh.password_hash):
        raise AuthError(400, "当前密码不正确")
    _validate_password(new)
    db.db.update_password(user.id, hash_password(new))
    db.db.revoke_user_sessions(user.id)


def same_origin(request) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        return True
    site = request.headers.get("sec-fetch-site")
    if site and site not in {"same-origin", "none"}:
        return False
    parsed = urlsplit(origin)
    if parsed.scheme not in {"http", "https"}:
        return False
    return parsed.netloc == request.headers.get("host", "")


def bootstrap_admin() -> tuple[User, bool]:
    users = db.db.list_users()
    admins = [user for user in users if user.role == "admin" and not user.disabled]
    if admins:
        return admins[0], False
    existing = db.db.get_user_by_key(ADMIN_USERNAME.casefold())
    if existing:
        raise RuntimeError(
            f"user '{ADMIN_USERNAME}' already exists but is not an active admin; "
            "set REIFY_ADMIN_USER to a different name"
        )
    admin = db.db.create_user(
        username=ADMIN_USERNAME,
        username_key=ADMIN_USERNAME.casefold(),
        email=None,
        email_key=None,
        display_name="Administrator",
        password_hash=hash_password(ADMIN_PASSWORD),
        role="admin",
        created_ip=None,
    )
    return admin, True
