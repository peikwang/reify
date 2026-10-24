from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import NEXT_ARTIFACT_MAX_BYTES
from .base import esc
from .react_app import build_files as react_build_files


def _js(value: Any) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def build_files(brief: dict[str, Any], prompt: str, project_id: str) -> dict[str, str]:
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
    base_path = f"/apps/{project_id}"

    package_json = json.dumps(
        {
            "name": "vibeforge-next-site",
            "private": True,
            "version": "1.0.0",
            "scripts": {
                "dev": "next dev",
                "typecheck": "tsc --noEmit",
                "build": "next build",
                "start": "next start",
            },
            "dependencies": {
                "next": "15.5.28",
                "react": "19.1.0",
                "react-dom": "19.1.0",
            },
            "devDependencies": {
                "@types/node": "22.15.3",
                "@types/react": "19.1.2",
                "@types/react-dom": "19.1.2",
                "typescript": "~5.8.3",
            },
        },
        ensure_ascii=False,
        indent=2,
    )

    tsconfig = json.dumps(
        {
            "compilerOptions": {
                "target": "ES2022",
                "lib": ["dom", "dom.iterable", "esnext"],
                "allowJs": False,
                "skipLibCheck": True,
                "strict": True,
                "noEmit": True,
                "esModuleInterop": True,
                "module": "esnext",
                "moduleResolution": "bundler",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "jsx": "preserve",
                "incremental": True,
                "plugins": [{"name": "next"}],
                "paths": {"@/*": ["./*"]},
            },
            "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
            "exclude": ["node_modules"],
        },
        ensure_ascii=False,
        indent=2,
    )

    next_env = """/// <reference types="next" />
/// <reference types="next/image-types/global" />

// NOTE: This file should not be edited
// see https://nextjs.org/docs/app/api-reference/config/typescript for more information.
"""

    next_config = f"""const nextConfig = {{
  output: "standalone",
  images: {{ unoptimized: true }},
  basePath: {_js(base_path)},
}};

export default nextConfig;
"""

    layout = f"""import type {{ ReactNode }} from "react";
import "./globals.css";

export const metadata = {{
  title: {_js(title)},
  description: {_js(tagline)},
}};

export default function RootLayout({{ children }}: {{ children: ReactNode }}) {{
  return (
    <html lang="zh-CN">
      <body>{{children}}</body>
    </html>
  );
}}
"""

    page = f"""import NoteBoard from "./NoteBoard";

const title = {_js(title)};
const tagline = {_js(tagline)};
const paragraph = {_js(paragraph)};
const highlights = {json.dumps(highlights, ensure_ascii=False)};

const steps = [
  {{ label: "01", title: "听见方向", text: "先确定语气、信息层级和第一屏要让人记住什么。" }},
  {{ label: "02", title: "服务端渲染", text: "用 Next.js App Router 把内容在服务端组装，再交给浏览器。" }},
  {{ label: "03", title: "运行与验证", text: "在独立沙箱中启动 standalone 服务，健康检查通过后开放预览。" }},
];

export default function Home() {{
  return (
    <div className="page">
      <header className="nav">
        <a className="brand" href="#top" aria-label="回到顶部">
          <span className="brand-mark">V</span>
          <span>{{title}}</span>
        </a>
        <nav className="nav-links">
          <a href="#work">作品</a>
          <a href="#process">过程</a>
          <a href="#board">留言</a>
        </nav>
      </header>

      <main id="top">
        <section className="hero">
          <div className="hero-copy">
            <p className="kicker">NEXT.JS / SERVER RENDERED STUDIO</p>
            <h1>{{tagline}}</h1>
            <p className="lede">{{paragraph}}</p>
            <div className="actions">
              <a className="button primary" href="#board">留下一个想法</a>
              <a className="button ghost" href="#work">看看怎么做</a>
            </div>
          </div>
          <div className="hero-visual" aria-hidden="true">
            <div className="orb" />
            <div className="visual-card">
              <span>NEXT / STANDALONE</span>
              <strong>Rendered on the server.</strong>
              <small>source → build → run → verify</small>
            </div>
          </div>
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
            <h2>从一句话，<br />到可运行。</h2>
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

        <section id="board" className="section">
          <div className="section-head">
            <p className="kicker">SERVER ROUTE / LIVE</p>
            <h2>一个真的<br />服务端接口。</h2>
            <p>下面的留言通过 App Router 的 Route Handler 写入当前运行时进程。</p>
          </div>
          <NoteBoard />
        </section>

        <section className="cta">
          <p className="kicker">START SOMETHING</p>
          <h2>让下一个想法，<br />今天就能打开。</h2>
          <p>{{title}} · 由 VibeForge 生成并在沙箱中运行</p>
          <a className="button primary" href="#board">说说你的想法</a>
        </section>
      </main>

      <footer>
        <span>{{title}}</span>
        <span>BUILT WITH NEXT.JS · SERVER RENDERED</span>
      </footer>
    </div>
  );
}}
"""

    note_board = f""""use client";

import {{ useEffect, useState, type FormEvent }} from "react";

const basePath = {_js(base_path)};

type Note = {{ id: number; text: string; at: string }};

export default function NoteBoard() {{
  const [notes, setNotes] = useState<Note[]>([]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");

  async function load(): Promise<void> {{
    try {{
      const response = await fetch(`${{basePath}}/api/notes`, {{ cache: "no-store" }});
      const data = (await response.json()) as {{ notes?: Note[] }};
      setNotes(data.notes ?? []);
    }} catch (_) {{
      setError("暂时读不到留言");
    }}
  }}

  useEffect(() => {{
    void load();
  }}, []);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {{
    event.preventDefault();
    const value = text.trim();
    if (!value) return;
    setError("");
    try {{
      const response = await fetch(`${{basePath}}/api/notes`, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ text: value }}),
      }});
      const data = (await response.json()) as {{ notes?: Note[] }};
      setNotes(data.notes ?? []);
      setText("");
    }} catch (_) {{
      setError("提交失败，请重试");
    }}
  }}

  return (
    <div className="board">
      <form className="board-form" onSubmit={{submit}}>
        <input
          value={{text}}
          onChange={{(event) => setText(event.target.value)}}
          maxLength={{120}}
          placeholder="写一句想留在服务端的话…"
          aria-label="留言"
        />
        <button className="button primary" type="submit">发送</button>
      </form>
      {{error ? <p className="board-error">{{error}}</p> : null}}
      <div className="notes">
        {{notes.map((note) => (
          <article className="note" key={{note.id}}>
            <p>{{note.text}}</p>
            <span>{{new Date(note.at).toLocaleTimeString("zh-CN")}} · SERVER MEMORY</span>
          </article>
        ))}}
      </div>
    </div>
  );
}}
"""

    api_route = """import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

export const dynamic = "force-dynamic";

interface Note {
  id: number;
  text: string;
  at: string;
}

const DATA_DIR = process.env.DATA_DIR || "/data";
const NOTES_FILE = path.join(DATA_DIR, "notes.json");
let cache: Note[] | null = null;

async function loadNotes(): Promise<Note[]> {
  if (cache) return cache;
  await mkdir(DATA_DIR, { recursive: true });
  try {
    const parsed: unknown = JSON.parse(await readFile(NOTES_FILE, "utf8"));
    cache = Array.isArray(parsed) ? (parsed as Note[]) : [];
  } catch (_) {
    cache = [{ id: 1, text: "这条留言保存在服务端数据卷中。", at: new Date().toISOString() }];
    await saveNotes(cache);
  }
  return cache;
}

async function saveNotes(notes: Note[]): Promise<void> {
  cache = notes;
  await mkdir(DATA_DIR, { recursive: true });
  await writeFile(NOTES_FILE, JSON.stringify(notes), "utf8");
}

export async function GET(): Promise<Response> {
  return Response.json({ notes: await loadNotes() });
}

export async function POST(request: Request): Promise<Response> {
  let body: { text?: unknown };
  try {
    body = (await request.json()) as { text?: unknown };
  } catch (_) {
    return Response.json({ error: "invalid json" }, { status: 400 });
  }
  const text = String(body?.text || "").trim().slice(0, 120);
  if (!text) {
    return Response.json({ error: "text is required" }, { status: 400 });
  }
  const notes = await loadNotes();
  const nextId = notes.reduce((max, note) => Math.max(max, Number(note.id) || 0), 0) + 1;
  const updated: Note[] = [...notes, { id: nextId, text, at: new Date().toISOString() }].slice(-20);
  await saveNotes(updated);
  return Response.json({ notes: updated });
}
"""

    styles = react_build_files(brief, prompt)["src/styles.css"]
    styles += """
.board { margin-top: 26px; display: grid; gap: 14px; }
.board-form { display: flex; gap: 10px; }
.board-form input {
  flex: 1; min-width: 0; border: 1px solid var(--line); border-radius: 12px;
  background: var(--card); padding: 13px 15px; color: var(--ink); outline: none;
}
.board-form input:focus { border-color: var(--accent); box-shadow: 0 0 0 4px rgba(30, 92, 64, 0.07); }
.board-error { color: #b4463f; font-size: 12px; margin: 0; }
.notes { display: grid; gap: 8px; }
.note { border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; background: var(--card); }
.note p { margin: 0 0 8px; font-size: 14px; }
.note span { color: var(--muted); font: 700 9px/1.4 ui-monospace, monospace; letter-spacing: 0.08em; }
@media (max-width: 620px) { .board-form { flex-direction: column; } }
"""

    readme = f"""# {title}

由 VibeForge 生成的 Next.js App Router + TypeScript 全栈项目。

- 服务端渲染页面
- `/api/notes` Route Handler，数据保存在当前运行时进程内
- standalone 构建，在 OpenSandbox 中启动
- `next build` 会执行 TypeScript 类型检查

## 本地开发

```bash
npm install
npm run dev
```

## 生产构建

```bash
npm run typecheck
npm run build
```

## 原始需求

{prompt}
"""

    return {
        "package.json": package_json,
        "package-lock.json": _lockfile(),
        "next.config.mjs": next_config,
        "tsconfig.json": tsconfig,
        "next-env.d.ts": next_env,
        "app/layout.tsx": layout,
        "app/page.tsx": page,
        "app/NoteBoard.tsx": note_board,
        "app/api/notes/route.ts": api_route,
        "app/globals.css": styles,
        "README.md": readme,
    }


def _lockfile() -> str:
    path = Path(__file__).with_name("next_package-lock.json")
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def next_checks_files(files: dict[str, bytes]) -> list[tuple[str, bool, str]]:
    total = sum(len(value) for value in files.values())
    return [
        ("服务端入口", "server.js" in files, "server.js 已生成" if "server.js" in files else "缺少 server.js"),
        ("构建清单", ".next/BUILD_ID" in files, "BUILD_ID 已生成" if ".next/BUILD_ID" in files else "缺少 BUILD_ID"),
        ("静态资源", any(name.startswith(".next/static/") for name in files), "Next 静态资源已打包"),
        ("运行时依赖", any(name.startswith("node_modules/next/") for name in files), "standalone 依赖已打包"),
        (
            "产物大小",
            0 < total <= NEXT_ARTIFACT_MAX_BYTES,
            f"{round(total / 1024 / 1024, 1)} MB / 上限 {round(NEXT_ARTIFACT_MAX_BYTES / 1024 / 1024)} MB",
        ),
    ]


def next_artifact_command() -> str:
    return (
        "cp -r .next/static .next/standalone/.next/static && "
        "if [ -d public ]; then cp -r public .next/standalone/public; fi && "
        "tar -czf /tmp/dist.tgz -C .next/standalone ."
    )
