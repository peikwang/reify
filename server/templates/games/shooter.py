from __future__ import annotations

from .base import render_game_page

SCRIPT = r"""
const livesEl = document.getElementById('lives');
const hudMeta = document.getElementById('hudMeta');
const keys = { left: false, right: false };
let player, bullets, enemies, stars, score, lives, best, running, paused, frameTimer, spawnTimer, lastShot;
best = readBest('reify-shooter-best');
bestEl.textContent = best;

function reset() {
  player = { x: canvas.width / 2 - 14, y: canvas.height - 54, w: 28, h: 24, speed: 5, invulnerable: 0 };
  bullets = []; enemies = [];
  stars = Array.from({ length: 54 }, () => ({ x: Math.random() * canvas.width, y: Math.random() * canvas.height, v: .6 + Math.random() * 1.5 }));
  score = 0; lives = 3; lastShot = 0;
  updateStats(); hudMeta.textContent = 'SHOOTER / WAVE 1'; draw();
}
function start() {
  reset(); running = true; paused = false; hideOverlay(); setStatus('RUNNING');
  clearInterval(frameTimer); clearInterval(spawnTimer);
  frameTimer = setInterval(tick, 30);
  spawnTimer = setInterval(spawn, 720);
  draw();
}
function spawn() {
  if (!running || paused) return;
  const w = 24 + Math.random() * 16;
  enemies.push({ x: Math.random() * (canvas.width - w), y: -30, w, h: 20, speed: 1.15 + score / 2600 });
}
function fire() {
  if (!running || paused) return;
  const now = Date.now();
  if (now - lastShot < 150) return;
  lastShot = now;
  bullets.push({ x: player.x + player.w / 2 - 2, y: player.y - 14, w: 4, h: 13, speed: 8 });
}
function updateStats() {
  scoreEl.textContent = score;
  livesEl.textContent = lives;
  bestEl.textContent = best;
}
function overlap(a, b) {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}
function loseLife() {
  if (Date.now() < player.invulnerable) return;
  lives -= 1;
  player.invulnerable = Date.now() + 900;
  updateStats();
  if (lives <= 0) gameOver(); else setStatus('HIT · ' + lives + ' LIVES');
}
function tick() {
  if (!running || paused) return;
  if (keys.left) player.x -= player.speed;
  if (keys.right) player.x += player.speed;
  player.x = clamp(player.x, 0, canvas.width - player.w);
  bullets.forEach(b => b.y -= b.speed);
  enemies.forEach(e => e.y += e.speed);
  stars.forEach(s => { s.y += s.v; if (s.y > canvas.height) { s.y = 0; s.x = Math.random() * canvas.width; } });
  bullets = bullets.filter(b => b.y > -20);
  for (let i = enemies.length - 1; i >= 0; i--) {
    const enemy = enemies[i];
    let hit = false;
    for (let j = bullets.length - 1; j >= 0; j--) {
      if (overlap(bullets[j], enemy)) { bullets.splice(j, 1); hit = true; break; }
    }
    if (hit) {
      enemies.splice(i, 1);
      score += 100;
      hudMeta.textContent = 'SHOOTER / WAVE ' + (1 + Math.floor(score / 1000));
      if (score > best) { best = score; bestEl.textContent = best; }
      continue;
    }
    if (enemy.y > canvas.height) { enemies.splice(i, 1); loseLife(); continue; }
    if (overlap(enemy, player)) { enemies.splice(i, 1); loseLife(); }
  }
  draw();
}
function gameOver() {
  running = false; clearInterval(frameTimer); clearInterval(spawnTimer); setStatus('GAME OVER');
  best = Math.max(best, score); saveBest('reify-shooter-best', best); bestEl.textContent = best;
  showOverlay('RUN COMPLETE', '本局得分 ' + score, '击落 ' + Math.floor(score / 100) + ' 架敌机，最高分 ' + best + '。再来一局，穿过弹幕。', '再来一局');
  draw();
}
function draw() {
  const bg = ctx.createLinearGradient(0, 0, 0, canvas.height);
  bg.addColorStop(0, '#071421'); bg.addColorStop(1, '#050907');
  ctx.fillStyle = bg; ctx.fillRect(0, 0, canvas.width, canvas.height);
  stars.forEach(s => { ctx.globalAlpha = .2 + s.v * .28; ctx.fillStyle = '#dff6ff'; ctx.fillRect(s.x, s.y, 2, 2); });
  ctx.globalAlpha = 1;
  bullets.forEach(b => {
    ctx.save(); ctx.shadowColor = accent; ctx.shadowBlur = 14; ctx.fillStyle = accent;
    ctx.fillRect(b.x, b.y, b.w, b.h); ctx.restore();
  });
  enemies.forEach(e => {
    ctx.save(); ctx.shadowColor = '#ff8a65'; ctx.shadowBlur = 12; ctx.fillStyle = '#ff8a65';
    ctx.beginPath(); ctx.moveTo(e.x + e.w / 2, e.y + e.h); ctx.lineTo(e.x, e.y); ctx.lineTo(e.x + e.w, e.y); ctx.closePath(); ctx.fill();
    ctx.fillStyle = '#511f16'; ctx.fillRect(e.x + e.w * .28, e.y + e.h * .35, e.w * .44, 4); ctx.restore();
  });
  const blink = Date.now() < player.invulnerable && Math.floor(Date.now() / 90) % 2 === 0;
  if (!blink) {
    ctx.save(); ctx.shadowColor = accent; ctx.shadowBlur = 18; ctx.fillStyle = accent;
    ctx.beginPath(); ctx.moveTo(player.x + player.w / 2, player.y); ctx.lineTo(player.x, player.y + player.h); ctx.lineTo(player.x + player.w, player.y + player.h); ctx.closePath(); ctx.fill();
    ctx.fillStyle = '#07110a'; ctx.fillRect(player.x + player.w / 2 - 3, player.y + 8, 6, 8); ctx.restore();
  }
}
document.addEventListener('keydown', e => {
  const k = e.key.toLowerCase();
  if (['arrowleft', 'a'].includes(k)) { e.preventDefault(); keys.left = true; }
  if (['arrowright', 'd'].includes(k)) { e.preventDefault(); keys.right = true; }
  if (k === ' ') { e.preventDefault(); fire(); }
  if (k === 'p') { if (!running) return; paused = !paused; setStatus(paused ? 'PAUSED' : 'RUNNING'); }
});
document.addEventListener('keyup', e => {
  const k = e.key.toLowerCase();
  if (['arrowleft', 'a'].includes(k)) keys.left = false;
  if (['arrowright', 'd'].includes(k)) keys.right = false;
});
document.querySelectorAll('[data-action]').forEach(btn => btn.addEventListener('click', () => {
  const a = btn.dataset.action;
  if (a === 'left') player.x = clamp(player.x - 22, 0, canvas.width - player.w);
  if (a === 'right') player.x = clamp(player.x + 22, 0, canvas.width - player.w);
  if (a === 'fire') fire();
}));
startBtn.addEventListener('click', start);
reset(); setStatus('READY');
"""


def render(brief: dict, prompt: str = "") -> str:
    controls = """
    <div class="keys"><span>A</span><span>←</span><span>⎵</span><span>D</span><span>→</span><span>P</span></div>
    <p style="margin-top:12px">A/D 或 ←/→ 移动，空格开火，P 暂停。</p>
    """
    touch = """
    <button type="button" data-action="left">←</button>
    <button type="button" data-action="right">→</button>
    <button type="button" data-action="fire">开火</button>
    """
    return render_game_page(
        brief,
        genre="shooter",
        hud_meta="SHOOTER / WAVE 1",
        canvas_width=420,
        canvas_height=560,
        canvas_max_width=420,
        canvas_label="飞机大战射击游戏画布",
        overlay_text="用 A/D 或 ←/→ 移动，空格开火，别让敌机穿过防线。",
        intro_span="穿过弹幕。",
        controls_html=controls,
        touch_html=touch,
        mission="击落敌机得分，敌机速度和数量会随分数提升；最高分保存在当前浏览器。",
        tips=[
            ("01 · 移动", "左右移动躲开敌机，保持在画面下方。"),
            ("02 · 节奏", "连续开火，优先清理靠近底部的敌机。"),
            ("03 · 记录", "最高分写入 localStorage，刷新页面也不会丢失。"),
        ],
        stats=[("SCORE", "score", "0"), ("LIVES", "lives", "3"), ("BEST", "best", "0")],
        script=SCRIPT,
    )
