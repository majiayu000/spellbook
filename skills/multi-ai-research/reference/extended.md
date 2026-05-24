# multi-ai-research Extended Reference

This file preserves detailed material moved out of `SKILL.md` for progressive disclosure. Load it only when the current task needs the specific examples, commands, templates, or checklists below.

Moved content starts at: `## Phase 0: Pre-flight Prerequisites（强制检查）`.

## Phase 0: Pre-flight Prerequisites（强制检查）

运行前**必须**按顺序检查，任一失败停止流程并向用户报告：

### 0.1 CLI 可用性

```bash
# opencli 存在
which opencli || echo "🔴 opencli 未安装"
opencli --version 2>&1 | head -1

# twitter-cli 存在（如果任务涉及 X 数据）
which twitter 2>&1
```

### 0.2 环境变量（grok 必需）

```bash
echo "OPENCLI_BROWSER_COMMAND_TIMEOUT=${OPENCLI_BROWSER_COMMAND_TIMEOUT:-未设置}"
```

如果**未设置**：
- **不要静默跳过**，否则 grok 会 60s 硬截断
- 在每次 Bash 调用时**强制前置**：`OPENCLI_BROWSER_COMMAND_TIMEOUT=300 opencli grok ask ...`
- 或提示用户在 shell rc 加 `export OPENCLI_BROWSER_COMMAND_TIMEOUT=300`

### 0.3 登录状态（手动）

首次运行时提醒用户确认：
- grok.com 在 Chrome 已登录（Premium/Premium+）
- gemini.google.com 在 Chrome 已登录（Advanced）

### 0.4 Claude Code Agent 工具可用

- 当前 session 能调 `general-purpose` subagent（用于内部数据任务）
- 能用 `run_in_background=true` 参数

### 0.5 数据源健康检查（针对 domain 特定场景）

如果研究问题涉及**内部数据分析**，先跑数据健康检查：

**示例：X reply 场景**
```python
# 检查 reply_tracking 数据完整度
import sqlite3
conn = sqlite3.connect('/path/to/tracker.db')

# Pending 堆积（collector bug 指示）
stale = conn.execute("""
    SELECT COUNT(*) FROM reply_tracking
    WHERE check_stage='pending'
      AND posted_at < datetime('now', '-24 hour')
""").fetchone()[0]

# 关键字段覆盖率
by_type = conn.execute("""
    SELECT type, COUNT(*) as total,
           SUM(CASE WHEN check_stage='pending' THEN 1 ELSE 0 END) as pending
    FROM reply_tracking
    GROUP BY type
""").fetchall()

# 硬阈值判断
if stale > 50:
    print("🔴 >50 条 reply 永久 pending，疑似 collector bug，先修再 research")
for t in by_type:
    if t[1] > 10 and t[2] / t[1] > 0.5:
        print(f"🔴 type={t[0]} 的 pending 率 >50%，可能 collector 只覆盖部分 type")
```

**教训**（2026-04-09 实测发现）：@your-account 的 collector 只追踪 `reply/quote` 不追 `post`，导致 N 条 post 全部 pending 被当成"0 views"。**Phase 0 的 data health check 能提前暴露这种 bug**，避免"拿污染数据做调研"。

### 判定规则

| Pre-check 状态 | 行动 |
|---|---|
| 全绿 | 继续 Phase 1 |
| CLI 缺失 | 停止，告知用户安装 |
| 环境变量缺失 | 自动 Bash 前置，**不要**跳过 |
| 登录状态不明 | 告知用户浏览器确认 |
| 数据源有 bug | **先修再研究**，不要对着污染数据做结论 |

---

## 命令参考

### 并行 Bash 调用（grok + gemini）

**在 Claude Code 里通过 Bash 工具启动**，`run_in_background=true`，一条消息里多个 tool call：

```bash
# Bash call 1 (background)
OPENCLI_BROWSER_COMMAND_TIMEOUT=300 opencli grok ask "{{PROMPT}}" --timeout 300 -f json

# Bash call 2 (background)
opencli gemini ask "{{PROMPT}}" --format plain
```

两个 Bash 调用 **必须在同一条 assistant 消息里**调用，否则会串行。

### 并行 Agent 派发（内部数据）

**使用 Agent 工具**，`run_in_background=true`，一条消息里多个 tool call：

```
Agent 1: subagent_type=general-purpose, description=...
Agent 2: subagent_type=general-purpose, description=...
Agent 3: subagent_type=general-purpose, description=...
```

每个 agent 的 prompt 独立且完整（Phase 2 生成）。

### 可选：更多 AI 并行（未来扩展）

opencli 还支持其他 AI 服务（perplexity 等，持续扩展），未来可加入：

```bash
opencli perplexity ask "{{PROMPT}}" --format plain
```

---

## Error handling

### grok 超时（60s 截断）
- **根因**：`OPENCLI_BROWSER_COMMAND_TIMEOUT` 没设
- **修复**：`export OPENCLI_BROWSER_COMMAND_TIMEOUT=300`
- **不要**靠缩短 prompt 绕开（用户 2026-04-08 反馈：不要改问题改超时）

### grok 返回 "Not logged in"
- 停止，让用户在浏览器手动打开 grok.com 登录
- 不要自动重试

### gemini 返回可疑概念（Phoenix 架构等）
- Phase 5 自动标为 "potential hallucination"
- 不采纳，需要 grok 交叉验证后才能采用

### 内部 agent timeout
- 缩小 agent 任务范围（分解成 2 个小 agent）
- 或者改用直接 Bash SQL 替代

### 部分任务失败
- 如果 grok 失败但 gemini 成功 → 降级到单外部 AI
- 如果 2 个外部都失败 → 降级到"仅内部数据"调研，标注报告为 "internal only"
- 不要掩盖失败

---

## 2026-04-08 实战案例（此 skill 的设计来源）

**研究问题**：X reply deboost 机制是什么？为什么有的 reply 有流量有的没有？

**Phase 1 分解**：
- Agent A：reply views 分布分层（n=1079）
- Agent B：高/低流量 reply 内容对比（A组 10 条 vs B组 10 条）
- Agent C：时序 × 作者 × 骨架 × 热度 多维切分
- Grok：2026 Reply Guy 模式机制
- Gemini：同上（独立对比）

**Phase 3 并行派发**：5 个任务同时启动，Claude 在等的时候继续读 docs

**Phase 4 等待**：5 个任务在 5-10 分钟内陆续完成（Agent B 最慢）

**Phase 5 自动交叉验证**：

| 发现 | 内部证据 | grok | gemini | Tier |
|---|---|---|---|---|
| 不是账号级 deboost | Agent A 长尾分布 | ✅ | ✅ | 🟢 强共识 |
| 原帖热度 U 型 | Agent A+C U 型 | ✅ | ✅ | 🟢 强共识 |
| 中文 reply >> 英文 reply（1000×） | Agent B 独家 | 部分 | 部分 | 🟡 部分共识 |
| 踩坑预警 > 补充实测 | Agent A 927V vs 308V | 无意见 | 无意见 | 🟡 数据独支 |
| Reply Guy 模式 | 行为匹配 | ✅ | ✅ | 🟢 外部强共识 |
| long 回复更好 | n=0 | ✅ | ✅ | ⚪ 数据不足 |
| Phoenix 架构 | — | 无提及 | ✅ | 🚫 潜在幻觉 |

**Phase 6 自动改动清单**：
- 🔴 必做：CN:EN 10:1 / 踩坑预警首选 / 禁顶满 / 作者白黑名单 / 时段加权
- 🟡 建议：原帖热度甜区软约束 / HVC 机制
- ⚪ 待验证：long 回复效果（需 A/B 测试）
- 🚫 不做：基于 Phoenix 架构的假设（不采纳单侧幻觉）

**结果**：30 分钟从"有困惑"到"SKILL.md v8.2 → v8.3 完整改动清单"。

---

## 和其他 skill 的关系

- **ask-opencli**：单次 grok/gemini 调用，日常 second opinion。本 skill 包含 ask-opencli 的能力但扩展为多 AI 编排。
- **x-learn-reply v2**：domain-specific 版本，专门做 X reply 策略优化。内部 Phase 4/5（交叉验证 + 改动清单）复用了本 skill 的方法论。
- **cognitive-portrait**：参考了本 skill 的"主 agent 派发 sub-agent 并行"模式，但场景是单人认知画像分析。

如果你的场景是 **domain-specific 优化**（如 X reply / X post），优先用 domain 版本。如果是**通用深度调研**，用本 skill。

---

## 禁止事项

- ❌ 不跳过 Phase 0 prerequisites 检查
- ❌ 不串行调 grok 和 gemini（必须同一消息并行）
- ❌ 不 poll 等待 background task（等通知）
- ❌ 不跳过 Phase 5 置信度分级（直接把 AI 回答当结论）
- ❌ 不把单家 AI 的独有概念当事实（可能是幻觉）
- ❌ 不采纳样本 n<10 的内部数据作为高置信度依据
- ❌ 不跳过 Phase 7 artifact 保存

---

Task: {{ARGUMENTS}}
