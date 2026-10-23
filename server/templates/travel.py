from __future__ import annotations

from .base import document, esc


STYLE = """
:root{--sand:#efe7d6;--ink:#1c2a24;--muted:#6c7468;--line:rgba(28,42,36,.15);--deep:#13251d}
body{background:var(--sand);color:var(--ink);font-family:ui-sans-serif,-apple-system,"SF Pro Display","PingFang SC",sans-serif}
.hero{min-height:78vh;position:relative;overflow:hidden;background:linear-gradient(180deg,#b8d6d0 0%,#d9e0cf 46%,#efe7d6 100%);display:flex;flex-direction:column}
.hero::after{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(19,37,29,.05) 1px,transparent 1px);background-size:100% 44px;pointer-events:none}
.wrap{width:min(1160px,calc(100% - 40px));margin:0 auto;position:relative;z-index:3}
nav{display:flex;justify-content:space-between;align-items:center;padding:24px 0;font-size:12px;letter-spacing:.12em;text-transform:uppercase}
nav .mark{font-weight:800;letter-spacing:-.02em}
nav .mark i{color:#c65d3b}
.scene{position:absolute;inset:0;overflow:hidden;pointer-events:none}
.sun{position:absolute;width:220px;height:220px;border-radius:50%;right:14%;top:14%;background:radial-gradient(circle at 40% 35%,#fff8dd,#f3c672 48%,#e79b68 72%);box-shadow:0 0 90px rgba(243,198,114,.55)}
.mountain{position:absolute;bottom:0;left:-10%;width:120%;height:52%;background:linear-gradient(180deg,#507a67,#244a3b);clip-path:polygon(0 74%,12% 48%,23% 63%,37% 22%,50% 58%,62% 36%,74% 62%,86% 44%,100% 70%,100% 100%,0 100%)}
.mountain.back{bottom:14%;height:42%;background:linear-gradient(180deg,#7da393,#426d5a);opacity:.62;clip-path:polygon(0 82%,16% 40%,30% 66%,46% 28%,61% 66%,74% 42%,88% 70%,100% 52%,100% 100%,0 100%)}
.mist{position:absolute;bottom:8%;left:0;width:100%;height:22%;background:linear-gradient(180deg,transparent,rgba(239,231,214,.85))}
.hero-copy{position:relative;z-index:2;margin-top:auto;padding:72px 0 54px;max-width:740px}
.kicker{display:inline-flex;align-items:center;gap:9px;border:1px solid rgba(19,37,29,.25);border-radius:999px;padding:8px 13px;font:10px/1 ui-monospace,monospace;letter-spacing:.18em;text-transform:uppercase;background:rgba(255,255,255,.18);backdrop-filter:blur(8px)}
.kicker i{width:6px;height:6px;border-radius:50%;background:#c65d3b}
h1{font-family:ui-serif,Georgia,"Songti SC","STSong",serif;font-size:clamp(48px,9vw,108px);line-height:.88;letter-spacing:-.06em;margin:22px 0 18px;font-weight:500}
h1 em{font-style:normal;color:#c65d3b}
.lede{max-width:48ch;font-size:15px;line-height:1.8;color:#44554c;margin:0}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:26px}
.meta span{border:1px solid rgba(19,37,29,.22);border-radius:999px;padding:8px 12px;font:10px/1 ui-monospace,monospace;letter-spacing:.08em;background:rgba(255,255,255,.16)}
.section{padding:72px 0}
.section-head{display:flex;justify-content:space-between;align-items:end;gap:24px;margin-bottom:26px}
.section-head h2{font-family:ui-serif,Georgia,"Songti SC",serif;font-size:clamp(30px,4.4vw,52px);letter-spacing:-.04em;margin:0;font-weight:500}
.section-head p{max-width:34ch;font-size:13px;line-height:1.7;color:var(--muted);margin:0}
.tabs{display:flex;gap:6px;border-bottom:1px solid var(--line);margin-bottom:22px;overflow-x:auto}
.tab{border:0;background:transparent;padding:12px 16px;font:11px/1 ui-monospace,monospace;letter-spacing:.12em;color:var(--muted);border-bottom:2px solid transparent;white-space:nowrap}
.tab.active{color:var(--ink);border-color:#c65d3b}
.day{display:none;grid-template-columns:repeat(4,1fr);gap:10px}
.day.active{display:grid;animation:fadeUp .45s ease both}
@keyframes fadeUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.stop{border:1px solid var(--line);border-radius:16px;padding:18px;background:rgba(255,255,255,.26);min-height:180px;display:flex;flex-direction:column;justify-content:space-between;transition:transform .2s,background .2s}
.stop:hover{transform:translateY(-4px);background:rgba(255,255,255,.48)}
.stop time{font:10px/1 ui-monospace,monospace;color:#c65d3b;letter-spacing:.12em}
.stop h3{font-family:ui-serif,Georgia,"Songti SC",serif;font-size:20px;letter-spacing:-.02em;margin:14px 0 8px;font-weight:500}
.stop p{font-size:12px;line-height:1.7;color:var(--muted);margin:0}
.stop .tag{font:9px/1 ui-monospace,monospace;letter-spacing:.1em;color:var(--muted);border-top:1px solid var(--line);padding-top:10px;margin-top:14px}
.grid{display:grid;grid-template-columns:1.1fr .9fr;gap:14px}
.card{border:1px solid var(--line);border-radius:20px;padding:24px;background:rgba(255,255,255,.28)}
.card h3{font-family:ui-serif,Georgia,"Songti SC",serif;font-size:24px;margin:0 0 14px;font-weight:500}
.budget{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.budget div{border-top:1px solid var(--line);padding-top:12px}
.budget small{display:block;font:9px/1 ui-monospace,monospace;color:var(--muted);letter-spacing:.1em;margin-bottom:7px}
.budget b{font:600 18px/1 ui-monospace,monospace;color:#c65d3b}
.tips{display:grid;gap:10px}
.tip{display:flex;gap:12px;align-items:start;font-size:12.5px;line-height:1.65;color:#4c5a50}
.tip i{width:18px;height:18px;border-radius:50%;background:#c65d3b;color:#fff;display:grid;place-items:center;font:9px/1 ui-monospace,monospace;flex:none;margin-top:2px}
footer{border-top:1px solid var(--line);padding:28px 0 44px;display:flex;justify-content:space-between;font:10px/1.5 ui-monospace,monospace;color:var(--muted);letter-spacing:.1em}
.reveal{opacity:0;transform:translateY(20px);transition:.7s}
.reveal.in{opacity:1;transform:none}
@media(max-width:900px){.day{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}.sun{width:160px;height:160px;right:8%}}
@media(max-width:560px){.day{grid-template-columns:1fr}.hero-copy{padding:92px 0 40px}.section{padding:52px 0}.budget{grid-template-columns:1fr 1fr}footer{flex-direction:column;gap:8px}.wrap{width:calc(100% - 28px)}}
"""

BODY = """
<header class="hero">
  <div class="scene"><div class="sun"></div><div class="mountain back"></div><div class="mountain"></div><div class="mist"></div></div>
  <div class="wrap"><nav><div class="mark">FIELD NOTES <i>/</i> {{DESTINATION}}</div><div>VIBEFORGE TRAVEL</div></nav></div>
  <div class="wrap hero-copy">
    <div class="kicker"><i></i> {{DAYS}} DAYS · {{SEASON}} · SLOW TRAVEL</div>
    <h1>{{TITLE_LINE}}</h1>
    <p class="lede">{{PARAGRAPH}}</p>
    <div class="meta"><span>◷ {{DAYS}} 天 {{NIGHTS}} 晚</span><span>◎ 人均 ¥{{BUDGET}}</span><span>⌖ {{DESTINATION}}及周边</span><span>✎ {{TAGLINE}}</span></div>
  </div>
</header>
<main class="wrap">
  <section class="section">
    <div class="section-head reveal"><h2>每天只做<br>三件事。</h2><p>不追赶景点，把时间留给路上的风、市场里的声音和一顿慢慢吃完的饭。</p></div>
    <div class="tabs">{{TABS}}</div>
    {{DAYS_HTML}}
  </section>
  <section class="section">
    <div class="section-head reveal"><h2>路线之外。</h2><p>预算、交通与那些容易被忽略的小事，提前知道会轻松很多。</p></div>
    <div class="grid">
      <div class="card reveal"><h3>预算参考 / 人均</h3><div class="budget"><div><small>住宿</small><b>¥{{HOTEL}}</b></div><div><small>餐饮</small><b>¥{{FOOD}}</b></div><div><small>交通</small><b>¥{{TRANSPORT}}</b></div><div><small>门票</small><b>¥{{TICKET}}</b></div><div><small>咖啡 &amp; 杂项</small><b>¥{{MISC}}</b></div><div><small>合计</small><b>¥{{BUDGET}}</b></div></div></div>
      <div class="card reveal"><h3>出发前</h3><div class="tips"><div class="tip"><i>1</i><span>把行程留出 30% 的空白，遇到喜欢的小店就停下来。</span></div><div class="tip"><i>2</i><span>山区昼夜温差大，带一件轻薄外套和舒服的鞋。</span></div><div class="tip"><i>3</i><span>热门餐馆错峰去，下午两点半往往比晚上更好吃。</span></div><div class="tip"><i>4</i><span>提前看好日落时间，把最好的光线留给湖面或山顶。</span></div></div></div>
    </div>
  </section>
  <footer><span>FIELD NOTES / {{DESTINATION}} / {{YEAR}}</span><span>GENERATED BY VIBEFORGE · PRINT IT, TAKE IT WITH YOU</span></footer>
</main>
"""

SCRIPT = r"""
document.querySelectorAll('.tab').forEach(tab => tab.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.day').forEach(d => d.classList.remove('active'));
  tab.classList.add('active');
  const day = document.getElementById(tab.dataset.day);
  if (day) day.classList.add('active');
}));
const io = new IntersectionObserver(entries => entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('in'); }), {threshold:.12});
document.querySelectorAll('.reveal').forEach(el => io.observe(el));
"""

DAY_PLACES = [
    [("09:00", "从一碗本地早餐开始", "找一家门口停着最多电动车的小店，点招牌，不要看点评。", "早餐 / 老城"),
     ("11:30", "老城慢行", "不设目的地地走两条街，留意窗框、招牌和晾在阳光里的衣服。", "步行 / 拍照"),
     ("15:00", "湖边咖啡与发呆", "挑一个能看见水面的位置，把下午浪费掉。", "咖啡 / 日落前"),
     ("19:30", "夜市边吃边走", "每样只买一份，两个人分着吃，才有肚子走到最后。", "晚餐 / 夜市")],
    [("08:30", "去山里的路上", "早一点出发，避开旅行团，让山路只属于你。", "自驾 / 包车"),
     ("11:00", "半山腰的村子", "在村口买一杯茶，和晒太阳的人聊两句。", "村落 / 徒步"),
     ("14:30", "溪边午后", "带一块野餐布，听水声，什么都不做。", "自然 / 野餐"),
     ("18:30", "回城吃一顿热的", "点当地最普通的家常菜，通常比网红店更接近这座城。", "晚餐 / 本地菜")],
    [("09:30", "市场里的颜色", "菜市场是最快认识一座城市的地方，早点去。", "市场 / 人文"),
     ("12:00", "一顿长长的午饭", "选一家可以坐很久的院子，饭后喝壶茶。", "午餐 / 院子"),
     ("16:00", "高处看城", "找一个不高的观景点，等风把云吹开。", "观景 / 日落"),
     ("20:00", "回酒店前散步", "绕远一点，看看这座城市晚上真正的生活。", "夜游 / 散步")],
    [("09:00", "把喜欢的地方再去一次", "旅行最后一天，不要赶新景点，回去看看昨天舍不得的地方。", "自由 / 二刷"),
     ("12:30", "买一点带得走的", "本地食材、手作或一张明信片，比景区纪念品更值得。", "伴手礼 / 市场"),
     ("15:30", "留白时间", "回酒店收行李，或者找一家书店坐到出发前。", "休息 / 书店"),
     ("18:00", "去车站 / 机场", "提前一点出发，给路上留出余地。", "返程 / 交通")],
    [("09:30", "周边小镇", "坐一趟慢车去附近的小镇，路程本身就是风景。", "周边 / 慢车"),
     ("12:30", "小镇午饭", "在菜市场旁边找一家只做几道菜的店。", "午餐 / 本地"),
     ("16:00", "河边散步", "沿着水走，直到太阳落下去。", "散步 / 日落"),
     ("19:30", "回到城市", "最后一晚，去第一天去过的那家店。", "晚餐 / 告别")],
]


def render(brief: dict) -> str:
    destination = brief.get("destination", "大理")
    days = int(brief.get("days", 3))
    days = max(2, min(days, 5))
    title = esc(brief.get("title", f"{destination} · 风花雪月 {days} 日"))
    tagline = esc(brief.get("tagline", "把时间浪费在风经过的地方。"))
    paragraph = esc(brief.get("paragraph", "不赶路，不打卡。以一座城为原点，每天只安排三件真正想做的事，把剩下的时间留给偶遇。"))
    title_line = f"{esc(destination)}<br><em>{days} 天，慢慢走。</em>"
    tabs = "".join(
        f'<button class="tab{" active" if i == 0 else ""}" data-day="day{i+1}">DAY 0{i+1}</button>'
        for i in range(days)
    )
    days_html = ""
    for i in range(days):
        items = DAY_PLACES[i % len(DAY_PLACES)]
        stops = "".join(
            f'<article class="stop"><div><time>{time}</time><h3>{place}</h3><p>{desc}</p></div><div class="tag">{tag}</div></article>'
            for time, place, desc, tag in items
        )
        days_html += f'<div class="day{" active" if i == 0 else ""}" id="day{i+1}">{stops}</div>'
    budget = 680 + days * 320
    body = (
        BODY.replace("{{DESTINATION}}", esc(destination))
        .replace("{{DAYS}}", str(days))
        .replace("{{NIGHTS}}", str(days - 1))
        .replace("{{TITLE_LINE}}", title_line)
        .replace("{{TAGLINE}}", tagline)
        .replace("{{PARAGRAPH}}", paragraph)
        .replace("{{TABS}}", tabs)
        .replace("{{DAYS_HTML}}", days_html)
        .replace("{{SEASON}}", "春末")
        .replace("{{BUDGET}}", str(budget))
        .replace("{{HOTEL}}", str(days * 180))
        .replace("{{FOOD}}", str(days * 120))
        .replace("{{TRANSPORT}}", str(days * 55))
        .replace("{{TICKET}}", "120")
        .replace("{{MISC}}", "80")
        .replace("{{YEAR}}", "2026")
    )
    return document(title, STYLE, body, SCRIPT, brief.get("accent", "#c65d3b"))
