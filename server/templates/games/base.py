from __future__ import annotations

from ..base import document, esc

COMMON_CSS = """
:root{--ink:#eaf7ef;--muted:#8fa39a;--panel:#0d1512;--line:rgba(184,255,90,.18)}
body{background:
  radial-gradient(900px 540px at 15% -10%, color-mix(in srgb, var(--accent) 18%, transparent), transparent 62%),
  radial-gradient(700px 420px at 100% 10%, rgba(84,225,255,.12), transparent 60%),
  #070b09;color:var(--ink);font-family:ui-sans-serif,-apple-system,"SF Pro Display","PingFang SC",sans-serif;overflow-x:hidden}
body::before{content:"";position:fixed;inset:0;pointer-events:none;background-image:linear-gradient(rgba(255,255,255,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.025) 1px,transparent 1px);background-size:48px 48px;mask-image:radial-gradient(circle at 50% 30%,#000,transparent 78%)}
.shell{width:min(1120px,calc(100% - 36px));margin:0 auto;padding:18px 0 28px;position:relative;z-index:1}
.top{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:16px}
.brand{display:flex;align-items:center;gap:10px;font-size:12px;letter-spacing:.2em;text-transform:uppercase;color:var(--muted)}
.brand i{width:9px;height:9px;border-radius:50%;background:var(--accent);box-shadow:0 0 18px var(--accent);animation:pulse 1.8s infinite}
.top .meta{font:10px/1 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted);letter-spacing:.14em}
@keyframes pulse{50%{opacity:.35;transform:scale(.8)}}
.intro{margin-bottom:4px}
.intro .kicker{font:9px/1 ui-monospace,monospace;letter-spacing:.18em;color:var(--accent);text-transform:uppercase;margin-bottom:10px}
.intro h1{font-size:clamp(28px,3.2vw,42px);line-height:.94;letter-spacing:-.05em;margin:0 0 10px;font-weight:800}
.intro h1 span{color:var(--accent);text-shadow:0 0 32px color-mix(in srgb,var(--accent) 45%,transparent)}
.intro .lede{color:var(--muted);font-size:12px;line-height:1.7;max-width:34ch;margin:0}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.stat{border:1px solid var(--line);background:rgba(13,21,18,.68);border-radius:13px;padding:11px 12px;backdrop-filter:blur(14px)}
.stat small{display:block;color:var(--muted);font:8px/1 ui-monospace,monospace;letter-spacing:.14em;text-transform:uppercase;margin-bottom:8px}
.stat strong{font:700 22px/1 ui-monospace,monospace;color:var(--accent)}
.arena{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:16px;align-items:start}
.game-card{position:relative;border:1px solid var(--line);border-radius:26px;background:linear-gradient(180deg,rgba(18,29,24,.94),rgba(8,13,11,.94));padding:12px;box-shadow:0 30px 90px rgba(0,0,0,.45),inset 0 1px rgba(255,255,255,.05)}
.canvas-wrap{position:relative;border-radius:18px;overflow:hidden;background:#050907;border:1px solid rgba(255,255,255,.07);margin:0 auto}
canvas{width:100%;height:auto;touch-action:none;background:#050907}
.overlay{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:24px;background:radial-gradient(circle at 50% 40%,rgba(7,11,9,.55),rgba(5,9,7,.94));backdrop-filter:blur(4px);transition:opacity .35s,visibility .35s}
.overlay.hide{opacity:0;visibility:hidden}
.overlay .kicker{font:10px/1 ui-monospace,monospace;letter-spacing:.22em;color:var(--accent);text-transform:uppercase;margin-bottom:14px}
.overlay h2{font-size:clamp(26px,4vw,44px);letter-spacing:-.04em;margin:0 0 10px}
.overlay p{color:var(--muted);font-size:13px;line-height:1.6;margin:0 0 20px;max-width:34ch}
.btn{border:0;border-radius:999px;padding:13px 22px;background:var(--accent);color:#07110a;font-weight:800;letter-spacing:.02em;box-shadow:0 0 30px color-mix(in srgb,var(--accent) 35%,transparent);transition:transform .2s,box-shadow .2s}
.btn:hover{transform:translateY(-2px);box-shadow:0 0 44px color-mix(in srgb,var(--accent) 55%,transparent)}
.hud{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:4px 4px 14px;font:11px/1 ui-monospace,monospace;letter-spacing:.12em;color:var(--muted)}
.hud b{color:var(--ink);font-size:14px}
.hud .live{display:flex;align-items:center;gap:7px;color:var(--accent)}
.hud .live i{width:6px;height:6px;border-radius:50%;background:var(--accent);animation:pulse 1.4s infinite}
.side{display:grid;gap:12px}
.panel{border:1px solid var(--line);background:rgba(13,21,18,.72);border-radius:18px;padding:18px;backdrop-filter:blur(14px)}
.panel small{display:block;font:10px/1 ui-monospace,monospace;letter-spacing:.18em;color:var(--muted);text-transform:uppercase;margin-bottom:12px}
.keys{display:grid;grid-template-columns:repeat(3,34px);grid-template-rows:repeat(2,34px);gap:6px;justify-content:center}
.keys span{display:grid;place-items:center;border:1px solid rgba(255,255,255,.1);border-radius:9px;color:var(--muted);font:11px/1 ui-monospace,monospace;background:rgba(255,255,255,.03)}
.panel p{color:var(--muted);font-size:12px;line-height:1.65;margin:0}
.touch-pad{display:none;grid-template-columns:repeat(auto-fit,minmax(52px,1fr));gap:8px;margin-top:14px}
.touch-pad button{border:1px solid var(--line);border-radius:14px;background:rgba(255,255,255,.04);color:var(--ink);font-size:16px;padding:12px 6px;transition:background .15s,transform .15s}
.touch-pad button:active{background:var(--accent);color:#07110a;transform:scale(.94)}
.tips{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px}
.tip{border-top:1px solid var(--line);padding-top:12px;color:var(--muted);font-size:12px;line-height:1.6}
.tip b{display:block;color:var(--ink);font-size:13px;margin-bottom:5px}
@media(max-width:860px){.arena{grid-template-columns:1fr}.side{grid-template-columns:1fr 1fr}.intro,.stats{grid-column:1/-1}.touch-pad{display:grid}.keys{display:none}}
@media(max-width:560px){.shell{padding-top:14px}.top .meta{display:none}.stats{gap:6px}.stat{padding:9px}.stat strong{font-size:18px}.side{grid-template-columns:1fr}.tips{grid-template-columns:1fr}}
"""

PRELUDE = r"""
const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');
const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#b8ff5a';
const scoreEl = document.getElementById('score');
const bestEl = document.getElementById('best');
const statusEl = document.getElementById('statusText');
const overlay = document.getElementById('overlay');
const startBtn = document.getElementById('startBtn');
function readBest(key) { try { return Number(localStorage.getItem(key) || 0); } catch (_) { return 0; } }
function saveBest(key, value) { try { localStorage.setItem(key, String(value)); } catch (_) {} }
function setStatus(text) { statusEl.textContent = text; }
function hideOverlay() { overlay.classList.add('hide'); }
function showOverlay(kicker, title, text, buttonText) {
  overlay.querySelector('.kicker').textContent = kicker;
  overlay.querySelector('h2').textContent = title;
  overlay.querySelector('p').textContent = text;
  startBtn.textContent = buttonText;
  overlay.classList.remove('hide');
}
function roundRectPath(x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}
function clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }
"""


def render_game_page(
    brief: dict,
    *,
    genre: str,
    hud_meta: str,
    canvas_width: int,
    canvas_height: int,
    canvas_max_width: int,
    canvas_label: str,
    overlay_text: str,
    intro_span: str,
    controls_html: str,
    touch_html: str,
    mission: str,
    tips: list[tuple[str, str]],
    stats: list[tuple[str, str, str]],
    script: str,
    extra_css: str = "",
) -> str:
    title = esc(brief.get("title", "小游戏"))
    tagline = esc(brief.get("tagline", "一个小而完整的浏览器街机。"))
    paragraph = esc(brief.get("paragraph", "打开即玩，键盘和触控都能操作。"))
    genre_label = esc(genre.upper())
    stats_html = "".join(
        f'<div class="stat"><small>{esc(label)}</small>'
        f'<strong id="{esc(element_id)}">{esc(initial)}</strong></div>'
        for label, element_id, initial in stats
    )
    tips_html = "".join(
        f'<div class="tip"><b>{esc(label)}</b>{esc(text)}</div>'
        for label, text in tips
    )
    body = f"""
<div class="shell">
  <header class="top">
    <div class="brand"><i></i> Reify · Game Studio</div>
    <div class="meta">{genre_label} / LOCAL BUILD / 60 FPS / NO DEPENDENCIES</div>
  </header>
  <section class="arena">
    <div class="game-card">
      <div class="hud"><span class="live"><i></i> LIVE</span><span id="hudMeta">{esc(hud_meta)}</span><span id="statusText">READY</span></div>
      <div class="canvas-wrap" style="max-width:{int(canvas_max_width)}px">
        <canvas id="game" width="{int(canvas_width)}" height="{int(canvas_height)}" aria-label="{esc(canvas_label)}"></canvas>
        <div class="overlay" id="overlay">
          <div class="kicker">A TINY ARCADE / {genre_label}</div>
          <h2>{title}</h2>
          <p>{tagline} {esc(overlay_text)}</p>
          <button class="btn" id="startBtn">开始游戏</button>
        </div>
      </div>
      <div class="touch-pad" aria-label="触控操作">{touch_html}</div>
    </div>
    <aside class="side">
      <div class="intro"><div class="kicker">A TINY ARCADE / {genre_label}</div><h1>{title}<br><span>{esc(intro_span)}</span></h1><p class="lede">{tagline} {paragraph}</p></div>
      <div class="stats">{stats_html}</div>
      <div class="panel"><small>CONTROLS</small>{controls_html}</div>
      <div class="panel"><small>MISSION</small><p>{esc(mission)}</p></div>
      <div class="panel"><small>BUILT BY AGENT</small><p>这个页面由 Reify 的 ToolAct 循环生成：规划 → 写文件 → 自检 → 部署。</p></div>
    </aside>
  </section>
  <div class="tips">{tips_html}</div>
</div>
"""
    return document(
        str(brief.get("title", "小游戏")),
        COMMON_CSS + extra_css,
        body,
        PRELUDE + "\n" + script,
        brief.get("accent", "#b8ff5a"),
    )
