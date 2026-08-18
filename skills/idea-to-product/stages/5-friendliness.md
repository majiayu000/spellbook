# Stage 5 — 友好性自检（硬门槛）

## 目标
用 **Nielsen 10 + Norman 7** 逐条审视前 4 阶段的设计输出。任何一条 **Fail** 必须修，不允许靠平均分蒙混过关。

## 开场白

> 现在进硬门槛。我会拿 17 条经典可用性原则对你的设计照妖镜。
>
> 规则：每条三选一 —— **Pass** / **Risk** / **Fail**。任何一条 Fail 都必须修复方案，否则不进 Stage 6。
>
> 这一步会让你不舒服，但这正是「用户友好」和「自我感觉良好」的分水岭。

## Nielsen 十大可用性启发（NN/g, Jakob Nielsen 1994/2024）

| # | 原则 | 检查问题 |
|---|---|---|
| N1 | 系统状态可见性 | 用户当前在哪一步，系统正在做什么，有反馈吗？ |
| N2 | 系统与现实世界匹配 | 用语是用户的语言还是开发者黑话？ |
| N3 | 用户控制与自由 | 用户能撤销、回退、退出吗？ |
| N4 | 一致性与标准 | 同样的操作在不同地方是同样的反馈吗？符合平台惯例吗？ |
| N5 | 错误预防 | 容易点错的地方有没有二次确认？危险操作有没有保护？ |
| N6 | 识别而非回忆 | 关键信息是显示出来还是要用户记住？ |
| N7 | 灵活与效率 | 新手有引导、老手有快捷键吗？ |
| N8 | 极简设计 | 每个界面只放该界面必需的东西吗？有没有装饰性元素抢戏？ |
| N9 | 错误恢复 | 出错时错误信息是技术堆栈还是人话+解决建议？ |
| N10 | 帮助与文档 | 关键操作旁是否就有上下文帮助？用户需要离开界面去查文档吗？ |

## Don Norman 七大设计原则（《设计心理学》/ 2013 修订版）

| # | 原则 | 检查问题 |
|---|---|---|
| D1 | Discoverability（可发现性） | 用户能看出哪些是可点击/可操作的吗？ |
| D2 | Feedback（反馈） | 每个动作都有立即可见的反馈吗？ |
| D3 | Conceptual model（概念模型） | 用户脑中的"这玩意怎么工作"和实际行为一致吗？ |
| D4 | Affordance & Signifier（功能可见性与符号） | 按钮看起来像按钮、可拖拽看起来可拖拽吗？ |
| D5 | Mapping（映射） | 控件位置和它控制的对象的位置/方向匹配吗？ |
| D6 | Constraints（约束） | 防止用户做错事的物理/逻辑/文化约束设了吗？ |
| D7 | Slips & Mistakes prevention | 区分"手滑"（slip）和"想错了"（mistake），各有保护吗？ |

## 评估流程

### Step 1. 自动初评
基于 Stage 1-4 的输出（first_screen, journey, aha_moment），对 17 条逐个给出初始判断：

```
N1 [Pass/Risk/Fail] — <一句话理由>
N2 [Pass/Risk/Fail] — <一句话理由>
...
D7 [Pass/Risk/Fail] — <一句话理由>
```

### Step 2. 高风险条目深挖
对所有 **Risk** 和 **Fail**，逐条对话：
- 用户解释为什么这条暂时 OK / 怎么修
- agent 决定接受用户的修复方案 → 改为 Pass，或继续标 Fail

### Step 3. 硬门槛检查
- 0 个 Fail → 进 Stage 6
- ≥1 个 Fail → **回炉**。明确告诉用户：「这些 Fail 不修，PRD 不会生成。要么改设计，要么明确接受是 v2 才补的妥协（写入 known_compromises）」

## 输出 schema

```json
{
  "nielsen": [
    { "id": "N1", "name": "状态可见性", "status": "Pass|Risk|Fail", "note": "..." }
  ],
  "norman": [
    { "id": "D1", "name": "Discoverability", "status": "Pass|Risk|Fail", "note": "..." }
  ],
  "fail_fixes": [
    { "principle_id": "N5", "fix": "<具体怎么修>", "applies_to_stage": "<回填到哪个 stage>" }
  ],
  "known_compromises": [
    { "principle_id": "N10", "reason": "<为何 v1 接受>", "v2_plan": "<v2 怎么补>" }
  ],
  "overall": "pass|blocked",
  "completed_at": "<ISO 8601>"
}
```

## 完成判定

- [ ] 17 条全部标了 status
- [ ] 所有 Fail 要么有 fix 要么明确写入 known_compromises
- [ ] overall = "pass" 才允许进 Stage 6

## 完成话术

> ✅ 友好性自检：
> - Pass: {N} 条
> - Risk: {N} 条（已记录待迭代）
> - Fail: {N} 条 → 已修复 / 已接受为 v2 补丁
>
> 进 Stage 6（PRD 生成）。

## 反模式

- ❌ 给所有条目都 Pass——这就是没认真做
- ❌ 用户说"这个不重要"就改 Pass——必须写入 known_compromises 留档
- ❌ 跳过这一阶段直接出 PRD——本 skill 的核心差异化就是这道门
- ❌ 把"未来会做"当作 Pass——v2 计划必须明确，不是模糊承诺

## 参考资料

- Nielsen 10：https://www.nngroup.com/articles/ten-usability-heuristics/
- Norman《设计心理学》（The Design of Everyday Things, Revised Edition, 2013）

## 进度报数模板

```
Stage 5/7 | 完成度: {x}/17 已评估 | Pass {p} / Risk {r} / Fail {f} | 当前阻塞: <一句话>
```
17 = Nielsen 10 + Norman 7

## Pre-Stage 6 checklist（**硬门槛 — 任何一条不过 = 阻塞**）

- [ ] Nielsen 10 全部已标 status
- [ ] Norman 7 全部已标 status
- [ ] 所有 `Fail` 已有 `fix` **或** 写入 `known_compromises`（含 v2_plan）
- [ ] `overall` == `"pass"`（**不准为了进 Stage 6 而把 Fail 改 Pass**）
- [ ] `state.stages.5` 已写入，`state.current_stage` 已 +1

> ⚠️ Red Flag：如果你觉得"6/10 也差不多"或"用户说不重要就 Pass"——回头读 SKILL.md §8。任何一条 Fail 必须真修或真接受为 v2 妥协，没有第三种选项。
