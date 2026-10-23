# VibeForge

> 从 Vibe Coding 到 Vibe Working：一句话生成网站、简历、小游戏、旅游攻略、多尺寸适配和编程演示，并把成品直接部署到自己的 Agent Server。

VibeForge 是一个单机优先的个人设计 Agent。它把自然语言拆成计划，逐步写文件，展示代码 Diff 与 Agent 思考流，跑结构/交互/语法自检，最后发布到 `/tasks/{id}/`。

## 能力

| Studio | 产物 | 自动验收 |
| --- | --- | --- |
| 小游戏 | 可玩的 Canvas 街机（键盘 + 触控 + 最高分） | 结构、viewport、脚本、canvas |
| 网站 | 有品牌感的响应式落地页 | 结构、viewport、内容区块、脚本 |
| 简历 | 单页双栏、在线可读、A4 可打印 | 结构、打印样式、viewport |
| 旅游攻略 | 按天切换的路线、预算与贴士 | 结构、每日路线交互、viewport |
| 适配制作 | 16:9 / 1:1 / 9:16 多画板切换 | 结构、多尺寸标记、viewport |
| 编程 | Python 代码 + 交互式可视化 | 结构、代码演示、`py_compile` |

## 双模式

- **日常模式**：左侧 Agent 流程以时间线动画逐条出现，右侧直接看成果预览、验收清单和部署状态。
- **编程模式**：左侧保留过程流，右侧展示文件树、逐行 Diff、终端日志和实时预览。每个 Agent 步骤都会留下一次文件快照，可一键重播。
- 两种模式共用同一条 SSE 事件流，不重跑 Agent。

## 访问保护

服务默认启用密码登录，使用 HMAC 签名的 HttpOnly Cookie，保护页面、SSE、任务 API 和生成物路由。

首次远端部署会自动生成凭据，保存在服务器：

```bash
ssh root@117.148.166.55 'grep VIBEFORGE_PASSWORD /opt/vibeforge/.auth.env'
```

登录状态保留 7 天；手机和电脑需要分别登录。修改密码：

```bash
ssh root@117.148.166.55 'nano /opt/vibeforge/.auth.env'
cd vibeforge && ./deploy_remote.sh root@117.148.166.55 12888
```

`docker restart` 不会重新读取 env-file，修改密码必须重建容器；上面的部署脚本会保留新密码并重建容器。

登录接口有按 IP 的简单限流（默认 1 分钟 8 次）。服务通过 Caddy 提供 HTTPS：应用只监听内部 12888，Caddy 在 12888 终止 TLS，并使用 Let's Encrypt 的公网 IP 证书（约 6 天有效期，自动续期）。80 端口只用于 ACME HTTP-01 验证和跳转，不直接暴露应用。

## 本地启动

```bash
cd vibeforge
python3 -m venv .venv
.venv/bin/pip install fastapi uvicorn httpx
VIBEFORGE_PASSWORD=your-password VIBEFORGE_SECRET=your-random-secret \
  .venv/bin/python -m uvicorn server.main:app --host 127.0.0.1 --port 7801
```

打开 <http://127.0.0.1:7801>。未设置密码时启动日志会生成一个临时密码。

## 手机访问

手机与服务器网络可达时，直接打开：

```text
https://117.148.166.55:12888/
```

输入访问密码即可。页面已适配 390px 手机宽度。部分运营商/公司网络会拦截 12888 这类非标准端口；换 Wi-Fi 或蜂窝网络再试。证书为受信任的公网 IP 证书，不需要手动信任。

## 可选：接入任意 OpenAI 兼容模型

不配置模型时，Agent 使用确定性的“本地导演 + 模板渲染”，保证每次都能生成可运行产物。配置后，模型只负责产出短创意 brief（标题、语气、强调色、要点），HTML 仍由可验证的模板渲染，避免模型输出坏页面。

```bash
export VIBEFORGE_LLM_BASE_URL=http://127.0.0.1:8000/v1
export VIBEFORGE_LLM_API_KEY=sk-...
export VIBEFORGE_LLM_MODEL=qwen-plus
```

也支持 vLLM / SGLang / Ollama 的 OpenAI 兼容接口。

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
  main.py              FastAPI、SSE、静态产物路由
  agent.py             ToolAct 编排（规划 → 写文件 → 自检 → 部署）
  events.py            任务、事件流、持久化
  tools.py             文件快照、Python 自检、部署工具
  llm.py               可选创意导演（失败自动回退）
  templates/           六类能力的可运行页面模板
web/                   双模式工作台（原生 HTML/CSS/JS）
projects/{task_id}/    Agent 产物（index.html、README.md、结构化数据）
data/tasks/{task_id}/  元信息与 events.jsonl
```

## API

- `POST /api/tasks` `{prompt, capability?}` → 创建任务
- `POST /api/tasks/{id}/refine` `{instruction}` → 基于当前成果对话修改
- `GET /api/tasks/{id}` → 元信息 + 事件历史
- `GET /api/tasks/{id}/events` → SSE 事件流
- `POST /api/tasks/{id}/deploy` → 重新部署
- `GET /api/tasks/{id}/bundle` → 下载项目 zip
- `GET /tasks/{id}/` → 已部署产物

生成完成后，工作台左侧会出现「继续修改」输入框。Agent 会读取当前 `index.html`，让模型返回精确的局部 patch，应用后重新自检并部署；修改失败时原页面保持不变。每次成功修改会增加 `revision`，原有事件流继续追加。

## 远程部署（HTTPS / Caddy）

应用容器 `vllm/vllm-openai:latest` 只在实际 Docker 网络中监听 12888，不直接发布端口。Caddy `2.10.2-alpine` 负责：

- 在 `12888` 终止 HTTPS
- 在 `80` 仅提供 ACME HTTP-01 验证（不承载应用页面）
- 使用 Let's Encrypt `shortlived` 配置申请公网 IP 证书（约 6 天，自动续期）
- 将 SSE 请求反向代理到应用，`flush_interval -1`

```bash
cd vibeforge
./deploy_remote.sh root@117.148.166.55 12888
```

验证：

```bash
curl -I https://117.148.166.55:12888/
curl https://117.148.166.55:12888/api/health
```

证书和 ACME 账户保存在 Docker volume `vibeforge-caddy-data` 中，重建应用容器不会丢失。

注意：公网 IP 证书的续期需要 80 端口可达；如果只能暴露 12888，则需要改用你自己的域名 + DNS-01 验证，或接受自签名证书。

## 安全边界

- 默认密码登录 + 签名 Cookie；未认证访问页面会跳转登录，API/预览返回 401。
- 所有 `/tasks/` 生成物响应带 `Content-Security-Policy: sandbox`，直接打开新窗口也不会获得主站同源权限。
- 产物只写入 `projects/{task_id}/`，所有文件工具做工作区路径校验。
- 预览 iframe 使用 sandbox，不开放 same-origin；生成页面不能读取主站 Cookie。
- 当前版本面向单用户/可信环境；已启用 HTTPS，建议再配合 Cloudflare Access 或 VPN 做外层访问控制。
- 若要开放给不可信多用户，执行环境应升级到 gVisor / microVM，不要只依赖 Docker。
