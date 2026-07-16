# 验证、资源与排障

部署完成后必须在当前会话运行本文件中的适用检查。没有真实输出时不能宣称成功。

## llama.cpp 验证

```bash
curl -fsS http://127.0.0.1:8080/health
curl -fsS http://127.0.0.1:8080/v1/models
curl -fsS http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"gemma-4-12b-it","messages":[{"role":"user","content":"用一句中文回答：现在可以问你问题吗？"}],"max_tokens":80,"temperature":0.2}'
```

成功需要：

- `/health` 返回 `{"status":"ok"}`
- `/v1/models` 包含选定 alias
- 长上下文请求的实际 `n_ctx` 与选择一致
- `choices[0].message.content` 非空
- `lsof -nP -iTCP:8080 -sTCP:LISTEN` 显示预期监听状态

QAT alias 不同时要同步修改聊天请求的 `model`，不要用错误 model id 制造假失败。

## Ollama 验证

```bash
curl -fsS http://127.0.0.1:11434/api/version
ollama list
```

再对实际安装的 model id 运行一次 `ollama run`，正文必须非空。

## 资源使用

llama.cpp 路线使用实际 PID：

```bash
pid=$(pgrep -f 'llama-server .*gemma-4-12B-it' | head -1)
ps -p "$pid" -o pid,stat,%cpu,%mem,rss,vsz,etime,command
footprint -p "$pid" -summary 2>/dev/null | sed -n '1,80p'
memory_pressure | sed -n '1,20p'
```

解释时区分：

- GGUF 文件大小、进程 RSS 和 `footprint` 物理压力不是同一指标。
- Apple Silicon 使用统一内存，不会出现独立 NVIDIA 风格 VRAM 数字。
- 更大的 `--ctx-size` 会增加 KV/cache 内存，并可能降低短提示速度。
- 只报告本次命令的数字，不复用旧机器上的近似值。

## Troubleshooting

| Symptom | Fix |
|---|---|
| `unknown model architecture: 'gemma4'` | 升级 `llama.cpp` 后重试。 |
| 端口 8080 忙 | 用 `lsof` 展示监听者；由用户决定停止它还是换端口。 |
| Chat `content` 为空、只有 reasoning | 用 `--reasoning off` 重启并复验。 |
| 首次 `-hf` 卡在 metadata resolution | 查找已缓存 GGUF，改用 `-m` 本地路径。 |
| `ollama pull gemma4:12b` 返回 manifest 不存在 | 当前官方 tag 不可用；按 Ollama 参考文档手工导入 GGUF。 |
| Ollama 报 `llama-server` / `llama-quantize` 不存在 | 只在确认错误后使用 `llama.cpp` sidecar 链接 workaround。 |
| 用户需要图片/多模态 | 只有完成 `mmproj` 兼容验证后才移除 `--no-mmproj`。 |
| 内存过高 | 降低 context、使用 `Q4_K_M`、保持 `--parallel 1`，然后重新测量。 |
