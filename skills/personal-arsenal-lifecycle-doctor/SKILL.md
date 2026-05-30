---
name: personal-arsenal-lifecycle-doctor
description: |
  扫描并诊断你个人 ~/.claude/skills 里的技能健康状态。当用户说“我的技能失效了”“升级后老技能不认了”“技能腐烂了”“外部依赖坏了”“我的个人 Arsenal 乱了”“帮我检查技能健康”“技能生命周期”“长期维护技能”时使用。

  特别适合维护 1 年以上个人技能集合的重度用户。Always protect 用户现有的 CLAUDE.md / AGENTS.md / 自定义配置，只读优先，任何修改必须用户明确确认后才执行。
---

# Personal Arsenal Lifecycle Doctor

帮助个人 power user 长期维护自己的技能集合，防止时间腐烂、升级失效、外部依赖僵尸化。

## 触发场景（严格按真实用户语言）
- “我 1-2 年前超好用的 Skill 现在 Claude 完全不认了”
- “升级 Claude Code / Arsenal 后好多技能失效”
- “我的部署类技能现在执行不了了，外部项目下线了”
- “帮我检查一下我装的技能哪些还能用”
- “个人技能腐烂了怎么办”

## 工作流程

1. **发现阶段**（只读）
   - 扫描 `~/.claude/skills`
   - 区分来源：Arsenal 符号链接 / 纯自定义 / 社区拷贝
   - 提取 frontmatter（name, description, version, last_tested, external_deps 等）
   - 检测外部硬依赖（GitHub URL、特定 commit、unpinned pip/npm）

2. **健康诊断**（结构化）
   - 时间维度风险（last_tested 距今 > 6/12 个月）
   - 触发风险（description 过时、与当前 Claude 机制不匹配）
   - 外部依赖风险（仓库 404、API 变更、pip 包消失）
   - 结构风险（缺少健康自检、过度复杂、无 graceful degrade）

3. **输出结构化报告**
   - 总体健康评分（🔴严重 / 🟡警告 / 🟢健康）
   - 问题清单（带证据）
   - 每个问题的**可执行修复建议**（最小变更优先）
   - 一键可运行的迁移/修复命令（用户确认后执行）

4. **安全执行（必须用户确认）**
   - 任何写操作前必须 dry-run + 明确确认
   - 提供 rollback 方案
   - 推荐与 `codex-retrospective` 结合，把学到的规则编码进 AGENTS.md

## 推荐的健康自检模块（可嵌入任何长期 Skill）

```markdown
## 技能健康自检（强烈建议所有长期 Skill 内置此模块）

每当用户说“检查技能健康”“这个技能还能用吗”“升级后验证”时，自动执行：

1. 声明当前版本 + last_tested 日期 + 测试过的 Claude Code 版本
2. 列出所有外部硬依赖 + 当前状态检查
3. 如果发现风险，给出最小修复建议
4. 输出固定格式报告，便于用户归档
```

## 与现有工具的协同

- 强烈建议与 `codex-retrospective` 配合：诊断后把学到的长期维护规则编码进 AGENTS.md
- 可与 `codex-fluent` 的维护仪式结合，形成个人定期健康检查习惯
- 输出结果可直接喂给 `skill-trigger-doctor` 进一步优化触发描述

## 注意事项（Safety Contract）

- **只读优先**：默认不修改任何文件
- 任何修改必须用户明确说“执行”或“确认修复”
- 永远保护用户现有的 CLAUDE.md、AGENTS.md、自定义配置
- 发现严重问题时优先给出“先备份、再操作”的建议
- 中文输出，结构清晰，便于个人归档

## 局限说明

本技能不会自动修复所有问题（尤其是需要大量人工判断的语义漂移）。它擅长发现“可通过元数据 + 启发式快速检测”的问题，并给出清晰的行动建议。

对于复杂语义失效，建议配合 `codex-retrospective` 做证据驱动的最小变更。
