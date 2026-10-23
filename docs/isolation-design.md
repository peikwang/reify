# VibeForge 隔离方案：用户、项目、SSR 运行时与沙箱

> 状态：设计稿 v3；Phase 1-3 已实施并通过本地 E2E（IP-only 模式：平台 12888 / SSR 应用 12889）；Phase 4 已落地管理员、分享、审计、存储配额；ACS/MicroVM 与 Next SSR 分享仍待后续
> 分支：`feature/isolation`
> 已确认：任意用户可自助注册；用户注册信息、会话、项目关联全部持久化在本地 SQLite；
> 旧项目归首个管理员；支持 SSR/全栈运行时；单机 OpenSandbox（Docker runtime）；
> 运行时空闲休眠 + 按需唤醒；当前只有 IP，SSR 运行时不对外公开，域名就绪后再开公网入口。

## 0. 结论先行

1. **用户隔离**：开放自助注册 + 本地 SQLite 用户/会话表 + 每用户目录 + 所有 API/预览/下载强制 owner 校验。移除当前 `/tasks` 静态直挂。
2. **本地持久化**：用户资料、密码哈希、登录会话、项目归属、运行时记录都写入 `data/vibeforge.db`（WAL），项目文件与事件写入 `data/users/{uid}/projects/{pid}/`；服务重启后账号、登录态、项目和修订全部可恢复。
3. **项目隔离**：静态项目按目录隔离；全栈项目每个都有独立沙箱、独立网络命名空间、独立 origin（子域名）、独立存储卷。
4. **SSR/全栈**：Next.js App Router + `output: 'standalone'`，构建与运行都在沙箱内完成；构建成功后蓝绿切换运行时。
5. **阿里云 ACS Agent Sandbox**：隔离能力强（MicroVM、休眠唤醒、Checkpoint），但依赖 ACK/ACS 集群与 Ingress/域名，**无法在现有单台 ECS + 纯 Docker 上直接部署**。它兼容 E2B SDK，适合作为第二阶段的托管后端。
6. **当前单机推荐**：自建 **OpenSandbox Server（Docker runtime）** 作为沙箱控制面，app 通过内网 API 调用；不把 docker.sock 交给 app 容器。接口按 OpenSandbox/E2B 语义设计，后续可切换 ACS。
7. **SSR 的硬前提**：生成应用必须在**独立 origin**（每个项目一个子域名）。路径前缀方案会让用户的应用 JS 与平台同源，可以读取平台 API 和覆盖平台 Cookie，不能作为多用户方案。

## 1. 现状审计

| 位置 | 现状 | 风险 |
|---|---|---|
| `server/main.py:107` | Cookie 只有过期时间，无用户身份 | 无法区分用户，无法做所有权判断 |
| `server/main.py:46` | `/tasks` 直接静态挂载项目根目录 | 登录即可读任意项目 |
| `server/main.py:203` | 媒体路由只校验路径在 `assets/` 下 | 知道 task id 即可读资产 |
| `server/main.py:129` | `/media/` 整个前缀免鉴权 | 资产实际公开 |
| `server/events.py:44` | 工作区扁平 `projects/{task_id}` | 无用户层级，无法配额/迁移 |
| `server/events.py:161` | `store.list()` 返回全部任务 | 项目列表跨用户 |
| `server/agent.py:259` | 在 app 进程内跑 `py_compile` | 无法安全执行 npm/构建脚本 |
| `deploy_remote.sh` | app 容器挂源码目录，无资源限额 | 构建可耗尽主机、读取 `.llm.env` |
| `server/tools.py:26` | 只保证不逃出项目目录 | 项目目录本身没有用户边界 |

现有 CSP `sandbox` 只解决了“静态生成页不能调用同源 API”，不解决用户之间、项目之间、构建执行、SSR 运行时四类隔离。

## 2. 威胁模型

1. **用户 A**：读取/修改/删除用户 B 的项目、运行时、日志、资产。
2. **生成页面**：读取平台 Cookie、调用平台 API、覆盖会话、外联回传。
3. **生成源码/依赖**：`npm install`、构建脚本、运行时 Node 进程执行任意代码。
4. **资源滥用**：大量项目、长驻运行时、超大构建、无限期沙箱。
5. **凭据泄露**：LLM/媒体 Key 在 app 环境变量中，构建与运行时绝不能继承。

不在范围：主机 root 被攻陷、内核 0-day、平台管理员作恶。

## 3. 隔离模型

| 层 | 目标 | 手段 |
|---|---|---|
| L0 身份 | 每个请求知道“是谁” | 开放注册、scrypt 密码、服务端会话（SQLite `sessions`）、Origin/CSRF 校验 |
| L1 数据 | 只触达自己的项目 | 每用户目录、DB owner 索引、所有入口统一鉴权 |
| L2 执行 | 不可信代码不碰主机/密钥/其他项目 | 每项目独立沙箱：非 root、只读根、资源限额、默认拒绝出网、无密钥注入 |
| L3 运行时 | 全栈应用独立进程与网络 | 每项目一个运行时沙箱、独立端口/子域名、独立数据卷、空闲休眠 |
| L4 发布 | 可访问但不越权 | 独立 origin（子域名）+ 短期签名访问 token + 可撤销分享 |

## 4. 关键硬约束：SSR 必须独立 origin

如果把 Next.js 应用挂在平台同源的 `/apps/{id}/`：

- 应用 JS 可以 `fetch('/api/projects')`，带着用户 Cookie 读取全部项目。
- 应用可以 `document.cookie = 'vibeforge_session=...; path=/'` 覆盖平台会话。
- CSP `sandbox` 不能用于 SSR：会变成不透明源，应用自身的同源 API 路由和 Cookie 全部失效。

因此全栈项目必须使用**每项目子域名**：

```text
平台:   https://app.example.com
应用:   https://p-{project_id}.apps.example.com
沙箱域: https://*.apps.example.com  → 运行时网关
```

隔离收益：

- Cookie 按 host 隔离，应用无法读写平台 Cookie。
- 平台 API 是跨源，应用即使请求也读不到响应。
- 分享/撤销按子域名与 token 独立控制。
- Next.js 可以用根路径部署，不需要 `basePath`。

**当前决策：只有 IP，SSR 运行时不对外公开。** Phase 3 先完成构建、运行时、休眠唤醒和本机验证，运行端口只绑定回环/内网；公网子域名网关与分享等域名就绪后再启用。不采用 sslip.io 临时方案，也不做同源路径预览。

## 5. 沙箱后端选型

### 5.1 阿里云 ACS Agent Sandbox（调研结论）

事实（来自阿里云文档）：

- 基于 **MicroVM** 的计算、网络、存储端到端隔离；支持内存级休眠/唤醒（1~10s）、Checkpoint/Restore、每分钟 15K 沙箱弹性。
- **依赖 ACK / ACS 集群**：需安装 `ack-agent-sandbox-controller`、`ack-sandbox-manager` 和 Ingress Controller；需要泛域名 + TLS（原生协议）或单域名（私有协议）。
- 兼容 **E2B SDK**（Python 固定 `e2b==2.50.0`），支持 `Sandbox.create/kill/connect`、`commands.run`、`files.read/write`、`run_code`（仅内置 code-interpreter 镜像）。
- 自定义镜像要求包含 `bash`/`cp`/`mv`/`mkdir`；自定义镜像下 `run_code` 不可用，但 `commands.run` 可用。
- 端口暴露：原生协议 `https://<PORT>-<SANDBOX_ID>.DOMAIN`；私有协议 `DOMAIN/kruise/<SANDBOX_ID>/<PORT>`。
- 公测中，仅 CPU + 内存，无 GPU；按 vCPU/内存按秒计费，休眠状态仍计临时存储费。

结论：**不能直接复用到当前单台 ECS + 纯 Docker 部署**；如果已有/愿意开通 ACK+ACS 集群，可以作为生产沙箱后端直接接入，且原生子域名正好满足 SSR 的 origin 隔离。

### 5.2 OpenSandbox（自建，当前单机推荐）

- 开源、可自建；Docker runtime 支持沙箱创建、命令执行、文件读写、端口 endpoint、出网策略（sidecar）、TTL。
- Docker 模式下 ingress 只支持 `direct`，端口从 `40000-60000` 分配；可通过 server 的 proxy 路由或绑定内网地址访问。
- Firecracker 快速沙箱需要 K8s；单机不采用。
- 缺点是容器级隔离，弱于 MicroVM；但配合非 root、只读根、cap-drop、seccomp/AppArmor、独立网络、默认拒绝出网，足够个人/小团队使用。

### 5.3 后端矩阵

| 能力 | OpenSandbox Docker（本期） | ACS Agent Sandbox（演进） |
|---|---|---|
| 隔离级别 | 容器 | MicroVM |
| 部署 | 当前 ECS，独立容器 | ACK/ACS 集群 |
| 命令/文件 API | 支持 | `commands.run` + files |
| 端口暴露 | server proxy / host port | 每端口子域名 |
| 空闲休眠 | stop/start（需自建） | 原生 pause/resume |
| 出网白名单 | egress sidecar | 需在 ACS 侧策略 |
| 成本 | 固定主机成本 | 按秒计费 |
| 适用 | 当前单机、开发/小团队 | 生产多租户、弹性 |

统一接口：

```python
class SandboxBackend(Protocol):
    async def create(self, project_id: str, image: str, ttl: int) -> Sandbox: ...
    async def upload(self, sandbox, files: dict[str, bytes]) -> None: ...
    async def run(self, sandbox, cmd: list[str], *, timeout: int, on_log) -> ExecResult: ...
    async def download(self, sandbox, path: str) -> bytes: ...
    async def endpoint(self, sandbox, port: int) -> str: ...
    async def pause(self, sandbox) -> None: ...
    async def resume(self, sandbox) -> None: ...
    async def destroy(self, sandbox) -> None: ...
```

## 6. 目标架构

```text
                    ┌─────────────────────────────────────────┐
Browser ──HTTPS──►  │ Caddy                                   │
                    │  app.example.com                        │
                    │  *.apps.example.com                     │
                    └───────┬─────────────────────┬───────────┘
                            │                     │
                    ┌───────▼────────┐   ┌────────▼─────────────┐
                    │ VibeForge App  │   │ Runtime Gateway      │
                    │ auth/owner     │   │ token 校验 + 反代     │
                    │ project store  │   │ (HTTP/SSE)           │
                    │ agent pipeline │   └────────┬─────────────┘
                    └───┬────────┬───┘            │
                        │        │                │
              ┌─────────▼──┐  ┌──▼──────────┐  ┌──▼─────────────────┐
              │ SQLite     │  │ Sandbox     │  │ 项目运行时沙箱       │
              │ 用户/项目  │  │ Backend     │  │ Next standalone     │
              └────────────┘  │ OpenSandbox │  │ :3000               │
                              │ / ACS E2B   │  └────────────────────┘
                              └─────────────┘
```

- app 容器不持有 docker.sock；OpenSandbox Server 单独部署，app 通过内网 API Key 调用。
- 构建沙箱与运行时沙箱分离：构建沙箱有 npm registry 出网；运行时沙箱默认无出网、无构建工具链、无平台密钥。
- Runtime Gateway 负责按子域名解析项目、校验短期 token、反向代理到沙箱端口；支持流式响应，后续补 WebSocket。

## 7. 用户与权限

### 7.1 账号与注册

- **任意用户可自助注册**：`POST /api/auth/register`，提交用户名、密码、可选显示名/邮箱；注册成功即创建本地用户并自动登录。
- 用户名 3~32 字符，允许中英文、数字、`_`、`-`；按 `username_key = casefold(username)` 做唯一约束，避免大小写重复账号。
- 密码 8~128 字符；使用标准库 `hashlib.scrypt`（每用户随机盐，参数随哈希一起存储），不存明文、不引入新依赖。
- 邮箱可选；填写时按小写做唯一约束。本期不做邮件验证与找回密码。
- 注册默认开放；需要封闭运行时设置 `VIBEFORGE_REGISTRATION=closed`，注册接口返回 403。
- 限流：同 IP 每小时最多 5 次注册、每分钟最多 10 次登录；同用户名失败次数单独计数。
- 管理员引导：
  - 启动时确保至少有一个管理员：优先使用 `VIBEFORGE_ADMIN_USER` / `VIBEFORGE_ADMIN_PASSWORD`；未配置密码时生成随机密码并打印到启动日志（沿用现有行为）。
  - 自助注册的用户一律为 `user`，不会因为“第一个注册”自动获得管理员权限，避免服务先暴露后被抢注管理员。
- 注册信息（用户名、哈希、显示名、邮箱、角色、注册 IP、注册时间、最近登录时间）全部写入本地 `users` 表。

### 7.2 会话（服务端持久化）

Cookie 只携带随机会话令牌，会话本体存 SQLite，服务重启后登录态不丢失：

```text
vibeforge_session = <32 字节随机令牌 base64url>
```

- `sessions` 表存 `sha256(token)`，不存明文令牌；查到会话后联表校验用户是否禁用。
- 默认有效期 7 天；每次请求校验 `expires_at`、`revoked_at`；`last_seen_at` 每 5 分钟最多更新一次，避免频繁写库。
- 登出：撤销当前会话；“退出所有设备”：撤销该用户全部会话并 `token_version += 1`。
- 修改密码：撤销全部旧会话，要求重新登录。
- Cookie：HttpOnly + Secure + SameSite=Lax；所有写请求校验 `Origin` 与 `Host` 同源，不启用 CORS。
- 启动时与每小时清理过期会话；管理员可查看/撤销某用户的会话。

### 7.3 注册与登录流程

```text
注册: 校验字段 → IP/用户名限流 → 唯一性检查 → scrypt → INSERT users
      → INSERT sessions → Set-Cookie → 返回当前用户

登录: 按 username_key / email_key 查用户 → 校验 disabled → scrypt 验证
      → INSERT sessions → Set-Cookie → 更新 last_login_at

请求: Cookie 令牌 → sha256 → 查 sessions JOIN users
      → 校验过期/撤销/禁用 → 注入 current_user
```

### 7.4 授权

```python
async def current_user(request) -> User: ...
async def owned_project(project_id, user) -> Project: ...
```

- `/api/projects/**`、`/p/**`、`/media/**`、`/api/apps/**` 全部走所有权校验。
- 管理员只额外拥有用户管理/配额权限，默认不跨用户读内容。
- 查询层强制 `owner_id` 条件。

### 7.5 数据模型（SQLite WAL，`PRAGMA foreign_keys=ON`）

```sql
users(
  id TEXT PRIMARY KEY,
  username TEXT NOT NULL,
  username_key TEXT NOT NULL UNIQUE,        -- casefold 后的唯一键
  email TEXT, email_key TEXT UNIQUE,        -- 可选，小写
  display_name TEXT NOT NULL DEFAULT '',
  password_hash TEXT NOT NULL,              -- scrypt$n$r$p$salt$hash
  role TEXT NOT NULL DEFAULT 'user',        -- user | admin
  token_version INTEGER NOT NULL DEFAULT 0,
  disabled INTEGER NOT NULL DEFAULT 0,
  created_ip TEXT,
  created_at TEXT NOT NULL,
  last_login_at TEXT
);

sessions(
  id TEXT PRIMARY KEY,
  token_hash TEXT NOT NULL UNIQUE,          -- sha256(token)
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  last_seen_at TEXT,
  revoked_at TEXT,
  ip TEXT,
  user_agent TEXT
);
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_expiry ON sessions(expires_at);

projects(
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL REFERENCES users(id),
  capability TEXT NOT NULL,
  stack TEXT NOT NULL DEFAULT 'static',      -- static | next
  title TEXT NOT NULL, status TEXT NOT NULL,
  revision INTEGER NOT NULL DEFAULT 0,
  visibility TEXT NOT NULL DEFAULT 'private',-- private | share
  share_token TEXT UNIQUE,
  asset_key TEXT NOT NULL,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX idx_projects_owner ON projects(owner_id, created_at DESC);

runtimes(
  project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
  revision INTEGER NOT NULL,
  backend TEXT NOT NULL,                    -- opensandbox | acs-e2b
  sandbox_id TEXT,
  endpoint TEXT,
  status TEXT NOT NULL,                     -- building | running | sleeping | error | stopped
  image TEXT NOT NULL,
  last_active_at TEXT,
  error TEXT
);
```

- 用户禁用不删除项目；项目删除才级联删除运行时记录。用户删除默认不提供，先做禁用。
- 项目 `meta.json` 同步写入 `owner_id`，作为文件层的第二道校验。
- `events.jsonl`、构建/运行日志仍在项目目录，DB 只保存索引与状态。
- `data/vibeforge.db` 及其 WAL 文件权限设为 `0600`；部署脚本在升级前做一次 SQLite 备份（`VACUUM INTO` 或文件复制），避免迁移失败丢账号。

### 7.6 存储布局

```text
data/
  vibeforge.db
  users/{uid}/projects/{pid}/
    meta.json
    events.jsonl
    workspace/          # 源码：app/、public/、package.json…
    builds/{rev}/
      artifact.tar      # Next standalone + static + public
    data/               # 运行时持久化卷（SQLite/JSON/上传）
    logs/
```

旧数据迁移：首个管理员接管现有全部项目；`scripts/migrate_v2.py --dry-run` 先出报告。

## 8. 全栈运行时设计

### 8.1 状态机

```text
draft → building → running → sleeping → running
                   └──────► error ──(重建)──► building
```

- `building`：构建沙箱中执行 npm install/build，流式回传日志。
- `running`：运行时沙箱健康检查通过，endpoint 可用。
- `sleeping`：空闲超过 TTL，停止/休眠；下次访问唤醒。
- `error`：构建失败/健康检查失败/进程崩溃多次；保留上一版可回滚。

### 8.2 构建

- 构建镜像：`node:24-bookworm-slim`（固定 digest）。
- 命令：
  ```bash
  npm install --ignore-scripts --no-audit --no-fund
  npm run build
  ```
- 强制 `--ignore-scripts`；依赖白名单：`next`、`react`、`react-dom`、`typescript`/`@types/*`（可选）、`clsx`、`lucide-react`；新增依赖需 allowlist 校验。
- Next 配置固定：
  ```js
  output: 'standalone'
  images: { unoptimized: true }
  // 子域名部署，无需 basePath
  ```
- 构建成功后打包 `.next/standalone`、`.next/static`、`public` 为 artifact；构建沙箱立即销毁。
- 超时 300s，产物上限 50MB。

### 8.3 运行

- 从干净 Node 镜像创建运行时沙箱，只上传 artifact 和 `data/`，不包含源码与构建工具。
- 启动：
  ```bash
  PORT=3000 HOSTNAME=0.0.0.0 NODE_ENV=production node server.js
  ```
- 健康检查 `GET /` 200（最多 60s）；失败则标记 error，保留旧版本端点。
- 运行时默认无出网、无平台环境变量；项目自有环境变量（后续）加密存储、按项目注入。
- 资源：0.5~1 vCPU / 512MB~1GB；数据卷上限 100MB。
- 空闲 10 分钟 → 休眠；访问时唤醒。OpenSandbox Docker 用 stop/start；ACS 用 pause/resume。
- 单用户最多 2 个活跃运行时；全局最多 8 个；超限时按 LRU 休眠。

### 8.4 路由与访问控制

- 平台：`https://app.example.com`
- 应用：`https://p-{id}.apps.example.com`
- 打开项目时，app 生成短期访问 token（HMAC，5 分钟），跳转：
  `https://p-{id}.apps.example.com/?t=<token>`
- Runtime Gateway 校验 token 与项目归属，设置该子域名的短期 Cookie，然后反代到沙箱 `:3000`。
- 分享：`visibility=share` + `share_token`，可生成只读/可交互的分享链接；撤销即失效。
- 反代保留 `Host` 为应用子域名，添加 `X-Forwarded-*`；流式响应直通；WebSocket 后续用专用代理实现。
- 应用子域名与平台子域名不同 origin，平台 Cookie 不会发送到应用。

### 8.5 二次修改与蓝绿切换

1. 对 `workspace/` 应用 patch。
2. 新 revision 构建到 `builds/{n}/`。
3. 创建新运行时沙箱，健康检查通过。
4. 更新 `runtimes.endpoint` 到新沙箱（原子切换）。
5. 销毁旧沙箱；旧 artifact 保留一个版本用于回滚。
6. 构建失败：不切换，旧运行时继续服务。

## 9. Next.js 生成流水线

### 9.1 脚手架

固定生成以下文件，避免模型自由发明工程配置：

```text
package.json          # 精确版本，脚本 dev/build/start
next.config.mjs       # output: 'standalone'
app/layout.jsx
app/page.jsx
app/globals.css
public/...
app/api/.../route.js  # 需要全栈接口时生成
lib/db.js             # 可选：node:sqlite 封装
```

- 默认 JavaScript/JSX，降低构建失败率；需要 TS 时作为选项。
- 依赖白名单内安装；不生成 `postinstall`。
- 全栈示例：表单提交 → Route Handler → `node:sqlite` → 页面读取；数据文件在 `data/`。

### 9.2 事件契约

新增事件：

- `build_started` / `build_log` / `build_done` / `build_failed`
- `runtime_starting` / `runtime_ready` / `runtime_sleeping` / `runtime_error`
- `deploy_switched`（含新旧 revision）

编程模式展示源码 diff + 构建日志；日常模式只显示“生成—构建—启动—可访问”。

### 9.3 降级

沙箱不可用时不回退到 app 进程执行 npm；项目标记为“构建环境未就绪”，静态模板路径不受影响。

## 10. 静态项目

保持现有模板与 CSP `sandbox` 发布方式，只做数据隔离与路由改造：

- `/p/{id}/` 鉴权后服务 `workspace/`（或 `dist/`）。
- 媒体资产使用每项目 `asset_key` 能力 URL，适配 CSP 不透明源。
- 分享走 `/s/{share_token}/`，只读。

## 11. 配额

| 维度 | 默认值 |
|---|---|
| 每用户项目 | 50 |
| 每用户存储 | 1 GB |
| 每用户并发任务 | 2（全局 4） |
| 每用户活跃运行时 | 2（全局 8） |
| 单项目源码 | 5 MB |
| 单项目 artifact | 50 MB |
| 单项目数据卷 | 100 MB |
| 单次构建 | 1 CPU / 1 GB / 300 s |
| 空闲休眠 | 10 min |

## 12. 实施阶段

### Phase 1 — 身份与数据边界（可先上线）

- SQLite 用户/会话/项目表；开放注册；scrypt；服务端会话。
- 每个项目写入 `owner_id`，文件落到 `data/users/{uid}/projects/{pid}/`。
- 旧项目迁移到首个管理员。
- 所有 API/预览/下载 owner 校验；移除 `/tasks` 直挂。
- 前端登录页增加注册表单；项目列表按当前用户过滤。
- 验收：任意用户可注册并只看到自己的项目；服务重启后账号、登录态、项目仍在；跨用户访问矩阵全 404。

### Phase 2 — 沙箱与静态发布收口

- 部署 OpenSandbox Server（Docker runtime）为独立容器；app 通过内网 API Key 调用。
- 实现 `SandboxBackend`（OpenSandbox）；构建/运行沙箱模板。
- 媒体能力 URL、静态项目 `/p/{id}` 路由。
- 验收：沙箱内 `npm install` 可运行；容器无法读宿主/密钥；出网白名单生效。

**实施记录（Phase 2）**：

- 已接入 OpenSandbox Server 1.1.x + Docker runtime；app 容器不挂 docker.sock，只有独立的 `vibeforge-sandbox` 容器持有。
- 新增 `stack=react`：生成 Vite + React 源码，沙箱内执行 `npm install --ignore-scripts` 与 `npm run build`，流式回传 `build_started/build_log/build_done/build_failed`。
- 构建产物通过 tar + base64 回传，原子安装到 `workspace/dist/`；`/p/{id}/` 发布 `dist/`。
- Vite 模块 JS/CSS 在 CSP sandbox 下不带 Cookie，构建时给 asset URL 追加项目 `asset_key`，`/p/` 资源路由支持 capability key。
- 出网策略使用 OpenSandbox egress allowlist（默认 `*.npmmirror.com`、`*.npmjs.org`），沙箱 1 CPU / 1 GiB / TTL 900s，构建后销毁。
- 当前 React 项目的对话式二次修改未接入；SSR/全栈运行时仍属于 Phase 3。

### Phase 3 — Next.js SSR 全栈（不含公网入口）

- Next 脚手架、构建流水线、artifact、运行时沙箱、健康检查。
- 运行时端口只绑定 `127.0.0.1`/内网；通过 SSH 隧道或服务器本机验证。
- 空闲休眠/唤醒、蓝绿切换、日志。
- 域名就绪后再加 Runtime Gateway、泛解析与短期 token，开放公网访问。
- 验收：生成一个带表单与 SQLite 的 Next 应用；二次修改重建并切换；跨项目/跨用户不可互访；应用无法读平台 Cookie。

**实施记录（Phase 3 首个版本）**：

- 已新增 `stack=next`：生成 Next.js App Router 源码，包含 `/api/notes` Route Handler；沙箱内 `npm ci` + `next build`，打包 `.next/standalone`。
- 新增 `server/runtime.py`：为项目创建独立运行时沙箱，上传 standalone 产物，后台启动 `node server.js`，健康检查通过后记录 `running`；支持 start/stop 和空闲 10 分钟自动停止。
- 新增 `/apps/{id}/` 预览代理，但由 `VIBEFORGE_SSR_PREVIEW` 控制，默认关闭；当前没有域名，路径预览与平台同源，不能作为公网方案。
- 当前 Docker runtime 的“休眠”是冷停止 + 冷启动，不是 MicroVM pause/resume。

**实施记录（Phase 3 收口）**：

- IP-only 方案落地：平台 `https://IP:12888`，SSR 应用独立 origin `https://IP:12889`；Caddy 只在 12889 暴露 `/apps/*`，12888 屏蔽 `/apps/*`，并移除 SSR 响应的 `X-Frame-Options` 以允许跨端口 iframe。
- 运行时数据卷：OpenSandbox host bind 项目 `runtime-data/` 到沙箱 `/data`；Next Route Handler 使用 `node:fs` 持久化 `notes.json`，停止/重启运行时后数据保留。
- React/Next 源码二次修改：LLM 返回唯一 patch，写入源码后重新构建；Next 先起新运行时、健康检查通过后再停旧运行时，实现蓝绿切换。
- 已用 mock OpenAI 兼容服务跑通 React/Next 修改 E2E；真实模型仍需远端凭据验证。

### Phase 4 — 托管沙箱与运营

- ACS E2B 后端适配器（如果已有 ACK/ACS 集群）。
- 用户管理（禁用、会话撤销）、配额面板、分享撤销、审计日志。

**实施记录（Phase 4 当前范围）**：

- `/admin` 管理页：用户列表、项目数、存储占用、最近审计；支持禁用/启用账号、撤销全部会话；禁止管理员禁用自己或最后一个管理员。
- 静态/React 项目支持只读分享 `/s/{token}/`，可撤销；Next SSR 分享暂不开放（需要独立分享网关）。
- 新增本地 `audit_log` 表，记录注册/登录、项目创建/修改/部署、运行时启停、分享、管理员操作。
- 每用户 1 GB 存储配额、项目数/活跃任务/源码构建并发限制。
- **未完成/不适用**：ACS Agent Sandbox 适配需要 ACK/ACS 集群与域名，当前 IP-only 单机部署不适用；MicroVM、Next SSR 分享、存储清理策略仍为后续工作。
- 视规模迁移到 MicroVM，获得 pause/resume 与更强隔离。

## 13. 决策记录与剩余开放项

已确认（2026-10-23）：

1. 账号：任意用户可自助注册；默认开放，可用 `VIBEFORGE_REGISTRATION=closed` 关闭。
2. 持久化：用户资料、密码哈希、登录会话、项目归属、运行时记录全部存本地 SQLite；项目文件与事件存本地用户目录。
3. 旧数据：全部归首个管理员。
4. SSR：Next.js 全栈运行时，构建/运行都在沙箱内。
5. 沙箱：当前单机部署 OpenSandbox Server（Docker runtime）；ACS 作为演进后端，需 ACK/ACS 集群。
6. 生命周期：空闲 10 分钟休眠，访问时唤醒。
7. 网络：当前只有 IP，SSR 运行时不对外公开。Phase 3 先实现构建、运行时、休眠唤醒和本机验证；公网子域名网关等域名就绪后再开。

剩余开放项：

- **域名**：申请到域名后配置泛解析 + DNS-01 通配证书，再接 Runtime Gateway。
- **Next.js 语言**：默认 JS/JSX（构建成功率高），需要 TypeScript 时作为项目选项。
- **ACS 接入时机**：只有当项目规模或隔离要求超过单机容器能力时再开通集群。

## 14. 安全验收清单

- [ ] A 无法通过 API/SSE/下载/预览/媒体/运行时读取 B 的项目（统一 404，不泄露存在性）。
- [ ] 任意用户可注册；重复用户名/邮箱（忽略大小写）被拒绝；注册频率受限。
- [ ] 服务重启后用户、会话、项目归属、修订号仍存在，登录态不丢失。
- [ ] 禁用用户或撤销会话后，旧 Cookie 立即失效；改密后其他设备全部下线。
- [ ] 未登录访问平台路由跳登录；无 token 的应用子域名返回 404/403。
- [ ] 静态生成页内 `document.cookie` 抛 SecurityError，`fetch('/api/projects')` 读不到响应。
- [ ] SSR 应用与平台不同 origin，应用无法读取平台 Cookie/API 响应。
- [ ] 跨站 POST 因 Origin 校验被拒绝。
- [ ] 构建/运行时容器读不到 `.runtime.env`、无 docker.sock、无宿主挂载。
- [ ] 构建容器只能访问 npm registry；`postinstall` 不执行。
- [ ] 运行时容器默认无出网；项目数据卷相互隔离。
- [ ] 构建/运行超时与资源限额生效；空闲运行时可休眠。
- [ ] 路径穿越、绝对路径、符号链接无法逃出项目目录。
- [ ] 项目/运行时 ID 枚举无法跨用户命中。
- [ ] 改密/踢下线后旧 Cookie 立即失效；分享撤销后链接立即失效。
- [ ] 构建失败/运行时崩溃不会替换上一版可用产物。

## 15. 代码改动清单

| 文件/模块 | 改动 |
|---|---|
| `server/db.py`（新） | SQLite schema、用户/会话/项目/运行时、迁移与事务 |
| `server/auth.py`（新） | 开放注册、scrypt、服务端会话、Origin/CSRF、限流 |
| `server/events.py` | Task→Project，增加 owner/stack/runtime 元数据 |
| `server/main.py` | 鉴权依赖、移除静态直挂、`/p`、`/s`、`/api/apps` 网关 |
| `server/tools.py` | 用户项目根、artifact 路径、asset_key |
| `server/agent.py` | Next 流水线、构建/运行时事件、蓝绿切换 |
| `server/sandbox/`（新） | `SandboxBackend`、OpenSandbox 实现、ACS/E2B 实现 |
| `server/templates/next_app.py`（新） | Next 脚手架与内容生成 |
| `runtime_gateway/`（新） | 子域名解析、token 校验、反代（或并入 app） |
| `web/login.html` | 登录 + 注册表单（用户名/密码/显示名） |
| `web/app.js` / `index.html` | 项目 URL、SSR 状态、构建日志、打开应用 |
| `Caddyfile` | 泛域名、通配证书、网关路由 |
| `deploy_remote.sh` | OpenSandbox 容器、运行时网络、环境变量、DB 备份 |
| `scripts/migrate_v2.py`（新） | 旧数据迁移与用户归属，dry-run |
