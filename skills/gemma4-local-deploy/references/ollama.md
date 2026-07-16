# Ollama 部署路线

只在用户明确要求 Ollama、需要 Ollama 生态，或询问 `ollama pull gemma4:12b` 时读取本文件。Ollama registry 状态可能变化，执行当时必须重新验证，不能复用旧结论。

## 安装与启动

```bash
brew install ollama
ollama --version
lsof -nP -iTCP:11434 -sTCP:LISTEN || true
tmux new-session -d -s ollama-gemma4 'OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 ollama serve'
curl -fsS http://127.0.0.1:11434/api/version
```

先尝试官方 tag：

```bash
ollama pull gemma4:12b
ollama run gemma4:12b "用一句中文回答：现在可以问你问题吗？"
```

如果明确返回 `pull model manifest: file does not exist`，再回退到 GGUF 导入：

```bash
mkdir -p "$HOME/Models/gemma4-12b"
huggingface-cli download ggml-org/gemma-4-12B-it-GGUF \
  gemma-4-12B-it-Q4_K_M.gguf \
  --local-dir "$HOME/Models/gemma4-12b"
```

创建 `$HOME/Models/gemma4-12b/Modelfile`：

```text
FROM /Users/<current-user>/Models/gemma4-12b/gemma-4-12B-it-Q4_K_M.gguf
```

用当前用户的真实绝对路径替换占位内容。不要把未展开的 `$HOME` 写进需要静态路径的 Modelfile。

Homebrew `ollama` 构建如果报告缺少 `llama-server` / `llama-quantize` sidecar，才创建专用工作目录并链接已安装的 `llama.cpp` 二进制：

```bash
mkdir -p "$HOME/ollama-gemma4/build/lib/ollama"
ln -sf /opt/homebrew/bin/llama-server "$HOME/ollama-gemma4/build/lib/ollama/llama-server"
ln -sf /opt/homebrew/bin/llama-quantize "$HOME/ollama-gemma4/build/lib/ollama/llama-quantize"
tmux kill-session -t ollama-gemma4 2>/dev/null || true
tmux new-session -d -s ollama-gemma4 "cd '$HOME/ollama-gemma4' && OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 ollama serve"
```

导入并验证：

```bash
ollama create gemma4-12b-gguf-local -f "$HOME/Models/gemma4-12b/Modelfile"
ollama list
ollama run gemma4-12b-gguf-local "用一句中文回答：Ollama 能跑 Gemma 4 12B 吗？"
```

最终必须区分实际成功路线：

- 官方 registry：`ollama pull gemma4:12b`
- 手工 GGUF：`ollama create gemma4-12b-gguf-local`
- 是否使用了 sidecar 链接 workaround
