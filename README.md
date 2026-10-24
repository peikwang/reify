# VibeForge

> 从 Vibe Coding 到 Vibe Working：一句话生成网站、简历、小游戏、旅游攻略、图片、视频制作和编程演示，并把成品直接部署到自己的 Agent Server。

VibeForge 是一个单机优先的个人设计 Agent。它把自然语言拆成计划，逐步写文件，展示代码 Diff 与 Agent 思考流，跑结构/交互/语法自检，最后发布到 `/p/{id}/`。当前版本支持多用户自助注册，账号、会话和项目归属全部持久化在本机 SQLite，每个用户只能访问自己的项目。

## 能力

| Studio | 产物 | 自动验收 |
| --- | --- | --- |
| 小游戏 | 贪吃蛇 / 俄罗斯方块 / 飞机大战 / 打砖块，以及 LLM 生成的长尾玩法 | 结构、viewport、脚本、canvas、离网自检 |
| 网站 | 有品牌感的响应式落地页 | 结构、viewport、内容区块、脚本 |
| 简历 | 单页双栏、在线可读、A4 可打印 | 结构、打印样式、viewport |
| 旅游攻略 | 按天切换的路线、预算与贴士 | 结构、每日路线交互、viewport |
| 图片 | 一次生成 4 张本地保存的图片 + 画廊 | 结构、图片资源、viewport |
| 视频制作 | 异步渲染视频 + 播放器页 | 结构、视频资源、viewport |
| 编程 | Python 代码 + 交互式可视化 | 结构、代码演示、`py_compile` |

实现方式由 Agent 自动选择，界面上不再暴露技术栈：小游戏、简历、攻略、图片、视频制作和编程固定使用静态模板；公司/工作室官网默认静态；个人网站、作品集、博客在沙箱可用时默认 React；只有提示词明确要求 Next.js/SSR 时才走 Next 源码工程——React 生成 Vite 工程并构建静态 `dist/`，Next 生成 App Router 全栈工程，构建 standalone 产物，并在独立运行时沙箱中启动 Node 服务。源码仍可在“编程模式”里逐个文件查看。

小游戏先按提示词命中内置引擎（贪吃蛇、俄罗斯方块、飞机大战、打砖块）；其他玩法（如 2048、数独、跑酷）会按 GameSpec 交给 LLM 生成单文件 Canvas 游戏。生成结果必须包含 canvas、游戏循环、键鼠/触控输入、计分和重开，且不引用外部资源或发起网络请求；首次校验失败会让模型修复一次，仍失败则回退到内置引擎，保证页面始终可玩。

## Next.js SSR 运行时

- 提示词明确要求 Next.js/SSR 时，Agent 生成 `app/`、`app/api/notes/route.ts`、`next.config.mjs` 等 TypeScript 源码，在 OpenSandbox 中执行 `npm ci` + `next build`，打包 `.next/standalone`。
- 构建完成后点击“启动应用”：创建独立运行时沙箱，上传 standalone 产物，后台启动 `node server.js`，健康检查通过后状态变为 `APP RUNNING`。
- 运行时默认 1 CPU / 1 GiB、TTL 1 小时；空闲 10 分钟由监控任务停止。当前 Docker runtime 采用 stop/start 冷启动，不是 MicroVM pause/resume。
- 远端 55 机器上 OpenSandbox server 同时接入 `vibeforge-net` 与默认 `bridge`：app 通过 `vibeforge-sandbox:8080` 调用，server 通过 bridge 直接代理到沙箱 execd；不把 41000-42000 端口暴露公网。
- 当前示例是带 `/api/notes` 的服务端接口，留言写入项目数据卷（`runtime-data/notes.json`），停止再启动仍保留；数据卷由 OpenSandbox host bind 提供。
- `/apps/{id}/` 预览默认关闭（`VIBEFORGE_SSR_PREVIEW=0`）。生产部署在 IP-only 模式下使用独立 HTTPS 端口 `12889`：平台在 `:12888`，SSR 应用在 `:12889`，两者不同 origin；Caddy 只在 `:12889` 暴露 `/apps/*`，并在 `:12888` 屏蔽 `/apps/*`。需要在云安全组放行 `12889`。生成应用仍可覆盖同主机 Cookie 造成登出（DoS），但无法读取平台 Cookie/API 响应。
- 运行时接口：`GET /api/projects/{id}/runtime`、`POST .../runtime/start`、`POST .../runtime/stop`。
- React/Next 的「继续修改」会修改源码 patch、重新构建；Next 会先启动新运行时并通过健康检查，再停掉旧运行时（蓝绿切换）。

## React 构建与执行沙箱

当前沙箱实现：

- **控制面**：独立部署的 OpenSandbox Server（`opensandbox/server`，Docker runtime），app 通过 Python SDK 调用；app 容器本身**不挂载 docker.sock**。
- **每个项目/每次构建一个临时沙箱**：`node:24-bookworm-slim`，构建默认 2 GiB（当前 55 机器用 4 GiB，Next 构建需要），运行时 1 GiB；启用 cap-drop、no-new-privileges、PID 限制，TTL 默认 15 分钟，构建结束立即销毁。当前 Docker runtime 下容器内命令仍以镜像默认用户执行；非 root、只读根要等 MicroVM/secure runtime 升级。
- **源码与日志**：源码通过文件 API 写入沙箱 `/workspace`；`npm install --ignore-scripts` 和 `npm run build` 的输出实时回传为 `build_log` 事件。
- **出网**：默认拒绝，只允许 `*.npmmirror.com`、`registry.npmjs.org`、`*.npmjs.org`；不向沙箱注入任何平台密钥。
- **产物**：构建完成后把 `dist/` 打包、下载、校验大小，原子切换到 `workspace/dist/`；构建失败保留上一版产物。
- **发布**：`/p/{id}/` 只服务 `dist/`，Vite 的 JS/CSS 资源使用项目 capability key，适配 CSP sandbox 下不携带 Cookie 的模块加载。
- **当前限制**：React/Next 的二次修改已接入“源码 patch → 重建 → 切换”，但需要可用的 LLM；SSR 预览使用独立端口 `12889`，不是域名级隔离。

本地启用沙箱：

```bash
# 1. 启动 OpenSandbox Server（Docker runtime）
uvx opensandbox-server init-config ~/.sandbox.toml --example docker
uvx opensandbox-server --config ~/.sandbox.toml

# 2. 启动 VibeForge
VIBEFORGE_SANDBOX=opensandbox \
VIBEFORGE_SANDBOX_DOMAIN=127.0.0.1:8080 \
VIBEFORGE_SANDBOX_API_KEY=your-sandbox-key \
VIBEFORGE_LLM_ENABLED=0 \
.venv/bin/python -m uvicorn server.main:app --host 127.0.0.1 --port 7801
```

OpenSandbox 的配置示例见 [`.env.example`](.env.example) 与 `deploy_remote.sh` 中的 `[docker]` / `[egress]` 段。当前使用 Docker 容器隔离；后续可切换 ACS Agent Sandbox / OpenSandbox Firecracker 获得 MicroVM 隔离。

## 双模式

- **日常模式**：左侧 Agent 流程以时间线动画逐条出现，右侧直接看成果预览、验收清单和部署状态。
- **编程模式**：左侧保留过程流，右侧展示文件树、逐行 Diff、终端日志和实时预览。每个 Agent 步骤都会留下一次文件快照，可一键重播。
- 两种模式共用同一条 SSE 事件流，不重跑 Agent。

## 账号与访问保护

- 任意用户可以在登录页自助注册；用户名 3~32 位，密码至少 8 位，注册后自动登录。
- 账号、scrypt 密码哈希、登录会话、项目归属和运行时记录都保存在本机 `data/vibeforge.db`（SQLite WAL），服务重启后登录态和项目不会丢失。
- Cookie 只保存随机令牌，会话本体在 SQLite；支持登出、退出所有设备、改密后失效。
- 登录/注册按 IP 和用户名限流；默认开放注册，可设置 `VIBEFORGE_REGISTRATION=closed` 关闭。
- 首个管理员由 `VIBEFORGE_ADMIN_USER` / `VIBEFORGE_ADMIN_PASSWORD` 启动时创建；未配置密码时会生成随机密码并打印到启动日志。
- 管理员角色已落库，并在 `/admin` 提供用户表、禁用/启用、撤销会话和审计日志；普通用户无法读取、修改、下载或预览其他用户的项目。

现有单密码部署升级时，旧的 `VIBEFORGE_PASSWORD` 会作为管理员密码继续使用；启动时会自动把旧的扁平项目迁移到首个管理员名下（原目录保留）。部署脚本在升级前会备份 `data/vibeforge.db`。也可以手动执行：

```bash
.venv/bin/python scripts/migrate_v2.py --dry-run
.venv/bin/python scripts/migrate_v2.py
```

登录接口限流默认 1 分钟 8 次/用户、20 次/IP；注册默认每 IP 每小时 5 次。服务通过 Caddy 提供 HTTPS：应用只监听内部 12888，Caddy 在 12888 终止 TLS，并使用 Let's Encrypt 的公网 IP 证书（约 6 天有效期，自动续期）。80 端口只用于 ACME HTTP-01 验证和跳转，不直接暴露应用。

## 本地启动

平台控制台是 Vite + React + TypeScript SPA，构建产物在 `web/dist/`；FastAPI 只服务该产物，不需要常驻 Node 进程。

前置条件：

- Python 3.12+（当前验证到 3.14）
- Node.js 20+（推荐 24）与 npm，仅用于构建平台前端和生成项目
- 静态模板/长尾游戏可以直接运行；React/Next 源码生成还需要 Docker + OpenSandbox

```bash
cd vibeforge-react-ts

# 1. 构建平台前端
cd frontend && npm ci && npm run build && cd ..

# 2. Python 环境
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. 可选：准备本地环境变量（不要提交）
cp .env.example .env

# 4. 启动
VIBEFORGE_ADMIN_PASSWORD=your-admin-password \
VIBEFORGE_REGISTRATION=open \
.venv/bin/python -m uvicorn server.main:app --host 127.0.0.1 --port 7801
```

打开 <http://127.0.0.1:7801>。管理员用户名默认 `admin`；未设置密码时启动日志会生成临时密码。其他用户在登录页切到“注册”创建账号。

前端热更新（可选，另开一个终端）：

```bash
cd frontend
npm run dev
# 默认 http://127.0.0.1:5173
# 后端不在 7801 时：VIBEFORGE_BACKEND=http://127.0.0.1:12888 npm run dev
```

本地启用 React/Next 构建沙箱：

```bash
# 1. 生成并启动 OpenSandbox Server（Docker runtime）
uvx opensandbox-server init-config ~/.sandbox.toml --example docker
uvx opensandbox-server --config ~/.sandbox.toml

# 2. 使用与服务端配置一致的 API Key 启动 VibeForge
VIBEFORGE_SANDBOX=opensandbox \
VIBEFORGE_SANDBOX_DOMAIN=127.0.0.1:8080 \
VIBEFORGE_SANDBOX_API_KEY=your-sandbox-key \
VIBEFORGE_SSR_PREVIEW=1 \
VIBEFORGE_SSR_PORT=12889 \
.venv/bin/python -m uvicorn server.main:app --host 127.0.0.1 --port 7801
```

`run.sh` 等价于在 `0.0.0.0:12888` 启动后端；它不会自动构建前端，首次运行仍需执行 `cd frontend && npm ci && npm run build`。

## E2E 测试

开发依赖：

```bash
.venv/bin/pip install -r requirements-dev.txt
# 浏览器 E2E 使用系统 Chrome（channel=chrome）；没有 Chrome 时执行：
# .venv/bin/python -m playwright install chromium
```

```bash
# 后端单测（61 项）
.venv/bin/python -m pytest -q

# 前端组件/Reducer/SSE 测试（57 项）+ 类型检查 + 构建
cd frontend && npm ci && npm test && npm run typecheck && npm run build && cd ..

# 生成工程的 TypeScript 真实构建（npm ci + tsc + vite/next build）
.venv/bin/python tests/e2e_typescript_scaffolds.py

# 平台 UI 全链路（真实 uvicorn + Chrome + mock LLM；注册、模板、生成、Refine、
# 编程模式、部署、分享、导出、项目库、管理员、移动端、长尾游戏）
.venv/bin/python tests/e2e_browser.py

# 已部署环境 UI 回归（需要一个可访问的 BASE）
VIBEFORGE_E2E_BASE=https://117.148.166.55:12888 \
  .venv/bin/python tests/e2e_deployed.py

# 已部署环境真实 LLM 长尾游戏（会消耗模型 token）
VIBEFORGE_E2E_BASE=https://117.148.166.55:12888 \
  .venv/bin/python tests/e2e_game_live.py

# 已部署环境 Next 运行时 UI：真实构建 -> 启动 -> 12889 iframe -> 服务端留言
VIBEFORGE_E2E_BASE=https://117.148.166.55:12888 \
  .venv/bin/python tests/e2e_next_live.py
```

`tests/e2e_react_sandbox.py`、`tests/e2e_next_ssr.py`、`tests/e2e_refine.py` 需要可用的 OpenSandbox，最好在 55 机器的内部网络里运行：

```bash
ssh root@117.148.166.55

docker run --rm --network vibeforge-net \
  -v /opt/vibeforge:/app -w /app \
  --env-file /opt/vibeforge/.runtime.env \
  --entrypoint python3 vibeforge-app:latest \
  tests/e2e_react_sandbox.py

docker run --rm --network vibeforge-net \
  -v /opt/vibeforge:/app -w /app \
  --env-file /opt/vibeforge/.runtime.env \
  --entrypoint python3 vibeforge-app:latest \
  tests/e2e_next_ssr.py

docker run --rm --network vibeforge-net \
  -v /opt/vibeforge:/app -w /app \
  --env-file /opt/vibeforge/.runtime.env \
  --entrypoint python3 vibeforge-app:latest \
  tests/e2e_refine.py
```

## 手机访问

手机与服务器网络可达时，直接打开：

```text
https://117.148.166.55:12888/
```

登录或注册后即可使用。页面已适配 390px 手机宽度。部分运营商/公司网络会拦截 12888 这类非标准端口；换 Wi-Fi 或蜂窝网络再试。证书为受信任的公网 IP 证书，不需要手动信任。

## 可选：接入任意 OpenAI 兼容模型

不配置模型时，Agent 使用确定性的“本地导演 + 模板渲染”，保证每次都能生成可运行产物。配置后，模型负责产出短创意 brief（标题、语气、强调色、要点），长尾小游戏还会生成完整单文件游戏；其余 HTML 仍由可验证的模板渲染，避免模型输出坏页面。长尾游戏默认关闭模型思考模式（`enable_thinking=false`），避免推理占满输出预算；如模型不支持该参数，可设置 `VIBEFORGE_LLM_GAME_DISABLE_THINKING=0`，并适当调大 `VIBEFORGE_LLM_GAME_MAX_TOKENS`。

```bash
export VIBEFORGE_LLM_BASE_URL=http://127.0.0.1:8000/v1
export VIBEFORGE_LLM_API_KEY=sk-...
export VIBEFORGE_LLM_MODEL=qwen-plus
```

也支持 vLLM / SGLang / Ollama 的 OpenAI 兼容接口。

图片默认使用 `qwen-image-3.0-pro`，一次生成 4 张；视频默认使用当前工作区已开放的 `wan3.0-video`。`wan2.7-video` 在当前工作区返回 Model not exist，如果后续开通可设置：

```bash
VIBEFORGE_VIDEO_MODEL=wan2.7-video
```

图片/视频素材会下载到 `data/users/{uid}/projects/{id}/workspace/assets/v{revision}/`，项目页展示画廊或播放器；二次修改会生成新的 `v{revision}` 目录，旧素材保留。素材 URL 带项目级能力 key，静态页面在 CSP sandbox 下也能正常加载。

### 安全注入模型凭据（不要发到对话里）

把凭据写成本地文件，再用 scp 传到服务器，Agent 不读取文件内容，也不会把它写进仓库：

```bash
umask 077
cat > ~/.vibeforge_llm.env <<'EOF'
VIBEFORGE_LLM_BASE_URL=https://your-provider/v1
VIBEFORGE_LLM_MODEL=your-model
VIBEFORGE_LLM_API_KEY=sk-your-key
VIBEFORGE_LLM_ENABLED=1
EOF

scp ~/.vibeforge_llm.env root@117.148.166.55:/opt/vibeforge/.llm.env
ssh root@117.148.166.55 'chmod 600 /opt/vibeforge/.llm.env'
cd vibeforge && ./deploy_remote.sh root@117.148.166.55 12888
```

部署脚本会把 `.auth.env` 与 `.llm.env` 合并成 600 权限的 `.runtime.env` 再注入容器；不会写入镜像、源码或 Git。

如果只想用一次，测完后删除凭据并重建容器：

```bash
ssh root@117.148.166.55 'shred -u /opt/vibeforge/.llm.env /opt/vibeforge/.runtime.env'
rm -f ~/.vibeforge_llm.env
cd vibeforge && ./deploy_remote.sh root@117.148.166.55 12888
```

重建后 `/api/health` 会回到 `llm:false`，模板导演继续兜底。

## 目录结构

```text
vibeforge-react-ts/
├── frontend/                    平台控制台：Vite + React 19 + TypeScript
│   ├── src/
│   │   ├── api/                 fetch 封装与 API 类型
│   │   ├── auth/                登录/注册、会话、受保护路由
│   │   ├── layout/              AppShell、Toast
│   │   ├── pages/               首页、项目库、项目页、管理员页
│   │   ├── features/
│   │   │   ├── composer/        通用输入框、7 模板画廊与插图
│   │   │   ├── project-library/ 项目卡片、筛选、统计、公开链接
│   │   │   └── workspace/       SSE 时间线、编程模式、Refine、部署/分享/运行时
│   │   ├── hooks/               useTaskStream、useProjects、useCapabilities
│   │   └── styles/              现有视觉与响应式样式
│   ├── vite.config.ts           dev server :5173，代理到本地后端
│   └── package.json / package-lock.json
├── server/                      FastAPI 服务
│   ├── main.py                  HTTP API、SSE、SPA 服务、鉴权入口
│   ├── auth.py / db.py          scrypt 密码、SQLite 会话、用户/项目/审计
│   ├── agent.py                 生成编排：规划 → 写文件 → 自检 → 部署/构建
│   ├── llm.py                   OpenAI 兼容 brief、Refine、长尾游戏生成
│   ├── media.py                 图片/视频生成与下载
│   ├── sandbox.py               OpenSandbox 客户端、React/Next 构建与产物校验
│   ├── runtime.py               Next standalone 运行时、健康检查、蓝绿切换
│   ├── events.py / tools.py     任务事件流、文件快照、部署工具
│   ├── migrate.py               旧扁平项目迁移
│   ├── stacks.py                static/react/next 自动路由策略
│   └── templates/
│       ├── library.py           7 类能力注册、分类、计划与自检
│       ├── website.py 等        静态页面模板
│       ├── react_app.py         Vite + React + TS 源码脚手架
│       ├── next_app.py          Next App Router + TS 源码脚手架
│       └── games/
│           ├── __init__.py      品类路由与默认文案
│           ├── snake.py         内置贪吃蛇
│           ├── tetris.py        内置俄罗斯方块
│           ├── shooter.py       内置飞机大战
│           ├── breakout.py      内置打砖块
│           ├── spec.py          长尾游戏 GameSpec
│           └── custom.py        LLM 单文件游戏、校验、修复与回退
├── web/dist/                    前端构建产物，由 FastAPI 直接服务
├── tests/                       pytest 单测与各阶段 E2E 脚本
├── docs/                        迁移设计、隔离设计
├── scripts/                     migrate_v2.py
├── data/                        运行时数据（忽略提交）
│   ├── vibeforge.db             SQLite：用户、会话、项目索引、运行时
│   └── users/{uid}/projects/{pid}/
│       ├── workspace/           源码、dist、runtime
│       ├── events.jsonl         事件流
│       └── meta.json            项目元信息
├── projects/                    旧版扁平项目（仅迁移用）
├── Dockerfile.app               前端构建 + 精简 Python 运行镜像
├── Caddyfile                    12888 平台 / 12889 SSR / 80 ACME
├── deploy_remote.sh             远端部署脚本
├── run.sh                       本地直接启动脚本
├── requirements.txt             生产 Python 依赖
├── requirements-dev.txt         测试依赖（pytest、Playwright）
└── .env.example                 环境变量样例
```

## API

- `POST /api/auth/register` `{username, password, display_name?, email?}` → 注册并登录
- `POST /api/auth/login` `{username, password}` → 登录（用户名或邮箱）
- `POST /api/auth/logout` → 撤销当前会话
- `GET /api/auth/me` → 当前登录用户
- `POST /api/projects` `{prompt, capability?}` → 创建项目；后端自动选择静态/React/Next，前端不暴露技术栈（`stack` 仅保留给内部测试）
- `POST /api/projects/{id}/refine` `{instruction}` → 基于当前成果对话修改（图片/视频会重新生成素材）
- `GET /api/projects/{id}` → 元信息 + 事件历史
- `GET /api/projects/{id}/events` → SSE 事件流
- `POST /api/projects/{id}/deploy` → 重新部署（静态/React）
- `GET|POST /api/projects/{id}/runtime[/start|/stop]` → Next SSR 运行时管理
- `GET /apps/{id}/` → SSR 预览（仅 `VIBEFORGE_SSR_PREVIEW=1`，且仅项目所有者）
- `GET /api/projects/{id}/bundle` → 下载项目 zip
- `GET /p/{id}/` → 已部署静态产物（仅项目所有者）
- `POST|DELETE /api/projects/{id}/share` → 创建/撤销只读分享
- `GET /s/{token}/` → 公开只读分享页（静态/React；新项目自动签发）
- `GET /api/admin/users`、`POST /api/admin/users/{id}/status`、`POST /api/admin/users/{id}/revoke-sessions`、`GET /api/admin/audit` → 管理员接口

生成完成后，静态项目的左侧会出现「继续修改」输入框。Agent 会读取当前 `index.html`，让模型返回精确的局部 patch，应用后重新自检并部署；修改失败时原页面保持不变。每次成功修改会增加 `revision`，原有事件流继续追加。React/Next 项目会修改对应源码文件，重新构建后切换产物；Next 运行时采用新沙箱健康检查通过后再停旧沙箱的蓝绿切换。

## 账号管理与分享

- 管理员在 `/admin` 查看用户、项目数、存储占用和最近审计；可禁用/启用账号、撤销某用户全部会话。
- 新生成的静态/React 项目会自动获得只读分享链接 `/s/{token}/`；也可用 `POST /api/projects/{id}/share` 重新签发，`DELETE` 立即撤销。分享页不需要登录，但不能调用平台 API；只暴露 `index.html` 与 `assets/`，源码、README 和 prompt 不会通过分享页泄露。撤销后旧 asset key 对匿名访问立即失效，项目所有者仍可在登录状态预览。Next SSR 项目暂不支持分享。
- 每用户最多保留 2 个运行中的 SSR 应用（`VIBEFORGE_MAX_RUNTIME_PER_USER`），超出时启动接口返回 429。
- 密码、会话和审计都保存在本机 SQLite；审计记录包含注册/登录、项目创建/修改/部署、运行时启停、分享和管理员操作。
- 每用户默认限制 50 个项目、1 GB 存储、2 个活跃任务、1 个源码构建；超出时 API 返回 429。

## 环境与资源要求

### 运行环境

- Linux 主机 + Docker Engine（推荐 24+），有 `docker` / `docker network` 权限
- 平台容器只需 Python 3.12；Node 24 只在镜像构建阶段和项目构建沙箱中使用
- 生产使用 Caddy 容器终止 TLS；不需要宿主机安装 Caddy/Nginx
- 浏览器 E2E 需要本机安装 Google Chrome（Playwright 使用 `channel=chrome`）
- 出网：npm 构建需要 `registry.npmmirror.com`（可配置）、LLM/媒体 API 域名；沙箱默认 allowlist
- 入网：`80`（ACME HTTP-01 + 跳转）、`12888`（平台 HTTPS）、`12889`（SSR 应用 HTTPS）

### 端口

| 端口 | 用途 | 暴露 |
|---|---|---|
| 80/tcp | ACME HTTP-01、跳转 | 公网 |
| 12888/tcp | 平台 UI/API/SSE、`/p/`、`/s/` | 公网 |
| 12889/tcp | Next SSR `/apps/*` | 公网（如启用 Next 运行时） |
| 8080/tcp | OpenSandbox Server | 仅 Docker 内网 |
| 3000/tcp | 单个 Next 运行时 | 仅沙箱网络 |
| 41000-42000 | 沙箱映射端口 | 仅绑定 `172.17.0.1` |

### 单机资源预算

| 场景 | vCPU | 内存 | 磁盘 | 说明 |
|---|---:|---:|---:|---|
| 只跑静态模板/长尾游戏，不启用源码沙箱 | 2 | 2 GB | 10 GB | 应用 + Caddy + SQLite |
| 推荐完整能力 | 4-8 | 16 GB | 60 GB | React/Next 构建 + 1-2 个 SSR 运行时 |
| 最低可尝试 Next | 4 | 8 GB | 30 GB | 构建需 4 GiB 沙箱；并发高会排队 |

实测占用（55 机器）：

- 平台容器空闲约 **55 MiB**，Caddy 约 **35 MiB**，OpenSandbox Server 约 **140 MiB**；应用容器限制 2 vCPU / 4 GiB / 512 PIDs，并 cap-drop ALL
- React/Next 构建沙箱：1 vCPU / 4 GiB（部署脚本覆盖为 4 GiB），并发上限 2
- Next 运行时：1 vCPU / 1 GiB，TTL 1 小时，空闲 10 分钟停止
- 当前 55：96 vCPU / 251 GiB RAM / 30 GB 磁盘，部署后约剩 8 GB；**磁盘是瓶颈**，建议清理悬空镜像或扩到 60 GB
- 平台镜像已切到 `python:3.12-slim`，约 150 MB；沙箱 Node 镜像约 220 MB；用户数据配额默认 1 GB/人

### 关键环境变量

| 变量 | 默认 | 用途 |
|---|---|---|
| `VIBEFORGE_DATA` | `./data` | SQLite 与用户项目根目录 |
| `VIBEFORGE_PROJECTS` | `./projects` | 旧版项目目录（迁移用） |
| `VIBEFORGE_DB` | `data/vibeforge.db` | SQLite 路径 |
| `VIBEFORGE_ADMIN_USER/PASSWORD` | `admin` / 随机 | 首个管理员 |
| `VIBEFORGE_COOKIE_SECURE` | `0` | HTTPS 部署必须设为 `1` |
| `VIBEFORGE_REGISTRATION` | `open` | `open` 或 `closed` |
| `VIBEFORGE_SANDBOX` | `off` | `opensandbox` 启用源码构建 |
| `VIBEFORGE_SANDBOX_DOMAIN` | `127.0.0.1:8080` | Sandbox Server 地址 |
| `VIBEFORGE_SANDBOX_API_KEY` | 空 | Sandbox API Key |
| `VIBEFORGE_SANDBOX_BUILD_MEMORY` | `2Gi`（55 用 `4Gi`） | 构建沙箱内存 |
| `VIBEFORGE_SANDBOX_CONCURRENCY` | `2` | 同时构建数 |
| `VIBEFORGE_NPM_REGISTRY` | `https://registry.npmmirror.com` | 构建 npm 源 |
| `VIBEFORGE_NPM_INSTALL_TIMEOUT` / `BUILD_TIMEOUT` | `600` | npm 超时（秒） |
| `VIBEFORGE_SSR_PREVIEW` | `0` | 是否代理 `/apps/*` 预览 |
| `VIBEFORGE_SSR_PORT` | `12889` | SSR origin 端口 |
| `VIBEFORGE_RUNTIME_IDLE/TTL` | `600` / `3600` | 运行时空闲停止/TTL（秒） |
| `VIBEFORGE_LLM_ENABLED` | `1` | 是否调用模型 |
| `VIBEFORGE_LLM_BASE_URL/API_KEY/MODEL` | 空 | OpenAI 兼容接口 |
| `VIBEFORGE_LLM_GAME_DISABLE_THINKING` | `1` | 长尾游戏关闭思考模式 |
| `VIBEFORGE_LLM_GAME_MAX_TOKENS` | `24000` | 长尾游戏输出预算 |
| `VIBEFORGE_MEDIA_API_BASE/KEY` | 继承 LLM | 图片/视频接口 |
| `VIBEFORGE_MAX_STORAGE_PER_USER` | `1073741824` | 每用户存储上限（1 GB） |

完整列表见 [.env.example](.env.example)。部署时敏感变量写入 `/opt/vibeforge/.auth.env`、`.sandbox.env`、`.llm.env`，由脚本合并为 600 权限的 `.runtime.env`。

## 远程部署（HTTPS / Caddy）

### 前置条件

- Linux 主机 + Docker Engine；建议 4 vCPU / 16 GB RAM / 60 GB 磁盘
- 安全组放行 `80`、`12888`、`12889`；`80` 用于 ACME HTTP-01
- 本机可 SSH 到目标机器，目标机器可拉取 Docker 镜像和 npm 包
- 可选：准备 `.llm.env`（不要把密钥写进仓库或对话）

### 首次部署

```bash
cd vibeforge-react-ts
./deploy_remote.sh root@117.148.166.55 12888
```

脚本会：

1. 同步源码到 `/opt/vibeforge`
2. 用 `python:3.12-slim` 构建 `vibeforge-app:latest`（内部多阶段用 Node 构建 `web/dist`）
3. 把镜像里的前端产物复制到宿主 `/opt/vibeforge/web/dist`（应用容器把 `/opt/vibeforge` 挂载为 `/app`）
4. 备份 `/opt/vibeforge/data/vibeforge.db` 到 `/opt/vibeforge/backups/`
5. 生成/复用 `.auth.env`、`.sandbox.env`，启动或复用 `vibeforge-sandbox`
6. 替换 `vibeforge` 与 `vibeforge-caddy`，保留沙箱容器
7. 校验 `/api/health`、未登录 `/api/projects` 返回 401、`/login` 返回 React 入口

首次启动的管理员密码在：

```text
root@<host>:/opt/vibeforge/.auth.env
```

### 数据、备份与回滚

- 数据全部在宿主 `/opt/vibeforge/data/`，容器重建不会丢失
- 每次部署前自动备份 SQLite 到 `/opt/vibeforge/backups/`；建议保留 7 天并定期复制到宿主机之外
- 项目产物体积受 `VIBEFORGE_MAX_STORAGE_PER_USER` 限制（默认 1 GB/用户）
- 回滚：切回上一个 Git 版本重新执行部署脚本；数据库备份在 `backups/`，恢复时先停 `vibeforge` 再替换 `data/vibeforge.db`

### 更新与沙箱

- 重复执行部署脚本即可更新；默认只重建 app/Caddy，不打断已有 SSR 运行时
- 修改了 `.sandbox.env` 或 `sandbox/config.toml` 后，需要手动重建 `vibeforge-sandbox`，否则旧配置继续生效
- `VIBEFORGE_IMAGE` 可替换 app 基座镜像；`VIBEFORGE_APP_IMAGE` 只改变镜像 tag，不会跳过构建

### 证书与验证

```bash
curl -kfsS https://117.148.166.55:12888/api/health
curl -kfsS -o /dev/null -w '%{http_code}\n' https://117.148.166.55:12888/login
```

Caddy 使用公网 IP 证书（短周期，自动续期），证书与 ACME 账户保存在 Docker volume `vibeforge-caddy-data`。如果 80 端口不可达，需要改用域名 + DNS-01 或接受自签名证书。12889 是独立 origin，平台 12888 会屏蔽 `/apps/*`，避免生成应用读取平台 Cookie/API 响应。

## 运维与故障排查

```bash
# 服务与沙箱状态
docker ps --format '{{.Names}}\t{{.Status}}' | grep vibeforge
docker logs --tail 100 vibeforge
docker logs --tail 100 vibeforge-sandbox
curl -kfsS https://<host>:12888/api/health

# 数据量
docker exec vibeforge python3 -c "import sqlite3; c=sqlite3.connect('/app/data/vibeforge.db'); print(c.execute('select count(*) from users').fetchone(), c.execute('select count(*) from projects').fetchone())"

# 备份与恢复（停服务后替换）
ls -lt /opt/vibeforge/backups | head
docker stop vibeforge
cp /opt/vibeforge/backups/vibeforge-<stamp>.db /opt/vibeforge/data/vibeforge.db
docker start vibeforge
```

常见问题：

| 现象 | 处理 |
|---|---|
| 页面 503，提示 React UI build is missing | 执行 `cd frontend && npm ci && npm run build`，确认 `web/dist/index.html` 存在 |
| 登录后立即跳回登录 | 生产 `VIBEFORGE_COOKIE_SECURE=1`；本地 HTTP 设为 `0` |
| React/Next 任务 503 或配置 503 | 检查沙箱容器、API Key、`vibeforge-sandbox:8080` 网络别名和 `/api/health` 的 `reachable` |
| npm ci 卡住 | 确认构建沙箱能访问 `VIBEFORGE_NPM_REGISTRY`；不要把 lockfile 指向内网 registry |
| Next 构建 OOM | 构建沙箱至少 4 GiB，降低 `VIBEFORGE_SANDBOX_CONCURRENCY` |
| 12889 打不开 | 安全组放行 12889；平台 12888 不代理 `/apps/*` |
| 公开页空白 / React 资源加载失败 | 确认 `/s/` 响应带 `Access-Control-Allow-Origin: *`，且 `web/dist` 完整 |
| 长尾游戏回退内置引擎 | 检查 LLM 配置；模型支持时保持 `VIBEFORGE_LLM_GAME_DISABLE_THINKING=1`，否则调整 `MAX_TOKENS`/超时 |
| 磁盘不足 | 清理悬空镜像（先确认没有容器使用）：`docker image prune`；长期方案扩容到 60 GB |

## 安全边界

- 自助注册 + SQLite 服务端会话；未认证访问页面会跳转登录，API/预览返回 401。
- 管理员可禁用用户、撤销会话；分享链接为只读 capability URL，可随时撤销；所有关键操作写入本地审计表。
- 公开分享只服务 `index.html` 与 `assets/`，不暴露 README、源码或 prompt；撤销分享后旧 asset key 对匿名访问失效。
- 每个项目强制 `owner_id`，所有 API、SSE、下载、预览和媒体都做所有权或项目能力 key 校验；跨用户统一返回 404。
- 所有 `/p/` 生成物响应带 `Content-Security-Policy: sandbox`，直接打开新窗口也不会获得主站同源权限。
- 产物只写入 `data/users/{uid}/projects/{pid}/workspace/`，所有文件工具做工作区路径校验。
- 静态 `/p/` 预览 iframe 不开放 same-origin；Next 预览在独立的 12889 origin 上允许 same-origin，以便其自身 `/apps/{id}/api/*` 工作，仍无法访问 12888 平台页面。
- 当前数据层已按用户隔离；React/Next 构建在独立 OpenSandbox 沙箱中执行，app 容器不持有 docker.sock。
- 沙箱不注入平台密钥，构建结束销毁。本机默认使用 npm registry allowlist；当前 55 机器的 OpenSandbox egress sidecar 无法启动，部署脚本使用 `VIBEFORGE_SANDBOX_EGRESS=open`（无 sidecar），隔离仍依赖容器边界，后续需修复/替换 sidecar。
- Next SSR 运行时是单独沙箱；`/apps/` 预览通过独立端口 `12889` 与平台 `12888` 隔离，Caddy 只在该端口暴露 `/apps/*`。运行时出网同样受上述 sidecar 限制。仍需注意同主机 Cookie 可被生成应用覆盖（DoS）。
- 若要开放给不可信多用户并执行任意生成代码，建议把 Docker runtime 升级为 OpenSandbox Firecracker 或 ACS Agent Sandbox（MicroVM）。
