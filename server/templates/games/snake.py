from __future__ import annotations

from .base import render_game_page

SCRIPT = r"""
let snake, dir, nextDir, food, score, best, running, paused, timer, tickMs, particles;
const speedEl = document.getElementById('speed');
best = readBest('vibeforge-snake-best');
bestEl.textContent = best;

function reset() {
  snake = [{x:12,y:12},{x:11,y:12},{x:10,y:12}];
  dir = {x:1,y:0}; nextDir = {x:1,y:0};
  score = 0; tickMs = 145; paused = false; particles = [];
  scoreEl.textContent = '0'; speedEl.textContent = '1.0x'; setStatus('READY');
  placeFood(); draw();
}
function placeFood() {
  do { food = {x: Math.floor(Math.random()*24), y: Math.floor(Math.random()*24)}; }
  while (snake.some(s => s.x === food.x && s.y === food.y));
}
function start() {
  reset(); running = true; hideOverlay(); setStatus('RUNNING');
  clearInterval(timer); timer = setInterval(tick, tickMs);
}
function tick() {
  if (!running || paused) return;
  dir = nextDir;
  const head = {x: snake[0].x + dir.x, y: snake[0].y + dir.y};
  if (head.x < 0 || head.y < 0 || head.x >= 24 || head.y >= 24 || snake.some(s => s.x === head.x && s.y === head.y)) return gameOver();
  snake.unshift(head);
  if (head.x === food.x && head.y === food.y) {
    score += 1; scoreEl.textContent = score; burst(head.x, head.y);
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
  for (let i=0;i<16;i++) particles.push({x:(gx+.5)*24,y:(gy+.5)*24,vx:(Math.random()-.5)*4,vy:(Math.random()-.5)*4,life:1});
}
function draw() {
  ctx.clearRect(0,0,canvas.width,canvas.height);
  const bg = ctx.createLinearGradient(0,0,canvas.width,canvas.height);
  bg.addColorStop(0,'#050a07'); bg.addColorStop(1,'#0a1410'); ctx.fillStyle = bg; ctx.fillRect(0,0,canvas.width,canvas.height);
  ctx.strokeStyle = 'rgba(255,255,255,.035)'; ctx.lineWidth = 1;
  for (let i=0;i<=24;i++){ctx.beginPath();ctx.moveTo(i*24,0);ctx.lineTo(i*24,canvas.height);ctx.stroke();ctx.beginPath();ctx.moveTo(0,i*24);ctx.lineTo(canvas.width,i*24);ctx.stroke();}
  const fx=(food.x+.5)*24, fy=(food.y+.5)*24;
  ctx.save(); ctx.shadowColor=accent; ctx.shadowBlur=28; ctx.fillStyle=accent;
  ctx.beginPath(); ctx.arc(fx,fy,24*.26,0,Math.PI*2); ctx.fill();
  ctx.globalAlpha=.22; ctx.beginPath(); ctx.arc(fx,fy,24*.55,0,Math.PI*2); ctx.fill(); ctx.restore();
  snake.forEach((seg,i)=>{
    const x=seg.x*24, y=seg.y*24;
    ctx.save(); ctx.shadowColor=accent; ctx.shadowBlur=i===0?22:8;
    ctx.fillStyle=i===0?accent:'rgba(184,255,90,'+Math.max(.22,.8-i*.028)+')';
    roundRectPath(x+2,y+2,20,20,i===0?7:5); ctx.fill(); ctx.restore();
    if(i===0){ctx.fillStyle='#07110a';ctx.beginPath();ctx.arc(x+24*.34,y+24*.38,2.1,0,Math.PI*2);ctx.arc(x+24*.66,y+24*.38,2.1,0,Math.PI*2);ctx.fill();}
  });
  particles.forEach(p=>{ctx.globalAlpha=Math.max(0,p.life);ctx.fillStyle=accent;ctx.fillRect(p.x,p.y,2,2);});
  ctx.globalAlpha=1;
}
function gameOver() {
  running = false; clearInterval(timer); setStatus('GAME OVER');
  best = Math.max(best, score); saveBest('vibeforge-snake-best', best); bestEl.textContent = best;
  showOverlay(score >= best && score > 0 ? 'NEW HIGH SCORE' : 'RUN COMPLETE', '本局得分 ' + score, '最高分 ' + best + '。再来一局，试试更长的轨迹。', '再来一局');
}
function setDir(x,y){ if (dir.x === -x && dir.y === -y) return; nextDir={x,y}; }
document.addEventListener('keydown', e=>{
  const k=e.key.toLowerCase();
  if(['arrowup','w'].includes(k)) return setDir(0,-1);
  if(['arrowdown','s'].includes(k)) return setDir(0,1);
  if(['arrowleft','a'].includes(k)) return setDir(-1,0);
  if(['arrowright','d'].includes(k)) return setDir(1,0);
  if(k==='p'){ if(!running)return; paused=!paused; setStatus(paused?'PAUSED':'RUNNING'); }
  if(k===' '){ e.preventDefault(); start(); }
});
document.querySelectorAll('[data-action]').forEach(btn=>btn.addEventListener('click',()=>{
  const d=btn.dataset.action;
  if(d==='up')setDir(0,-1); if(d==='down')setDir(0,1); if(d==='left')setDir(-1,0); if(d==='right')setDir(1,0);
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


def render(brief: dict, prompt: str = "") -> str:
    controls = """
    <div class="keys"><span>W</span><span>↑</span><span>P</span><span>A</span><span>S</span><span>D</span></div>
    <p style="margin-top:12px">方向键 / WASD 移动，P 暂停，空格重开。</p>
    """
    touch = """
    <button type="button" data-action="up">↑</button>
    <button type="button" data-action="left">←</button>
    <button type="button" data-action="down">↓</button>
    <button type="button" data-action="right">→</button>
    """
    return render_game_page(
        brief,
        genre="snake",
        hud_meta="GRID 24 × 24",
        canvas_width=576,
        canvas_height=576,
        canvas_max_width=440,
        canvas_label="霓虹贪吃蛇游戏画布",
        overlay_text="用方向键 / WASD 控制，吃掉能量点，别撞上墙和自己。",
        intro_span="再吃一颗。",
        controls_html=controls,
        touch_html=touch,
        mission="每吃 5 颗能量点，速度提升一级。最高分会保存在当前浏览器。",
        tips=[
            ("01 · 移动", "键盘与触控双操作，移动端自动显示方向键。"),
            ("02 · 节奏", "速度会随得分提升，留出下一格的判断时间。"),
            ("03 · 记录", "最高分写入 localStorage，刷新页面也不会丢失。"),
        ],
        stats=[("SCORE", "score", "0"), ("BEST", "best", "0"), ("SPEED", "speed", "1.0x")],
        script=SCRIPT,
    )
