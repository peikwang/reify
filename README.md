# VibeForge

> 从 Vibe Coding 到 Vibe Working：一句话生成网站、简历、小游戏、旅游攻略、多尺寸适配、图片、视频和编程演示，并把成品直接部署到自己的 Agent Server。

VibeForge 是一个单机优先的个人设计 Agent。它把自然语言拆成计划，逐步写文件，展示代码 Diff 与 Agent 思考流，跑结构/交互/语法自检，最后发布到 `/p/{id}/`。当前版本支持多用户自助注册，账号、会话和项目归属全部持久化在本机 SQLite，每个用户只能访问自己的项目。

## 能力

| Studio | 产物 | 自动验收 |
| --- | --- | --- |
| 小游戏 | 可玩的 Canvas 街机（键盘 + 触控 + 最高分） | 结构、viewport、脚本、canvas |
| 网站 | 有品牌感的响应式落地页 | 结构、viewport、内容区块、脚本 |
| 简历 | 单页双栏、在线可读、A4 可打印 | 结构、打印样式、viewport |
| 旅游攻略 | 按天切换的路线、预算与贴士 | 结构、每日路线交互、viewport |
| 适配制作 | 16:9 / 1:1 / 9:16 多画板切换 | 结构、多尺寸标记、viewport |
| 图片 | 一次生成 4 张本地保存的图片 + 画廊 | 结构、图片资源、viewport |
| 视频 | 异步渲染视频 + 播放器页 | 结构、视频资源、viewport |
| 编程 | Python 代码 + 交互式可视化 | 结构、代码演示、`py_compile` |

生成网站时可以在首页的 STACK 选择 **React 源码** 或 **Next SSR**：React 生成 Vite 工程并构建静态 `dist/`；Next 生成 App Router 全栈工程，构建 standalone 产物，并在独立运行时沙箱中启动 Node 服务。源码仍可在“编程模式”里逐个文件查看。

## Next.js SSR 运行时

- 选择 **Next SSR** 后，Agent 生成 `app/`、`app/api/notes/route.js`、`next.config.mjs` 等源码，在 OpenSandbox 中执行 `npm ci` + `next build`，打包 `.next/standalone`。
- 构建完成后点击“启动 SSR”：创建独立运行时沙箱，上传 standalone 产物，后台启动 `node server.js`，健康检查通过后状态变为 `SSR RUNNING`。
- 运行时默认拒绝出网，1 CPU / 1 GiB，TTL 1 小时；空闲 10 分钟由监控任务停止。当前 Docker runtime 采用 stop/start 冷启动，不是 MicroVM pause/resume。
- 当前示例是带 `/api/notes` 的服务端接口，留言写入项目数据卷（`runtime-data/notes.json`），停止再启动仍保留；数据卷由 OpenSandbox host bind 提供。
- `/apps/{id}/` 预览默认关闭（`VIBEFORGE_SSR_PREVIEW=0`）。生产部署在 IP-only 模式下使用独立 HTTPS 端口 `12889`：平台在 `:12888`，SSR 应用在 `:12889`，两者不同 origin；Caddy 只在 `:12889` 暴露 `/apps/*`，并在 `:12888` 屏蔽 `/apps/*`。需要在云安全组放行 `12889`。生成应用仍可覆盖同主机 Cookie 造成登出（DoS），但无法读取平台 Cookie/API 响应。
- 运行时接口：`GET /api/projects/{id}/runtime`、`POST .../runtime/start`、`POST .../runtime/stop`。
- React/Next 的「继续修改」会修改源码 patch、重新构建；Next 会先启动新运行时并通过健康检查，再停掉旧运行时（蓝绿切换）。

## React 构建与执行沙箱

当前 Phase 2 的沙箱实现：

- **控制面**：独立部署的 OpenSandbox Server（`opensandbox/server`，Docker runtime），app 通过 Python SDK 调用；app 容器本身**不挂载 docker.sock**。
- **每个项目/每次构建一个临时沙箱**：`node:24-bookworm-slim`，1 CPU / 1 GiB，启用 cap-drop、no-new-privileges、PID 限制，TTL 默认 15 分钟，构建结束立即销毁。当前 Docker runtime 下容器内命令仍以镜像默认用户执行；非 root、只读根要等 MicroVM/secure runtime 升级。
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
- 管理员角色已落库，用户管理界面留待后续阶段；普通用户无法读取、修改、下载或预览其他用户的项目。

现有单密码部署升级时，旧的 `VIBEFORGE_PASSWORD` 会作为管理员密码继续使用；启动时会自动把旧的扁平项目迁移到首个管理员名下（原目录保留）。部署脚本在升级前会备份 `data/vibeforge.db`。也可以手动执行：

```bash
.venv/bin/python scripts/migrate_v2.py --dry-run
.venv/bin/python scripts/migrate_v2.py
```

登录接口限流默认 1 分钟 8 次/用户、20 次/IP；注册默认每 IP 每小时 5 次。服务通过 Caddy 提供 HTTPS：应用只监听内部 12888，Caddy 在 12888 终止 TLS，并使用 Let's Encrypt 的公网 IP 证书（约 6 天有效期，自动续期）。80 端口只用于 ACME HTTP-01 验证和跳转，不直接暴露应用。

## 本地启动

```bash
cd vibeforge
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
VIBEFORGE_ADMIN_PASSWORD=your-admin-password VIBEFORGE_REGISTRATION=open \
  .venv/bin/python -m uvicorn server.main:app --host 127.0.0.1 --port 7801
```

打开 <http://127.0.0.1:7801>。管理员用户名默认 `admin`；未设置密码时启动日志会生成一个临时管理员密码。其他用户在登录页切换到“注册”即可创建自己的账号。

## 手机访问

手机与服务器网络可达时，直接打开：

```text
https://117.148.166.55:12888/
```

登录或注册后即可使用。页面已适配 390px 手机宽度。部分运营商/公司网络会拦截 12888 这类非标准端口；换 Wi-Fi 或蜂窝网络再试。证书为受信任的公网 IP 证书，不需要手动信任。

## 可选：接入任意 OpenAI 兼容模型

不配置模型时，Agent 使用确定性的“本地导演 + 模板渲染”，保证每次都能生成可运行产物。配置后，模型只负责产出短创意 brief（标题、语气、强调色、要点），HTML 仍由可验证的模板渲染，避免模型输出坏页面。

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

## 目录

```text
server/
  main.py              FastAPI、SSE、鉴权、按用户项目路由
  auth.py              注册、scrypt 密码、SQLite 服务端会话、限流
  db.py                SQLite schema 与用户/会话/项目持久化
  migrate.py           旧扁平项目迁移到用户目录
  agent.py             ToolAct 编排（规划 → 写文件 → 自检 → 部署）
  events.py            项目对象、事件流、按用户工作区
  tools.py             文件快照、Python 自检、构建/运行时产物安装、部署工具
  sandbox.py           OpenSandbox 客户端、React/Next 构建、产物打包与校验
  runtime.py           Next standalone 运行时沙箱、健康检查、空闲停止
  llm.py               可选创意导演（失败自动回退）
  templates/           八类能力页面模板 + Vite/React 与 Next.js 脚手架
web/                   双模式工作台（原生 HTML/CSS/JS）
data/vibeforge.db      用户、会话、项目、运行时索引
data/users/{uid}/projects/{pid}/workspace/   Agent 产物
data/users/{uid}/projects/{pid}/events.jsonl 事件流
```

## API

- `POST /api/auth/register` `{username, password, display_name?, email?}` → 注册并登录
- `POST /api/auth/login` `{username, password}` → 登录（用户名或邮箱）
- `POST /api/auth/logout` → 撤销当前会话
- `GET /api/auth/me` → 当前登录用户
- `POST /api/projects` `{prompt, capability?, stack?}` → 创建项目；`stack=react|next` 使用沙箱构建源码工程
- `POST /api/projects/{id}/refine` `{instruction}` → 基于当前成果对话修改（图片/视频会重新生成素材）
- `GET /api/projects/{id}` → 元信息 + 事件历史
- `GET /api/projects/{id}/events` → SSE 事件流
- `POST /api/projects/{id}/deploy` → 重新部署（静态/React）
- `GET|POST /api/projects/{id}/runtime[/start|/stop]` → Next SSR 运行时管理
- `GET /apps/{id}/` → SSR 预览（仅 `VIBEFORGE_SSR_PREVIEW=1`，且仅项目所有者）
- `GET /api/projects/{id}/bundle` → 下载项目 zip
- `GET /p/{id}/` → 已部署静态产物（仅项目所有者）
- `POST|DELETE /api/projects/{id}/share` → 创建/撤销只读分享
- `GET /s/{token}/` → 公开只读分享页（静态/React）
- `GET /api/admin/users`、`POST /api/admin/users/{id}/status`、`POST /api/admin/users/{id}/revoke-sessions`、`GET /api/admin/audit` → 管理员接口

生成完成后，静态项目的左侧会出现「继续修改」输入框。Agent 会读取当前 `index.html`，让模型返回精确的局部 patch，应用后重新自检并部署；修改失败时原页面保持不变。每次成功修改会增加 `revision`，原有事件流继续追加。React/Next 项目会修改对应源码文件，重新构建后切换产物；Next 运行时采用新沙箱健康检查通过后再停旧沙箱的蓝绿切换。

## 账号管理与分享

- 管理员在 `/admin` 查看用户、项目数、存储占用和最近审计；可禁用/启用账号、撤销某用户全部会话。
- 静态/React 项目支持只读分享链接：`POST /api/projects/{id}/share` 生成 `/s/{token}/`，`DELETE` 立即撤销。分享页不需要登录，但不能调用平台 API；Next SSR 项目暂不支持分享。
- 密码、会话和审计都保存在本机 SQLite；审计记录包含注册/登录、项目创建/修改/部署、运行时启停、分享和管理员操作。
- 每用户默认限制 50 个项目、1 GB 存储、2 个活跃任务、1 个源码构建；超出时 API 返回 429。

## 远程部署（HTTPS / Caddy）

应用容器 `vllm/vllm-openai:latest` 只在实际 Docker 网络中监听 12888，不直接发布端口。OpenSandbox Server 以独立容器 `vibeforge-sandbox` 运行在同一内部网络，只有它挂载 `/var/run/docker.sock`，用于创建临时 Node 构建沙箱；它不发布 8080 到公网。Caddy `2.10.2-alpine` 负责：

- 在 `12888` 终止 HTTPS
- 在 `80` 仅提供 ACME HTTP-01 验证（不承载应用页面）
- 使用 Let's Encrypt `shortlived` 配置申请公网 IP 证书（约 6 天，自动续期）
- 将 SSE 请求反向代理到应用，`flush_interval -1`

```bash
cd vibeforge
./deploy_remote.sh root@117.148.166.55 12888
```

部署脚本会基于 `${VIBEFORGE_IMAGE:-vllm/vllm-openai:latest}` 构建 `vibeforge-app:latest`（安装 `requirements.txt`），生成 `/opt/vibeforge/.sandbox.env`（沙箱 API Key）与 `/opt/vibeforge/sandbox/config.toml`，并启动 `vibeforge-sandbox`。`/api/health` 会返回沙箱 `backend` 与 `reachable`。如果已有预装依赖的镜像，可设置 `VIBEFORGE_APP_IMAGE` 跳过本地构建。Caddy 同时暴露 `12889` 作为 SSR 应用 origin；请确认云安全组已放行该端口。

验证：

```bash
curl -I https://117.148.166.55:12888/
curl https://117.148.166.55:12888/api/health
```

证书和 ACME 账户保存在 Docker volume `vibeforge-caddy-data` 中，重建应用容器不会丢失。

注意：公网 IP 证书的续期需要 80 端口可达；如果只能暴露 12888，则需要改用你自己的域名 + DNS-01 验证，或接受自签名证书。

## 安全边界

- 自助注册 + SQLite 服务端会话；未认证访问页面会跳转登录，API/预览返回 401。
- 管理员可禁用用户、撤销会话；分享链接为只读 capability URL，可随时撤销；所有关键操作写入本地审计表。
- 每个项目强制 `owner_id`，所有 API、SSE、下载、预览和媒体都做所有权或项目能力 key 校验；跨用户统一返回 404。
- 所有 `/p/` 生成物响应带 `Content-Security-Policy: sandbox`，直接打开新窗口也不会获得主站同源权限。
- 产物只写入 `data/users/{uid}/projects/{pid}/workspace/`，所有文件工具做工作区路径校验。
- 预览 iframe 使用 sandbox，不开放 same-origin；生成页面不能读取主站 Cookie。
- 当前数据层已按用户隔离；React/Next 构建在独立 OpenSandbox 沙箱中执行，app 容器不持有 docker.sock。
- 沙箱默认拒绝出网，仅放行 npm registry；不注入平台密钥，构建结束销毁。
- Next SSR 运行时是单独沙箱，默认拒绝出网；`/apps/` 预览通过独立端口 `12889` 与平台 `12888` 隔离，Caddy 只在该端口暴露 `/apps/*`。仍需注意同主机 Cookie 可被生成应用覆盖（DoS）。
- 若要开放给不可信多用户并执行任意生成代码，建议把 Docker runtime 升级为 OpenSandbox Firecracker 或 ACS Agent Sandbox（MicroVM）。
