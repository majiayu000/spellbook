# Claude Code Static Analysis Notes

只在目标明确是 Claude Code 时读取本页。

## 定位安装

原生安装通常通过以下路径暴露当前版本：

```bash
readlink "$HOME/.local/bin/claude"
ls "$HOME/.local/share/claude/versions/"
cat "$HOME/.claude/.last-update-result.json"
```

若是 npm 安装，先用 `command -v claude` 定位入口，再沿符号链接确认实际文件。不要把整个 npm 包目录交给 `extract.sh`；传入精确入口文件或包内目标文件。

## 常用锚点

| 要验证的表面 | 候选字面锚点 |
|---|---|
| 模型自述或客户端 prompt | `This iteration of Claude`、模型代号、已观察到的完整短句 |
| 计费或额度文案 | `usage credits`、`purchased separately`、`usage limit reached` |
| connector 体系 | `slack.mcp.claude.com`、`claudeai-proxy`、`tool_reference` |
| 安全分类器文案 | `Data Exfiltration`、`visible action`、`Interfere With Workloads` |
| 功能开关 | 已知配置键或 `policy-limits.json` |
| UI 提示 | 用户界面上可逐字确认的短句 |

锚点只是检索入口，不是预设结论。版本变化后，旧锚点可能不存在；如无命中，报告无命中，不要编造替代字段。

## Minified JavaScript 上下文

脚本的 `search` 使用字面匹配和 `awk substr`，避免 macOS 上某些 grep 实现对大范围量词的复杂度限制。若必须跨字符串边界检索，可对私有 cache 文件使用 `perl -0777`，但先限制上下文窗口和匹配次数，避免把整份 minified bundle 输出到对话。

## 不能由本地静态文件证明的内容

- 运行时通过 `tools/list` 等接口下发的远程 MCP 描述。
- Anthropic 服务端 prompt、策略和远程 feature flag 当前值。
- 混淆变量的真实业务名。
- 某个字符串对应的代码路径在当前账户、平台或版本上实际可达。

这些问题需要服务端、网络或运行时证据。不要把本地 bundle 中的相邻文本当成服务端当前行为。
