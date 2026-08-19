"""Anonymous browser session helpers (session_id doubles as user_id)."""

from __future__ import annotations

import os
import re
import uuid

from dotenv import load_dotenv
from fastapi import Request, Response

load_dotenv()

SESSION_COOKIE_NAME = "stylescout_session"
LEGACY_USER_ID = "default"
ALLOW_DEFAULT_OVERRIDE_ENV = "ALLOW_DEFAULT_OVERRIDE"
SESSION_ID_PATTERN = re.compile(r"^sess_[0-9a-f]{32}$")

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def allow_default_override() -> bool:
    """Return True when the legacy `default` cookie shortcut is explicitly enabled."""
    raw = (os.getenv(ALLOW_DEFAULT_OVERRIDE_ENV) or "").strip().lower()
    return raw in _TRUTHY


def generate_session_id() -> str:
    """Return a new anonymous session identifier used as user_id."""
    return f"sess_{uuid.uuid4().hex}"


def is_valid_session_id(session_id: str) -> bool:
    """Accept anonymous sessions and optionally the legacy default user."""
    if session_id == LEGACY_USER_ID:
        return allow_default_override()
    return bool(SESSION_ID_PATTERN.match(session_id))


def resolve_session_id(raw_value: str | None) -> str:
    """Normalize a cookie value or return a freshly generated session id."""
    if raw_value and is_valid_session_id(raw_value):
        return raw_value
    return generate_session_id()


def get_session_user_id(request: Request, response: Response) -> str:
    """FastAPI dependency: read cookie or issue stylescout_session on first visit."""
    cookie_value = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_value and is_valid_session_id(cookie_value):
        return cookie_value

    session_id = resolve_session_id(cookie_value)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 365,
    )
    return session_id
