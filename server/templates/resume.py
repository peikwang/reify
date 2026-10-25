from __future__ import annotations

from .base import document, esc


STYLE = """
:root{--paper:#f3efe6;--ink:#171713;--muted:#6d6a60;--line:rgba(23,23,19,.14);--soft:#e8e2d6}
body{background:#d8d2c5;color:var(--ink);font-family:ui-sans-serif,-apple-system,"SF Pro Text","PingFang SC",sans-serif;padding:34px 18px}
.page{width:min(1040px,100%);margin:0 auto;background:var(--paper);border-radius:4px;box-shadow:0 30px 90px rgba(30,28,22,.24);overflow:hidden;position:relative}
.page::before{content:"";position:absolute;inset:0;pointer-events:none;background-image:radial-gradient(rgba(23,23,19,.11) .6px,transparent .6px);background-size:4px 4px;opacity:.18}
.toolbar{position:fixed;right:24px;top:24px;z-index:5;display:flex;gap:8px}
.toolbar button{border:1px solid rgba(255,255,255,.2);background:#171713;color:#f3efe6;border-radius:999px;padding:10px 15px;font-size:12px;box-shadow:0 10px 30px rgba(0,0,0,.18)}
.toolbar button.ghost{background:rgba(243,239,230,.9);color:#171713;border-color:rgba(23,23,19,.15)}
.inner{padding:clamp(28px,5vw,58px) clamp(26px,5.6vw,68px) 48px}
.top{display:grid;grid-template-columns:1.4fr .6fr;gap:36px;align-items:start;padding-bottom:30px;border-bottom:2px solid var(--ink)}
.eyebrow{font:10px/1 ui-monospace,monospace;letter-spacing:.2em;color:var(--accent,#8a6f3d);text-transform:uppercase;margin-bottom:18px}
h1{font-family:ui-serif,Georgia,"Songti SC","STSong",serif;font-size:clamp(42px,7vw,76px);line-height:.92;letter-spacing:-.055em;margin:0 0 12px;font-weight:600}
.role{font-size:15px;color:var(--muted);letter-spacing:.04em}
.contact{display:grid;gap:9px;justify-items:end;font:11px/1.5 ui-monospace,monospace;color:var(--muted);padding-top:6px}
.contact b{color:var(--ink);font-weight:600}
.body{display:grid;grid-template-columns:1.55fr .75fr;gap:46px;padding-top:34px}
h2{font:10px/1 ui-monospace,monospace;letter-spacing:.2em;text-transform:uppercase;color:var(--accent,#8a6f3d);margin:0 0 16px}
.summary{font-family:ui-serif,Georgia,"Songti SC",serif;font-size:18px;line-height:1.75;margin:0 0 34px;max-width:52ch}
.job{padding:0 0 24px;margin-bottom:24px;border-bottom:1px solid var(--line)}
.job:last-child{border-bottom:0;margin-bottom:0}
.job-head{display:flex;justify-content:space-between;gap:18px;align-items:baseline;margin-bottom:8px}
.job h3{font-size:16px;letter-spacing:-.02em;margin:0}
.job .when{font:10px/1 ui-monospace,monospace;color:var(--muted);white-space:nowrap}
.job .company{font-size:12px;color:var(--muted);margin-bottom:10px}
.job ul{margin:0;padding-left:16px;color:#3c3a33;font-size:12.5px;line-height:1.75}
.job li{margin-bottom:5px}
.project{display:grid;grid-template-columns:1fr auto;gap:10px;padding:14px 0;border-top:1px solid var(--line)}
.project h3{font-size:14px;margin:0 0 4px}
.project p{font-size:12px;line-height:1.65;color:var(--muted);margin:0}
.project span{font:10px/1 ui-monospace,monospace;color:var(--accent,#8a6f3d)}
.skill{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid var(--line);font-size:12px}
.skill i{display:block;width:76px;height:3px;border-radius:9px;background:var(--soft);position:relative;overflow:hidden}
.skill i::after{content:"";position:absolute;inset:0;width:var(--w);background:var(--accent,#8a6f3d);border-radius:9px}
.side-block{margin-bottom:30px}
.side-block p{font-size:12px;line-height:1.7;color:var(--muted);margin:0}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chips span{border:1px solid var(--line);border-radius:999px;padding:6px 9px;font:10px/1 ui-monospace,monospace;color:#4e4b42}
.note{margin-top:34px;padding-top:14px;border-top:2px solid var(--ink);display:flex;justify-content:space-between;font:9px/1.5 ui-monospace,monospace;color:var(--muted);letter-spacing:.06em}
@media(max-width:760px){body{padding:0}.page{border-radius:0}.toolbar{top:14px;right:14px}.top{grid-template-columns:1fr}.contact{justify-items:start;grid-template-columns:1fr 1fr}.body{grid-template-columns:1fr;gap:30px}.note{flex-direction:column;gap:6px}}
@media print{body{background:#fff;padding:0}.page{box-shadow:none;width:100%;border-radius:0}.toolbar{display:none}.inner{padding:14mm 16mm}@page{size:A4;margin:0}}
"""

BODY = """
<div class="toolbar"><button onclick="window.print()">打印 / 导出 PDF</button><button class="ghost" onclick="navigator.clipboard.writeText(location.href).then(()=>this.textContent='链接已复制')">复制链接</button></div>
<main class="page">
  <div class="inner">
    <header class="top">
      <div><div class="eyebrow">Curriculum Vitae / {{YEAR}}</div><h1>{{NAME}}</h1><div class="role">{{ROLE}} · {{LOCATION}}</div></div>
      <div class="contact"><span><b>hello@{{SLUG}}.design</b></span><span>+86 138 0000 0000</span><span>{{SLUG}}.design</span><span>WeChat: {{SLUG}}</span></div>
    </header>
    <div class="body">
      <div>
        <section><h2>Profile</h2><p class="summary">{{PARAGRAPH}}</p></section>
        <section>
          <h2>Experience</h2>
          <article class="job"><div class="job-head"><h3>独立产品设计师</h3><span class="when">2022 — 至今</span></div><div class="company">Self-employed / Remote</div><ul><li>为早期团队完成从品牌叙事、信息架构到高保真界面的端到端设计，平均 6 周上线首个版本。</li><li>建立可复用的设计系统与前端组件映射，把设计交付到开发的往返次数降低约 40%。</li><li>与工程团队一起定义验收标准，用真实数据和可用性测试推动迭代。</li></ul></article>
          <article class="job"><div class="job-head"><h3>高级视觉设计师</h3><span class="when">2019 — 2022</span></div><div class="company">Northstar Lab / Shanghai</div><ul><li>负责核心产品的品牌升级与 Web 体验，主导 3 次大型改版。</li><li>用动效和排版建立产品节奏，官网转化率提升 28%。</li></ul></article>
          <article class="job"><div class="job-head"><h3>视觉设计师</h3><span class="when">2017 — 2019</span></div><div class="company">Studio Fold / Hangzhou</div><ul><li>参与品牌识别、包装与数字体验项目，服务消费与科技客户。</li></ul></article>
        </section>
        <section>
          <h2>Selected Projects</h2>
          <div class="project"><div><h3>Lumen — 创作者作品发布平台</h3><p>从 0 到 1 的品牌与产品设计，建立可扩展的作品展示结构。</p></div><span>2025</span></div>
          <div class="project"><div><h3>Field Notes — 旅行内容产品</h3><p>以路线为核心的内容体验，覆盖移动端与桌面端。</p></div><span>2024</span></div>
        </section>
      </div>
      <aside>
        <div class="side-block"><h2>Skills</h2>{{SKILLS}}</div>
        <div class="side-block"><h2>Tools</h2><div class="chips"><span>FIGMA</span><span>FRAMER</span><span>HTML/CSS</span><span>REACT</span><span>AFTER EFFECTS</span><span>BLENDER</span></div></div>
        <div class="side-block"><h2>Education</h2><p><b>中国美术学院</b><br>视觉传达设计 · 本科<br>2013 — 2017</p></div>
        <div class="side-block"><h2>Recognition</h2><p>Awwwards Honorable Mention<br>CSS Design Awards · UI Design<br>站酷推荐设计师</p></div>
        <div class="side-block"><h2>Languages</h2><p>中文 · 母语<br>English · 工作流利</p></div>
      </aside>
    </div>
    <div class="note"><span>Designed &amp; generated with Reify</span><span>ATS-FRIENDLY · PRINT READY · LAST UPDATED {{YEAR}}</span></div>
  </div>
</main>
"""

SCRIPT = r"""
document.querySelectorAll('.skill i').forEach(bar => {
  const width = bar.dataset.w || '78%';
  bar.style.setProperty('--w', '0%');
  setTimeout(() => { bar.style.transition = 'all 1s cubic-bezier(.2,.7,.2,1)'; bar.style.setProperty('--w', width); }, 250);
});
const io = new IntersectionObserver(entries => entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('in'); }), {threshold:.1});
document.querySelectorAll('.job,.project,.side-block').forEach(el => io.observe(el));
"""


def render(brief: dict) -> str:
    name = esc(brief.get("name", "林知夏"))
    role = esc(brief.get("role", "产品设计师 / 视觉设计"))
    title = f"{name} · 个人简历"
    paragraph = esc(brief.get("paragraph", "我是一名横跨品牌与数字产品的设计师，擅长把复杂的信息整理成清晰、有温度的体验。相信好的设计不是装饰，而是让人更快做出决定。"))
    slug = "linzhixia"
    skills = brief.get("highlights", ["品牌视觉", "产品设计", "设计系统", "前端实现"])
    widths = [92, 86, 78, 72, 84]
    skill_html = "".join(
        f'<div class="skill"><span>{esc(item)}</span><i data-w="{widths[i % len(widths)]}%"></i></div>'
        for i, item in enumerate(skills[:5])
    )
    body = (
        BODY.replace("{{NAME}}", name)
        .replace("{{ROLE}}", role)
        .replace("{{LOCATION}}", esc(brief.get("location", "上海")))
        .replace("{{PARAGRAPH}}", paragraph)
        .replace("{{SKILLS}}", skill_html)
        .replace("{{SLUG}}", slug)
        .replace("{{YEAR}}", "2026")
    )
    return document(title, STYLE, body, SCRIPT, brief.get("accent", "#8a6f3d"))
