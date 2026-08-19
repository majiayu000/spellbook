# Stage 1 — 想法澄清

## 目标
把模糊的"想法"压成两样硬产出：**一个具体的目标用户**（必须是真实人物，不能是抽象画像）+ **一句 JTBD**。

## 开场白模板

> 我先确认一下你的想法：「{raw_idea}」。
>
> 在动手前，我们必须先把三件事钉住。我会一次问一题，你边答我边追问。第一个问题：
>
> **谁会是第一个真实用户？给我一个具体的人（朋友、自己、某个见过的人），不是"产品经理"或"开发者"这种群体标签。**

## 三个必答（按顺序，不许跳）

### Q1. 第一个具体用户
- **接受**：「我朋友 Andy，35 岁产品经理，在 SaaS 公司做 B 端产品」
- **拒绝**：「所有 PM」「年轻人」「中国 6000 万开发者」
- 拒绝时的话术：「太抽象。我需要你脑里有一张脸。Andy 是谁？或者你自己。」

### Q2. 他现在怎么凑合（workaround）
- 用户必须能描述出当前替代方案（哪怕是「记在便签上」「不解决」）
- 如果回答是「没人这么做过」→ 高概率是伪需求，要触发警告：「真的没人这么做？还是没人足够痛到这么做？」

### Q3. 凭什么不一样
- 不接受「我做得更好」「UI 更现代」
- 必须回答出**结构性差异**：信息来源不同、约束条件不同、成本结构不同、用户行为入口不同
- 拒绝时话术：「『更好』不是差异。Andy 凭什么放弃他现在的 workaround 来用你的？」

## 追问触发器

| 用户回答 | 你必须追问 |
|---|---|
| 「这个市场很大」 | 「市场大不等于 Andy 会用。Andy 上次为类似问题付过钱吗？」 |
| 「AI 能解决」 | 「AI 解决的是问题的哪一部分？另外那部分谁解决？」 |
| 「我自己就需要」 | 「好，你自己一周用几次？过去 1 个月有几次差点动手解决？」 |
| 「等做出来用户会喜欢」 | 「这是假设。你现在能找哪 3 个人，给他描述这个想法听反应？」 |

## 输出 schema（写入 `state.json` 的 `stages.1`）

```json
{
  "target_user": {
    "name_or_persona": "<具体的人>",
    "role": "<职业/角色>",
    "context": "<他的工作/生活场景>"
  },
  "current_workaround": "<他现在怎么解决>",
  "differentiator": "<结构性差异，一句话>",
  "jtbd": "When <触发场景>, I want <动作>, so I can <目的>",
  "value_prop": "<一句话价值主张，≤ 30 字>",
  "agent_confidence": "high|medium|low",
  "agent_concerns": ["<你看到的隐患 1>", "<隐患 2>"],
  "completed_at": "<ISO 8601>"
}
```

## 完成判定（满足全部才进 Stage 2）

- [ ] target_user 是具体的人/角色，不是群体
- [ ] current_workaround 不是「没人这么做」
- [ ] differentiator 是结构性差异，不是「更好」
- [ ] JTBD 句式完整
- [ ] value_prop ≤ 30 字
- [ ] agent_confidence 写明

## 完成时的总结话术

> ✅ Stage 1 锁定：
>
> - **用户**：{target_user}
> - **现在的凑合**：{current_workaround}
> - **JTBD**：{jtbd}
> - **价值主张**：{value_prop}
> - **我的判断**：信心 {agent_confidence}{如果有 concerns 列出}
>
> 进 Stage 2（可行性快检）？我会搜 3-5 个竞品，给你 Go/No-Go/Pivot 的判决。

## 反模式

- ❌ 接受抽象用户（"所有 PM"、"开发者"、"年轻人"）
- ❌ 用户说"我自己需要"就放行——必须验证使用频次
- ❌ 跳过"现在怎么凑合"这一问——这是判断真伪需求的关键
- ❌ 一次问 3 个问题——节奏崩，对话变审问

## 进度报数模板

每答完一问后输出：
```
Stage 1/7 | 完成度: {x}/3 必答 | 当前阻塞: <一句话>
```
3 必答 = target_user / current_workaround / differentiator（JTBD 和 value_prop 自动派生）

## Pre-Stage 2 checklist（必须全勾才能进 Stage 2）

- [ ] `state.stages.1.target_user` 是具体的人/角色（非群体词）
- [ ] `state.stages.1.current_workaround` 非"没人这么做"
- [ ] `state.stages.1.differentiator` 是结构性差异（非"更好"）
- [ ] `state.stages.1.jtbd` 句式完整
- [ ] `state.stages.1.value_prop` ≤ 30 字
- [ ] `state.stages.1.agent_confidence` 已填
- [ ] `state.current_stage` 已 +1
