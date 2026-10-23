from __future__ import annotations

from .base import document, esc, highlight_cards


STYLE = """
:root{--ink:#f4f0e8;--muted:#999487;--panel:#11120f;--line:rgba(244,240,232,.12)}
body{background:#0b0c0a;color:var(--ink);font-family:ui-sans-serif,-apple-system,"SF Pro Display","PingFang SC",sans-serif;overflow-x:hidden}
body::before{content:"";position:fixed;inset:0;z-index:0;pointer-events:none;background:
 radial-gradient(720px 520px at 80% -10%,color-mix(in srgb,var(--accent) 20%,transparent),transparent 65%),
 radial-gradient(620px 420px at 0% 30%,rgba(110,231,255,.09),transparent 60%)}
.grain{position:fixed;inset:0;z-index:0;pointer-events:none;opacity:.035;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}
.wrap{width:min(1180px,calc(100% - 40px));margin:0 auto;position:relative;z-index:1}
nav{display:flex;align-items:center;justify-content:space-between;padding:24px 0;border-bottom:1px solid var(--line)}
.logo{display:flex;align-items:center;gap:10px;font-weight:800;letter-spacing:-.02em}
.logo b{width:30px;height:30px;display:grid;place-items:center;border-radius:9px;background:var(--accent);color:#10120e;font-size:13px}
.links{display:flex;align-items:center;gap:28px;font-size:13px;color:var(--muted)}
.links a:hover{color:var(--ink)}
.nav-cta{border:1px solid var(--line);border-radius:999px;padding:10px 17px;color:var(--ink)!important;background:rgba(255,255,255,.03)}
.hero{padding:clamp(64px,10vw,130px) 0 54px;position:relative}
.eyebrow{display:flex;align-items:center;gap:10px;color:var(--muted);font:10px/1 ui-monospace,SFMono-Regular,monospace;letter-spacing:.22em;text-transform:uppercase;margin-bottom:26px}
.eyebrow i{width:26px;height:1px;background:var(--accent)}
h1{font-size:clamp(48px,9vw,118px);line-height:.88;letter-spacing:-.075em;margin:0;font-weight:800;max-width:11ch}
h1 em{font-style:normal;color:var(--accent)}
.hero-row{display:grid;grid-template-columns:1fr 360px;gap:40px;align-items:end;margin-top:34px}
.hero-copy{max-width:52ch;color:var(--muted);font-size:15px;line-height:1.8;margin:0}
.hero-actions{display:flex;align-items:center;gap:14px;margin-top:24px}
.primary{border:0;border-radius:999px;padding:14px 22px;background:var(--accent);color:#10120e;font-weight:800;box-shadow:0 0 40px color-mix(in srgb,var(--accent) 25%,transparent);transition:transform .2s}
.primary:hover{transform:translateY(-2px)}
.secondary{border:1px solid var(--line);background:transparent;color:var(--ink);border-radius:999px;padding:14px 22px}
.orb{aspect-ratio:1;border-radius:50%;position:relative;background:
 radial-gradient(circle at 34% 28%,rgba(255,255,255,.85),color-mix(in srgb,var(--accent) 85%,#000) 26%,#141610 60%,#090a08 100%);
 box-shadow:inset -22px -28px 60px rgba(0,0,0,.65),0 40px 100px color-mix(in srgb,var(--accent) 18%,transparent);animation:float 7s ease-in-out infinite}
.orb::before,.orb::after{content:"";position:absolute;inset:-14%;border:1px solid color-mix(in srgb,var(--accent) 35%,transparent);border-radius:50%;transform:rotateX(62deg)}
.orb::after{inset:-28%;border-color:rgba(255,255,255,.12);transform:rotateY(64deg)}
@keyframes float{50%{transform:translateY(-14px) rotate(2deg)}}
.marquee{border-top:1px solid var(--line);border-bottom:1px solid var(--line);overflow:hidden;padding:17px 0;margin-top:56px;color:var(--muted);font:11px/1 ui-monospace,monospace;letter-spacing:.18em;text-transform:uppercase}
.marquee div{display:flex;gap:40px;width:max-content;animation:slide 28s linear infinite}
.marquee span{white-space:nowrap}.marquee b{color:var(--accent)}
@keyframes slide{to{transform:translateX(-50%)}}
section{padding:88px 0}
.section-head{display:flex;align-items:end;justify-content:space-between;gap:24px;margin-bottom:36px}
.section-head h2{font-size:clamp(30px,4.4vw,56px);letter-spacing:-.055em;line-height:1;margin:0;max-width:12ch}
.section-head p{color:var(--muted);max-width:38ch;line-height:1.7;font-size:14px;margin:0}
.features{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.feature{border:1px solid var(--line);border-radius:20px;padding:22px;min-height:190px;background:linear-gradient(180deg,rgba(255,255,255,.035),rgba(255,255,255,.012));transition:transform .25s,border-color .25s;position:relative;overflow:hidden}
.feature:hover{transform:translateY(-5px);border-color:color-mix(in srgb,var(--accent) 45%,transparent)}
.feature .idx{font:10px/1 ui-monospace,monospace;color:var(--accent);letter-spacing:.18em}
.feature h3{font-size:18px;letter-spacing:-.02em;margin:54px 0 10px}
.feature p{font-size:12px;line-height:1.7;color:var(--muted);margin:0}
.process{border-top:1px solid var(--line)}
.step{display:grid;grid-template-columns:80px 1fr 1.2fr;gap:24px;padding:28px 0;border-bottom:1px solid var(--line);align-items:start}
.step .n{font:12px/1 ui-monospace,monospace;color:var(--accent)}
.step h3{margin:0;font-size:24px;letter-spacing:-.03em}
.step p{margin:0;color:var(--muted);line-height:1.75;font-size:14px}
.cta{border:1px solid var(--line);border-radius:28px;padding:clamp(30px,6vw,72px);background:
 radial-gradient(500px 300px at 80% 0%,color-mix(in srgb,var(--accent) 22%,transparent),transparent 70%),#10120e;display:flex;align-items:center;justify-content:space-between;gap:28px}
.cta h2{font-size:clamp(32px,5vw,64px);letter-spacing:-.06em;line-height:.95;margin:0;max-width:13ch}
footer{display:flex;align-items:center;justify-content:space-between;padding:30px 0 46px;border-top:1px solid var(--line);color:var(--muted);font-size:11px;letter-spacing:.08em}
.reveal{opacity:0;transform:translateY(24px);transition:opacity .7s,transform .7s}
.reveal.in{opacity:1;transform:none}
@media(max-width:900px){.hero-row{grid-template-columns:1fr}.orb{width:min(320px,70vw);justify-self:end}.features{grid-template-columns:repeat(2,1fr)}.links{display:none}.step{grid-template-columns:46px 1fr}.step p{grid-column:2}.cta{flex-direction:column;align-items:flex-start}}
@media(max-width:560px){.wrap{width:min(100% - 28px,1180px)}.features{grid-template-columns:1fr}.hero{padding-top:64px}.hero-actions{flex-wrap:wrap}.section-head{flex-direction:column;align-items:flex-start}footer{flex-direction:column;gap:12px;align-items:flex-start}}
"""

BODY = """
<div class="grain"></div>
<div class="wrap">
  <nav>
    <div class="logo"><b>V</b>{{TITLE}}</div>
    <div class="links"><a href="#features">能力</a><a href="#process">过程</a><a href="#contact">联系</a><a class="nav-cta" href="#contact">开始合作</a></div>
  </nav>
  <header class="hero">
    <div class="eyebrow"><i></i> INDEPENDENT DESIGN &amp; BUILD STUDIO</div>
    <h1>{{HEADLINE}}</h1>
    <div class="hero-row">
      <div>
        <p class="hero-copy">{{PARAGRAPH}}</p>
        <div class="hero-actions"><a class="primary" href="#contact">把想法变成作品</a><a class="secondary" href="#features">看看怎么做</a></div>
      </div>
      <div class="orb" aria-hidden="true"></div>
    </div>
    <div class="marquee"><div><span>STRATEGY</span><b>✦</b><span>IDENTITY</span><b>✦</b><span>WEB EXPERIENCE</span><b>✦</b><span>MOTION</span><b>✦</b><span>SHIP IT</span><b>✦</b><span>STRATEGY</span><b>✦</b><span>IDENTITY</span><b>✦</b><span>WEB EXPERIENCE</span><b>✦</b><span>MOTION</span><b>✦</b><span>SHIP IT</span><b>✦</b></div></div>
  </header>
  <section id="features">
    <div class="section-head reveal"><h2>不是模板，<br>是你的语气。</h2><p>{{TAGLINE}} 每一个区块都为真实内容服务，而不是为了填满画布。</p></div>
    <div class="features">{{FEATURES}}</div>
  </section>
  <section id="process" class="process">
    <div class="section-head reveal"><h2>从一句话<br>到可访问。</h2><p>Agent 把模糊的描述拆成可执行的动作，写代码、自检、部署，整个过程可回放。</p></div>
    <div class="step reveal"><div class="n">01</div><h3>听见方向</h3><p>先确定品牌语气、信息层级和第一屏要让人记住什么。不是先选模板。</p></div>
    <div class="step reveal"><div class="n">02</div><h3>长出骨架</h3><p>写出语义化结构，再用排版、留白和动效建立节奏。代码在编程模式里逐行出现。</p></div>
    <div class="step reveal"><div class="n">03</div><h3>验证再发布</h3><p>检查结构、响应式与交互，部署到本地 Agent Server，拿到一个真正能打开的地址。</p></div>
  </section>
  <section id="contact">
    <div class="cta reveal"><h2>让下一个想法，<br>今天就能打开。</h2><div><p style="color:var(--muted);line-height:1.7;max-width:34ch;margin:0 0 18px;font-size:14px">这是一张由 VibeForge 即时生成的品牌页。改一句描述，版式和语气就会重新长出来。</p><a class="primary" href="mailto:hello@vibeforge.local">hello@vibeforge.local</a></div></div>
  </section>
  <footer><span>{{TITLE}} · BUILT LOCALLY</span><span>VIBEFORGE / {{YEAR}}</span></footer>
</div>
"""

SCRIPT = r"""
const io = new IntersectionObserver(entries => {
  entries.forEach(entry => { if (entry.isIntersecting) entry.target.classList.add('in'); });
}, {threshold:.14});
document.querySelectorAll('.reveal').forEach(el => io.observe(el));
document.querySelectorAll('a[href^="#"]').forEach(a => a.addEventListener('click', e => {
  const target = document.querySelector(a.getAttribute('href'));
  if (target) { e.preventDefault(); target.scrollIntoView({behavior:'smooth'}); }
}));
"""


def render(brief: dict) -> str:
    title = esc(brief.get("title", "Lumen Studio"))
    tagline = esc(brief.get("tagline", "把每一个想法，变成可被看见的作品。"))
    paragraph = esc(brief.get("paragraph", "我们做品牌、网站和数字产品，也相信好的设计应该让复杂的事情看起来简单。"))
    highlights = [esc(item) for item in brief.get("highlights", ["品牌叙事", "视觉系统", "Web 体验", "动效设计"])]
    headline = f'让想法<br><em>{esc(tagline[:16])}</em>'
    body = (
        BODY.replace("{{TITLE}}", title)
        .replace("{{HEADLINE}}", headline)
        .replace("{{TAGLINE}}", tagline)
        .replace("{{PARAGRAPH}}", paragraph)
        .replace("{{FEATURES}}", highlight_cards(highlights))
        .replace("{{YEAR}}", "2026")
    )
    return document(title, STYLE, body, SCRIPT, brief.get("accent", "#ff7a59"))
