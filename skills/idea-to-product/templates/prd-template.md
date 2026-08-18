# PRD: {{product_name}}

> 由 `/idea` skill 生成于 {{generated_at}}
> Slug: `{{slug}}` | 状态文件: `.idea/{{slug}}/state.json`

## 0. 一句话

{{value_prop}}

## 1. 目标用户

| 字段 | 值 |
|---|---|
| 名字/画像 | {{target_user.name_or_persona}} |
| 角色 | {{target_user.role}} |
| 工作/生活场景 | {{target_user.context}} |

## 2. Job To Be Done

> {{jtbd}}

**当前他们怎么凑合**：{{current_workaround}}

**我们的结构性差异**：{{differentiator}}

## 3. 竞品扫描

| 名称 | 链接 | 他们的做法 | 没解决好的部分（我们的机会） |
|---|---|---|---|
{{#each competitors}}
| {{name}} | {{url}} | {{approach}} | {{gap}} |
{{/each}}

## 4. MVP 范围（北极星指标驱动）

### 北极星指标
- **指标**：{{north_star.metric}}
- **目标**：{{north_star.target}}
- **为何是它**：{{north_star.why}}

### MVP 三件套（仅这些）

{{#each mvp_features}}
#### M{{@index_plus_1}}. {{this}}

**验收用例**：
```
Given <前置条件>
When <用户动作>
Then <可观察的响应>
Verify: <60 秒内可跑的命令或可观察现象>
```
{{/each}}

## 5. 明确不做（Out of Scope）

> ⚠️ AI Coding Agent 注意：以下功能 **明确不实现**，请勿"顺手加上"。

{{#each out_of_scope}}
- {{this}}
{{/each}}

## 6. 用户旅程

```
{{ascii_journey}}
```

**Aha 时刻**：{{aha_moment.observation}}
**从首次打开到 Aha 的时长**：≤ {{aha_moment.seconds_from_launch}} 秒

### 流失风险点
{{#each dropoff_risks}}
- **{{moment}}**：{{cause}} → 缓解：{{mitigation}}
{{/each}}

## 7. 友好性承诺（Nielsen + Norman 检查后）

### 已通过
{{nielsen_pass_summary}} (Nielsen)
{{norman_pass_summary}} (Norman)

### 已知妥协（v2 补丁）
{{#each known_compromises}}
- **{{principle_id}}**：{{reason}}
  - v2 计划：{{v2_plan}}
{{/each}}

## 8. 技术决策

| 维度 | 选择 | 理由 |
|---|---|---|
| 前端 | {{tech_stack.frontend}} | {{tech_stack.frontend_reason}} |
| 后端 | {{tech_stack.backend}} | {{tech_stack.backend_reason}} |
| 存储 | {{tech_stack.storage}} | {{tech_stack.storage_reason}} |
| 第三方 API | {{tech_stack.third_party_list}} | — |

## 9. 风险与缓解

{{#each risks}}
- **[{{dimension}}/{{severity}}] {{description}}**
  - 缓解/验证方法：{{mitigation}}
{{/each}}

## 10. File Ownership（给 AI Coding Agent）

> 多 agent 协作时按此分边界（参考 vibeguard W-14）。

| 模块 | 拥有文件 | 不可越界 |
|---|---|---|
| {{module_1_name}} | {{module_1_files}} | {{module_1_forbidden}} |

（如 MVP 单文件，此节可只有一行）

## 11. 下一步

- [ ] 用 `/init` 初始化项目骨架
- [ ] 把本 PRD 喂给 Claude Code / Cursor 开始实现
- [ ] 找 3 个 {{target_user.name_or_persona}} 看 `prototype.html` 收第一反应
- [ ] 上线后跟踪北极星：{{north_star.metric}}
