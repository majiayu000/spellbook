# Stage 4 — 用户旅程

## 目标
画出从"用户听说产品"到"Aha 时刻"的 **5-7 步关键路径**，标出每步的情绪、卡点、流失风险。

## 开场白

> MVP 三件套钉住了。现在我们要画用户怎么从「不知道你」走到「Wow 这个真好用」。
>
> 我会问 5 个问题，按用户的视角而不是开发者的视角。开始：

## 5 个必答问题

### Q1. 入口（用户怎么听说你）
- 候选：朋友推荐 / 搜索结果 / 社交媒体 / 应用商店 / 公司内部
- 追问：「这个入口现实吗？你能描述一个真实场景：Andy 在什么情境下首次听说？」
- 如果用户答「会发朋友圈宣传」——挑战：「你和 Andy 在同一个朋友圈吗？」

### Q2. 第一秒（首次打开看到的第一个屏幕）
- 必答：用户首屏看到**什么**、能**做什么**、被引导**去哪**
- 追问：「需要登录吗？需要的话用户会立刻退吗？能不能延后登录？」
- 关键判断：**首屏到核心动作能不能 ≤ 3 次点击**

### Q3. 核心路径（首次完成 MVP 三件套之一的最短路径）
- 列出步骤：1. ... → 2. ... → 3. ... → ✨
- 每步标注：用户当前情绪（期待/疑惑/烦躁/兴奋）+ 潜在卡点
- 硬约束：路径 ≤ 7 步。超过必须砍。

### Q4. Aha 时刻（用户第一次说 "Wow" 是什么）
- 必须具体到一个可观察的瞬间：
  - 好例：「输入想法 30 秒后，弹出 5 个差异化竞品分析」
  - 坏例：「用户感受到价值」
- **从首次打开到 Aha 时刻 ≤ 60 秒**（这是教练定的硬指标）
- 如果做不到 ≤ 60 秒，必须问：「能不能预填示例？能不能跳过登录？能不能砍掉某一步？」

### Q5. 流失点（用户最可能放弃的两个时刻）
- 必答 2 个具体的流失风险点
- 每个标注：原因 + 怎么减缓
- 经典流失点：注册卡点、首次加载慢、不知道下一步、操作失败无错误提示

## 输出 schema

```json
{
  "entry_point": {
    "channel": "<入口渠道>",
    "scenario": "<具体场景>"
  },
  "first_screen": {
    "content": "<首屏内容>",
    "primary_cta": "<首要按钮/动作>",
    "requires_auth": true,
    "clicks_to_core_action": <数字>
  },
  "journey": [
    {
      "step": 1,
      "action": "<用户做什么>",
      "system_response": "<系统给什么反馈>",
      "emotion": "<情绪>",
      "risk": "<潜在卡点>"
    }
  ],
  "aha_moment": {
    "trigger": "<什么时候触发>",
    "observation": "<可观察的具体瞬间>",
    "seconds_from_launch": <数字>
  },
  "dropoff_risks": [
    {
      "moment": "<流失时刻>",
      "cause": "<原因>",
      "mitigation": "<怎么减缓>"
    }
  ],
  "completed_at": "<ISO 8601>"
}
```

## 完成判定

- [ ] entry_point 是具体场景，不是"在网上推广"
- [ ] first_screen.clicks_to_core_action ≤ 3
- [ ] journey 步骤在 5-7
- [ ] aha_moment.seconds_from_launch ≤ 60
- [ ] dropoff_risks ≥ 2

## ASCII 旅程图（自动渲染到 journey.md）

完成时按以下格式输出到 `.idea/<slug>/journey.md`：

```
[听说]──→[首次打开]──→[Step 1]──→[Step 2]──→[Step 3]──→[✨ Aha]
  ↓         ↓            ↓          ↓          ↓
{channel}  {首屏}       {action}   {action}   {action}
  😐        😐           🤔         😊         🤩
                                  ⚠️流失点1
```

## 反模式

- ❌ 入口写"会做营销"——空头支票
- ❌ 首屏强制注册——99% MVP 都该延后登录
- ❌ Aha 时刻定义为"用户感受到价值"——必须可观察
- ❌ 旅程 10+ 步——这是 v2.0，不是 MVP
- ❌ 不标情绪——产品教练必须站在用户视角，不是技术实现视角

## 进度报数模板

```
Stage 4/7 | 完成度: {x}/5 必答 | 当前阻塞: <一句话>
```
5 必答 = entry_point / first_screen / journey / aha_moment / dropoff_risks

## Pre-Stage 5 checklist（必须全勾才能进 Stage 5）

- [ ] `entry_point` 是具体场景（拒绝"会做营销"）
- [ ] `first_screen.clicks_to_core_action` ≤ 3
- [ ] `journey` 步骤在 5-7（少于 5 或多于 7 都阻塞）
- [ ] `aha_moment.seconds_from_launch` ≤ 60
- [ ] `aha_moment.observation` 是可观察的具体瞬间（非"感受到价值"）
- [ ] `dropoff_risks` ≥ 2，每个有 mitigation
- [ ] 已生成 `journey.md` 的 ASCII 旅程图（写入文件，不仅在对话里）
- [ ] `state.stages.4` 已写入，确认前 `current_stage` = 4 且 pending 指向 5；确认后才进入 5
