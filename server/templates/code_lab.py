from __future__ import annotations

from .base import document, esc


STYLE = """
:root{--bg:#080b0d;--panel:#0f1417;--ink:#e7f0ef;--muted:#859592;--line:rgba(231,240,239,.11);--cyan:#72e6d1}
body{background:var(--bg);color:var(--ink);font-family:ui-sans-serif,-apple-system,"SF Pro Display","PingFang SC",sans-serif;overflow-x:hidden}
body::before{content:"";position:fixed;inset:0;pointer-events:none;background:radial-gradient(700px 400px at 80% 0%,rgba(114,230,209,.09),transparent 65%),linear-gradient(rgba(255,255,255,.022) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.022) 1px,transparent 1px);background-size:auto,40px 40px,40px 40px;mask-image:radial-gradient(circle at 50% 30%,#000,transparent 82%)}
.shell{width:min(1180px,calc(100% - 36px));margin:0 auto;padding:22px 0 42px;position:relative;z-index:1}
nav{display:flex;justify-content:space-between;align-items:center;padding:8px 0 18px;border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:10px;font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.brand i{width:8px;height:8px;border-radius:50%;background:var(--accent);box-shadow:0 0 14px var(--accent)}
nav .right{font:9px/1 ui-monospace,monospace;color:var(--muted);letter-spacing:.16em}
.hero{padding:40px 0 28px;display:flex;justify-content:space-between;align-items:end;gap:24px}
.kicker{font:9px/1 ui-monospace,monospace;letter-spacing:.2em;color:var(--accent);text-transform:uppercase;margin-bottom:12px}
h1{font-size:clamp(34px,5vw,64px);line-height:.94;letter-spacing:-.06em;margin:0;font-weight:800}
h1 em{font-style:normal;color:var(--accent)}
.hero p{max-width:34ch;color:var(--muted);font-size:12px;line-height:1.7;margin:0}
.workspace{display:grid;grid-template-columns:1.05fr .95fr;gap:12px}
.panel{border:1px solid var(--line);border-radius:18px;background:rgba(15,20,23,.86);overflow:hidden;backdrop-filter:blur(12px)}
.panel-head{display:flex;align-items:center;justify-content:space-between;padding:12px 15px;border-bottom:1px solid var(--line);font:9px/1 ui-monospace,monospace;letter-spacing:.12em;color:var(--muted)}
.dots{display:flex;gap:5px}.dots i{width:7px;height:7px;border-radius:50%;background:#2b3436}.dots i:first-child{background:#ff6b5e}.dots i:nth-child(2){background:#ffca64}.dots i:nth-child(3){background:#67d98b}
pre{margin:0;padding:18px;font:11px/1.75 ui-monospace,SFMono-Regular,Menlo,monospace;color:#c8d5d2;overflow:auto;max-height:430px}
.kw{color:#ff8da1}.fn{color:#8bd8ff}.str{color:#d7f7a5}.num{color:#ffcc80}.com{color:#5b6d6a}
.visual{padding:16px;display:flex;flex-direction:column;justify-content:space-between;min-height:470px}
.viz-head{display:flex;justify-content:space-between;align-items:center;font:9px/1 ui-monospace,monospace;color:var(--muted);letter-spacing:.1em}
.bars{height:290px;display:flex;align-items:flex-end;gap:4px;padding:26px 6px 0;border-bottom:1px solid var(--line)}
.bar{flex:1;background:linear-gradient(180deg,var(--accent),rgba(114,230,209,.18));border-radius:3px 3px 0 0;position:relative;transition:height .12s,background .12s;min-height:3px}
.bar.active{background:#ffcf6b;box-shadow:0 0 18px rgba(255,207,107,.5)}
.bar.done{background:#7a9f98}
.bar span{position:absolute;bottom:-18px;left:50%;transform:translateX(-50%);font:7px/1 ui-monospace,monospace;color:var(--muted)}
.controls{display:flex;align-items:center;gap:8px;margin-top:24px}
.btn{border:1px solid var(--line);background:rgba(255,255,255,.03);color:var(--ink);border-radius:999px;padding:9px 13px;font:10px/1 ui-monospace,monospace;letter-spacing:.04em;transition:background .2s}
.btn:hover{background:rgba(255,255,255,.08)}
.btn.primary{background:var(--accent);color:#07110c;border-color:var(--accent);font-weight:700}
.legend{display:flex;gap:12px;margin-left:auto;font:8px/1 ui-monospace,monospace;color:var(--muted)}
.legend span{display:flex;align-items:center;gap:5px}.legend i{width:6px;height:6px;border-radius:2px;background:var(--accent)}
.legend span:nth-child(2) i{background:#ffcf6b}.legend span:nth-child(3) i{background:#7a9f98}
.insights{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:12px}
.insight{border:1px solid var(--line);border-radius:16px;padding:16px;background:rgba(15,20,23,.6)}
.insight small{display:block;font:8px/1 ui-monospace,monospace;letter-spacing:.14em;color:var(--muted);margin-bottom:10px}
.insight b{font-size:14px;letter-spacing:-.02em}.insight p{font-size:10px;line-height:1.6;color:var(--muted);margin:6px 0 0}
.status{margin-top:12px;border-top:1px solid var(--line);padding-top:11px;font:9px/1.6 ui-monospace,monospace;color:var(--muted)}
.status b{color:var(--accent)}
@media(max-width:860px){.workspace{grid-template-columns:1fr}.hero{flex-direction:column;align-items:start}.insights{grid-template-columns:1fr}}
@media(max-width:560px){.shell{width:calc(100% - 24px)}pre{font-size:9px}.bars{height:220px}}
"""

BODY = """
<div class="shell">
  <nav><div class="brand"><i></i> Reify / Code Lab</div><div class="right">TOOLACT RUNTIME · LOCAL</div></nav>
  <section class="hero"><div><div class="kicker">ALGORITHM / INTERACTIVE EXPLAINER</div><h1>{{HEADLINE}}</h1></div><p>{{TAGLINE}} {{PARAGRAPH}}</p></section>
  <section class="workspace">
    <div class="panel"><div class="panel-head"><div class="dots"><i></i><i></i><i></i></div><span>main.py</span><span>PYTHON 3.12</span></div><pre><code><span class="kw">def</span> <span class="fn">quick_sort</span>(items):
    <span class="com"># 递归基线：空数组或单元素已经有序</span>
    <span class="kw">if</span> len(items) &lt;= <span class="num">1</span>:
        <span class="kw">return</span> items
    pivot = items[len(items) // <span class="num">2</span>]
    left = [x <span class="kw">for</span> x <span class="kw">in</span> items <span class="kw">if</span> x &lt; pivot]
    mid = [x <span class="kw">for</span> x <span class="kw">in</span> items <span class="kw">if</span> x == pivot]
    right = [x <span class="kw">for</span> x <span class="kw">in</span> items <span class="kw">if</span> x &gt; pivot]
    <span class="kw">return</span> quick_sort(left) + mid + quick_sort(right)

<span class="kw">if</span> __name__ == <span class="str">"__main__"</span>:
    data = [<span class="num">8</span>, <span class="num">3</span>, <span class="num">5</span>, <span class="num">1</span>, <span class="num">9</span>, <span class="num">2</span>, <span class="num">7</span>, <span class="num">4</span>, <span class="num">6</span>]
    <span class="fn">print</span>(quick_sort(data))
    <span class="com"># [1, 2, 3, 4, 5, 6, 7, 8, 9]</span></code></pre></div>
    <div class="panel"><div class="panel-head"><span>LIVE VISUALIZER</span><span id="algoState">READY</span></div><div class="visual"><div class="viz-head"><span>QUICK SORT · 9 ELEMENTS</span><span id="stepCount">STEP 0</span></div><div class="bars" id="bars"></div><div class="controls"><button class="btn primary" id="runBtn">运行排序</button><button class="btn" id="shuffleBtn">重新打乱</button><div class="legend"><span><i></i>待排序</span><span><i></i>pivot</span><span><i></i>已完成</span></div></div><div class="status" id="status">数组已就绪。点击运行，观察每一次分区。</div></div></div>
  </section>
  <section class="insights"><div class="insight"><small>TIME</small><b>O(n log n)</b><p>平均情况；最坏 O(n²)，取决于 pivot 选择。</p></div><div class="insight"><small>SPACE</small><b>O(log n)</b><p>递归栈空间；原地版本可做到 O(log n)。</p></div><div class="insight"><small>IDEA</small><b>分而治之</b><p>选一个基准，把小的放左边，大的放右边，再递归。</p></div></section>
</div>
"""

SCRIPT = r"""
let values = [8,3,5,1,9,2,7,4,6];
const bars = document.getElementById('bars');
const statusEl = document.getElementById('status');
const stepEl = document.getElementById('stepCount');
const stateEl = document.getElementById('algoState');
let steps = [], running = false;
function render(active = [], done = []) {
  bars.innerHTML = values.map((v,i) => '<div class="bar '+(active.includes(i)?'active':'')+' '+(done.includes(i)?'done':'')+'" style="height:'+(v/9*100)+'%"><span>'+v+'</span></div>').join('');
}
function recordQuick(arr, lo, hi, snapshots, depth = 0) {
  if (lo >= hi) return;
  const pivot = arr[hi]; let i = lo;
  snapshots.push({arr:[...arr], pivot:hi, note:'选择 pivot = '+pivot});
  for (let j=lo;j<hi;j++) {
    if (arr[j] < pivot) { [arr[i],arr[j]]=[arr[j],arr[i]]; i++; snapshots.push({arr:[...arr], pivot:hi, note:'交换 '+arr[j]+' 与 '+arr[i-1]}); }
  }
  [arr[i],arr[hi]]=[arr[hi],arr[i]];
  snapshots.push({arr:[...arr], pivot:i, note:'pivot 归位到索引 '+i});
  recordQuick(arr, lo, i-1, snapshots, depth+1);
  recordQuick(arr, i+1, hi, snapshots, depth+1);
}
async function run() {
  if (running) return; running = true; stateEl.textContent = 'RUNNING';
  const arr = [...values], snapshots = [];
  recordQuick(arr, 0, arr.length-1, snapshots);
  for (let s=0;s<snapshots.length;s++) {
    const snap = snapshots[s]; values = snap.arr; render([snap.pivot], []);
    stepEl.textContent = 'STEP ' + (s+1); statusEl.textContent = snap.note;
    await new Promise(r => setTimeout(r, 150));
  }
  values = [...arr].sort((a,b)=>a-b); render([], values.map((_,i)=>i));
  stateEl.textContent = 'DONE'; statusEl.textContent = '排序完成：[1, 2, 3, 4, 5, 6, 7, 8, 9]'; running = false;
}
document.getElementById('runBtn').addEventListener('click', run);
document.getElementById('shuffleBtn').addEventListener('click', () => {
  if (running) return;
  values = [8,3,5,1,9,2,7,4,6].sort(() => Math.random()-.5);
  render(); stepEl.textContent = 'STEP 0'; statusEl.textContent = '已重新打乱。点击运行开始。'; stateEl.textContent = 'READY';
});
render();
"""


def render(brief: dict) -> str:
    title = esc(brief.get("title", "快速排序实验室"))
    tagline = esc(brief.get("tagline", "看见每一次分区，理解算法如何把混乱变成秩序。"))
    paragraph = esc(brief.get("paragraph", "一个可以运行的算法可视化页面：左边是代码，右边是每一步的状态。"))
    headline = f'{esc(brief.get("headline", "把混乱，"))}<br><em>变成秩序。</em>'
    body = (
        BODY.replace("{{HEADLINE}}", headline)
        .replace("{{TAGLINE}}", tagline)
        .replace("{{PARAGRAPH}}", paragraph)
    )
    return document(title, STYLE, body, SCRIPT, brief.get("accent", "#72e6d1"))
