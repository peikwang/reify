from __future__ import annotations

from .base import document, esc


STYLE = """
:root{--paper:#f4f1e9;--ink:#171915;--muted:#73776d;--line:rgba(23,25,21,.14);--accent:#c05e3c}
body{background:var(--paper);color:var(--ink);font-family:ui-sans-serif,-apple-system,"SF Pro Display","PingFang SC",sans-serif}
.shell{width:min(1180px,calc(100% - 32px));margin:0 auto;padding:22px 0 44px}
nav{display:flex;align-items:center;justify-content:space-between;padding:6px 0 20px;border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:9px;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.brand b{width:28px;height:28px;display:grid;place-items:center;border-radius:8px;background:var(--ink);color:#fff;font:800 12px/1 ui-monospace,monospace}
nav .meta{font:8px/1 ui-monospace,monospace;letter-spacing:.12em;color:var(--muted)}
header{padding:44px 0 28px;display:grid;grid-template-columns:1.25fr .75fr;gap:30px;align-items:end}
.kicker{font:8px/1 ui-monospace,monospace;letter-spacing:.2em;color:var(--accent);text-transform:uppercase;margin-bottom:14px}
h1{font-family:ui-serif,Georgia,"Songti SC","STSong",serif;font-size:clamp(38px,6vw,78px);line-height:.94;letter-spacing:-.055em;margin:0;font-weight:500;max-width:12ch}
.prompt{color:var(--muted);font-size:12px;line-height:1.8;margin:0;padding-left:18px;border-left:1px solid var(--line)}
.film{border:1px solid var(--line);border-radius:20px;overflow:hidden;background:#0c110e;box-shadow:0 28px 70px rgba(23,25,21,.16)}
video{display:block;width:100%;aspect-ratio:16/9;background:#0c110e;object-fit:cover}
.film-bar{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:12px 15px;background:#fff;border-top:1px solid var(--line);font:8px/1 ui-monospace,monospace;letter-spacing:.1em;color:var(--muted)}
.film-bar b{color:var(--ink);font-weight:600}
.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.btn{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line);border-radius:999px;padding:9px 12px;font:9px/1 ui-monospace,monospace;color:var(--muted);background:#fff}
.btn.primary{background:var(--ink);color:#fff;border-color:var(--ink)}
.btn:hover{border-color:var(--ink);color:var(--ink)}
.btn.primary:hover{background:var(--accent);border-color:var(--accent);color:#fff}
.meta-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:16px}
.meta-cell{border-top:1px solid var(--line);padding-top:11px}
.meta-cell small{display:block;font:8px/1 ui-monospace,monospace;letter-spacing:.12em;color:var(--muted);margin-bottom:7px}
.meta-cell b{font:600 13px/1 ui-monospace,monospace}
.footer{display:flex;justify-content:space-between;gap:20px;border-top:1px solid var(--line);margin-top:32px;padding-top:16px;color:var(--muted);font:8px/1.6 ui-monospace,monospace;letter-spacing:.08em}
@media(max-width:760px){header{grid-template-columns:1fr;gap:18px}.prompt{border-left:0;padding-left:0}.meta-grid{grid-template-columns:1fr 1fr}.footer{flex-direction:column;gap:6px}}
"""

BODY = """
<div class="shell">
  <nav><div class="brand"><b>V</b> VibeForge / Video Studio</div><div class="meta">REV {{REVISION}} · {{MODEL}}</div></nav>
  <header><div><div class="kicker">MOTION STUDY / {{DURATION}} SEC</div><h1>{{TITLE}}</h1></div><p class="prompt">{{PROMPT}}</p></header>
  <main>
    <div class="film">
      <video id="player" controls playsinline preload="metadata" src="{{VIDEO_SRC}}"></video>
      <div class="film-bar"><span><b>LOCAL RENDER</b> · {{RESOLUTION}}</span><span>{{DURATION}}s · MP4</span></div>
    </div>
    <div class="actions"><button class="btn primary" id="replay">重新播放</button><a class="btn" href="{{VIDEO_SRC}}" download>下载视频</a></div>
    <div class="meta-grid"><div class="meta-cell"><small>MODEL</small><b>{{MODEL}}</b></div><div class="meta-cell"><small>REVISION</small><b>REV {{REVISION}}</b></div><div class="meta-cell"><small>FORMAT</small><b>16:9 / MP4</b></div></div>
  </main>
  <div class="footer"><span>{{TAGLINE}}</span><span>GENERATED LOCALLY · {{DATE}}</span></div>
</div>
"""

SCRIPT = r"""
const player = document.getElementById('player');
document.getElementById('replay').addEventListener('click', () => { player.currentTime = 0; player.play(); });
"""


def render(brief: dict, asset: dict, revision: int, prompt: str, meta: dict) -> str:
    title = esc(brief.get("title", "动态影像"))
    tagline = esc(brief.get("tagline", "让画面动起来。"))
    body = (
        BODY.replace("{{TITLE}}", title)
        .replace("{{PROMPT}}", esc(prompt))
        .replace("{{VIDEO_SRC}}", esc(asset.get("url") or asset["path"]))
        .replace("{{MODEL}}", esc(str(meta.get("model", "WAN3.0-VIDEO")).upper()))
        .replace("{{REVISION}}", str(revision))
        .replace("{{DURATION}}", str(meta.get("duration", 5)))
        .replace("{{RESOLUTION}}", esc(str(meta.get("resolution", "720P"))))
        .replace("{{TAGLINE}}", tagline)
        .replace("{{DATE}}", "2026")
    )
    return document(title, STYLE, body, SCRIPT, brief.get("accent", "#c05e3c"))
