from __future__ import annotations

from typing import Any

from .games import defaults as _defaults
from .games import detect_genre, render as _render


def defaults(prompt: str) -> dict[str, Any]:
    return _defaults(prompt)


def render(brief: dict[str, Any], prompt: str = "") -> str:
    return _render(brief, prompt)
