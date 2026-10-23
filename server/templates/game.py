from __future__ import annotations

from .base import document, esc


STYLE = """
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
.canvas-wrap{position:relative;border-radius:18px;overflow:hidden;background:#050907;border:1px solid rgba(255,255,255,.07);max-width:440px;margin:0 auto}
canvas{width:100%;height:auto;aspect-ratio:1;touch-action:none}
.overlay{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:24px;background:radial-gradient(circle at 50% 40%,rgba(7,11,9,.55),rgba(5,9,7,.94));backdrop-filter:blur(4px);transition:opacity .35s,visibility .35s}
.overlay.hide{opacity:0;visibility:hidden}
.overlay .kicker{font:10px/1 ui-monospace,monospace;letter-spacing:.22em;color:var(--accent);text-transform:uppercase;margin-bottom:14px}
.overlay h2{font-size:clamp(26px,4vw,44px);letter-spacing:-.04em;margin:0 0 10px}
.overlay p{color:var(--muted);font-size:13px;line-height:1.6;margin:0 0 20px;max-width:34ch}
.btn{border:0;border-radius:999px;padding:13px 22px;background:var(--accent);color:#07110a;font-weight:800;letter-spacing:.02em;box-shadow:0 0 30px color-mix(in srgb,var(--accent) 35%,transparent);transition:transform .2s,box-shadow .2s}
.btn:hover{transform:translateY(-2px);box-shadow:0 0 44px color-mix(in srgb,var(--accent) 55%,transparent)}
.btn.ghost{background:transparent;color:var(--ink);border:1px solid var(--line);box-shadow:none}
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
.dpad{display:none;grid-template-columns:repeat(3,52px);grid-template-rows:repeat(2,52px);gap:8px;justify-content:center;margin-top:14px}
.dpad button{border:1px solid var(--line);border-radius:14px;background:rgba(255,255,255,.04);color:var(--ink);font-size:18px;transition:background .15s,transform .15s}
.dpad button:active{background:var(--accent);color:#07110a;transform:scale(.94)}
.tips{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px}
.tip{border-top:1px solid var(--line);padding-top:12px;color:var(--muted);font-size:12px;line-height:1.6}
.tip b{display:block;color:var(--ink);font-size:13px;margin-bottom:5px}
@media(max-width:860px){.arena{grid-template-columns:1fr}.side{grid-template-columns:1fr 1fr}.intro,.stats{grid-column:1/-1}.dpad{display:grid}.keys{display:none}}
@media(max-width:560px){.shell{padding-top:14px}.top .meta{display:none}.stats{gap:6px}.stat{padding:9px}.stat strong{font-size:18px}.side{grid-template-columns:1fr}.tips{grid-template-columns:1fr}}
"""

BODY = """
<div class="shell">
  <header class="top">
    <div class="brand"><i></i> VibeForge · Game Studio</div>
    <div class="meta">LOCAL BUILD / 60 FPS / NO DEPENDENCIES</div>
  </header>
  <section class="arena">
    <div class="game-card">
      <div class="hud"><span class="live"><i></i> LIVE</span><span>GRID 24 × 24</span><span id="statusText">READY</span></div>
      <div class="canvas-wrap">
        <canvas id="game" width="576" height="576" aria-label="霓虹贪吃蛇游戏画布"></canvas>
        <div class="overlay" id="overlay">
          <div class="kicker">A TINY ARCADE</div>
          <h2>{{TITLE}}</h2>
          <p>{{TAGLINE}} 用方向键 / WASD 控制，吃掉能量点，别撞上墙和自己。</p>
          <button class="btn" id="startBtn">开始游戏</button>
        </div>
      </div>
      <div class="dpad" aria-label="触控方向键">
        <span></span><button data-dir="up">↑</button><span></span>
        <button data-dir="left">←</button><button data-dir="down">↓</button><button data-dir="right">→</button>
      </div>
    </div>
    <aside class="side">
      <div class="intro"><div class="kicker">A TINY ARCADE</div><h1>{{TITLE}}<br><span>再吃一颗。</span></h1><p class="lede">{{TAGLINE}} {{PARAGRAPH}}</p></div>
      <div class="stats">
        <div class="stat"><small>SCORE</small><strong id="score">0</strong></div>
        <div class="stat"><small>BEST</small><strong id="best">0</strong></div>
        <div class="stat"><small>SPEED</small><strong id="speed">1.0x</strong></div>
      </div>
      <div class="panel"><small>CONTROLS</small><div class="keys"><span>W</span><span>↑</span><span>P</span><span>A</span><span>S</span><span>D</span></div><p style="margin-top:12px">方向键 / WASD 移动，P 暂停，空格重开。</p></div>
      <div class="panel"><small>MISSION</small><p>每吃 5 颗能量点，速度提升一级。最高分会保存在当前浏览器。</p></div>
      <div class="panel"><small>BUILT BY AGENT</small><p>这个页面由 VibeForge 的 ToolAct 循环生成：规划 → 写文件 → 自检 → 部署。</p></div>
    </aside>
  </section>
  <div class="tips">
    <div class="tip"><b>01 · 移动</b>键盘与触控双操作，移动端自动显示方向键。</div>
    <div class="tip"><b>02 · 节奏</b>速度会随得分提升，留出下一格的判断时间。</div>
    <div class="tip"><b>03 · 记录</b>最高分写入 localStorage，刷新页面也不会丢失。</div>
  </div>
</div>
"""

SCRIPT = r"""
const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');
const CELL = 24, COLS = 24, ROWS = 24;
const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#b8ff5a';
const scoreEl = document.getElementById('score');
const bestEl = document.getElementById('best');
const speedEl = document.getElementById('speed');
const statusEl = document.getElementById('statusText');
const overlay = document.getElementById('overlay');
const startBtn = document.getElementById('startBtn');

let snake, dir, nextDir, food, score, best, running, paused, timer, tickMs, particles;
function readBest() { try { return Number(localStorage.getItem('vibeforge-snake-best') || 0); } catch (_) { return 0; } }
function saveBest(value) { try { localStorage.setItem('vibeforge-snake-best', value); } catch (_) {} }
best = readBest();
bestEl.textContent = best;

function reset() {
  snake = [{x:12,y:12},{x:11,y:12},{x:10,y:12}];
  dir = {x:1,y:0}; nextDir = {x:1,y:0};
  score = 0; tickMs = 145; paused = false; particles = [];
  scoreEl.textContent = '0'; speedEl.textContent = '1.0x'; statusEl.textContent = 'READY';
  placeFood(); draw();
}
function placeFood() {
  do { food = {x: Math.floor(Math.random()*COLS), y: Math.floor(Math.random()*ROWS)}; }
  while (snake.some(s => s.x === food.x && s.y === food.y));
}
function start() {
  reset(); running = true; overlay.classList.add('hide'); statusEl.textContent = 'RUNNING';
  clearInterval(timer); timer = setInterval(tick, tickMs);
}
function tick() {
  if (!running || paused) return;
  dir = nextDir;
  const head = {x: snake[0].x + dir.x, y: snake[0].y + dir.y};
  if (head.x < 0 || head.y < 0 || head.x >= COLS || head.y >= ROWS || snake.some(s => s.x === head.x && s.y === head.y)) return gameOver();
  snake.unshift(head);
  if (head.x === food.x && head.y === food.y) {
    score += 1; scoreEl.textContent = score;
    burst(head.x, head.y);
    if (score % 5 === 0 && tickMs > 75) {
      tickMs = Math.max(75, tickMs - 12);
      clearInterval(timer); timer = setInterval(tick, tickMs);
      speedEl.textContent = (145 / tickMs).toFixed(1) + 'x';
    }
    placeFood();
  } else snake.pop();
  draw();
}
function burst(gx, gy) {
  for (let i=0;i<16;i++) particles.push({x:(gx+.5)*CELL,y:(gy+.5)*CELL,vx:(Math.random()-.5)*4,vy:(Math.random()-.5)*4,life:1});
}
function draw() {
  ctx.clearRect(0,0,canvas.width,canvas.height);
  const bg = ctx.createLinearGradient(0,0,canvas.width,canvas.height);
  bg.addColorStop(0,'#050a07'); bg.addColorStop(1,'#0a1410'); ctx.fillStyle = bg; ctx.fillRect(0,0,canvas.width,canvas.height);
  ctx.strokeStyle = 'rgba(255,255,255,.035)'; ctx.lineWidth = 1;
  for (let i=0;i<=COLS;i++){ctx.beginPath();ctx.moveTo(i*CELL,0);ctx.lineTo(i*CELL,canvas.height);ctx.stroke();ctx.beginPath();ctx.moveTo(0,i*CELL);ctx.lineTo(canvas.width,i*CELL);ctx.stroke();}
  const fx=(food.x+.5)*CELL, fy=(food.y+.5)*CELL;
  ctx.save(); ctx.shadowColor=accent; ctx.shadowBlur=28; ctx.fillStyle=accent;
  ctx.beginPath(); ctx.arc(fx,fy,CELL*.26,0,Math.PI*2); ctx.fill();
  ctx.globalAlpha=.22; ctx.beginPath(); ctx.arc(fx,fy,CELL*.55,0,Math.PI*2); ctx.fill(); ctx.restore();
  snake.forEach((seg,i)=>{
    const x=seg.x*CELL, y=seg.y*CELL;
    ctx.save(); ctx.shadowColor=accent; ctx.shadowBlur=i===0?22:8;
    ctx.fillStyle=i===0?accent:'rgba(184,255,90,'+Math.max(.22,.8-i*.028)+')';
    roundRect(x+2,y+2,CELL-4,CELL-4,i===0?7:5); ctx.fill(); ctx.restore();
    if(i===0){ctx.fillStyle='#07110a';ctx.beginPath();ctx.arc(x+CELL*.34,y+CELL*.38,2.1,0,Math.PI*2);ctx.arc(x+CELL*.66,y+CELL*.38,2.1,0,Math.PI*2);ctx.fill();}
  });
  particles.forEach(p=>{ctx.globalAlpha=Math.max(0,p.life);ctx.fillStyle=accent;ctx.fillRect(p.x,p.y,2,2);});
  ctx.globalAlpha=1;
}
function roundRect(x,y,w,h,r){ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath();}
function gameOver() {
  running = false; clearInterval(timer); statusEl.textContent = 'GAME OVER';
  best = Math.max(best, score); saveBest(best); bestEl.textContent = best;
  overlay.classList.remove('hide');
  overlay.querySelector('.kicker').textContent = score >= best && score > 0 ? 'NEW HIGH SCORE' : 'RUN COMPLETE';
  overlay.querySelector('h2').textContent = '本局得分 ' + score;
  overlay.querySelector('p').textContent = '最高分 ' + best + '。再来一局，试试更长的轨迹。';
  startBtn.textContent = '再来一局';
}
function setDir(x,y){ if (dir.x === -x && dir.y === -y) return; nextDir={x,y}; }
document.addEventListener('keydown', e=>{
  const k=e.key.toLowerCase();
  if(['arrowup','w'].includes(k)) return setDir(0,-1);
  if(['arrowdown','s'].includes(k)) return setDir(0,1);
  if(['arrowleft','a'].includes(k)) return setDir(-1,0);
  if(['arrowright','d'].includes(k)) return setDir(1,0);
  if(k==='p'){ if(!running)return; paused=!paused; statusEl.textContent=paused?'PAUSED':'RUNNING'; }
  if(k===' '){ e.preventDefault(); start(); }
});
document.querySelectorAll('[data-dir]').forEach(btn=>btn.addEventListener('click',()=>{
  const d=btn.dataset.dir; if(d==='up')setDir(0,-1); if(d==='down')setDir(0,1); if(d==='left')setDir(-1,0); if(d==='right')setDir(1,0);
}));
let touchStart=null;
canvas.addEventListener('touchstart',e=>{touchStart=e.touches[0];},{passive:true});
canvas.addEventListener('touchend',e=>{
  if(!touchStart)return; const t=e.changedTouches[0]; const dx=t.clientX-touchStart.clientX, dy=t.clientY-touchStart.clientY;
  if(Math.max(Math.abs(dx),Math.abs(dy))<20)return;
  if(Math.abs(dx)>Math.abs(dy)) setDir(dx>0?1:-1,0); else setDir(0,dy>0?1:-1);
  touchStart=null;
},{passive:true});
startBtn.addEventListener('click', start);
setInterval(()=>{particles.forEach(p=>{p.x+=p.vx;p.y+=p.vy;p.vy+=.06;p.life-=.035;});particles=particles.filter(p=>p.life>0);},33);
reset();
"""


def render(brief: dict) -> str:
    title = esc(brief.get("title", "霓虹贪吃蛇"))
    tagline = esc(brief.get("tagline", "在霓虹网格里收集能量，别撞上自己的轨迹。"))
    paragraph = esc(brief.get("paragraph", "一个足够小、足够快的浏览器街机，打开就能玩。"))
    body = (
        BODY.replace("{{TITLE}}", title)
        .replace("{{TAGLINE}}", tagline)
        .replace("{{PARAGRAPH}}", paragraph)
    )
    return document(title, STYLE, body, SCRIPT, brief.get("accent", "#b8ff5a"))
