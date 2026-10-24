from __future__ import annotations

import re

STACKS = ("static", "react", "next")
SOURCE_STACKS = frozenset({"react", "next"})
SOURCE_CAPABILITIES = frozenset({"website"})

_NEXT_INTENT = re.compile(
    r"(?:用|使用|基于|采用)\s*(?:next(?:\.js)?|nextjs|ssr|服务端渲染)"
    r"|(?:next(?:\.js)?|nextjs)\s*的?\s*(?:官网|网站|应用|项目|源码)"
    r"|(?:服务端渲染|ssr)\s*的?\s*(?:官网|网站|应用|项目)",
    re.IGNORECASE,
)
_REACT_INTENT = re.compile(
    r"(?:用|使用|基于|采用)\s*(?:react|vite)"
    r"|(?:react|vite)\s*的?\s*(?:官网|网站|应用|项目|源码)",
    re.IGNORECASE,
)


def detect_source_stack(prompt: str) -> str | None:
    if _NEXT_INTENT.search(prompt):
        return "next"
    if _REACT_INTENT.search(prompt):
        return "react"
    return None


def resolve_stack(capability: str, prompt: str, requested: str | None = None) -> str:
    if capability not in SOURCE_CAPABILITIES:
        return "static"
    if requested in SOURCE_STACKS:
        return requested
    if requested == "static":
        return "static"
    return detect_source_stack(prompt) or "static"
