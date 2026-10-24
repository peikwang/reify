from __future__ import annotations

from .base import document, esc


STYLE = """
:root{--paper:#f4f1e9;--ink:#171915;--muted:#73776d;--line:rgba(23,25,21,.14);--accent:#336b57}
body{background:var(--paper);color:var(--ink);font-family:ui-sans-serif,-apple-system,"SF Pro Display","PingFang SC",sans-serif}
.shell{width:min(1180px,calc(100% - 32px));margin:0 auto;padding:22px 0 44px}
nav{display:flex;align-items:center;justify-content:space-between;padding:6px 0 20px;border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:9px;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.brand b{width:28px;height:28px;display:grid;place-items:center;border-radius:8px;background:var(--ink);color:#fff;font:800 12px/1 ui-monospace,monospace}
nav .meta{font:8px/1 ui-monospace,monospace;letter-spacing:.12em;color:var(--muted)}
header{padding:48px 0 30px;display:grid;grid-template-columns:1.2fr .8fr;gap:30px;align-items:end}
.kicker{font:8px/1 ui-monospace,monospace;letter-spacing:.2em;color:var(--accent);text-transform:uppercase;margin-bottom:14px}
h1{font-family:ui-serif,Georgia,"Songti SC","STSong",serif;font-size:clamp(38px,6vw,78px);line-height:.94;letter-spacing:-.055em;margin:0;font-weight:500;max-width:12ch}
.prompt{color:var(--muted);font-size:12px;line-height:1.8;margin:0;padding-left:18px;border-left:1px solid var(--line)}
.gallery{display:grid;grid-template-columns:repeat(2,1fr);grid-auto-rows:minmax(180px,auto);gap:10px;padding-top:10px}
figure{margin:0;position:relative;overflow:hidden;border-radius:16px;background:#e5e0d4;min-height:180px;border:1px solid var(--line)}
figure:first-child{grid-column:span 2;min-height:420px}
figure img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .6s cubic-bezier(.2,.7,.2,1)}
figure:hover img{transform:scale(1.025)}
figcaption{position:absolute;left:12px;right:12px;bottom:10px;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 10px;border-radius:8px;background:rgba(15,20,16,.58);backdrop-filter:blur(8px);color:#f4f1e9;font:8px/1 ui-monospace,monospace;letter-spacing:.06em}
figcaption a{color:#d9ff8a;border-bottom:1px solid rgba(217,255,138,.4);padding-bottom:2px}
.footer{display:flex;justify-content:space-between;gap:20px;border-top:1px solid var(--line);margin-top:32px;padding-top:16px;color:var(--muted);font:8px/1.6 ui-monospace,monospace;letter-spacing:.08em}
.lightbox{position:fixed;inset:0;z-index:10;display:none;place-items:center;background:rgba(12,16,13,.82);padding:24px;backdrop-filter:blur(8px)}
.lightbox.open{display:grid}
.lightbox img{max-width:min(1100px,96vw);max-height:86vh;object-fit:contain;border-radius:12px;box-shadow:0 30px 90px rgba(0,0,0,.4)}
.lightbox button{position:absolute;right:18px;top:16px;border:1px solid rgba(255,255,255,.2);background:rgba(255,255,255,.08);color:#fff;border-radius:999px;padding:8px 12px;font:9px/1 ui-monospace,monospace}
@media(max-width:760px){header{grid-template-columns:1fr;gap:18px}.prompt{border-left:0;padding-left:0}figure:first-child{min-height:260px}.gallery{grid-template-columns:1fr}figure:first-child{grid-column:auto}.footer{flex-direction:column;gap:6px}}
"""

BODY = """
<div class="shell">
  <nav><div class="brand"><b>R</b> Reify / Image Studio</div><div class="meta">{{COUNT}} FRAMES · {{MODEL}}</div></nav>
  <header><div><div class="kicker">VISUAL STUDY / REV {{REVISION}}</div><h1>{{TITLE}}</h1></div><p class="prompt">{{PROMPT}}</p></header>
  <main class="gallery">{{CARDS}}</main>
  <div class="footer"><span>{{TAGLINE}}</span><span>GENERATED LOCALLY · {{DATE}}</span></div>
</div>
<div class="lightbox" id="lightbox"><button id="closeLightbox">关闭</button><img id="lightboxImage" alt="生成图片大图" /></div>
"""

SCRIPT = r"""
const lightbox = document.getElementById('lightbox');
const lightboxImage = document.getElementById('lightboxImage');
document.querySelectorAll('.gallery figure img').forEach(img => {
  img.addEventListener('click', () => {
    lightboxImage.src = img.src;
    lightbox.classList.add('open');
  });
});
document.getElementById('closeLightbox').addEventListener('click', () => lightbox.classList.remove('open'));
lightbox.addEventListener('click', (event) => { if (event.target === lightbox) lightbox.classList.remove('open'); });
document.addEventListener('keydown', (event) => { if (event.key === 'Escape') lightbox.classList.remove('open'); });
"""


def render(brief: dict, assets: list[dict], revision: int, prompt: str) -> str:
    title = esc(brief.get("title", "图像工作室"))
    tagline = esc(brief.get("tagline", "把一句话，变成一张可以保存的画面。"))
    cards = []
    for index, asset in enumerate(assets, start=1):
        path = esc(asset.get("url") or asset["path"])
        cards.append(
            f'<figure><img src="{path}" alt="生成图片 {index}" loading="lazy" />'
            f'<figcaption><span>FRAME {index:02d} / {esc(asset.get("mime", "image"))}</span>'
            f'<a href="{path}" download>下载</a></figcaption></figure>'
        )
    body = (
        BODY.replace("{{TITLE}}", title)
        .replace("{{COUNT}}", str(len(assets)))
        .replace("{{MODEL}}", esc(brief.get("model", "QWEN-IMAGE")))
        .replace("{{REVISION}}", str(revision))
        .replace("{{PROMPT}}", esc(prompt))
        .replace("{{TAGLINE}}", tagline)
        .replace("{{CARDS}}", "".join(cards))
        .replace("{{DATE}}", "2026")
    )
    return document(title, STYLE, body, SCRIPT, brief.get("accent", "#336b57"))
