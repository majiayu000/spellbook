# llama.cpp 部署路线

只在主 `SKILL.md` 已选择 llama.cpp profile 后读取本文件。

## 安装或升级

在 macOS 上使用 Homebrew：

```bash
brew install llama.cpp
# 已安装时只升级这个包。
brew upgrade llama.cpp
llama-server --version
```

Gemma 4 GGUF 要求 `llama.cpp` 能识别 `general.architecture = gemma4`。如果加载时报 `unknown model architecture: 'gemma4'`，升级后再试；不要把升级前的失败当作模型损坏。

## 下载并加载模型

默认 `daily-q4km-32k` 可让 `llama-server -hf` 完成首次下载：

```bash
llama-server \
  -hf ggml-org/gemma-4-12B-it-GGUF:Q4_K_M \
  --no-mmproj \
  --ctx-size 32768 \
  --gpu-layers 99 \
  --parallel 1 \
  --reasoning off \
  --host 127.0.0.1 \
  --port 8080 \
  --alias gemma-4-12b-it
```

缓存后优先用本地路径启动。常见路径：

```text
$HOME/Library/Caches/llama.cpp/ggml-org_gemma-4-12B-it-GGUF_gemma-4-12B-it-Q4_K_M.gguf
```

`qat-q4_0-256k` 使用 Google QAT GGUF：

```bash
llama-server \
  -hf google/gemma-4-12B-it-qat-q4_0-gguf:Q4_0 \
  --ctx-size 262144 \
  --gpu-layers 99 \
  --parallel 1 \
  --flash-attn on \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --reasoning off \
  --host 127.0.0.1 \
  --port 8080 \
  --alias gemma-4-12b-it-qat-q4_0
```

需要显式、可复用下载位置时：

```bash
mkdir -p "$HOME/Models/gemma4-qat"
huggingface-cli download google/gemma-4-12B-it-qat-q4_0-gguf \
  gemma-4-12b-it-qat-q4_0.gguf \
  --local-dir "$HOME/Models/gemma4-qat"
```

## 用 tmux 持久运行

确认端口空闲且会话不存在后，默认 profile：

```bash
tmux new-session -d -s gemma4-12b 'llama-server -m "$HOME/Library/Caches/llama.cpp/ggml-org_gemma-4-12B-it-GGUF_gemma-4-12B-it-Q4_K_M.gguf" --ctx-size 32768 --gpu-layers 99 --parallel 1 --reasoning off --host 127.0.0.1 --port 8080 --alias gemma-4-12b-it'
```

如果目标 shell 的单引号环境不展开 `$HOME`，先查得绝对模型路径并替换，不要猜路径。

QAT 256K profile：

```bash
tmux new-session -d -s gemma4-qat-256k 'llama-server -m "$HOME/Models/gemma4-qat/gemma-4-12b-it-qat-q4_0.gguf" --ctx-size 262144 --gpu-layers 99 --parallel 1 --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0 --reasoning off --host 127.0.0.1 --port 8080 --alias gemma-4-12b-it-qat-q4_0'
```

对比 profile 使用不同会话与端口：

```bash
tmux new-session -d -s gemma4-left-32k 'llama-server -m "$HOME/Library/Caches/llama.cpp/ggml-org_gemma-4-12B-it-GGUF_gemma-4-12B-it-Q4_K_M.gguf" --ctx-size 32768 --gpu-layers 99 --parallel 1 --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0 --reasoning off --host 127.0.0.1 --port 8080 --alias gemma-4-12b-it'
tmux new-session -d -s gemma4-right-256k 'llama-server -m "$HOME/Models/gemma4-qat/gemma-4-12b-it-qat-q4_0.gguf" --ctx-size 262144 --gpu-layers 99 --parallel 1 --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0 --reasoning off --host 127.0.0.1 --port 8081 --alias gemma-4-12b-it-qat-q4_0'
```

管理命令：

```bash
tmux attach -t gemma4-12b
tmux kill-session -t gemma4-12b
tmux kill-session -t gemma4-qat-256k
tmux kill-session -t gemma4-left-32k
tmux kill-session -t gemma4-right-256k
```

停止现有会话属于写操作；只停止本 Skill 创建且用户明确要替换的会话。

## 长上下文

`32768` 是保守默认值，不是 12B 的唯一上限。按用户目标选择：

| 用户需求 | `--ctx-size` | 说明 |
|---|---:|---|
| 日常聊天 / 低内存 | `32768` | 默认。 |
| 长编码会话或中型文档 | `65536` | 16GB+ Mac 可尝试，仍要观察内存压力。 |
| 最大原生 12B 上下文 | `131072` | 只在用户明确要求时使用；RSS 更高、速度更低。 |
| 超过原生上下文 | 默认避免 | 需要缩放并可能损失质量，尝试前先解释风险。 |

使用 Flash Attention 和量化 KV cache 降低长上下文压力：

```bash
tmux kill-session -t gemma4-12b 2>/dev/null || true
tmux new-session -d -s gemma4-12b 'llama-server -m "$HOME/Library/Caches/llama.cpp/ggml-org_gemma-4-12B-it-GGUF_gemma-4-12B-it-Q4_K_M.gguf" --ctx-size 131072 --gpu-layers 99 --parallel 1 --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0 --reasoning off --host 127.0.0.1 --port 8080 --alias gemma-4-12b-it'
```

模型路径不同时先查找：

```bash
find "$HOME/Library/Caches/llama.cpp" "$HOME/Models" -name '*gemma-4-12B-it*Q4_K_M*.gguf 2>/dev/null
```

启动后必须从 `/v1/models` 证明实际上下文，而不是复述命令行计划：

```bash
curl -fsS http://127.0.0.1:8080/v1/models | jq '.data[0].meta | {n_ctx, n_ctx_train, n_params, size}'
```

如果启动失败或内存压力过高，回退到 `65536` 并重新验证。
