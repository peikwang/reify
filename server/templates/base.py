from __future__ import annotations

import html
import re

RESET = """
*,*::before,*::after{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;min-height:100vh;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
img,svg,canvas{display:block;max-width:100%}
button,input,textarea{font:inherit;color:inherit}
button{cursor:pointer}
a{color:inherit;text-decoration:none}
::selection{background:var(--accent,#b8ff5a);color:#06110a}
"""

HTML_SHELL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="generator" content="VibeForge Agent Server" />
<title>{{TITLE}}</title>
<style>
{{STYLE}}
</style>
</head>
<body>
{{BODY}}
<script>
{{SCRIPT}}
</script>
</body>
</html>
"""


def esc(value: str) -> str:
    return html.escape(str(value), quote=True)


def accent(value: str) -> str:
    if re.fullmatch(r"#[0-9a-fA-F]{6}", str(value).strip()):
        return str(value).strip()
    return "#b8ff5a"


def document(title: str, style: str, body: str, script: str = "", accent_color: str = "#b8ff5a") -> str:
    return (
        HTML_SHELL.replace("{{TITLE}}", esc(title))
        .replace("{{STYLE}}", RESET + "\n:root{--accent:" + accent(accent_color) + "}\n" + style)
        .replace("{{BODY}}", body)
        .replace("{{SCRIPT}}", script)
    )


def highlight_cards(highlights: list[str], class_name: str = "feature") -> str:
    cards = []
    for index, item in enumerate(highlights, start=1):
        cards.append(
            f'<article class="{class_name}"><span class="idx">0{index}</span>'
            f"<h3>{esc(item)}</h3><p>由 VibeForge 根据你的描述生成的设计要点。</p></article>"
        )
    return "\n".join(cards)
