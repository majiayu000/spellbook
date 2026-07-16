---
name: gemma4-local-deploy
description: 在本机 Mac 或 Apple Silicon 上部署 Gemma 4 12B。本地安装/升级 llama.cpp，下载 GGUF 量化模型，用 llama-server 暴露 OpenAI-compatible API，或用 Ollama 暴露本地模型服务；按用户需求在默认 Q4_K_M、64K/128K 长上下文、QAT Q4_0 @ 256K、左右对比演示之间选择，配置 tmux 后台运行，验证健康检查、问答接口、资源占用和常见故障。当用户说部署 Gemma 4、Gemma 4 12B、本地大模型、长上下文、QAT、量化、llama-server、Ollama、GGUF、Mac 本地模型服务时使用。
allowed-tools: Bash, Read, WebSearch, WebFetch
metadata:
  argument-hint: "[模型量化/端口/是否后台运行]"
---

# Gemma 4 12B 本地部署

把 Gemma 4 12B 的 GGUF 版本部署成本机模型服务。默认使用 `llama.cpp` / `llama-server`、Apple Metal、`Q4_K_M` 和 `tmux`，只监听 loopback；用户明确要求 QAT、256K、对比演示或 Ollama 时才切换路线。

## Operating Contract

- Direct actions: 读取本机硬件、磁盘、端口、进程和模型缓存；在用户已要求本地部署时，安装或升级明确的软件包、下载选定模型、创建专用模型目录和 tmux 会话，并只绑定 `127.0.0.1`。
- Escalate before: 停止不属于本 Skill 的现有进程、覆盖已有模型或配置、删除用户数据、监听公网地址、改变防火墙，或下载用户未选择的大型模型变体。
- Evidence-backed pushback: 如果用户指定的模型标签、上下文、内存预算或本机能力与当前可验证状态冲突，先展示命令输出并提出可运行的 profile，不伪造支持状态。
- Feedback loop: 现状检查 → 选择并复述 profile → 执行一条部署路线 → 当前会话完成健康、模型和聊天验证 → 报告端点、资源与限制。

## 默认选择

- 默认模型仓库：`ggml-org/gemma-4-12B-it-GGUF`
- 默认量化：`Q4_K_M`
- 默认模型名：`gemma-4-12b-it`
- 默认端点：`http://127.0.0.1:8080`
- 默认上下文：`32768`
- 12B 长上下文：用户明确要求时选择 `65536` 或 `131072`
- QAT 仓库：`google/gemma-4-12B-it-qat-q4_0-gguf`
- QAT profile：`Q4_0`、`262144` 上下文
- 默认后台会话：`gemma4-12b`
- 默认关闭 thinking：`--reasoning off`，避免 OpenAI API 的 `message.content` 为空
- Ollama：只在用户明确要求 Ollama 或需要 Ollama 生态时使用

QAT 是训练时模拟量化，不等于无损。关键任务仍要用当前会话的真实响应验证。用户明确要更高质量时，优先建议 `Q6_K` 或 `Q8_0`；除非用户接受更高内存和更慢加载，不默认使用 `bf16`。

## Profile 选择

| Profile | 适用场景 | Model / quant | Context | Port / alias |
|---|---|---|---:|---|
| `daily-q4km-32k` | 默认日常聊天、编码、低风险本地 API | `ggml-org/...:Q4_K_M` | `32768` | `8080` / `gemma-4-12b-it` |
| `long-q4km-128k` | 明确需要更长上下文，但保留默认 GGUF 路线 | `ggml-org/...:Q4_K_M` | `65536` 或 `131072` | `8080` / `gemma-4-12b-it` |
| `qat-q4_0-256k` | 明确要求 QAT、Q4_0、256K 或低内存长上下文 | `google/...qat-q4_0-gguf:Q4_0` | `262144` | `8080` / `gemma-4-12b-it-qat-q4_0` |
| `compare-32k-vs-256k` | 录屏、演示或 A/B 比较资源与速度 | 左 `Q4_K_M`，右 `QAT Q4_0` | `32768` + `262144` | `8080` + `8081` |

最终回复必须说明选定 profile、端口、上下文和选择依据。不要把 256K 当作日常默认值。

## 执行流程

### 1. 搜索并确认现状

先检查已有安装、进程、端口、缓存、硬件和磁盘，避免重复部署：

```bash
command -v llama-server || true
llama-server --version || true
tmux has-session -t gemma4-12b 2>/dev/null && tmux display-message -p -t gemma4-12b '#S #{pane_pid}' || true
lsof -nP -iTCP:8080 -sTCP:LISTEN || true
ls -lh "$HOME/Library/Caches/llama.cpp/"*gemma-4-12B-it*Q4_K_M*.gguf 2>/dev/null || true
find "$HOME/Library/Caches/llama.cpp" "$HOME/Models" \( -name '*gemma-4-12b-it-qat-q4_0*.gguf' -o -name '*gemma-4-12B-it-qat-q4_0*.gguf' \) 2>/dev/null || true
system_profiler SPHardwareDataType | sed -n '1,30p'
df -h "$HOME"
```

这些 `|| true` 只用于允许“尚未安装/尚未运行”这一预期发现结果；必须展示实际输出，不能把查询失败描述成部署成功。

### 2. 执行一条部署路线

- `daily-q4km-32k`、`long-q4km-128k`、`qat-q4_0-256k` 或 `compare-32k-vs-256k`：先读并执行 [llama.cpp 部署路线](references/llama-cpp.md)。
- 用户明确要求 Ollama：先读并执行 [Ollama 部署路线](references/ollama.md)。
- 不要同时混用两条路线，也不要在没有端口检查的情况下启动第二个服务。

### 3. 验证并报告

部署后必须读取并执行 [验证、资源与排障](references/verification.md)。成功至少需要当前会话证明：

- `/health` 返回健康状态
- `/v1/models` 或 Ollama 模型列表包含选定模型
- 用户要求长上下文时，运行时报告实际 `n_ctx`
- 一次聊天响应的正文非空
- 端点仍只监听预期的本机地址和端口

## Final response shape

默认用中文回答，并包含：

- 实际 endpoint URL 和 model id
- 选定 profile、量化与上下文
- tmux/session 管理命令
- 当前会话的验证结果
- 实际资源摘要、失败项和限制

没有验证数据时写“未验证”，不能用计划值代替运行值。

## Cross-check

部署计划涉及超出默认 profile 的模型、上下文或资源判断时，使用
[`agents/openai.yaml`](agents/openai.yaml) 做独立复核；复核不能替代当前会话的本机验证。
