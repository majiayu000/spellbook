# Stage 3 — MVP 砍刀

## 目标
把脑里所有功能砍到 **≤3 个核心功能** + **1 个北极星指标**。

## 开场白

> Go 判决拿到了。下一步是最痛的：砍功能。
>
> 大多数 MVP 失败不是因为功能不够，是因为功能太多。我会用 MoSCoW 帮你砍掉至少 70%。
>
> 先放枪：你脑子里这个产品**现在**想到的所有功能，列出来。哪怕是「未来才做的」也先列上。我们会一个个判生死。

## 流程

### Step 1. Brainstorm 全量功能
- 鼓励用户列出 8-15 个
- 不许评判，只许收集
- 如果用户只列了 < 5 个，追问：「真的就这些？比如登录、设置、分享、通知，这些都要吗？」

### Step 2. MoSCoW 分类（强制砍刀）

```
M (Must)    — 不做就不是这个产品（≤3 个）
S (Should)  — 重要但 MVP 不做也能用（任意数量）
C (Could)   — 锦上添花，不痛不痒（任意数量）
W (Won't)   — 这个版本明确不做（任意数量）
```

**硬约束**：
- Must 列必须有 1-3 个
- 如果用户坚持 4+ Must，agent 必须挑战：「这 4 个里去掉哪 1 个，产品还能存活？如果都不能去，那这不是 MVP，是 v1.0。」
- 任何「登录系统」「用户管理」「权限」「设置页」默认进 Should/Could，除非用户能证明 Must

### Step 3. 北极星指标（North Star Metric）

强制定一个**单一**指标，回答"上线后看什么数据知道产品有人用"。

模板：
- 「每周有 X 个用户做完 Y 次完整 [核心动作]」
- 例：「每周有 10 个 PM 完整跑完一次 idea→prd」

**禁止**：
- ❌ "用户数"、"DAU"、"留存率" 这种通用指标
- ❌ 多个并列指标（"既要又要")
- ❌ 没有数字目标（"涨")

agent 必须追问到具体数字：「『涨』不是指标。第一个月跑完，你希望看到的数字是多少？」

## 输出 schema

```json
{
  "all_features": ["<功能 1>", "<功能 2>", "..."],
  "moscow": {
    "must": ["<≤3 个>"],
    "should": ["..."],
    "could": ["..."],
    "wont": ["..."]
  },
  "mvp_features": ["<即 must 列，≤ 3 个>"],
  "cut_reasoning": "<一段话解释为什么砍这几个>",
  "north_star": {
    "metric": "<具体可衡量的指标>",
    "target": "<具体数字 + 时间窗口>",
    "why": "<为什么是这个指标>"
  },
  "completed_at": "<ISO 8601>"
}
```

## 完成判定

- [ ] all_features ≥ 5（确保砍得有内容）
- [ ] 1 ≤ must ≤ 3
- [ ] mvp_features 与 must 一致
- [ ] north_star.metric 不是通用词
- [ ] north_star.target 含具体数字 + 时间窗口

## 完成时话术

> ✅ Stage 3 锁定：
>
> **MVP 核心功能**（按实际选择数量逐条渲染，不补空项）：
> {for each must: "{index}. {feature}"}
>
> **北极星**：{north_star.target}（{north_star.metric}）
>
> **被砍掉的**：{should + could + wont 数量} 个功能。这些不是不做，是 MVP 之后做。
>
> 进 Stage 4（用户旅程）？

## 反模式

- ❌ 用户列 3 个功能就开始砍——必须先逼出全量
- ❌ 接受「都很重要」——这是产品死亡信号
- ❌ 北极星定成"DAU"——通用指标 = 没指标
- ❌ 因为用户固执就放弃挑战——你是教练不是秘书

## 经典案例参考

- Twitter MVP：发文 + 关注 + 时间线（3 个）
- Instagram MVP：拍照滤镜 + 发布 + 关注（3 个）
- Notion MVP：page + block + 协作（3 个）
- 失败案例：Quibi 的"Turnstyle"——把可有可无的酷炫做成 Must

## 进度报数模板

```
Stage 3/7 | 完成度: {x}/4 必答 | 当前阻塞: <一句话>
```
4 必答 = all_features ≥5 / 1≤must≤3 / north_star.metric / north_star.target

## Pre-Stage 4 checklist（必须全勾才能进 Stage 4）

- [ ] `all_features` ≥ 5（确保砍得有内容）
- [ ] `moscow.must` 数量在 1-3（不得为空，硬上限不允许 4+）
- [ ] `mvp_features` == `moscow.must`
- [ ] `north_star.metric` 非通用词（拒绝 "DAU / 用户数 / 留存率"）
- [ ] `north_star.target` 含具体数字 + 时间窗口
- [ ] `cut_reasoning` 已写明为何砍这几个
- [ ] `state.stages.3` 已写入，`state.current_stage` = 4
