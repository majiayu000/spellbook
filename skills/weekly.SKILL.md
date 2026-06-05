---
name: weekly
description: 当用户要求生成 om-generator 前后端周报、按日期范围汇总提交/任务/进展时使用。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task, mcp__plugin_claude-mem_mcp-search__search, mcp__plugin_claude-mem_mcp-search__timeline, mcp__plugin_claude-mem_mcp-search__get_observations
metadata:
  argument-hint: "<日期范围，如 2-1到2-7>"
---

# 生成周报

根据用户提供的日期范围 `$ARGUMENTS`，收集 om-generator 前后端两个仓库的工作记录，生成周报文档。

## 步骤 1：解析日期范围

从 `$ARGUMENTS` 中提取起止日期。支持格式：
- `2-1到2-7` → 2026-02-01 ~ 2026-02-07
- `1-27到2-2` → 2026-01-27 ~ 2026-02-02
- `2026-02-01到2026-02-07` → 完整日期
- 无参数 → 默认本周一到今天

将解析结果存为变量 `DATE_START` 和 `DATE_END`（格式 YYYY-MM-DD）。年份默认 2026。

## 步骤 2：收集 Git 提交记录

先获取当前用户名：
```bash
git config user.name
```

然后分别从两个仓库收集该用户在日期范围内的提交：

**前端仓库**：
```bash
git -C $HOME/Desktop/code/work/mutil-om/om-generator-web log --author="<用户名>" --after="<DATE_START>" --before="<DATE_END + 1天>" --oneline --no-merges --all
```

**后端仓库**：
```bash
git -C $HOME/Desktop/code/work/mutil-om/om-generator log --author="<用户名>" --after="<DATE_START>" --before="<DATE_END + 1天>" --oneline --no-merges --all
```

对每个有意义的提交，用 `git show --stat <hash>` 查看改动范围。

## 步骤 3：收集 Claude Code 会话记录

读取两个项目的 sessions-index.json：

- 前端：`~/.claude/projects/<om-generator-web 绝对路径转义>/sessions-index.json`
- 后端：`~/.claude/projects/<om-generator 绝对路径转义>/sessions-index.json`

> 注：Claude Code 把项目 cwd 绝对路径转义为目录名（`/` 替换为 `-`），例如 `$HOME/Desktop/code/work/mutil-om/om-generator` → `-Users-<用户名>-Desktop-code-work-mutil-om-om-generator`。

JSON 结构为 `{ version, entries: [{ sessionId, summary, firstPrompt, created, modified, gitBranch, messageCount }] }`。

过滤 `created` 或 `modified` 在日期范围内的会话，提取 `summary` 和 `firstPrompt`。

## 步骤 4：收集 Codex 会话记录

遍历日期范围内每天的 Codex 会话目录：
```
~/.codex/sessions/2026/MM/DD/*.jsonl
```

对每个 JSONL 文件，读取第一行（`type: session_meta`），检查 `payload.cwd` 是否包含 `om-generator`。
如果匹配，提取：
- `payload.cwd` — 工作目录（区分前端/后端）
- `payload.timestamp` — 会话时间
- `payload.git.branch` — 分支

然后读取文件中 `type` 为 `message` 且 `payload.role` 为 `user` 的第一条消息作为会话主题。

## 步骤 5：查询 claude-mem 记忆系统

使用 MCP search 工具搜索日期范围内的记忆记录：
```
search(query="om-generator", dateStart="<DATE_START>", dateEnd="<DATE_END>")
```

提取相关的 session 摘要和工作记录，补充到周报中。

## 步骤 6：分类整理

将所有收集到的信息按以下类别分类：

1. **架构重构** — 代码结构调整、模块拆分、技术债清理
2. **新功能** — 新增的用户可见功能
3. **Bug 修复** — 问题修复
4. **研究与设计** — 技术调研、方案设计、原型验证
5. **其他** — 文档、配置、依赖更新等

每个条目包含：
- 简短描述（一句话）
- 涉及的仓库（前端/后端/两者）
- 关键改动文件（可选）

## 步骤 7：生成周报文档

输出文件路径：`$HOME/Desktop/code/work/mutil-om/docs/weekly/YYYY-MM-DD_to_YYYY-MM-DD.md`

文档格式：

```markdown
# OM Generator 周报

**周期**: YYYY-MM-DD ~ YYYY-MM-DD
**作者**: <git user.name>

---

## 本周概要

<!-- 2-3 句话总结本周主要工作方向和成果 -->

## 工作详情

### 架构重构
- [ 条目 ]

### 新功能
- [ 条目 ]

### Bug 修复
- [ 条目 ]

### 研究与设计
- [ 条目 ]

### 其他
- [ 条目 ]

---

## 数据来源

### Git 提交统计
- 前端 (om-generator-web): X 个提交
- 后端 (om-generator): X 个提交

### AI 辅助会话
- Claude Code 会话: X 个
- Codex 会话: X 个
```

## 注意事项

- 全部使用中文
- 只统计当前 git 用户的提交，不包含其他人的
- 如果某个数据源为空（如没有 Codex 会话），跳过该部分，不要生成空节
- 合并重复内容：同一个功能可能在 git 提交和 AI 会话中都有记录，合并为一条
- 周报应该是人类可读的总结，不是原始数据的罗列
