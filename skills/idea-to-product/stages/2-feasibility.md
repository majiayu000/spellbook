# Stage 2 — 可行性快检

## 目标
给一个明确的 **Go / No-Go / Pivot** 判决，附竞品扫描和风险清单。

## 开场白

> 用户和价值主张钉住了。现在做一次 5-10 分钟的可行性快检：
>
> 1. 我去搜 3-5 个最相关的竞品/替代方案
> 2. 列出 3 个最大的风险（技术、市场、用户）
> 3. 给一个明确的判决：Go / No-Go / Pivot
>
> 开始搜了。

## 执行流程

### 1. 竞品扫描（WebSearch / WebFetch）
- 用 Stage 1 的 jtbd 和 value_prop 派生搜索词
- 至少检索 3-5 个真实存在的对手或替代方案
- 每个对手记录：
  - 名称 + 链接
  - 他们怎么解决这个问题
  - 他们没解决好的部分（你的机会）

如果搜不到对手 → **高度警惕**。话术：
> 「我搜不到直接对手。可能性：(A) 你发现了真空白市场；(B) 这个问题没人足够痛。倾向 B。证伪 B 的办法：你能在 24 小时内找到 3 个目标用户描述这个问题给他们听，看反应吗？」

### 2. 风险三连
强制列至少 3 个，分布在不同维度：

| 维度 | 例子 |
|---|---|
| 技术 | 需要 GPU 推理 / 跨平台同步 / 实时性 |
| 市场 | 现有玩家护城河 / 用户教育成本 / 监管 |
| 用户行为 | 用户习惯改变成本 / 切换成本 / 信任建立 |
| 商业 | 付费意愿 / 单位经济模型 / 获客成本 |

每个风险要给 mitigation（怎么应对/怎么验证）。

### 3. 判决（必须三选一，不许"看情况"）

| 判决 | 触发条件 | 下一步 |
|---|---|---|
| **Go** | 有真实竞品但有清晰缺口；或无竞品但用户痛感已验证 | 进 Stage 3 |
| **No-Go** | 竞品已占据主流量且没有结构性差异；或目标用户根本不存在 | 停止流程，建议用户换想法 |
| **Pivot** | 想法核心问题成立但切入点错了 | 回到 Stage 1，重写 JTBD |

判决话术示例：
> **Go**："有 4 个对手但都漏了 X。你的差异化（structural diff）能站住，可以继续。"
>
> **No-Go**："ChatPRD/Cursor 已经把 80% 占了，你说的「更好」我没看到结构性差异。建议要么换想法，要么换切入点。"
>
> **Pivot**："底层问题成立——确实有人因为 X 痛。但你切的功能（功能 A）不是最痛点。最痛的是功能 B。建议 Pivot 到 B。"

## 输出 schema

```json
{
  "competitors": [
    {
      "name": "<对手 1>",
      "url": "<链接>",
      "approach": "<他怎么做>",
      "gap": "<他没解决好的部分>"
    }
  ],
  "risks": [
    {
      "dimension": "tech|market|user|business",
      "description": "<风险描述>",
      "severity": "high|medium|low",
      "mitigation": "<怎么应对/验证>"
    }
  ],
  "verdict": "Go|No-Go|Pivot",
  "verdict_reasoning": "<一段话，3-5 句>",
  "pivot_suggestion": "<如果 Pivot，建议的新方向>",
  "completed_at": "<ISO 8601>"
}
```

## 完成判定

- [ ] competitors ≥ 3（或明确解释为什么搜不到）
- [ ] risks ≥ 3，至少覆盖 2 个不同维度
- [ ] verdict 三选一，不允许 "TBD"
- [ ] 如果 verdict = Pivot，pivot_suggestion 必填

## 判决后的状态转换

- **Go**：写入 `state.stages.2`，保持 `current_stage = 2` 并设置 `pending_confirmation = {"kind":"advance","completed_stage":2,"next_stage":3,"action":"advance"}`；用户明确确认后才清空 pending、进入 Stage 3。
- **Pivot**：先把 `pivot_suggestion` 作为候选新想法展示给用户，保持 Stage 2 并持久化 `pending_confirmation = {"kind":"pivot","completed_stage":2,"next_stage":1,"action":"reset_to_stage_1","proposed_raw_idea":"<pivot_suggestion>"}`。用户确认或改写新方向后，把旧 `raw_idea`、Stage 1/2 判断、判决理由、最终新想法和时间追加到顶层 `pivot_history`；把 `raw_idea` 更新为用户确认的新想法，清空 `state.stages` 以失效所有派生状态，清空 pending，设置 `state.current_stage = 1`、`state.status = "active"`，再重走 Stage 1。不得执行通用递增。
- **No-Go**：写入 `state.stages.2`，设置 `state.status = "stopped"`、`state.current_stage = 2`，停止流程。除非用户明确提出新想法，否则不得继续 Stage 3。

## 反模式

- ❌ 看到 1 个竞品就说"有对手了，No-Go"——竞品多反而说明市场存在
- ❌ 看到 0 个竞品就说"蓝海，Go"——更可能是伪需求
- ❌ 为了让用户开心就给 Go——产品教练的价值是说真话
- ❌ 判决"看情况"、"取决于 X"——必须明确判决

## 进度报数模板

```
Stage 2/7 | 完成度: {x}/3 必答 | 当前阻塞: <一句话>
```
3 必答 = competitors ≥3 / risks ≥3 / verdict

## Pre-Stage 3 checklist（必须全勾才能进 Stage 3）

- [ ] `competitors` ≥ 3（或明确解释为何搜不到 + 引发警惕）
- [ ] `risks` ≥ 3，覆盖 ≥ 2 个不同维度
- [ ] `verdict` ∈ {Go, No-Go, Pivot}，不允许 TBD
- [ ] verdict = Pivot 时 `pivot_suggestion` 已填；确认后旧状态已归档、`raw_idea` 已更新为新方向、`state.stages` 已清空且 `state.current_stage = 1`
- [ ] verdict = No-Go 时不允许继续，提示用户换想法或承认结束
- [ ] verdict = Go 时确认前 `current_stage = 2` 且 pending 指向 3；确认后才进入 3
- [ ] verdict = No-Go 时 `state.status = "stopped"` 且 `state.current_stage = 2`
