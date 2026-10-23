from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import REACT_DIST_MAX_BYTES
from .base import esc


def _js(value: Any) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def build_files(brief: dict[str, Any], prompt: str) -> dict[str, str]:
    title = str(brief.get("title") or "Lumen Studio")
    tagline = str(brief.get("tagline") or "把每一个想法，变成可被看见的作品。")
    paragraph = str(
        brief.get("paragraph")
        or "我们做品牌、网站和数字产品，也相信好的设计应该让复杂的事情看起来简单。"
    )
    highlights = [str(item) for item in (brief.get("highlights") or [])][:4]
    if len(highlights) < 4:
        highlights += ["品牌叙事", "视觉系统", "Web 体验", "动效设计"][: 4 - len(highlights)]
    accent = str(brief.get("accent") or "#1e5c40")

    package_json = json.dumps(
        {
            "name": "vibeforge-react-site",
            "private": True,
            "version": "1.0.0",
            "type": "module",
            "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
            "dependencies": {"react": "19.1.0", "react-dom": "19.1.0"},
            "devDependencies": {"@vitejs/plugin-react": "4.4.1", "vite": "6.3.5"},
        },
        ensure_ascii=False,
        indent=2,
    )

    vite_config = """import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "./",
  build: { outDir: "dist", emptyOutDir: true },
});
"""

    index_html = """<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>__TITLE__</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
""".replace("__TITLE__", esc(title))

    main_jsx = """import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
"""

    app_jsx = f"""import {{ useEffect, useState }} from "react";

const title = {_js(title)};
const tagline = {_js(tagline)};
const paragraph = {_js(paragraph)};
const highlights = {json.dumps(highlights, ensure_ascii=False)};
const prompt = {_js(prompt)};

const steps = [
  {{ label: "01", title: "听见方向", text: "先确定语气、信息层级和第一屏要让人记住什么。" }},
  {{ label: "02", title: "长出骨架", text: "用 React 组件把结构、排版和节奏拆成可维护的模块。" }},
  {{ label: "03", title: "验证再发布", text: "在沙箱内完成依赖安装与生产构建，再把静态产物发布上线。" }},
];

export default function App() {{
  const [open, setOpen] = useState(false);
  useEffect(() => {{
    document.documentElement.style.setProperty("--accent", {_js(accent)});
  }}, []);

  return (
    <div className="page">
      <header className="nav">
        <a className="brand" href="#top" aria-label="回到顶部">
          <span className="brand-mark">V</span>
          <span>{{title}}</span>
        </a>
        <button className="menu" type="button" onClick={{() => setOpen(!open)}} aria-label="打开菜单">
          {{open ? "关闭" : "菜单"}}
        </button>
        <nav className={{open ? "nav-links open" : "nav-links"}}>
          <a href="#work" onClick={{() => setOpen(false)}}>作品</a>
          <a href="#process" onClick={{() => setOpen(false)}}>过程</a>
          <a href="#contact" onClick={{() => setOpen(false)}}>联系</a>
        </nav>
      </header>

      <main id="top">
        <section className="hero">
          <div className="hero-copy">
            <p className="kicker">INDEPENDENT DESIGN &amp; BUILD STUDIO</p>
            <h1>{{tagline}}</h1>
            <p className="lede">{{paragraph}}</p>
            <div className="actions">
              <a className="button primary" href="#contact">开始一个项目</a>
              <a className="button ghost" href="#work">看看怎么做</a>
            </div>
          </div>
          <div className="hero-visual" aria-hidden="true">
            <div className="orb" />
            <div className="visual-card">
              <span>REACT / VITE</span>
              <strong>Built in a sandbox.</strong>
              <small>source → install → build → deploy</small>
            </div>
          </div>
        </section>

        <section className="marquee" aria-hidden="true">
          <div>STRATEGY · IDENTITY · WEB EXPERIENCE · MOTION · SHIP IT · STRATEGY · IDENTITY · WEB EXPERIENCE · MOTION · SHIP IT ·</div>
        </section>

        <section id="work" className="section">
          <div className="section-head">
            <p className="kicker">WHAT WE MAKE</p>
            <h2>不是模板，<br />是你的语气。</h2>
            <p>{{paragraph}}</p>
          </div>
          <div className="cards">
            {{highlights.map((item, index) => (
              <article className="card" key={{item}}>
                <span className="card-index">0{{index + 1}}</span>
                <h3>{{item}}</h3>
                <p>从内容出发，找到真正值得被看见的部分。</p>
              </article>
            ))}}
          </div>
        </section>

        <section id="process" className="section process">
          <div className="section-head">
            <p className="kicker">THE PROCESS</p>
            <h2>从一句话，<br />到可访问。</h2>
          </div>
          <div className="steps">
            {{steps.map((step) => (
              <article className="step" key={{step.label}}>
                <span>{{step.label}}</span>
                <h3>{{step.title}}</h3>
                <p>{{step.text}}</p>
              </article>
            ))}}
          </div>
        </section>

        <section id="contact" className="cta">
          <p className="kicker">START SOMETHING</p>
          <h2>让下一个想法，<br />今天就能打开。</h2>
          <p>{{title}} · 由 VibeForge 生成并构建</p>
          <a className="button primary" href="mailto:hello@vibeforge.local">说说你的想法</a>
        </section>
      </main>

      <footer>
        <span>{{title}}</span>
        <span>BUILT WITH REACT + VITE · SOURCE: {{prompt.slice(0, 42)}}</span>
      </footer>
    </div>
  );
}}
"""

    styles_css = f""":root {{
  --accent: {accent};
  --ink: #171915;
  --muted: #6f746b;
  --line: rgba(23, 25, 21, 0.13);
  --paper: #f7f5ef;
  --card: #fffdf8;
}}

* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif;
  -webkit-font-smoothing: antialiased;
}}
a {{ color: inherit; text-decoration: none; }}
button {{ font: inherit; }}
.page {{ overflow: hidden; }}

.nav {{
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 18px clamp(20px, 5vw, 72px);
  background: rgba(247, 245, 239, 0.82);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--line);
}}
.brand {{ display: flex; align-items: center; gap: 10px; font-weight: 700; letter-spacing: -0.03em; }}
.brand-mark {{
  width: 30px; height: 30px; border-radius: 9px;
  display: grid; place-items: center;
  background: var(--ink); color: #fff; font: 800 13px/1 ui-monospace, monospace;
}}
.nav-links {{ display: flex; gap: 26px; font-size: 13px; color: var(--muted); }}
.nav-links a:hover {{ color: var(--ink); }}
.menu {{ display: none; border: 1px solid var(--line); background: transparent; border-radius: 8px; padding: 7px 10px; }}

.hero {{
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(300px, 0.85fr);
  gap: clamp(30px, 6vw, 90px);
  padding: clamp(58px, 9vw, 130px) clamp(20px, 5vw, 72px) clamp(40px, 7vw, 90px);
  min-height: 72vh;
  align-items: center;
}}
.kicker {{ margin: 0 0 16px; font: 700 10px/1 ui-monospace, monospace; letter-spacing: 0.2em; color: var(--muted); }}
.hero h1 {{
  margin: 0;
  max-width: 12ch;
  font-family: ui-serif, Georgia, "Songti SC", "STSong", serif;
  font-size: clamp(48px, 7.5vw, 104px);
  line-height: 0.94;
  letter-spacing: -0.06em;
  font-weight: 500;
}}
.lede {{ max-width: 38ch; margin: 26px 0 0; color: var(--muted); font-size: 15px; line-height: 1.9; }}
.actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 34px; }}
.button {{
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 999px; padding: 13px 22px; font-size: 13px; font-weight: 700;
  border: 1px solid var(--ink); transition: transform 0.2s ease, background 0.2s ease;
}}
.button:hover {{ transform: translateY(-2px); }}
.button.primary {{ background: var(--ink); color: #fff; }}
.button.primary:hover {{ background: var(--accent); border-color: var(--accent); }}
.button.ghost {{ background: transparent; }}
.hero-visual {{ position: relative; min-height: 360px; display: grid; place-items: center; }}
.orb {{
  position: absolute; width: 78%; aspect-ratio: 1; border-radius: 50%;
  background: radial-gradient(circle at 32% 28%, var(--accent), transparent 62%);
  filter: blur(6px); opacity: 0.5; animation: breathe 7s ease-in-out infinite;
}}
.visual-card {{
  position: relative; z-index: 1; width: min(100%, 340px);
  border: 1px solid var(--line); border-radius: 22px; padding: 24px;
  background: rgba(255, 253, 248, 0.78); backdrop-filter: blur(14px);
  box-shadow: 0 30px 80px rgba(25, 31, 24, 0.12);
}}
.visual-card span, .visual-card small {{ display: block; font: 700 9px/1.6 ui-monospace, monospace; letter-spacing: 0.14em; color: var(--muted); }}
.visual-card strong {{ display: block; margin: 70px 0 10px; font-family: ui-serif, Georgia, serif; font-size: 28px; font-weight: 500; letter-spacing: -0.04em; }}
@keyframes breathe {{ 50% {{ transform: scale(1.08); opacity: 0.68; }} }}

.marquee {{ border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); padding: 14px 0; overflow: hidden; white-space: nowrap; }}
.marquee div {{ font: 700 10px/1 ui-monospace, monospace; letter-spacing: 0.2em; color: var(--muted); animation: slide 24s linear infinite; }}
@keyframes slide {{ to {{ transform: translateX(-50%); }} }}

.section {{ padding: clamp(60px, 9vw, 120px) clamp(20px, 5vw, 72px); }}
.section-head {{ display: grid; grid-template-columns: 0.7fr 1.2fr 0.9fr; gap: 28px; align-items: end; border-bottom: 1px solid var(--line); padding-bottom: 28px; }}
.section-head h2 {{ margin: 0; font-family: ui-serif, Georgia, "Songti SC", serif; font-size: clamp(36px, 5vw, 64px); line-height: 1; letter-spacing: -0.05em; font-weight: 500; }}
.section-head p:last-child {{ margin: 0; color: var(--muted); font-size: 14px; line-height: 1.8; }}
.cards {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 26px; }}
.card {{ background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 22px; min-height: 190px; }}
.card-index {{ font: 700 10px/1 ui-monospace, monospace; color: var(--muted); }}
.card h3 {{ margin: 48px 0 10px; font-size: 19px; letter-spacing: -0.02em; }}
.card p {{ margin: 0; color: var(--muted); font-size: 12px; line-height: 1.7; }}
.process .section-head {{ grid-template-columns: 0.7fr 1.3fr; }}
.steps {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 26px; }}
.step {{ border-top: 1px solid var(--line); padding-top: 18px; }}
.step span {{ font: 700 10px/1 ui-monospace, monospace; color: var(--accent); }}
.step h3 {{ margin: 22px 0 8px; font-size: 18px; }}
.step p {{ margin: 0; color: var(--muted); font-size: 12px; line-height: 1.8; }}

.cta {{
  margin: 0 clamp(20px, 5vw, 72px) clamp(40px, 6vw, 80px);
  padding: clamp(38px, 6vw, 80px);
  border-radius: 26px;
  background: var(--ink);
  color: #f7f5ef;
  text-align: center;
}}
.cta .kicker {{ color: rgba(247, 245, 239, 0.6); }}
.cta h2 {{ margin: 0 auto 16px; max-width: 16ch; font-family: ui-serif, Georgia, "Songti SC", serif; font-size: clamp(38px, 5vw, 68px); line-height: 1; letter-spacing: -0.05em; font-weight: 500; }}
.cta p {{ color: rgba(247, 245, 239, 0.62); font-size: 13px; }}
.cta .button {{ margin-top: 24px; background: #f7f5ef; color: var(--ink); border-color: #f7f5ef; }}
.cta .button:hover {{ background: var(--accent); border-color: var(--accent); }}

footer {{
  display: flex; justify-content: space-between; gap: 18px; flex-wrap: wrap;
  padding: 24px clamp(20px, 5vw, 72px);
  border-top: 1px solid var(--line);
  color: var(--muted);
  font: 700 9px/1.6 ui-monospace, monospace;
  letter-spacing: 0.12em;
}}

@media (max-width: 900px) {{
  .hero {{ grid-template-columns: 1fr; min-height: auto; }}
  .hero-visual {{ min-height: 280px; }}
  .section-head {{ grid-template-columns: 1fr; align-items: start; }}
  .cards {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .steps {{ grid-template-columns: 1fr; }}
}}
@media (max-width: 620px) {{
  .nav {{ padding: 14px 20px; }}
  .menu {{ display: inline-flex; }}
  .nav-links {{
    display: none; position: absolute; top: 100%; left: 0; right: 0;
    flex-direction: column; gap: 0; padding: 8px 20px 16px;
    background: var(--paper); border-bottom: 1px solid var(--line);
  }}
  .nav-links.open {{ display: flex; }}
  .nav-links a {{ padding: 12px 0; border-bottom: 1px solid var(--line); }}
  .cards {{ grid-template-columns: 1fr; }}
  .hero h1 {{ font-size: clamp(42px, 13vw, 64px); }}
}}
"""

    readme = f"""# {title}

由 VibeForge 生成的 Vite + React 源码工程。

## 本地开发

```bash
npm install
npm run dev
```

## 生产构建

```bash
npm run build
```

构建产物位于 `dist/`，由 VibeForge 的沙箱构建并发布到项目页面。

## 原始需求

{prompt}
"""

    return {
        "package.json": package_json,
        "package-lock.json": _lockfile(),
        "vite.config.js": vite_config,
        "index.html": index_html,
        "src/main.jsx": main_jsx,
        "src/App.jsx": app_jsx,
        "src/styles.css": styles_css,
        "README.md": readme,
    }


def _lockfile() -> str:
    path = Path(__file__).with_name("react_package-lock.json")
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _artifact_checks(files: dict[str, bytes]) -> list[tuple[str, bool, str]]:
    index_bytes = files.get("index.html", b"")
    index_text = index_bytes.decode("utf-8", errors="replace") if index_bytes else ""
    asset_paths = [name for name in files if name.startswith("assets/")]
    js_assets = [
        name for name in asset_paths if name.lower().endswith((".js", ".mjs"))
    ]
    total = sum(len(value) for value in files.values())
    return [
        ("构建产物", bool(index_bytes), "dist/index.html 已生成" if index_bytes else "缺少 dist/index.html"),
        ("React 入口", 'id="root"' in index_text, "root 挂载点存在" if 'id="root"' in index_text else "缺少 root 挂载点"),
        ("JS Bundle", bool(js_assets), f"{len(js_assets)} 个 JS 文件"),
        (
            "产物大小",
            total > 0 and total <= REACT_DIST_MAX_BYTES,
            f"{round(total / 1024)} KB / 上限 {round(REACT_DIST_MAX_BYTES / 1024 / 1024)} MB",
        ),
    ]


def react_checks_files(files: dict[str, bytes]) -> list[tuple[str, bool, str]]:
    return _artifact_checks(files)


def react_checks(dist: Path) -> list[tuple[str, bool, str]]:
    files: dict[str, bytes] = {}
    if dist.is_dir():
        for path in dist.rglob("*"):
            if path.is_file():
                files[path.relative_to(dist).as_posix()] = path.read_bytes()
    return _artifact_checks(files)
