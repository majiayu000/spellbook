# 个人技能健康自检嵌入式模块 v1.0

**目标受众**：任何希望长期存活（>12个月）的个人 Skill 作者
**核心原则**：元数据饥饿是所有腐烂的根源。每个 Skill 必须声明自己的“出生证 + 健康史”。

## 必须在 SKILL.md frontmatter 中声明的时态字段（推荐）

```yaml
---
name: your-skill-name
description: ...
version: "1.3"
last_verified: "2026-05-28"
tested_on:
  claude_code: "claude-sonnet-4-20250514"
  arsenal_commit: "a1b2c3d"
external_deps:
  - "https://github.com/router-for-me/CLIProxyAPI (last_checked: 2026-04-01)"
  - "pip: Pillow>=10.0"
provenance: "个人 fork + 基于 PAIN-1001 经验自建"
---
```

**注意**：当前 validate_skills.py 不强制这些字段（PAIN-1001 根因之一），但你的 Skill 应该主动声明，方便 lifecycle-doctor 扫描。

## 推荐在 SKILL.md 末尾嵌入的“健康自检声明”（复制即用）

```markdown
## 健康与升级韧性自检（本模块推荐所有长期 Skill 内置）

**当前版本**：vX.Y
**最后人工验证**：2026-05-28（使用 Claude Code 20250514 + Arsenal 主分支）

### 外部依赖声明
- 无硬编码 GitHub 仓库路径（或已 pin 到具体 commit + 提供 fallback）
- 无 unpinned pip/npm 指令（所有依赖必须有版本约束）
- 如有外部服务调用，必须在 references/ 中记录“最后健康检查日期”

### 触发描述健康度
- description 长度：已控制在 8-12 行真实用户痛点语言
- 已包含 5+ 条真实用户原话触发词
- 已与 codex-retrospective / codex-fluent 建立协同点

### 已知风险与 graceful degrade
- 当 Claude Code 大版本升级后 description 匹配失败 → 自动降级为“请手动运行本技能做健康检查”
- 当外部依赖 404 → 输出清晰错误 + 替代方案建议，不静默失败

### 维护仪式建议（推荐用户每 3-6 个月执行一次）
1. 运行 `personal-arsenal-lifecycle-doctor`
2. 把本次诊断结果喂给 `codex-retrospective`，提炼 1-2 条 AGENTS.md 规则
3. 更新本段的 `last_verified` + `tested_on`

**如果本技能在你升级后突然不触发**：请直接对我说“检查我的个人 arsenal 健康”，本技能会自报问题。
```

## 与 codex-retrospective 的推荐集成点

诊断完成后，lifecycle-doctor 应该建议用户：

> “已发现 3 个技能存在时间腐烂风险。建议把以下证据喂给 codex-retrospective，生成持久化到 AGENTS.md 的维护规则：
> - 证据1: cliproxy-deploy 硬编码的 GitHub 仓库在 2026-03 已 404
> - 规则建议: 所有 deploy 类技能必须在 references/ 中声明 'last_external_check' + 提供 404 时的用户提示文案”

## 推荐的轻量扫描辅助逻辑（供作者参考）

一个健康的长期 Skill 应该能响应以下自检提示（即使不依赖外部 doctor）：

- “这个技能最近验证过吗？”
- “你的外部依赖还活着吗？”
- “升级后你还认得我吗？”

实现方式：在 SKILL.md 中加入显式处理分支，当用户问健康相关问题时，优先输出当前版本 + 最后验证时间 + 风险自报。

## 版本演进记录（建议维护在 references/CHANGELOG.md）

保持极简：
- v1.0 (2026-05-20): 初版，解决 PAIN-1001 核心场景
- v1.1 (2026-05-28): 增加 external_deps 声明模板 + 与 retrospective 协同

---

**设计哲学**（来自长期健康研究）：
- 诊断永远优先于修改（report-only）
- 元数据是唯一可低成本自动扫描的信号
- 一切变更必须有“至少两个不同会话的重复证据”才持久化
- 用户的 CLAUDE.md / AGENTS.md 是神圣不可擅自改动的领地

这个模块的目标是让“个人 1-2 年后还能用”从运气变成工程实践。
