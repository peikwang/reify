# VibeForge 前端 React + TypeScript 化设计方案

> 状态：设计稿，未实施
> 范围：平台控制台 React 化、生成 React/Next 项目的 TypeScript 化；静态模板是否 React 化单独决策
> 实施分支建议：`feature/react-ts`，从 `feature/isolation` 当前 HEAD 拉出

## 1. 背景

当前项目里“React”出现在两个不同位置，不能混为一谈：

| 对象 | 当前实现 | 产物 |
|---|---|---|
| 平台控制台 | `web/index.html` + `web/app.js`（约 1500 行原生 JS）+ `web/app.css` | HTML 壳 + 浏览器 JS 动态渲染 |
| 平台登录页 | `web/login.html` | 独立静态页面 |
| 生成的 React 项目 | `server/templates/react_app.py`：Vite 6 + React 19 + JSX | `dist/` 静态 HTML/CSS/JS |
| 生成的 Next 项目 | `server/templates/next_app.py`：Next 15 App Router + JSX | `.next/standalone` + Node 运行时 |
| 静态模板/游戏 | `server/templates/*.py` 确定性模板 | 静态 HTML/CSS/JS，不经过 npm |

目标不是把“所有产物”都改成 React，而是把**工程化程度高的部分**统一到 Vite + React + TypeScript：

1. 平台控制台：Vite + React + TypeScript SPA。
2. 生成 React 项目：Vite + React + TypeScript（`.tsx`）。
3. 生成 Next 项目：Next + React + TypeScript（`.tsx`/`.ts`）。
4. 静态模板/游戏：保留当前轻量 HTML/CSS/JS 快速路径；是否新增 `react-game` 另行评估。

## 2. 目标与非目标

### 目标

- 平台 UI 组件化，去掉 `app.js` 的字符串拼 HTML 和全局 DOM 操作。
- 统一 TypeScript 类型：用户、项目、事件流、运行时、分享、管理员接口。
- React/Next 生成项目使用 TSX/TS，构建前做类型检查。
- API、认证、SSE、项目数据格式保持不变，迁移不影响已有项目。
- 保持现有视觉、动画、移动端布局和 12888/12889 部署方式。
- 每个阶段可独立验收、可回滚。
- 产品约束：技术栈对用户不可见。用户只选择模板或描述需求，Composer 不提供 STACK 选择器；非网站模板固定使用静态实现，网站由后端根据提示词自动选择静态/React/Next，沙箱不可用时自动回退静态。
- 模板库固定为 7 个模板：小游戏、网站、图片、视频制作、简历、旅游攻略、编程。每个模板有独立插图和提示词，位于聊天框外；点击模板后把提示词填入单一通用 Composer。
- 新生成的静态/React 项目自动获得不可猜的 `/s/<token>/` 免登录只读公开链接；Next 应用运行时的公开链接需要单独的 12889 token 方案。
- 用户可见的运行时文案统一使用“应用运行时 / APP RUNNING”，不暴露 SSR、React、Next 等技术栈术语。

### 非目标

- 不把平台控制台改成 Next SSR；它是登录后的控制台，不需要 SEO 和服务端拼 HTML。
- 不把图片/视频画廊强行改成 React。
- 不在本期把游戏、简历、攻略等全部静态模板改成 React；这会显著增加构建时间和资源消耗。
- 不引入 ACS/MicroVM（当前无 ACK 集群，继续 Docker）。

## 3. 目标架构

```text
Browser
  ├─ 12888 平台：Caddy → FastAPI
  │    ├─ /                 React SPA（Vite build → web/dist）
  │    ├─ /projects/:id     React Router 页面
  │    ├─ /admin            React Router 页面（管理员）
  │    ├─ /login            React 登录/注册路由
  │    ├─ /api/**           FastAPI（JSON + SSE）
  │    ├─ /p/**             静态/React 产物
  │    └─ /media/**         媒体 capability URL
  └─ 12889 SSR 网关：Caddy → FastAPI /apps/{id} → Next 运行时沙箱
```

平台控制台是静态 SPA：生产环境只由 FastAPI/Caddy 服务 `web/dist` 的 HTML/CSS/JS，不需要 Node 进程。Node 只在构建镜像时使用。

## 4. 平台控制台设计

### 4.1 目录结构

```text
frontend/
  package.json
  vite.config.ts
  tsconfig.json
  tsconfig.node.json
  index.html
  src/
    main.tsx
    App.tsx
    router.tsx
    api/
      client.ts          # fetch 封装、401 跳登录、JSON 错误
      types.ts           # User/Task/TaskEvent/Capabilities/Runtime
    auth/
      AuthProvider.tsx
      ProtectedRoute.tsx
      LoginPage.tsx      # 登录 + 注册
    layout/
      AppShell.tsx       # 顶部导航、模式切换、Toast、连接状态
    pages/
      HomePage.tsx
      ProjectsPage.tsx
      ProjectPage.tsx
      AdminPage.tsx
    features/
      composer/          # 模板画廊、插图、通用提示词输入
      projects/          # 项目卡片、筛选、统计（实现目录名 project-library）
      workspace/
        AgentFlow.tsx    # 计划步骤、时间线、重播
        CodingPane.tsx   # 文件树、Diff、终端
        DailyOutput.tsx  # 预览 iframe、验收清单
        RefineBar.tsx
        RuntimePanel.tsx # SSR 启动/停止、预览
        ShareButton.tsx
      admin/
        UserTable.tsx
        AuditList.tsx
    hooks/
      useTaskStream.ts   # EventSource 生命周期
      useCapabilities.ts
    styles/
      tokens.css
      app.css
```

构建输出：

```text
web/dist/
  index.html
  assets/index-<hash>.js
  assets/index-<hash>.css
```

`web/` 旧文件在迁移完成前保留，通过开关切换；切换完成后删除旧 `app.js`/`app.css`/`index.html`。

### 4.2 路由

```text
/                  HomePage
/projects          ProjectsPage
/projects/:id      ProjectPage
/admin             AdminPage（仅 admin）
/login             LoginPage（已登录跳回 next）
*                  NotFound → /
```

路由使用 React Router；浏览器前进/后退与当前原生路由行为保持一致。

### 4.3 认证

- 继续使用 HttpOnly Cookie，不引入 token 存储。
- `AuthProvider` 启动时请求 `/api/auth/me`，保存当前用户与 `role`。
- 401 统一跳 `/login?next=...`；`next` 仍做同源、`//`、反斜杠、控制字符校验。
- 登录/注册页面复用现有 UI 视觉；注册成功自动登录。
- 管理员路由和导航入口根据 `user.role` 显示；后端仍然是最终权限边界。

### 4.4 API 与类型

`api/client.ts`：

```ts
async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (response.status === 401) {
    location.replace("/login?next=" + encodeURIComponent(location.pathname + location.search));
  }
  if (!response.ok) throw new ApiError(...);
  return response.json();
}
```

核心类型：

```ts
type Stack = "static" | "react" | "next";
type TaskStatus = "queued" | "running" | "deploying" | "done" | "error" | "interrupted";

interface Task {
  id: string;
  prompt: string;
  capability: string;
  stack: Stack;
  status: TaskStatus;
  title: string;
  revision: number;
  result: Record<string, unknown> | null;
  share_url: string | null;
}

type TaskEvent =
  | { type: "task_started"; ... }
  | { type: "plan"; steps: string[]; ... }
  | { type: "step_started" | "step_done"; index: number; ... }
  | { type: "file_diff"; path: string; before: string; after: string; ... }
  | { type: "build_log"; line: string }
  | { type: "runtime_ready"; url: string | null; ... }
  | { type: "done" | "error" | "interrupted"; ... };
```

事件类型集中定义，避免页面里出现 `any`。API 字段以现有后端为准，前端类型只做描述，不改后端契约。

`Stack` 仅作为任务元数据保留在 `Task` 中；创建请求只发送 `{prompt, capability}`，不发送也不展示技术栈选择。

### 4.5 SSE 状态机

`useTaskStream(taskId, lastSeq)` 负责：

- 创建 `EventSource("/api/projects/{id}/events?after=" + lastSeq)`。
- `onopen`：连接状态 `STREAMING`。
- `onmessage`：按 `seq` 去重后追加事件，并调用 reducer/处理函数。
- `done` / `error`：关闭连接，设置 `streamClosed=true`，不自动重连。
- `interrupted`：显示中断状态，关闭连接。
- `onerror`：任务仍在运行时延迟重连；401 跳登录。
- 组件卸载/切换项目时关闭旧连接。
- `after` 游标与 `lastSeq` 必须与当前原生实现一致，避免重复回放。

### 4.6 状态管理

- 项目页使用 `useReducer` 管理 `task/events/files/diffs/checks/plan/timeline`。
- 跨页面只保留轻量 Context：当前用户、Toast、连接状态。
- 不引入 Redux/Zustand/TanStack Query；当前数据规模很小，React 内建状态足够。
- 文件 Diff 继续使用现有逐行算法，迁移为纯函数并加单元测试。

### 4.7 视觉与动画

- 保留现有 CSS 变量、版式、响应式和动画；不做无收益的 UI 改版。
- 组件使用局部 CSS 或统一 `app.css`，不引入 UI 组件库。
- 时间线、步骤卡、打字机效果、`prefers-reduced-motion` 行为保持。
- iframe 预览继续使用现有 `/p`、`/apps`、`/media` URL 规则；不把生成页面 HTML 注入 React DOM。
- Composer 只展示模板与提示词，不展示 STACK/React/Next 选项；项目卡片只展示能力标签（GAME/WEB/CV 等）。

### 4.8 构建与部署

开发：

```bash
cd frontend
npm install
npm run dev        # Vite dev server，代理 /api /p /media /apps 到 FastAPI
```

生产：

```bash
npm ci
npm run typecheck  # tsc --noEmit
npm run build      # vite build --outDir ../web/dist
```

FastAPI 修改：

- `web/dist/index.html` 作为 `/`、`/projects/*`、`/admin` 的入口。
- `/assets/*` 使用静态文件服务。
- 对非 `/api`、非 `/p`、非 `/media`、非 `/apps` 的导航路径做 SPA fallback。
- `/login` 可先继续使用旧静态页，React 登录页完成后切换。

Docker：

- `Dockerfile.app` 增加 `node:24-slim` 构建阶段，执行 `npm ci && npm run typecheck && npm run build`，把 `web/dist` 复制到最终镜像。
- 最终镜像仍然只运行 Python/FastAPI；Node 不进入运行时。
- 如果新机器不想用 21.5GB 的 `vllm/vllm-openai` 作为 app 基座，可改为 `python:3.12-slim`，前端构建阶段独立。

### 4.9 迁移开关

迁移期间加一个临时配置：

```text
VIBEFORGE_UI=legacy | react
```

- `legacy` 继续服务旧 `web/index.html`。
- `react` 服务 `web/dist`。
- 全部页面验收通过后删除开关和旧文件，不保留兼容分支。

## 5. 生成 React 项目改成 Vite + React + TypeScript

当前 `server/templates/react_app.py` 生成 `.jsx`。目标：

```text
package.json
package-lock.json
vite.config.ts
tsconfig.json
tsconfig.node.json
index.html
src/main.tsx
src/App.tsx
src/styles.css
src/vite-env.d.ts
```

`package.json` 增加：

```json
{
  "devDependencies": {
    "typescript": "^5.7",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "@vitejs/plugin-react": "...",
    "vite": "..."
  },
  "scripts": {
    "typecheck": "tsc --noEmit",
    "build": "tsc --noEmit && vite build"
  }
}
```

实现要点：

- `build_files()` 生成 TSX 字符串；brief 字段仍然通过模板插值，不把用户输入拼成可执行 TS。
- `src/App.tsx` 的 props/状态使用显式类型；不引入 `any`。
- `vite.config.ts` 继续 `base: "./"`，产物仍然是 `dist/index.html` + hashed JS/CSS。
- 构建沙箱执行 `npm ci` + `npm run build`；`tsc --noEmit` 失败时输出类型错误并标记构建失败。
- `react_checks_files` 增加：`tsconfig.json`、`src/App.tsx`、类型检查通过、产物 JS/CSS。
- LLM refine 目标从 `src/App.jsx` 改为 `src/App.tsx`；prompt 明确“TypeScript/TSX、保留类型和导入”；patch 仍要求唯一锚点。
- 构建内存：默认 2Gi；当前 55 机器统一给 4Gi 上限也不影响；耗时预计增加 1~3s。
- 产物格式不变，发布、分享、asset key、CSP 全部不受影响。

## 6. 生成 Next 项目改成 Next + TypeScript

目标文件：

```text
next.config.mjs (或 next.config.ts)
tsconfig.json
next-env.d.ts
app/layout.tsx
app/page.tsx
app/NoteBoard.tsx
app/api/notes/route.ts
app/globals.css
```

实现要点：

- `next build` 默认会做 TypeScript 检查；如果类型错误，构建直接失败，不部署。
- `app/api/notes/route.ts` 使用显式 Request/Response 类型。
- `next.config.mjs` 保持 `output: "standalone"`、`basePath: "/apps/{id}"`、`images.unoptimized`。
- 构建沙箱保持 4Gi（当前 55 机器已验证；1~2Gi 会 OOM）。
- LLM refine 目标为 `app/page.tsx`；patch 锚点、重建、蓝绿运行时逻辑不变。
- standalone 产物结构仍是 `server.js` + `.next` + `node_modules`，运行时沙箱和 `/data` 卷不变。

## 7. 静态模板与游戏

建议保留：

- 小游戏、简历、旅游攻略、编程演示继续走确定性模板，秒级生成，不启动 Node 构建。
- 图片/视频继续走静态画廊/播放器，不引入 React。

如果后续确实要“所有生成物都是 React”：

- 新增 `react-game` / `react-resume` 等 stack，而不是替换现有静态路径。
- 每个项目都需要 `npm ci + vite build`，构建沙箱 2Gi、10~20 秒；2C4G 机器无法稳定承载。
- 游戏逻辑可以放在 React 组件内继续用 Canvas，但收益主要是统一工程，不是玩法能力。

## 8. API 契约

平台 React 化和生成项目 TS 化都不改 API 路径和数据结构。需要保持：

- `POST /api/auth/register|login|logout`
- `GET /api/auth/me`
- `GET /api/projects`、`POST /api/projects`
- `GET /api/projects/{id}`、`/events`
- `POST /api/projects/{id}/refine|deploy|share`
- `GET|POST /api/projects/{id}/runtime[/start|/stop]`
- `GET /api/admin/users|audit`
- `/p/{id}/`、`/s/{token}/`、`/media/{id}/...?k=`
- 新生成的静态/React 项目自动签发 `/s/{token}/`，持有链接的人无需登录即可只读访问；Next 暂不签发。
- `/apps/{id}/`（12889）

## 9. 安全边界

- 平台控制台是可信代码；生成项目是不可信内容，二者不能共享 bundle、不能共享 origin。
- React 平台页面不使用 `dangerouslySetInnerHTML` 渲染生成内容；Diff/日志一律作为文本节点。
- 生成页面继续在 iframe + CSP `sandbox` 中运行；不把生成 HTML 插入平台 DOM。
- `/apps` 仍在 12889 独立 origin；平台 12888 屏蔽 `/apps/*`。
- 登录 Cookie、CSRF/Origin、项目 owner 校验、分享撤销、管理员权限全部由后端继续兜底。
- 公开链接使用高熵 token，不对外列举，可撤销；生成页面仍在 CSP `sandbox` 中运行，不与平台共享执行上下文。Next 公开访问需要独立的 12889 token 路由，不在本期复用平台会话。
- TypeScript 只是开发期约束，不是运行时安全边界。

## 10. 资源与部署影响

| 项目 | 构建 | 运行时 |
|---|---|---|
| 平台 SPA | Docker 构建阶段 Node，一次构建 | 只有 Python/FastAPI |
| 生成 React TS | 临时沙箱，2Gi 上限，约 10~20s | 静态文件，无 Node |
| 生成 Next TS | 临时沙箱，4Gi 上限，约 60s | Node 沙箱 1Gi，空闲停止 |
| 静态模板/游戏 | 无 Node | 静态文件 |

- 2C4G 机器：平台 + 静态可用；React TS 单并发勉强；Next 构建不可行。
- 前端构建放在 Docker 多阶段构建，避免生产容器常驻 Node。
- `web/dist` 不手工提交；由构建产物生成。

## 11. 实施阶段

### Phase 0 — 脚手架与并行预览

- 新建 `frontend/`，Vite + React + TS + Router。
- 保留旧 UI；新增 `VIBEFORGE_UI=react` 预览入口。
- 完成登录、导航、空状态；验收：可在同源下打开 React 页面并登录。

### Phase 1 — 首页与项目库

- 通用 Composer、模板画廊、最近项目、项目卡片、筛选、统计。
- 创建请求只发送 `{prompt, capability}`；技术栈由后端自动路由，前端不提供选择器。
- 验收：创建静态项目后项目库正确刷新；提示词驱动的 React/Next 自动路由在后端合并后验收；移动端布局一致。

### Phase 1.5 — 模板画廊与免登录公开链接

- 模板合并为 7 个：移除“适配制作”，把“视频”更名为“视频制作”。
- 每个模板有独立插图和提示词；模板画廊位于聊天框外，点击后填入单一通用 Composer，Composer 不显示模板 tab 或 STACK。
- 新生成的静态/React 项目自动获得 `/s/<token>/` 免登录只读公开链接；项目库显示公开页入口、复制链接和创建成功提示。
- 验收：点击模板正确填入提示词；公开链接在无 Cookie 下返回 200，撤销后 404；Next 公开链接留待应用运行时阶段。

### Phase 2 — 项目页只读 + SSE

- `useTaskStream`、计划步骤、时间线、状态、预览 iframe。
- 验收：大文件事件流不丢 seq；刷新/重连不重复；完成后关闭连接；401 跳登录。

### Phase 3 — 编程模式

- 文件树、Diff、终端、构建日志、事件回放。
- 验收：React/Next 构建日志逐行出现；Diff 与当前实现一致；重播不产生重复事件。

### Phase 4 — 操作与管理员

- Refine、Deploy、Share、Runtime start/stop、项目导出。
- 管理员用户表、禁用/下线、审计。
- 验收：所有操作与现有 API 对齐；管理员权限和跨用户 404 不变。

### Phase 5 — 生成项目 TS 化

- `react-ts` 脚手架、lockfile、typecheck、validate、refine 目标 `.tsx`。
- `next-ts` 脚手架、`route.ts`、build、refine 目标 `.tsx`。
- 验收：本地 mock LLM + 远端真实 LLM 各跑一遍创建与修改；`dist`/standalone 产物不变。

### Phase 6 — 切流与清理

- 全量 E2E 通过后默认 `VIBEFORGE_UI=react`。
- 删除旧 `web/index.html`、`web/app.js`、`web/app.css`（以及旧登录页，若已迁移）。
- 更新 README、部署脚本、测试文档。
- 验收：刷新任意 `/projects/:id` 不 404；旧链接可用；Caddy 配置不变。

## 12. 测试矩阵

- 单元/组件：Vitest + React Testing Library；Diff 算法、URL 校验、事件 reducer。
- 模板库：7 个模板、独立插图、点击填入通用输入框。
- 公开链接：静态/React 新项目自动签发；无 Cookie 200、撤销后 404；Next 不签发。
- SSE：模拟 EventSource，覆盖 open/message/error/done/interrupted/401。
- E2E：Playwright 复用现有真实链路：
  - 注册/登录/退出
  - 创建静态、React TS、Next TS
  - 项目列表刷新
  - 编程模式 Diff/终端
  - Refine（mock LLM 和真实 LLM 各一次）
  - SSR 运行时启动/停止、12889 预览、数据持久化
  - 分享创建/撤销
  - 管理员禁用/下线
- 构建检查：`npm ci && npm run typecheck && npm run build`。
- 视觉检查：桌面 + 390px 手机宽度；首屏动画、滚动、iframe 预览。

## 13. 风险与回滚

| 风险 | 处理 |
|---|---|
| SSE 断线/重连重复事件 | 独立 hook + seq 去重测试；保留旧 UI 直至验收 |
| 动画/移动端回归 | 保留 CSS，不引入 UI 库；逐页对比 |
| 前端构建拖慢部署 | Docker 多阶段 + npm cache；构建失败不替换旧产物 |
| TS 类型错误阻断生成 | `tsc --noEmit` 明确报告；LLM refine 失败保留旧版本 |
| Next 构建 OOM | 4Gi 沙箱；限制并发；2C4G 不启用 Next |
| 迁移期间双入口混乱 | `VIBEFORGE_UI` 开关；切流后删除旧代码 |

回滚：保留 `feature/isolation` 的旧 UI 产物和 `VIBEFORGE_UI=legacy`；任何阶段失败可切回旧入口，不改数据库/API。

## 14. 文件改动清单（预估）

| 文件/模块 | 改动 |
|---|---|
| `frontend/`（新） | Vite + React + TS 平台 UI |
| `server/main.py` | 服务 `web/dist`、SPA fallback、UI 开关 |
| `Dockerfile.app` | Node 构建阶段，复制 `web/dist` |
| `deploy_remote.sh` | 前端构建/缓存、必要时 app 基座切换 |
| `server/templates/react_app.py` | JSX → TSX、tsconfig、typecheck |
| `server/templates/next_app.py` | JSX/JS → TSX/TS、tsconfig |
| `server/sandbox.py` | 构建命令/内存/校验适配 |
| `server/agent.py` | refine 目标 `.tsx`、校验 |
| `tests/` | Vitest/RTL、Playwright、构建 smoke |
| `README.md` / docs | 技术栈、构建、部署说明 |

## 15. 开放决策

1. 平台 UI 组件库：建议不用，沿用现有 CSS。
2. 状态管理：建议 `useReducer` + Context，不引入 Redux/Zustand。
3. 平台登录页：建议一并 React 化；迁移期可先保留旧登录页。
4. 静态模板：默认保留；是否新增 `react-game` 等按需求另开议题。
5. 包管理器：npm + lockfile（与当前 sandbox 一致），不引入 pnpm/yarn。
6. 分支：`feature/react-ts` 从 `feature/isolation` 拉出；每阶段一个 commit，全部通过后再合并。
7. 技术栈选择：不暴露给用户；后端 `resolve_stack` 自动路由（在 `feature/isolation` 实现），前端只传 `{prompt, capability}`。
8. 模板数量：固定 7 个；适配制作不进入模板库，历史数据仍可渲染和筛选。
9. 公开链接：默认免登录只读，自动签发、可撤销；不做 magic link 自动登录。Next 公开链接另行设计 12889 token。

## 16. 验收定义

完成标准：

- 平台所有页面由 React Router 驱动，旧 `app.js` 不再被引用。
- 平台构建产物只有 `web/dist`，运行时无 Node。
- 生成 React/Next 项目源码为 TSX/TS，构建前类型检查通过。
- 已有静态模板、图片/视频、分享、管理员、SSR 12889 全部回归通过。
- 模板库为 7 个且有独立插图；Composer 不暴露模板 tab 或 STACK。
- 新生成的静态/React 项目有无需登录的公开链接；Next 公开链接待应用运行时阶段。
- 2C4G 的部署限制在 README 中写明；Next 构建仍要求 4Gi 沙箱。
- 远端真实 LLM E2E 至少覆盖：React 创建/修改、Next 创建/修改、SSR 运行时与 12889 预览。
