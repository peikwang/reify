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
_PERSONAL_MARKER = re.compile(r"(?:个人|我的|personal|my\b)", re.IGNORECASE)
_NON_PERSONAL_MARKER = re.compile(
    r"(?:公司|团队|企业|工作室|机构|品牌方|organization|company|team|studio)",
    re.IGNORECASE,
)
_PORTFOLIO_MARKER = re.compile(r"(?:作品集|portfolio|博客|blog)", re.IGNORECASE)


def detect_source_stack(prompt: str) -> str | None:
    if _NEXT_INTENT.search(prompt):
        return "next"
    if _REACT_INTENT.search(prompt):
        return "react"
    return None


def is_personal_website(prompt: str) -> bool:
    if _PERSONAL_MARKER.search(prompt):
        return True
    if _NON_PERSONAL_MARKER.search(prompt):
        return False
    return bool(_PORTFOLIO_MARKER.search(prompt))


def resolve_stack(capability: str, prompt: str, requested: str | None = None) -> str:
    if capability not in SOURCE_CAPABILITIES:
        return "static"
    if requested in SOURCE_STACKS:
        return requested
    if requested == "static":
        return "static"
    detected = detect_source_stack(prompt)
    if detected:
        return detected
    if is_personal_website(prompt):
        return "react"
    return "static"
