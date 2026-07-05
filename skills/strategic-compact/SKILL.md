---
name: strategic-compact
description: "当用户需要在长会话的逻辑边界手动压缩上下文、做 context engineering、目标复述、上下文审计、外部 scratchpad、handoff 或 compaction policy 时使用。"
---

# Strategic Compact

## 概述

在长会话中，上下文窗口有限且会腐烂。此 skill 指导何时压缩、保留什么、丢弃什么，以及如何把 durable state 外部化。

核心原则：**在逻辑边界压缩，不在任意时刻压缩。**

## Lightweight Context Engineering Guard

在重大阶段开始、handoff、压缩前，用一段短文本执行：

```text
objective:
plan_5_steps_or_less:
context_audit:
- keep:
- externalize:
- discard:
- stale_or_conflicting:
next_boundary:
```

计划最多 5 步。若无法用 5 步表达，先收敛当前 tranche，不要扩大范围。

## 压缩决策表

| 当前阶段 | 下一阶段 | 是否压缩 | 理由 |
|----------|----------|----------|------|
| 研究/探索 | 规划 | 是 | 探索细节不需要带入规划 |
| 规划 | 实现 | 是 | 保留计划，丢弃规划过程 |
| 实现步骤 N | 实现步骤 N+1 | 否 | 实现中途压缩会丢失上下文 |
| 实现完成 | 验证 | 可选 | 如果上下文接近上限 |
| 验证 | 提交 | 否 | 验证结果需要带入提交 |
| 任务 A 完成 | 任务 B 开始 | 是 | 不同任务间压缩 |

## Context Audit

压缩前必须分类：

- keep: 目标、约束、当前分支、修改文件、关键决策、最新验证结果、下一步
- externalize: 原始日志、大 diff、宽泛搜索结果、CI 全量输出、长 JSON
- discard: 已解决错误的完整堆栈、探索过程、失败假设的重复细节
- stale_or_conflicting: 旧计划、旧 head SHA、过期 CI、与当前文件冲突的记忆

外部化优先使用 repo artifact、checkpoint、issue/PR 描述、run log 或用户指定 scratchpad。不要把 raw session logs 当成当前事实来源。

## 压缩后保留清单

必须保留：
- 当前任务目标和约束
- 不超过 5 步的当前计划
- 已做的架构决策及理由
- 已修改的文件列表
- 未完成的步骤
- 发现的问题和 TODO
- VibeGuard 约束（始终保留）
- fresh verification evidence
- review gate decision when landing is next

可以丢弃：
- 文件内容的完整引用（保留路径即可）
- 搜索过程中的中间结果
- 已解决的错误的完整堆栈
- 探索性的代码阅读记录

## 使用方式

当感觉上下文即将耗尽时：

1. 判断当前处于哪个阶段
2. 查压缩决策表，确认是否适合压缩
3. 执行 context audit，决定 keep / externalize / discard / stale_or_conflicting
4. 如果适合，按保留清单整理摘要
5. 执行压缩

## 反模式

- 在实现中途压缩 → 丢失关键上下文，导致重复工作
- 压缩时丢弃约束 → 后续步骤违反规则
- 不压缩直到溢出 → 被动截断比主动压缩更危险
- 把旧总结当远端真相 → 需要重新 fetch、检查文件或查询 API
