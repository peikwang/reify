from __future__ import annotations

from .base import render_game_page

SCRIPT = r"""
const COLS = 10, ROWS = 20, CELL = 28;
canvas.width = COLS * CELL; canvas.height = ROWS * CELL;
const linesEl = document.getElementById('lines');
let board, piece, score, lines, level, best, running, paused, timer, dropMs;
const SHAPES = {
  I: [[1,1,1,1]],
  O: [[1,1],[1,1]],
  T: [[0,1,0],[1,1,1]],
  S: [[0,1,1],[1,1,0]],
  Z: [[1,1,0],[0,1,1]],
  J: [[1,0,0],[1,1,1]],
  L: [[0,0,1],[1,1,1]],
};
const COLORS = { I:'#5ee0ff', O:'#f5d76e', T:'#c792ea', S:'#7ee787', Z:'#ff7b72', J:'#79c0ff', L:'#ffa657' };
best = readBest('vibeforge-tetris-best');
bestEl.textContent = best;

function emptyBoard() { return Array.from({length: ROWS}, () => Array(COLS).fill(null)); }
function randomType() { const keys = Object.keys(SHAPES); return keys[Math.floor(Math.random() * keys.length)]; }
function makePiece(type) {
  return { type, matrix: SHAPES[type].map(row => [...row]), x: Math.floor((COLS - SHAPES[type][0].length) / 2), y: 0 };
}
function rotateMatrix(matrix) { return matrix[0].map((_, i) => matrix.map(row => row[i]).reverse()); }
function collides(matrix, px, py) {
  for (let y = 0; y < matrix.length; y++) {
    for (let x = 0; x < matrix[y].length; x++) {
      if (!matrix[y][x]) continue;
      const bx = px + x, by = py + y;
      if (bx < 0 || bx >= COLS || by >= ROWS) return true;
      if (by >= 0 && board[by][bx]) return true;
    }
  }
  return false;
}
function merge() {
  piece.matrix.forEach((row, y) => row.forEach((cell, x) => {
    if (cell) board[piece.y + y][piece.x + x] = piece.type;
  }));
}
function clearLines() {
  let cleared = 0;
  for (let y = ROWS - 1; y >= 0; y--) {
    if (board[y].every(Boolean)) {
      board.splice(y, 1);
      board.unshift(Array(COLS).fill(null));
      cleared++;
      y++;
    }
  }
  if (!cleared) return;
  const table = [0, 100, 300, 500, 800];
  lines += cleared;
  score += (table[Math.min(cleared, 4)]) * level;
  const nextLevel = 1 + Math.floor(lines / 10);
  if (nextLevel !== level) {
    level = nextLevel;
    dropMs = Math.max(120, 650 - (level - 1) * 55);
    restartTimer();
  }
  best = Math.max(best, score);
  saveBest('vibeforge-tetris-best', best);
  updateStats();
}
function updateStats() {
  scoreEl.textContent = score;
  linesEl.textContent = lines;
  bestEl.textContent = best;
}
function restartTimer() {
  clearInterval(timer);
  timer = setInterval(() => { if (running && !paused) step(); }, dropMs);
}
function start() {
  board = emptyBoard(); score = 0; lines = 0; level = 1; dropMs = 650;
  running = true; paused = false; piece = makePiece(randomType());
  hideOverlay(); setStatus('RUNNING'); updateStats(); restartTimer(); draw();
}
function step() {
  if (!running || paused) return;
  if (!collides(piece.matrix, piece.x, piece.y + 1)) {
    piece.y++;
  } else {
    merge(); clearLines();
    piece = makePiece(randomType());
    if (collides(piece.matrix, piece.x, piece.y)) { gameOver(); return; }
  }
  draw();
}
function move(dx) {
  if (!running || paused) return;
  if (!collides(piece.matrix, piece.x + dx, piece.y)) { piece.x += dx; draw(); }
}
function rotatePiece() {
  if (!running || paused) return;
  const rotated = rotateMatrix(piece.matrix);
  if (!collides(rotated, piece.x, piece.y)) { piece.matrix = rotated; draw(); }
}
function softDrop() {
  if (!running || paused) return;
  step();
}
function hardDrop() {
  if (!running || paused) return;
  while (!collides(piece.matrix, piece.x, piece.y + 1)) piece.y++;
  step();
}
function gameOver() {
  running = false; clearInterval(timer); setStatus('GAME OVER');
  best = Math.max(best, score); saveBest('vibeforge-tetris-best', best); bestEl.textContent = best;
  showOverlay('RUN COMPLETE', '本局得分 ' + score, '消掉 ' + lines + ' 行，最高分 ' + best + '。再来一局，拼出完整一行。', '再来一局');
  draw();
}
function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#050907'; ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = 'rgba(255,255,255,.045)'; ctx.lineWidth = 1;
  for (let i = 0; i <= COLS; i++) { ctx.beginPath(); ctx.moveTo(i * CELL, 0); ctx.lineTo(i * CELL, canvas.height); ctx.stroke(); }
  for (let j = 0; j <= ROWS; j++) { ctx.beginPath(); ctx.moveTo(0, j * CELL); ctx.lineTo(canvas.width, j * CELL); ctx.stroke(); }
  for (let y = 0; y < ROWS; y++) for (let x = 0; x < COLS; x++) if (board[y][x]) drawCell(x, y, COLORS[board[y][x]]);
  piece.matrix.forEach((row, y) => row.forEach((cell, x) => {
    if (cell) drawCell(piece.x + x, piece.y + y, COLORS[piece.type]);
  }));
}
function drawCell(x, y, color) {
  ctx.save();
  ctx.shadowColor = color; ctx.shadowBlur = 10;
  ctx.fillStyle = color;
  roundRectPath(x * CELL + 1.5, y * CELL + 1.5, CELL - 3, CELL - 3, 4);
  ctx.fill();
  ctx.restore();
}
document.addEventListener('keydown', e => {
  const k = e.key.toLowerCase();
  if (['arrowleft', 'a'].includes(k)) { e.preventDefault(); move(-1); }
  if (['arrowright', 'd'].includes(k)) { e.preventDefault(); move(1); }
  if (['arrowup', 'w'].includes(k)) { e.preventDefault(); rotatePiece(); }
  if (['arrowdown', 's'].includes(k)) { e.preventDefault(); softDrop(); }
  if (k === ' ') { e.preventDefault(); hardDrop(); }
  if (k === 'p') { if (!running) return; paused = !paused; setStatus(paused ? 'PAUSED' : 'RUNNING'); }
});
document.querySelectorAll('[data-action]').forEach(btn => btn.addEventListener('click', () => {
  const a = btn.dataset.action;
  if (a === 'left') move(-1);
  if (a === 'right') move(1);
  if (a === 'rotate') rotatePiece();
  if (a === 'down') softDrop();
  if (a === 'drop') hardDrop();
}));
startBtn.addEventListener('click', start);
board = emptyBoard(); score = 0; lines = 0; level = 1; dropMs = 650; piece = makePiece('T');
updateStats(); draw(); setStatus('READY');
"""


def render(brief: dict, prompt: str = "") -> str:
    controls = """
    <div class="keys"><span>←</span><span>↑</span><span>⎵</span><span>→</span><span>↓</span><span>P</span></div>
    <p style="margin-top:12px">←/→ 移动，↑ 旋转，↓ 加速，空格直接落下，P 暂停。</p>
    """
    touch = """
    <button type="button" data-action="left">←</button>
    <button type="button" data-action="rotate">↻</button>
    <button type="button" data-action="right">→</button>
    <button type="button" data-action="down">↓</button>
    <button type="button" data-action="drop">⤓</button>
    """
    return render_game_page(
        brief,
        genre="tetris",
        hud_meta="TETRIS 10 × 20",
        canvas_width=280,
        canvas_height=560,
        canvas_max_width=320,
        canvas_label="俄罗斯方块游戏画布",
        overlay_text="用 ←/→ 移动，↑ 旋转，↓ 加速，空格直接落下。",
        intro_span="拼出完整一行。",
        controls_html=controls,
        touch_html=touch,
        mission="消除整行得分，每 10 行升一级，速度会逐渐加快；最高分保存在当前浏览器。",
        tips=[
            ("01 · 移动", "左右移动方块，向上旋转，找到能填满整行的位置。"),
            ("02 · 节奏", "每消 10 行升一级，下落速度会加快。"),
            ("03 · 记录", "最高分写入 localStorage，刷新页面也不会丢失。"),
        ],
        stats=[("SCORE", "score", "0"), ("LINES", "lines", "0"), ("BEST", "best", "0")],
        script=SCRIPT,
    )
