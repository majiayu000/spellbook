---
name: cliproxy-newapi-stack
description: 在已经过独立验证的 CLIProxyAPI upstream 之上部署 NewAPI 计费层，把 Codex/Claude/Gemini/Qwen 等订阅账号包装成可计费的 OpenAI 兼容 API。本 Skill 不负责新建裸 CLIProxyAPI；负责 NewAPI Docker 部署、容器到宿主桥接、模型计费倍率、参数化额度修正、多账号 OAuth 凭据热加载和双路径验证。当用户说“给现有 cliproxy 加 NewAPI”“配置 NewAPI 渠道接已运行的 cliproxy”“NewAPI 价格不对”“给现有部署加账号”“172.17.0.1 容器网络”或“408 冷却放大故障”时触发。
allowed-tools: Bash, Read, Write, Edit
metadata:
  argument-hint: '[ssh-目标，例如 root@1.2.3.4]'
---

# CLIProxyAPI + NewAPI Metering Stack

在用户已有并已验证的 **CLIProxyAPI** upstream 前增加 **NewAPI**
(`calciumion/new-api`) 计费、限流和多用户 token 层。本 Skill 不安装裸
CLIProxyAPI，也不调用其他部署 Skill 补齐这个前置条件。

所有"完成"结论必须基于**本会话**命令输出（W-16）。价格和额度变更后必须真发一次请求并查
`logs.quota` 与本次请求的 token 数和目标价格相符。

## Operating Contract

- Direct actions: 只读检查、配置备份和本地 dry-run 可直接执行。
- Escalate before: 安装容器、修改既有 upstream、重启服务、改防火墙或写生产额度前必须取得本次任务的明确授权。
- Evidence-backed pushback: 密钥只从环境变量或密码管理器读取；要求明文落盘或公网暴露原始端口时，展示具体风险并改用 tunnel/TLS。
- Feedback loop: 每次变更后重跑 upstream、NewAPI 和精确计费验证；任一步骤无法取得真实状态时停止并报告，不用默认值伪造成功。

---

## 0. 前置确认（必问）

- **SSH 目标**：`root@HOST` 是否能免密
- **端口分配**：`CLIPROXY_PORT`（默认 `8317`）、`NEWAPI_PORT`（默认 `8200`）
- **upstream 证据**：CLIProxyAPI 已在目标主机运行，当前会话能通过用户批准的
  SSH tunnel 或 loopback 请求验证健康、模型列表和认证；证据不足就停止，不猜测、
  不自动安装裸 upstream
- **登录账号供应商**：`codex` / `claude` / `qwen` / `iflow` / `gemini`
- **价格输入格式**：每个虚拟模型给我 input / cached / output 三个 USD per 1M 数字
- **客户端机器**：要在哪些机器上落 `BASE_URL` 环境变量

安全默认：本地 OAuth + scp 同步；NewAPI 仅绑定 VPS loopback，通过 SSH
tunnel 完成首次注册。公网访问必须走已配置 TLS 的反向代理，不能直接开放
NewAPI 原始 HTTP 端口。

---

## Phase 1 — 验证现有 CLIProxyAPI upstream

先记录现有服务的进程、监听地址、健康响应、模型列表和配置备份位置。任何一项
无法验证都停止。只有用户在当前消息批准修改这个既有 upstream 时，才执行以下
两个补丁：

1. **加稳定性开关**到 `/root/CLIProxyAPI/config.yaml`：
   ```yaml
   disable-cooling: true
   ```
   原因见 `references/troubleshooting.md` "CLIProxyAPI cooldown 原理"。
   若漏改，30 并发 5KB payload 会出现混合 ~50% 503。

2. **不要把 CLIProxyAPI 端口暴露到公网**（与裸部署不同）：
   - 先用 `ip -4 addr show docker0` 确认 Docker bridge 地址，再把 `host` 绑定到该地址（常见值为 `172.17.0.1`）
   - 删除已有的公网 `ufw allow <CLIPROXY_PORT>/tcp`；管理访问统一走 SSH tunnel，不保留公网 admin 后门

---

## Phase 2 — 部署 NewAPI 容器

```bash
IMAGE='calciumion/new-api@sha256:<VERIFIED_DIGEST>' \
SSH_TARGET=root@<HOST> SSH_KEY=~/.ssh/id_ed25519 PORT=8200 \
  scripts/deploy_newapi.sh
```

脚本只绑定远端 `127.0.0.1:8200`。首次注册前保持防火墙关闭该端口，建立
SSH tunnel：

```bash
ssh -N -L 8200:127.0.0.1:8200 -i <KEY> <SSH_TARGET>
```

仅访问本机 `http://127.0.0.1:8200` 完成 root 账号注册，并把密码保存到密码
管理器。注册和登录验证成功后，再配置带 TLS 的 Caddy/Nginx 反向代理；先
验证 HTTPS、认证和来源限制，再按需开放 `443/tcp`。禁止开放 `<NEWAPI_PORT>`。

---

## Phase 3 — 渠道 + Token

### 3a. 创建渠道（CLIProxyAPI as upstream）

NewAPI 后台 → "渠道" → 新建 → OpenAI 类型：

- **base_url**：`http://172.17.0.1:<CLIPROXY_PORT>`
  ⚠️ **不能写 `127.0.0.1`** — 容器里的 127.0.0.1 是容器自己。详见
  `references/troubleshooting.md` "容器网络速记"。
- **密钥**：CLIProxyAPI 的 `cpa_xxx` key
- **模型**：以逗号分隔填 CLIProxyAPI 暴露的虚拟模型名，例如：
  `gpt-5.4,gpt-5.3-codex,gpt-5.3-codex-spark,gpt-5.4-mini,gpt-5.2`
- 测试按钮应当 200 OK；失败先查 `references/troubleshooting.md`。

### 3b. 创建 Token（客户端用）

NewAPI 后台 → "令牌" → 新建：
- **名称**：`client-default` 之类标识
- **额度**：先放 `unlimited` 或一个大数（实际计费由 user.quota 控制）
- **可用模型**：勾上你给客户端开放的模型
- 复制生成的 `sk-xxx`（这是客户端的 BASE_API_KEY）

---

## Phase 4 — 写价格 + 充额度

### 4a. 写价格

用 `scripts/set_pricing.py`（基于实测 USD/1M 自动算出三个倍率）：

```bash
SSH_TARGET=root@<HOST> SSH_KEY=~/.ssh/id_ed25519 \
  scripts/set_pricing.py \
    --model gpt-5.4       --input 2.5  --cached 0.25  --output 15 \
    --model gpt-5.3-codex --input 1.75 --cached 0.175 --output 14
```

脚本会：合并写入 `options` 表的 `ModelRatio` / `CacheRatio` / `CompletionRatio`，重启容器。

⚠️ 倍率语义见 `references/newapi-pricing.md` —— `CacheRatio` / `CompletionRatio` 是**相对
输入价的倍数**，不是绝对单价。`ModelRatio` 在不同 fork 里可能除以 2，第一次配置务必发请求
看 `logs.quota` 实际值匹配预期。

### 4b. 充额度

NewAPI 在线充值通常未配。需要紧急修正额度时，可使用参数化 SQLite helper：
```bash
SSH_TARGET=root@<HOST> SSH_KEY=~/.ssh/id_ed25519 \
  scripts/topup.sh <user_id> <quota>
# 例：1 1000000000  → 1B quota ≈ USD 2000 (默认 QuotaPerUnit=500000)
```

### 4c. 配置在线充值（可选）

如果要让用户自助充值，NewAPI 后台 → 系统 → 支付：
- Stripe / 易支付 / 自定义 → 填 `TopUpLink` 等字段
- 不配在线充值时，管理员可使用经验证的 `scripts/topup.sh`；输入必须为整数，脚本会参数化 SQL 并验证恰好更新一行

---

## Phase 5 — 客户端环境变量

只把非敏感配置写入客户端 shell 配置：

```bash
export BASE_URL="https://<NEWAPI_DOMAIN>/v1"
export BASE_MODEL="<虚拟模型名>"       # 如 gpt-5.4
```

API key 必须存进 Keychain 或其他密码管理器，在当前进程启动前读取；禁止写入
`~/.zshrc`、聊天、脚本或命令行参数。例如 macOS 可使用：

```bash
export BASE_API_KEY="$(security find-generic-password -s newapi-client -a client-default -w)"
```

跨多台机器同步时（W-14 文件归属）：单台单台手动 SSH 改各自的 rc 文件，避免并行写覆盖。

---

## Phase 6 — 加新账号（OpenAI/Anthropic/etc）

不需要重启服务，CLIProxyAPI 有 file watcher。

最简单：
```bash
PROVIDER=codex \
  SSH_TARGET=root@<HOST> SSH_KEY=~/.ssh/id_ed25519 \
  CLIPROXY_LOCAL=<本地 CLIProxyAPI 仓库路径> \
  scripts/add_codex_account.sh
```

脚本流程：
1. 本地启 `go run ./cmd/server -<provider>-login -config config.yaml`
2. 浏览器**用新账号**登录（先在浏览器登出旧账号或用无痕窗口 — 否则会复用旧 session 把旧凭据
   覆盖回去）
3. 自动 diff `~/.cli-proxy-api/<provider>-*.json`，把新文件 `scp` 到 VPS
4. tail VPS 日志确认 `auth file changed (CREATE)`

详见 `references/multi-account.md`（含订阅条件、轮询语义、删除账号、验证方法）。

---

## 验证（Phase 4/5/6 之后必跑）

```bash
SSH_TARGET=root@<HOST> SSH_KEY=~/.ssh/id_ed25519 \
  CLIPROXY_URL=http://127.0.0.1:<TUNNELED_CLIPROXY_PORT> \
  NEWAPI_URL=https://<NEWAPI_DOMAIN> \
  CLIPROXY_KEY="$(security find-generic-password -s cliproxy-admin -w)" \
  NEWAPI_TOKEN="$(security find-generic-password -s newapi-client -a client-default -w)" \
  MODEL=<虚拟模型> INPUT_USD_PER_M=<输入价> OUTPUT_USD_PER_M=<输出价> \
  QUOTA_PER_UNIT=500000 \
  scripts/verify_stack.sh
```

通过判定：
- 直连 CLIProxyAPI HTTP 200
- 经 NewAPI HTTP 200
- `logs` 中对应 `request_id`、模型和 token 数匹配本次请求
- 实际 `quota` 与目标输入/输出价格计算结果的误差不超过 5%（且至少允许 1 quota 的整数舍入）

任一不满足都不得声称"部署完成"。

---

## 资源索引

| 文件 | 用途 |
|---|---|
| `scripts/deploy_newapi.sh` | NewAPI 容器一键部署 + 健康自检 |
| `scripts/set_pricing.py` | 用 USD/1M 三参数自动写 NewAPI ratios |
| `scripts/topup.sh` | 直接 SQLite 改 `users.quota` |
| `scripts/verify_stack.sh` | 双路径 + 计费日志验证 |
| `scripts/add_codex_account.sh` | OAuth 登录 + 同步凭据 + watcher 校验 |
| `agents/openai.yaml` | 需要独立复核高风险部署或计费方案时的 agent 配置 |
| `references/newapi-pricing.md` | ModelRatio / CacheRatio / CompletionRatio / QuotaPerUnit 完整语义 + 计算示例 |
| `references/troubleshooting.md` | 容器网络、cooldown、PUT 不生效、UFW 等踩坑表 |
| `references/multi-account.md` | 多账号轮询语义 + 加号 / 删号 / 订阅条件 |

---

## 不要做的事

- ❌ NewAPI 渠道 base_url 写 `http://127.0.0.1:<port>`（容器内自指）
- ❌ 把 `CacheRatio` 当绝对单价（实际是相对输入的倍数）
- ❌ 价格只走 `/api/option/` PUT 不验证（已知该接口可能静默失败）
- ❌ 远端 OAuth 隧道折腾（5 分钟窗口 + 隧道配合，已踩过坑，统一用本地登录 + scp）
- ❌ 把 CLIProxyAPI 公网端口的 `cpa_` key 和 NewAPI 的 `sk-` token 共享给同一类客户端
- ❌ 跨会话声称"价格生效"——必须本会话发请求 + 看 `logs.quota`
- ❌ 在没有 `disable-cooling: true` 的情况下做高并发压测
