from __future__ import annotations

from .base import document, esc


STYLE = """
:root{--paper:#ece9e1;--ink:#141412;--muted:#78746a;--line:rgba(20,20,18,.14);--warm:#f5f1e7}
body{background:var(--paper);color:var(--ink);font-family:ui-sans-serif,-apple-system,"SF Pro Display","PingFang SC",sans-serif}
.shell{width:min(1220px,calc(100% - 36px));margin:0 auto;padding:22px 0 48px}
nav{display:flex;align-items:center;justify-content:space-between;padding:10px 0 22px;border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:9px;font-weight:800;letter-spacing:-.02em}
.brand b{width:28px;height:28px;display:grid;place-items:center;background:var(--ink);color:var(--paper);border-radius:8px;font-size:12px}
nav .right{font:10px/1 ui-monospace,monospace;letter-spacing:.14em;color:var(--muted)}
.hero{display:grid;grid-template-columns:1.25fr .75fr;gap:30px;align-items:end;padding:42px 0 30px}
.kicker{font:10px/1 ui-monospace,monospace;letter-spacing:.2em;color:var(--muted);text-transform:uppercase;margin-bottom:16px}
h1{font-size:clamp(40px,6.8vw,90px);line-height:.9;letter-spacing:-.07em;margin:0 0 16px;font-weight:800}
h1 em{font-style:normal;color:var(--accent)}
.lede{max-width:50ch;color:var(--muted);font-size:14px;line-height:1.75;margin:0}
.controls{display:flex;flex-wrap:wrap;gap:6px;justify-content:flex-end}
.size-btn{border:1px solid var(--line);background:transparent;border-radius:999px;padding:10px 13px;font:10px/1 ui-monospace,monospace;letter-spacing:.06em;color:var(--muted)}
.size-btn.active{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.stage{display:grid;grid-template-columns:1fr 280px;gap:14px;align-items:start}
.artboard-wrap{border:1px solid var(--line);border-radius:24px;background:
 linear-gradient(45deg,rgba(20,20,18,.035) 25%,transparent 25%,transparent 75%,rgba(20,20,18,.035) 75%),var(--warm);background-size:18px 18px;padding:26px;min-height:520px;display:grid;place-items:center;position:relative;overflow:hidden}
.artboard-wrap::before{content:"LIVE ARTBOARD";position:absolute;left:22px;top:18px;font:9px/1 ui-monospace,monospace;letter-spacing:.18em;color:var(--muted)}
.artboard{width:min(100%,820px);aspect-ratio:16/9;background:#151513;color:#f2eee4;border-radius:18px;overflow:hidden;position:relative;display:grid;grid-template-columns:1.1fr .9fr;box-shadow:0 30px 80px rgba(25,24,20,.25);transition:aspect-ratio .45s cubic-bezier(.2,.7,.2,1),width .45s}
.artboard[data-ratio="1:1"]{aspect-ratio:1;width:min(72%,560px);grid-template-columns:1fr}
.artboard[data-ratio="9:16"]{aspect-ratio:9/16;width:min(46%,320px);grid-template-columns:1fr}
.copy{padding:clamp(20px,4vw,48px);display:flex;flex-direction:column;justify-content:space-between;position:relative;z-index:2}
.mini{font:9px/1 ui-monospace,monospace;letter-spacing:.18em;color:var(--accent);text-transform:uppercase}
.artboard h2{font-size:clamp(26px,4vw,54px);line-height:.94;letter-spacing:-.055em;margin:18px 0 12px;font-weight:800}
.artboard p{font-size:11px;line-height:1.7;color:#a7a297;max-width:32ch;margin:0}
.artboard .cta{align-self:flex-start;border:1px solid rgba(255,255,255,.2);border-radius:999px;padding:9px 13px;font:9px/1 ui-monospace,monospace;letter-spacing:.08em;margin-top:18px}
.visual{position:relative;overflow:hidden;background:radial-gradient(circle at 30% 30%,color-mix(in srgb,var(--accent) 75%,#fff),var(--accent) 38%,#22221e 72%);min-height:160px}
.visual::before{content:"";position:absolute;width:70%;aspect-ratio:1;border:1px solid rgba(255,255,255,.3);border-radius:50%;right:-10%;top:14%;transform:rotate(-18deg)}
.visual::after{content:"";position:absolute;width:36%;aspect-ratio:1;border-radius:50%;background:#f4efe2;right:18%;top:32%;box-shadow:0 0 60px rgba(255,255,255,.35)}
.artboard[data-ratio="1:1"] .visual,.artboard[data-ratio="9:16"] .visual{position:absolute;inset:0;opacity:.34}
.artboard[data-ratio="1:1"] .copy,.artboard[data-ratio="9:16"] .copy{justify-content:flex-end;min-height:100%}
.artboard[data-ratio="9:16"] h2{font-size:clamp(24px,3.8vw,38px)}
.side{display:grid;gap:10px}
.panel{border:1px solid var(--line);border-radius:18px;padding:18px;background:rgba(255,255,255,.3)}
.panel small{display:block;font:9px/1 ui-monospace,monospace;letter-spacing:.16em;color:var(--muted);margin-bottom:12px}
.spec{display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid var(--line);font-size:11px}
.spec:last-child{border-bottom:0}
.spec b{font-family:ui-monospace,monospace;font-weight:600}
.panel p{font-size:11px;line-height:1.7;color:var(--muted);margin:0}
.bars{display:grid;gap:8px;margin-top:6px}
.bar{height:7px;border-radius:9px;background:rgba(20,20,18,.09);overflow:hidden}
.bar i{display:block;height:100%;width:var(--w);background:var(--accent);border-radius:9px}
.thumbs{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:20px}
.thumb{border:1px solid var(--line);border-radius:14px;padding:12px;background:rgba(255,255,255,.26);text-align:left;transition:transform .2s}
.thumb:hover{transform:translateY(-3px)}
.thumb.active{border-color:var(--ink);background:var(--ink);color:var(--paper)}
.thumb span{display:block;font:9px/1 ui-monospace,monospace;color:var(--muted);margin-bottom:8px}
.thumb.active span{color:rgba(255,255,255,.55)}
.thumb b{font:600 13px/1 ui-monospace,monospace}
footer{display:flex;justify-content:space-between;border-top:1px solid var(--line);margin-top:30px;padding-top:18px;font:9px/1.5 ui-monospace,monospace;color:var(--muted);letter-spacing:.1em}
@media(max-width:900px){.hero{grid-template-columns:1fr}.controls{justify-content:flex-start}.stage{grid-template-columns:1fr}.side{grid-template-columns:1fr 1fr}.artboard{width:100%}.artboard[data-ratio="1:1"]{width:min(92%,560px)}.artboard[data-ratio="9:16"]{width:min(70%,340px)}}
@media(max-width:560px){.side{grid-template-columns:1fr}.artboard{padding:0}.artboard-wrap{padding:18px;min-height:420px}.artboard h2{font-size:28px}.copy{padding:22px}footer{flex-direction:column;gap:6px}}
"""

BODY = """
<div class="shell">
  <nav><div class="brand"><b>V</b>VibeForge / Adaptive Studio</div><div class="right">ONE IDEA · EVERY FORMAT</div></nav>
  <section class="hero">
    <div><div class="kicker">ADAPTIVE PRODUCTION / {{YEAR}}</div><h1>一个想法，<br><em>适配所有尺寸。</em></h1><p class="lede">{{PARAGRAPH}} {{TAGLINE}}</p></div>
    <div class="controls"><button class="size-btn active" data-ratio="16:9">16:9 横版</button><button class="size-btn" data-ratio="1:1">1:1 方图</button><button class="size-btn" data-ratio="9:16">9:16 竖版</button></div>
  </section>
  <section class="stage">
    <div class="artboard-wrap">
      <div class="artboard" id="artboard" data-ratio="16:9">
        <div class="copy"><div><div class="mini">{{KICKER}}</div><h2>{{HEADLINE}}</h2><p>{{TAGLINE}}</p><div class="cta">SWIPE TO ADAPT ↗</div></div></div>
        <div class="visual"></div>
      </div>
      <div class="thumbs"><button class="thumb active" data-ratio="16:9"><span>FORMAT 01</span><b>16:9</b></button><button class="thumb" data-ratio="1:1"><span>FORMAT 02</span><b>1:1</b></button><button class="thumb" data-ratio="9:16"><span>FORMAT 03</span><b>9:16</b></button></div>
    </div>
    <aside class="side">
      <div class="panel"><small>EXPORT SPECS</small><div class="spec"><span>Desktop hero</span><b>1920 × 1080</b></div><div class="spec"><span>Social square</span><b>1080 × 1080</b></div><div class="spec"><span>Story / Reels</span><b>1080 × 1920</b></div><div class="spec"><span>Safe margin</span><b>64 px</b></div></div>
      <div class="panel"><small>LAYOUT HEALTH</small><div class="bars"><div class="bar"><i style="--w:100%"></i></div><div class="bar"><i style="--w:92%"></i></div><div class="bar"><i style="--w:86%"></i></div></div><p style="margin-top:12px">标题、正文与 CTA 在每个画板内自动重排，不裁切、不溢出。</p></div>
      <div class="panel"><small>DESIGN TOKENS</small><p>Accent · {{ACCENT}}<br>Type · 8pt baseline<br>Radius · 18 / 999<br>Grid · 12 columns</p></div>
    </aside>
  </section>
  <footer><span>ADAPTIVE STUDIO / GENERATED BY VIBEFORGE</span><span>SWITCH FORMATS ABOVE · RESIZE WINDOW TO TEST</span></footer>
</div>
"""

SCRIPT = r"""
const artboard = document.getElementById('artboard');
function setRatio(ratio) {
  artboard.dataset.ratio = ratio;
  document.querySelectorAll('[data-ratio]').forEach(el => el.classList.toggle('active', el.dataset.ratio === ratio));
}
document.querySelectorAll('[data-ratio]').forEach(el => el.addEventListener('click', () => setRatio(el.dataset.ratio)));
window.addEventListener('keydown', e => {
  if (e.key === '1') setRatio('16:9'); if (e.key === '2') setRatio('1:1'); if (e.key === '3') setRatio('9:16');
});
"""


def render(brief: dict) -> str:
    title = esc(brief.get("title", "多端适配工坊"))
    tagline = esc(brief.get("tagline", "让同一套内容，在每一块屏幕上都成立。"))
    paragraph = esc(brief.get("paragraph", "从主视觉出发，自动重排标题、正文与行动按钮，生成横版、方图与竖版三种投放规格。"))
    headline = esc(brief.get("headline", "把复杂，留给我们。"))
    body = (
        BODY.replace("{{HEADLINE}}", headline)
        .replace("{{TAGLINE}}", tagline)
        .replace("{{PARAGRAPH}}", paragraph)
        .replace("{{KICKER}}", "VIBEFORGE / CAMPAIGN SYSTEM")
        .replace("{{ACCENT}}", esc(brief.get("accent", "#ff6b4a")))
        .replace("{{YEAR}}", "2026")
    )
    return document(title, STYLE, body, SCRIPT, brief.get("accent", "#ff6b4a"))
