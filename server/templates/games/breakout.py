from __future__ import annotations

from .base import render_game_page

SCRIPT = r"""
const livesEl = document.getElementById('lives');
const hudMeta = document.getElementById('hudMeta');
const keys = { left: false, right: false };
const COLS = 8, ROWS = 5, BRICK_W = 52, BRICK_H = 16, GAP = 4, OFFSET_X = 16, OFFSET_Y = 66;
const ROW_COLORS = ['#ff8a65', '#f5d76e', '#7ee787', '#5ee0ff', '#c792ea'];
let paddle, ball, bricks, score, lives, level, best, running, paused, raf, lastTime;
best = readBest('vibeforge-breakout-best');
bestEl.textContent = best;

function resetBall() {
  ball = { x: paddle.x + paddle.w / 2, y: paddle.y - 8, r: 6, vx: 2.2 + level * .15, vy: -3.2 - level * .12, stuck: true };
}
function resetLevel() {
  bricks = [];
  for (let row = 0; row < ROWS; row++) {
    for (let col = 0; col < COLS; col++) {
      bricks.push({
        x: OFFSET_X + col * (BRICK_W + GAP),
        y: OFFSET_Y + row * (BRICK_H + GAP),
        w: BRICK_W, h: BRICK_H, alive: true, color: ROW_COLORS[row % ROW_COLORS.length],
      });
    }
  }
  paddle = { x: canvas.width / 2 - 38, y: canvas.height - 28, w: 76, h: 10, speed: 6 };
  resetBall();
}
function resetGame() {
  score = 0; lives = 3; level = 1;
  resetLevel(); updateStats();
  hudMeta.textContent = 'BREAKOUT / LEVEL 1';
  draw();
}
function updateStats() {
  scoreEl.textContent = score;
  livesEl.textContent = lives;
  bestEl.textContent = best;
}
function start() {
  resetGame(); running = true; paused = false; hideOverlay(); setStatus('RUNNING');
  lastTime = performance.now(); cancelAnimationFrame(raf); raf = requestAnimationFrame(loop);
}
function launch() {
  if (!running || paused || !ball.stuck) return;
  ball.stuck = false;
  ball.vx = (Math.random() > .5 ? 1 : -1) * (2.2 + level * .15);
  ball.vy = -3.2 - level * .12;
}
function loop(now) {
  if (!running) return;
  if (paused) { lastTime = now; raf = requestAnimationFrame(loop); return; }
  const dt = Math.min(2.2, (now - lastTime) / 16.67);
  lastTime = now;
  update(dt); draw();
  raf = requestAnimationFrame(loop);
}
function hitsBrick(brick) {
  return ball.x + ball.r > brick.x && ball.x - ball.r < brick.x + brick.w &&
    ball.y + ball.r > brick.y && ball.y - ball.r < brick.y + brick.h;
}
function update(dt) {
  if (keys.left) paddle.x -= paddle.speed * dt;
  if (keys.right) paddle.x += paddle.speed * dt;
  paddle.x = clamp(paddle.x, 0, canvas.width - paddle.w);
  if (ball.stuck) {
    ball.x = paddle.x + paddle.w / 2;
    ball.y = paddle.y - ball.r - 2;
    return;
  }
  ball.x += ball.vx * dt;
  ball.y += ball.vy * dt;
  if (ball.x - ball.r < 0) { ball.x = ball.r; ball.vx = Math.abs(ball.vx); }
  if (ball.x + ball.r > canvas.width) { ball.x = canvas.width - ball.r; ball.vx = -Math.abs(ball.vx); }
  if (ball.y - ball.r < 0) { ball.y = ball.r; ball.vy = Math.abs(ball.vy); }
  if (ball.vy > 0 && ball.y + ball.r >= paddle.y && ball.y - ball.r <= paddle.y + paddle.h &&
      ball.x >= paddle.x - ball.r && ball.x <= paddle.x + paddle.w + ball.r) {
    const offset = (ball.x - (paddle.x + paddle.w / 2)) / (paddle.w / 2);
    ball.y = paddle.y - ball.r;
    ball.vx = clamp(offset * 4.2, -4.2, 4.2);
    ball.vy = -Math.abs(ball.vy);
  }
  for (const brick of bricks) {
    if (brick.alive && hitsBrick(brick)) {
      brick.alive = false;
      ball.vy = -ball.vy;
      score += 10;
      if (score > best) { best = score; saveBest('vibeforge-breakout-best', best); }
      updateStats();
      break;
    }
  }
  if (ball.y - ball.r > canvas.height) {
    lives -= 1; updateStats();
    if (lives <= 0) { gameOver(); return; }
    resetBall(); setStatus('READY'); return;
  }
  if (bricks.every(brick => !brick.alive)) {
    level += 1;
    resetLevel();
    hudMeta.textContent = 'BREAKOUT / LEVEL ' + level;
    setStatus('LEVEL ' + level);
  }
}
function gameOver() {
  running = false; cancelAnimationFrame(raf); setStatus('GAME OVER');
  best = Math.max(best, score); saveBest('vibeforge-breakout-best', best); bestEl.textContent = best;
  showOverlay('RUN COMPLETE', '本局得分 ' + score, '到达第 ' + level + ' 关，最高分 ' + best + '。再来一局，清空所有砖块。', '再来一局');
  draw();
}
function draw() {
  const bg = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
  bg.addColorStop(0, '#071421'); bg.addColorStop(1, '#050907');
  ctx.fillStyle = bg; ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = 'rgba(255,255,255,.035)'; ctx.lineWidth = 1;
  for (let i = 0; i < canvas.width; i += 32) { ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, canvas.height); ctx.stroke(); }
  bricks.forEach(brick => {
    if (!brick.alive) return;
    ctx.save(); ctx.shadowColor = brick.color; ctx.shadowBlur = 10; ctx.fillStyle = brick.color;
    roundRectPath(brick.x, brick.y, brick.w, brick.h, 5); ctx.fill(); ctx.restore();
  });
  ctx.save(); ctx.shadowColor = accent; ctx.shadowBlur = 16; ctx.fillStyle = accent;
  roundRectPath(paddle.x, paddle.y, paddle.w, paddle.h, 6); ctx.fill();
  ctx.fillStyle = '#f7f5ef'; ctx.beginPath(); ctx.arc(ball.x, ball.y, ball.r, 0, Math.PI * 2); ctx.fill(); ctx.restore();
}
document.addEventListener('keydown', e => {
  const k = e.key.toLowerCase();
  if (['arrowleft', 'a'].includes(k)) { e.preventDefault(); keys.left = true; }
  if (['arrowright', 'd'].includes(k)) { e.preventDefault(); keys.right = true; }
  if (k === ' ') { e.preventDefault(); launch(); }
  if (k === 'p') { if (!running) return; paused = !paused; setStatus(paused ? 'PAUSED' : 'RUNNING'); }
});
document.addEventListener('keyup', e => {
  const k = e.key.toLowerCase();
  if (['arrowleft', 'a'].includes(k)) keys.left = false;
  if (['arrowright', 'd'].includes(k)) keys.right = false;
});
canvas.addEventListener('pointermove', e => {
  const rect = canvas.getBoundingClientRect();
  const x = (e.clientX - rect.left) / rect.width * canvas.width;
  paddle.x = clamp(x - paddle.w / 2, 0, canvas.width - paddle.w);
});
canvas.addEventListener('pointerdown', e => {
  const rect = canvas.getBoundingClientRect();
  const x = (e.clientX - rect.left) / rect.width * canvas.width;
  paddle.x = clamp(x - paddle.w / 2, 0, canvas.width - paddle.w);
  launch();
});
document.querySelectorAll('[data-action]').forEach(btn => btn.addEventListener('click', () => {
  const a = btn.dataset.action;
  if (a === 'left') paddle.x = clamp(paddle.x - 24, 0, canvas.width - paddle.w);
  if (a === 'right') paddle.x = clamp(paddle.x + 24, 0, canvas.width - paddle.w);
  if (a === 'launch') launch();
}));
startBtn.addEventListener('click', start);
resetGame(); setStatus('READY');
"""


def render(brief: dict, prompt: str = "") -> str:
    controls = """
    <div class="keys"><span>←</span><span>⎵</span><span>↔</span><span>→</span><span>P</span><span>◉</span></div>
    <p style="margin-top:12px">←/→ 或鼠标移动挡板，空格/点击发射，P 暂停。</p>
    """
    touch = """
    <button type="button" data-action="left">←</button>
    <button type="button" data-action="right">→</button>
    <button type="button" data-action="launch">发射</button>
    """
    return render_game_page(
        brief,
        genre="breakout",
        hud_meta="BREAKOUT / LEVEL 1",
        canvas_width=480,
        canvas_height=360,
        canvas_max_width=480,
        canvas_label="打砖块游戏画布",
        overlay_text="用 ←/→ 或鼠标移动挡板，空格或点击发射。",
        intro_span="清空所有砖块。",
        controls_html=controls,
        touch_html=touch,
        mission="接住弹球、清空砖块得分；每清一关速度提升，最高分保存在当前浏览器。",
        tips=[
            ("01 · 接球", "挡板接住弹球，角度会随落点变化。"),
            ("02 · 清屏", "清空所有砖块进入下一关，弹球速度会提升。"),
            ("03 · 记录", "最高分写入 localStorage，刷新页面也不会丢失。"),
        ],
        stats=[("SCORE", "score", "0"), ("LIVES", "lives", "3"), ("BEST", "best", "0")],
        script=SCRIPT,
    )
