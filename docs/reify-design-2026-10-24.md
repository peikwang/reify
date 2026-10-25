# Reify 产品与架构设计（2026-10-24）

> 品牌：Reify（原 VibeForge）。
> 当前线上：55 使用 `/data/reify-deploy`、`reify` / `reify-caddy` / `reify-sandbox`、`reify-net`、`REIFY_*`、`data/reify.db`；旧 VibeForge 容器/网络已清理。
> 代码：`reify` 分支已完成品牌、7 模板与通用生成；本次合并到 `main`，并把完整仓库同步到 `/data/reify-deploy/repo`。
> 系统架构的权威说明见 [架构设计文档](架构设计文档.md)；本文保留产品视角与演进背景，历史 `vibeforge` 路径只用于回溯。

---

## 0. 一句话总结

Reify（原 VibeForge）正在从“单用户设计 Agent Demo”升级为“**多用户隔离的单机 Agent 创作平台**”：生成链路是“确定性优先 + 内置模板 + 通用生成兜底”，真正新增的是身份、数据、执行、运行时、发布五层底座。

产品的主线不是让 Agent 更聪明，而是让平台更可用：**让多个用户各自生成、构建、运行、发布，而互不越界。**

---

## 一、产品思路

### 1.1 产品定位

Reify 的定位是“**一句话，把想法变成现实**”（One sentence. Made real.）：

- 用户用一句话描述想法；
- 系统完成理解、模板命中或通用生成、自检、构建和发布；
- 最终交付一个可以直接访问、可以直接使用的页面或应用。

当前固定 7 个模板：小游戏、网站、图片、视频制作、简历、旅游攻略、编程。适配制作已移除；历史 adapt 项目仍可渲染和筛选。

所有静态能力采用“**内置模板 + 通用生成**”：先命中内置模板，未命中再走受约束的通用生成；生成结果必须通过结构、移动端、离网依赖、交互/打印/语法检查，首次失败修复一次，仍失败回退内置模板。图片/视频本身由提示词驱动的模型生成，内置模板只负责画廊/播放器。

### 1.2 用户旅程

```text
一句话描述
  → 模板选择（聊天框外的插图画廊，可选）
  → 意图路由 / 技术栈自动选择（对用户不可见）
  → 创意 brief
  → 内置模板命中或通用生成
  → 构建（static / React / Next，按需）
  → 发布（/p/、/s/、/apps/）
  → 对话式二次修改
```

模板选择在聊天框外；Composer 是唯一输入，不显示模板 tab/chip 或 STACK/React/Next。技术栈由 `server/stacks.py` 自动路由，用户不需要理解 React/Next。

### 1.3 双模式

- **日常模式**：看结果。预览、验收清单、部署状态。
- **编程模式**：看过程。文件树、逐行 Diff、终端日志、实时预览。
- 两种模式共用同一条 SSE 事件流，不重跑 Agent。

### 1.4 生成原则：确定性优先 + 通用生成兜底

当前生成层不是 MetaGPT 式的多 Agent，也不是 OpenManus 式的通用工具调用 Agent，而是“**确定性优先 + 内置模板 + 通用生成兜底 + 多个受控 LLM 介入点**”：

| 环节 | 由谁负责 | 说明 |
|---|---|---|
| 意图路由 | 规则 / capability | 选择能力类型和技术栈（技术栈对用户不可见） |
| 模板命中 | 内置模板 | 游戏题材、网站模板、经典简历、城市攻略、快速排序等 |
| 通用生成 | LLM + 规则 | 未命中模板时长尾生成；受 spec / 结构约束 |
| 创意方向 | LLM | 标题、语气、视觉调性、强调色 |
| 构建 | 沙箱 | React 或 Next 的真实构建 |
| 自检 | 规则 | 结构、移动端、离网依赖、交互/打印/语法 |
| 修复/回退 | LLM + 规则 | 首次失败带问题修复一次；仍失败回退内置模板 |
| 二次修改 | LLM + 规则 | 唯一锚点 patch，失败回滚 |

这样做的收益是**交付稳定、成本低、坏页面不会直接交给用户**；代价是**生成自由度受模板与自检约束**。Reify 不是“只换文案的假模板”，而是内置模板保底、通用生成兜底。

小游戏先命中内置引擎（贪吃蛇、俄罗斯方块、飞机大战、打砖块），其他玩法按 GameSpec 生成单文件 Canvas 游戏；网站、简历、攻略、编程也各有内置模板与长尾生成路径。

### 1.5 平台 UI 与自动技术栈

平台自己的工作台 UI 是固定的 **React + TypeScript + Vite** 应用：源码在 `frontend/`，构建到 `web/dist`，由 FastAPI 同源托管；它不是按项目生成的产物。

用户生成项目支持三种 stack，但**技术栈对用户不可见**：

| Stack | 源码 | 构建 | 产物 | 访问方式 | 常驻 Node 运行时 |
|---|---|---|---|---|---|
| `static` | 模板直接渲染 | 无 | `index.html` + 资源 | `/p/{id}/` | 无 |
| `react` | Vite + React + TypeScript | 沙箱内 `npm run build` | `dist/` 静态文件 | `/p/{id}/` | 无，Node 只参与构建 |
| `next` | Next.js App Router + TypeScript | 沙箱内 `next build` | `.next/standalone` | `/apps/{id}/`（12889） | 有，独立 Node 沙箱 |

自动路由规则：

- 非网站能力 → `static`；
- 公司/工作室/产品官网 → `static`；
- 个人网站/作品集/博客 → `react`（沙箱可用时）；
- 明确 React/Vite → `react`；
- 明确 Next/SSR → `next`；
- 沙箱不可用 → `static`；显式 API 指定源码且沙箱不可用 → 503。

Next 是高级旁路：需要 4Gi 构建沙箱、独立 12889 origin、运行时蓝绿切换；当前 7 模板都是展示型，不应默认 Next。

> **关键区分**：平台 UI 的 React、用户生成项目的 React、Next 的 Node 运行时是三件不同的事。平台 UI 是固定的 Vite 应用；生成项目的 React 只做静态构建；只有 Next SSR 有常驻 Node 运行时。

> 运行时状态文案统一“应用运行时 / APP RUNNING”，不向用户暴露 SSR/React/Next。静态/React 项目自动签发 `/s/<token>/` 只读公开链接，可撤销；Next 公开链接仍待 12889 token 方案。

---

## 二、架构设计

### 2.1 总览

![Reify 当前运行架构](diagrams/reify-architecture.svg)

> 图 1：Reify 当前运行架构。可编辑源：[reify-architecture.html](diagrams/reify-architecture.html)；矢量图：[reify-architecture.svg](diagrams/reify-architecture.svg)。每项目独立轻量沙箱的目标图见 [reify-sandbox-deployment.svg](diagrams/reify-sandbox-deployment.svg)。

### 2.2 前后端是怎么分离的

准确说法是：**逻辑分离、物理同源**。

| 维度 | 当前做法 | 说明 |
|---|---|---|
| 代码层 | `frontend/` 是前端，`server/` 是后端 | 前端只依赖 REST/SSE，不直接碰数据库 |
| 部署层 | 同一个 FastAPI 容器 | 没有独立前端服务；`web/dist` 由 FastAPI 托管 |
| 通信 | REST `/api/*` + SSE 事件流 | 前端消费 JSON 和事件 |
| 鉴权 | 服务端 Session + HttpOnly Cookie | 写请求做 Origin 校验，跨用户统一 404 |
| 前端构建 | React + TypeScript + Vite | `frontend/` 构建到 `web/dist`，随应用发布 |
| 发布 | 前后端随同一个应用发布 | 没有独立前端版本和 CDN 链路 |

为什么这样设计：

- 单机部署简单，不需要额外的前端服务器；
- 同源 Cookie、SSE 不需要处理 CORS；
- 调试链路短，前端改动可以随应用一起验证。

代价是前后端一起伸缩，前端没有独立发布能力。如果以后要“真分离”，第一步是把 `frontend/` 的构建产物 `web/dist` 抽到 Caddy/CDN 或独立静态站点，API 保持 REST + SSE，而不是先拆微服务。

### 2.3 请求与发布拓扑

```text
浏览器
  → Caddy :12888（平台 UI / API / SSE）
  → FastAPI（鉴权、项目 API、Agent 流水线、沙箱/运行时调度）
  → SQLite / 用户项目目录

浏览器
  → Caddy :12889（只暴露 /apps/*）
  → FastAPI /apps/*（owner 校验 + 反向代理）
  → Next 运行时沙箱 :3000
```

平台 UI 的构建链路：

```text
frontend/ (React + TypeScript)
  → vite build
  → web/dist
  → FastAPI 同源托管
```

关键约束：

- 平台 `:12888` 主动屏蔽 `/apps/*`；
- SSR `:12889` 只暴露 `/apps/*`；
- 静态产物走 `/p/{id}/`，只允许 owner；
- 只读分享走 `/s/{token}/`，目前只支持静态/React；
- 媒体资产走 `/media/{id}/...?k=asset_key` 能力 URL。

> **当前限制**：当前只有 IP，没有域名。`:12889` 只是端口级隔离，不是设计稿里的“每项目子域名 origin”。同主机 Cookie 仍可能被生成应用覆盖，造成登出类 DoS；真正的子域名隔离要等 Runtime Gateway。

### 2.4 数据与持久化

数据分为两层：

| 层 | 内容 | 位置 |
|---|---|---|
| 索引/状态 | 用户、会话、项目、运行时、审计 | `data/reify.db`（SQLite WAL；历史 `vibeforge.db` 由迁移脚本接管） |
| 文件/产物 | 源码、事件、构建产物、运行时数据 | `data/users/{uid}/projects/{pid}/` |

目录结构：

```text
data/
  reify.db
  users/{uid}/projects/{pid}/
    meta.json
    events.jsonl
    workspace/          # 源码与静态产物
    workspace/dist/     # React 构建产物
    workspace/runtime/  # Next standalone 产物
    runtime-data/       # Next 运行时持久化卷
```

持久化的收益：

- 服务重启后账号、登录态、项目和修订可恢复；
- 运行时记录可追踪，空闲可回收；
- 项目归属和配额有数据库依据；
- 管理员可做用户管理、会话撤销和审计。

### 2.5 沙箱设计

#### 2.5.1 控制面

- 独立部署 **OpenSandbox Server**（Docker runtime）；
- **只有 OpenSandbox Server 持有 `docker.sock`**，app 容器不持有；
- app 通过内部 API 调用沙箱控制面，不直接操作 Docker。

#### 2.5.2 构建沙箱

- 镜像：`node:24-bookworm-slim`；
- 资源：默认 1 CPU / 2 GiB，55 机器 Next 构建使用 4 GiB；
- 命令：`npm ci --ignore-scripts`（或 `npm install --ignore-scripts`）→ `npm run build`；
- 出网：设计默认 allowlist（npm registry）；**55 机器因 egress sidecar 无法启动，当前部署实际使用 `open`**；
- TTL：默认 15 分钟，构建结束立即销毁；
- 产物：React 打包 `dist/`，Next 打包 `.next/standalone`，通过 tar + base64 回传，原子安装到项目目录。

#### 2.5.3 运行时沙箱

- 只用于 Next SSR；
- 镜像：`node:24-bookworm-slim`；
- 启动：`PORT=3000 HOSTNAME=0.0.0.0 node server.js`；
- 资源：1 CPU / 1 GiB；
- 网络：默认无出网；
- 数据：host bind 项目 `runtime-data/` 到沙箱 `/data`；
- 生命周期：健康检查通过后 `running`，空闲 10 分钟停止；Docker runtime 是冷停止/冷启动，不是 MicroVM pause/resume；
- 二次修改：先起新运行时并通过健康检查，再停旧运行时，实现蓝绿切换；失败保留旧版本。

#### 2.5.4 React 与 Next 的分工

| 能力 | React | Next |
|---|---|---|
| 构建沙箱 | 需要 | 需要 |
| 构建命令 | `vite build` | `next build` |
| 产物 | `dist/` 静态文件 | `.next/standalone` |
| 运行时沙箱 | 不需要 | 需要 |
| 访问 | `/p/{id}/` 静态路由 | `/apps/{id}/` 反代到 Node |
| 适用 | 纯前端站点 | 需要服务端接口/SSR 的全栈应用 |

> 平台 UI 的 React 与生成项目的 React 是两套代码：前者是 `frontend/` 固定工作台，后者是 `workspace/` 里按模板生成的项目。不要把两者混为一谈。

> 演进方向：每个项目（包括静态/React）都将独立部署在一个最轻量沙箱中，由 Runtime Gateway 按项目 origin 路由。设计、边界与迁移路径见 [架构设计文档 §5](架构设计文档.md)；目标拓扑见 [reify-sandbox-deployment.svg](diagrams/reify-sandbox-deployment.svg)。

### 2.6 隔离模型

| 层 | 目标 | 当前手段 |
|---|---|---|
| L0 身份 | 每个请求知道“是谁” | 自助注册、scrypt、服务端 Session、Origin 校验 |
| L1 数据 | 只触达自己的项目 | 每用户目录、DB owner 索引、统一鉴权 |
| L2 执行 | 不可信代码不碰主机/密钥/其他项目 | 独立构建沙箱、非 root、资源限额、不注入平台密钥 |
| L3 运行时 | 全栈应用独立进程与网络 | 每项目运行时沙箱、独立端口、独立数据卷、空闲停止 |
| L4 发布 | 可访问但不越权 | owner-only、capability URL、可撤销分享、SSR 独立端口 |

### 2.7 配额、审计与运营

当前已落地：

- 每用户 50 个项目；
- 每用户 1 GB 存储；
- 每用户 2 个并发任务；
- 每用户 1 个源码构建；
- 审计日志：注册/登录、项目创建/修改/部署、运行时启停、分享、管理员操作；
- 管理员：用户列表、项目数、存储占用、禁用/启用账号、撤销全部会话。

尚未强制：

- 每用户/全局活跃运行时配额（设计稿有，代码尚未强制）；
- 存储清理策略；
- Next SSR 分享。

---

## 三、当前边界

| 边界 | 现状 | 影响 |
|---|---|---|
| 域名 | 只有 IP，没有域名 | SSR 只能用 `:12889` 端口隔离，不是真正的子域名 origin |
| SSR 隔离 | 同主机不同端口 | Cookie 不按端口隔离，仍有覆盖/DoS 风险 |
| 沙箱隔离 | Docker 容器级 | 弱于 MicroVM；运行时休眠是冷停止，不是 pause/resume |
| 出网策略 | 代码支持 allowlist；55 实际 `open` | 线上 `REIFY_SANDBOX_EGRESS=open`；构建沙箱没有网络白名单，是下一步安全项 |
| 运行时配额 | 设计有，代码未强制 | 大量运行时可能耗尽主机资源 |
| 生成自由度 | 内置模板 + 通用生成 | 长尾生成受 spec/自检约束；Next 仍是高级旁路 |
| 修复闭环 | 通用生成有一轮修复 + 回退 | 跨阶段 Inspector → Builder 自动修复仍未做 |
| 分享 | 静态/React 自动签发 `/s/<token>/` | Next 公开链接仍待 12889 token 方案 |
| 品牌/部署命名 | Reify：`/data/reify-deploy` + `reify` / `reify-caddy` / `reify-sandbox` + `reify-net` + `REIFY_*` | 旧 VibeForge 容器/网络已清理 |
| 线上版本 | 55 已迁移到 Reify（7 模板 + 通用生成） | 本文与 repo 同步 |
| 55 Git | 部署目录 `/data/reify-deploy` 本身无 `.git`；完整仓库同步到 `/data/reify-deploy/repo` | 直接改运行目录仍无回滚；应优先在 repo 目录修改 |

---

## 四、下一步计划

### P0：先补齐“能安全给别人用”的基础

1. **域名 + 泛解析 + Runtime Gateway**
   把 SSR 从 `:12889` 端口预览升级为 `p-{id}.apps.example.com`。这是设计稿里的硬前提，也是 SSR 公网访问、分享和真正 origin 隔离的前提。

2. **沙箱出网收口**
   修复 OpenSandbox egress sidecar，恢复 allowlist：构建沙箱只放行 npm registry，运行时沙箱保持默认无出网。线上 `REIFY_SANDBOX_EGRESS=open` 是临时方案。

3. **运行时治理**
   强制每用户/全局活跃运行时配额；补齐空闲回收、存储清理、构建失败重试和运行时崩溃恢复。

4. **55 的 Git 基线（已完成）**
   `feature/isolation`、`feature/react-ts` 与 `reify` 已合并到 `main`；完整仓库（含 `.git`）同步到 `/data/reify-deploy/repo`（容器 `/app/repo`），55 上的 Agent 可以直接改、可以回滚。

5. **Reify 部署迁移（已完成 2026-10-24 20:30）**
   已完成 `REIFY_*`、`/data/reify-deploy`、`reify` / `reify-caddy` / `reify-sandbox`、`reify-net`、`data/reify.db` 迁移；旧 VibeForge 容器/网络已清理。剩余：公网域名/子域名网关、egress allowlist、运行时配额。

### P1：把“生成—构建—运行—分享”闭环做顺

5. **Next SSR 分享**：补齐分享网关和 token 校验。
6. **构建/运行时可观测性**：结构化日志、状态面板、失败原因归类。
7. **前端发布解耦（可选）**：把 `frontend/` 的构建产物 `web/dist` 抽成独立静态站点，API 保持 REST/SSE；先解决缓存和版本，不急着拆微服务。
8. **部署即项目**：为每次生成记录 deployment id、revision、健康状态、SLO 指标和回滚点，让一次小部署也具备完整的发布生命周期。

### P2：从“固定版式”走向“可组合应用”

9. **更多通用生成能力**：在现有 7 模板上扩展长尾类型，而不是无限加模板。
10. **修复循环**：自检/构建失败后把错误回灌给模型，形成 Inspector → Builder 的自动修复。
11. **组件 schema**：从整页模板走向“组件库 + 配置 schema”，在保持可验收的前提下提升生成自由度。
12. **SLA 分层与成本模型**：区分基础/标准/企业隔离等级，补齐配额、成本归集和计费口径。

---

## 五、如果给更多时间：更远端的设想

### 5.1 隔离升级：从单机多用户到托管多租户

- OpenSandbox Firecracker 或 ACS Agent Sandbox；
- MicroVM、pause/resume、checkpoint、按秒计费；
- 从“单机 Docker 容器”升级为“强隔离、可弹性、可休眠”的托管执行平面。

### 5.2 发布升级：每项目独立 origin

- 每项目子域名 + Runtime Gateway；
- 短期访问 token + 可撤销分享；
- 自定义域名、WebSocket、后台任务、定时任务；
- 生成应用与平台真正不同 origin，Cookie/API 不再互相影响。

### 5.3 能力升级：从固定模板到可组合应用

- 组件库 + schema + 代码生成 + 自动修复；
- 支持数据库、表单、支付、邮件、第三方集成；
- 从“生成一个页面”升级为“生成一个可持续运行的小产品”。

### 5.4 协作升级：从个人工作台到团队创作平台

- 项目版本、分支、评论、多人协作；
- 模板市场、组件市场、分享与复用；
- 团队空间、权限、审计和配额。

### 5.5 Agent 升级：最后再做多 Agent

当前不建议先上多 Agent。更合理的顺序是：

```text
隔离与运行时 → 持久化与恢复 → 构建/修复闭环 → 多角色协作
```

当平台底座稳定后，再引入：

- **Planner**：生成结构化计划；
- **Builder**：真实工具调用与代码生成；
- **Inspector**：结构、运行时、视觉验收；
- **Operator**：部署、运行时、回滚和运维。

没有可靠执行环境，多 Agent 只会放大失败；先把“能安全地跑、能稳定地回滚”做好，再谈角色协作。

### 5.6 运营升级：从单机 ECS 到可水平扩展

- 配额、计费、审计、备份、灾备；
- 可观测性：日志、指标、追踪；
- 从单机 ECS 走向可水平扩展的架构。

### 5.7 一次部署 = 一个小项目：从云的角度保证 SLA 与隔离

这是比“补功能”更重要的产品视角：**不要只把一个项目看成一堆文件，而要把它看成一次完整的小部署。**

每次生成/部署都应该有：

| 维度 | 一次小部署应该具备什么 |
|---|---|
| 版本 | deployment id、revision、构建产物、变更记录 |
| 发布 | 构建 → 健康检查 → 切换 → 回滚点 |
| 运行时 | 独立进程/沙箱、端口、数据卷、空闲休眠 |
| 隔离 | 独立 origin、独立数据、独立配额、默认无出网 |
| 观测 | 构建成功率、首次可用时间、p95 延迟、错误率、可用性 |
| 治理 | 配额、成本、审计、分享/撤销、过期回收 |

对应的云化能力：

- **多租户调度**：按用户/项目分配构建与运行时资源；
- **SLA 分层**：基础（共享容器、冷启动）、标准（独立 runtime、常驻）、企业（MicroVM、专属域名、备份/合规）；
- **弹性与发布**：蓝绿、金丝雀、自动扩缩、失败回滚；
- **数据与灾备**：项目数据卷、备份、恢复、删除策略；
- **成本与计费**：按构建时长、运行时秒数、存储和出网计费；
- **审计与合规**：谁在什么时候部署了什么、访问了什么、撤销了什么。

建议跟踪的核心指标：

```text
build_success_rate
time_to_first_usable
p95_runtime_latency
runtime_availability
cold_start_p95
isolation_violations = 0
cost_per_project
```

这意味着下一步不只是“把项目跑起来”，而是让每个小项目都具备**可发布、可观测、可回滚、可计费、可隔离**的云化生命周期。

---

## 六、结论

**这次演进的核心不是“Agent 更聪明”，而是“平台更完整”。**

- 生成层是确定性优先：内置模板保底，通用生成兜底；LLM 负责创意、长尾生成和局部 patch，规则负责结构/离网/语法自检与回退；
- 平台层已经具备用户、数据、沙箱、运行时和发布边界；
- 下一步的瓶颈不是模型能力，而是域名级隔离、沙箱出网、运行时治理和修复闭环。

一句话：**先把“能安全地给别人用”做扎实，再谈“让 Agent 更自主”。**

---

## 附录 A：关键代码路径

| 模块 | 作用 |
|---|---|
| `server/main.py` | FastAPI 入口、鉴权、项目 API、SSE、SSR 代理、分享、管理 |
| `server/auth.py` | 注册、登录、scrypt、服务端会话、限流 |
| `server/db.py` | SQLite schema、用户/会话/项目/运行时/审计 |
| `server/events.py` | Task/Project 对象、事件流、用户工作区 |
| `server/agent.py` | 五段式生成、React/Next 构建、二次修改、蓝绿切换 |
| `server/llm.py` | 创意 brief、局部 patch、长尾游戏 HTML 生成 |
| `server/stacks.py` | stack 解析、React/Next 意图识别与 static 回退 |
| `server/sandbox.py` | OpenSandbox 客户端、构建、产物打包与校验 |
| `server/runtime.py` | Next standalone 运行时、健康检查、空闲停止 |
| `server/tools.py` | 文件快照、产物安装、静态部署 |
| `server/templates/` | 7 类能力模板 + Vite/React + Next TypeScript 脚手架 |
| `server/templates/longtail.py` | 长尾通用生成、约束与回退策略 |
| `server/templates/games/` | 游戏题材识别、GameSpec 与内置/自定义游戏渲染 |
| `server/templates/adapt.py` | 历史 adapt 项目兼容渲染（新项目不再创建） |
| `frontend/` | 平台工作台：React + TypeScript + Vite |
| `web/dist/` | 平台 UI 构建产物，由 FastAPI 托管 |

> Reify 使用 `REIFY_*` 环境变量和 `reify.db`；55 已完成迁移，历史 `VIBEFORGE_*` / `vibeforge.db` 仅用于回溯。

## 附录 B：55 部署与直接编辑

截至 2026-10-24：

- 线上 `/data/reify-deploy` 运行 Reify（React + TypeScript + 7 模板 + 通用生成），容器为 `reify` / `reify-caddy` / `reify-sandbox`，环境变量为 `REIFY_*`，数据库为 `data/reify.db`；
- 完整仓库（含 `.git`）同步在 `/data/reify-deploy/repo`，容器内路径是 `/app/repo`；`/data/reify-deploy` 本身仍不包含 `.git`；
- `/opt/git/vibeforge.git` 是历史裸仓库名；`main` 已合并 `reify`，包含最新部署；
- 仓库里有 `frontend/`（React + TypeScript 源码）、`docs/frontend-react-ts-design.md`、`docs/isolation-design.md`、`docs/reify-design-2026-10-24.md`；线上 `/data/reify-deploy/web/dist` 是前端构建产物；
- 线上 `README.md` 是 Reify 版本；`docs/` 同步后与仓库一致；
- 直接在 55 上改代码是可行的：优先在 `/data/reify-deploy/repo` 里用 Git 修改；线上部署树 `/data/reify-deploy` 按下面的方式更新。静态文件通常立即生效，Python/模板改动需要 `docker restart reify`，依赖变更需要重建镜像，`.runtime.env` 变更需要重建容器；
- 如果只想快速改运行中的代码，也可以直接改 `/data/reify-deploy`，但建议先在 `/data/reify-deploy/repo` 留一个可回滚的提交。

### B.1 推荐工作流

```bash
# 在容器内或宿主机上
cd /data/reify-deploy/repo
git pull
# 修改代码
git diff
git add <files>
git commit -m "..."

# 后端 / 模板 / 文档
rsync -a /data/reify-deploy/repo/server/ /data/reify-deploy/server/
rsync -a /data/reify-deploy/repo/docs/ /data/reify-deploy/docs/

# 前端：先同步源码，再在部署树里构建，输出到 /data/reify-deploy/web/dist
rsync -a /data/reify-deploy/repo/frontend/ /data/reify-deploy/frontend/
cd /data/reify-deploy/frontend
npm ci
npm run build

# Python/模板改动后
docker restart reify
```

> 不要用 `rsync --delete` 把仓库根目录直接覆盖 `/data/reify-deploy`，否则会删除 `web/dist`、`data/` 和密钥文件。完整发布仍建议走 `deploy_remote.sh` 或镜像构建。

### B.2 历史 VibeForge 目录

历史 `/opt/vibeforge` 仅用于回溯，旧容器/网络已清理。需要回滚时使用 `/data/reify-deploy/backups` 或旧镜像，不要重新启动旧 VibeForge 容器。
