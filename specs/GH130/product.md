# Product Spec

## Linked Issue

GH-130

Covered issues: #127, #128, #129.

## User Problem

用户希望 Spellbook 的核心 agent workflow skills 不只是加速执行，还能降低长期维护成本、上下文漂移和落地前审核负担。当前 `skill-audit`、`skill-creator`、`flowguard`、`strategic-compact` 等能力分散存在，但没有统一的“Reliable Skill + Context Hygiene + Review Gate”组合入口。

## Goals

- 为高价值 skills 定义可复用的 Reliable Skill Contract，并覆盖 #127 的 5 个元素。
- 将 Context Engineering 的目标复述、上下文审计、压缩策略、外部 scratchpad 建议接入长任务与 handoff 流程，覆盖 #128。
- 提供 Review Gate skill，要求 agent diff 在 commit、push、PR、merge 或落地前产生 review pack 并等待明确人工批准，覆盖 #129。
- 在核心 docs 与 README 中记录三者的归属和组合使用方式，覆盖 #130 的协调目标。

## Non-Goals

- 不重写所有现有 skills。
- 不引入新的 registry 字段、install 行为或 runtime API。
- 不自动执行发布、权限变更、强推或远端 branch 删除。
- 不把 Context Engineering 拆成新的重复 skill；本轮优先增强 `flowguard` 与 `strategic-compact`。

## Behavior Invariants

1. Reliable Skill Contract 必须包含 explicit negative examples、verification checkpoints、machine-checkable done conditions、replay or smoke hooks with log-to-patch loop、drift signal detection。
2. Long-running guard flows 必须在重大步骤前重新陈述目标并给出不超过 5 步的小计划。
3. Handoff 或 compaction flow 必须包含 context audit，区分保留、外部化、丢弃的内容。
4. Review Gate 必须阻止未经明确人工批准的 agent diff 被 commit、push、PR、merge 或落地。
5. 新 agent-workflow skill 的 authoring guidance 必须要求考虑可靠性 contract，而不是只写触发描述。
6. 相关 registry 或 install metadata 必须由生成器更新，不手改生成文件。

## Acceptance Criteria

- [ ] `skill-lifeguard` 存在，并能输出/检查 Reliable Skill Contract 的 5 元素。
- [ ] `skill-audit` 能报告 Reliable Skill Contract 覆盖度，`skill-creator` 将这些元素纳入新 agent-workflow skill 的默认作者检查。
- [ ] `flowguard` 与 `strategic-compact` 包含 objective re-statement、context audit、compaction policy、external scratchpad guidance。
- [ ] `review-gate` 存在，并定义 review pack、human approval gate、decision recording。
- [ ] docs/README 让新用户能发现 Agent Reliability Trio，并包含一个端到端示例。
- [ ] `python3 scripts/validate_skills.py --check` 和 GH130 SpecRail packet check 通过。

## Edge Cases

- 如果任务是只读 review，不应触发 Review Gate 的 landing approval。
- 如果用户明确要求只做本地草稿，不应创建 PR 或 merge。
- 如果上下文接近上限但任务处于实现中途，应该外部化 scratchpad 或 checkpoint，而不是丢失当前实现状态。
- 如果某个 skill 暂处 manual validation 阶段，Reliable Skill Contract 可记录缺口，但不能假装已自动化。

## Rollout Notes

本轮是文档和 skill workflow 层更新；没有运行时迁移。新增 skills 通过现有 installer 和 registry 生成流程发布。
