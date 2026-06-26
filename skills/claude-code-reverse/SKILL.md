---
name: claude-code-reverse
description: 静态逆向本机 Claude Code 原生二进制，提取字符串、UI 文案、prompt、计费/额度逻辑与功能实现。当用户要 扒/逆向/拆解/看看 Claude Code 内部真实代码或字符串、验证某条关于 CC 行为的说法、对比两个 CC 版本、或搞清某功能（Fable credits、@claude、Slack connector、tool_reference 等）到底如何实现时使用。只读，不改二进制。
allowed-tools: Bash, Read
metadata:
  argument-hint: '[锚点字符串 | dump [版本] | diff <vA> <vB> <锚点>]'
---

# Claude Code Reverse

静态逆向本机 Claude Code（native 安装）提取实现细节。所有命令只读，不改二进制。

## 1. 定位二进制

native 安装（当前主流，非 npm）：

```bash
readlink "$HOME/.local/bin/claude"
# → ~/.local/share/claude/versions/<version>   Mach-O arm64, Bun 单文件可执行
ls "$HOME/.local/share/claude/versions/"          # 保留多版本 → 可做版本 diff
cat "$HOME/.claude/.last-update-result.json"      # 升级记录 (version_from / version_to)
```

npm 安装则在 `$(npm root -g)/@anthropic-ai/claude-code/`。

## 2. strings 存盘（一次性，别反复遍历）

215MB 二进制每次 `strings` 都要几秒。先 dump 到文本：

```bash
BIN=$(readlink "$HOME/.local/bin/claude")
strings "$BIN" > /tmp/cc_strings.txt     # ~39 万行 / 28MB，后续 grep 飞快
```

## 3. 检索模式

字面 / 计数：

```bash
grep -F "Fable 5" /tmp/cc_strings.txt | sort -u
grep -cF "purchased separately" /tmp/cc_strings.txt
```

版本 diff（验证"某版加了/删了 X"）：

```bash
for v in 2.1.190 2.1.191; do
  strings ~/.local/share/claude/versions/$v | grep -i fable | sort -u > /tmp/f_$v.txt
done
diff /tmp/f_2.1.190.txt /tmp/f_2.1.191.txt
```

## 4. 上下文截取（minified JS 必备技巧）

**坑：macOS 的 `grep` 实为 ugrep，对 `.{0,N}` 范围量词报 "exceeds complexity limits"。** 改用：

awk substr（按单行，strings 已按 null 切分；适合普通 minified 代码）：

```bash
awk 'index($0,"slack.mcp.claude.com"){i=index($0,"slack.mcp.claude.com"); print substr($0,i>500?i-500:1,1500)}' /tmp/cc_strings.txt
```

perl slurp（跨字符；适合含字面 `\n` 的 template literal / JSON / YAML 文档）：

```bash
perl -0777 -ne 'while(/(.{0,600}Validate connections.{0,1600})/gs){print "$1\n"}' /tmp/cc_strings.txt
```

## 5. 过滤 minified 噪声

大数组（如 spinner tips）把几十条目压一行，`grep` 整行就刷屏。过滤：

```bash
awk 'length>60 && length<2500 && !/isRelevant|cooldownSessions|=>\{|function\(/' /tmp/cc_strings.txt
```

输出仍可能很大 → 重定向 `> /tmp/out.txt` 再用 Read 工具看，别直接刷屏。

## 6. 侦察地图（已知内部结构 → 锚点）

| 找什么 | 锚点关键词 |
|---|---|
| 模型自述 system prompt | `This iteration of Claude` / `Mythos` |
| 计费 / 额度文案 | `usage credits` / `Fable 5` / `purchased separately` / `usage limit reached` |
| connector 体系 | `slack.mcp.claude.com` / `claudeai-proxy` / `tool_reference` / `Connected connectors` |
| 安全分类器 prompt | `Data Exfiltration` / `visible action` / `Interfere With Workloads` |
| 功能开关 | `~/.claude/policy-limits.json`（restrictions / compliance_taints）|
| UI 提示 tips | `isRelevant` / `cooldownSessions` |

## 7. 静态扒不到的边界（别浪费时间）

- 远程 MCP 工具 description（`tools/list` 运行时下发，本地不缓存）
- 服务端 prompt（Claude-in-Slack / Tag Claude 等跑在 Anthropic 后端）
- minified 变量真实名（如 prompt 里的 `${v8e}`，需运行时 hook）
- 编译 / 优化掉的逻辑

## 8. 伦理

只逆向自己机器上合法安装的软件，用于理解行为 / 验证说法 / 学习。不用于绕过计费、破解授权或再分发。

---

辅助脚本：同目录 `extract.sh` —— 封装"定位最新二进制 + strings 存盘 + 锚点上下文截取 + 两版本 diff"。用法：`./extract.sh`（存盘）/ `./extract.sh <锚点>` / `./extract.sh diff <vA> <vB> <锚点>`。
