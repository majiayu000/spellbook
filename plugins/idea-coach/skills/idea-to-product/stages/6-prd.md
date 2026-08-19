# Stage 6 — PRD 生成

## 目标
从前 5 阶段的 state 自动生成一份 **可被 Claude Code 直接消费** 的 PRD，写到 `.idea/<slug>/prd.md`。

## 关键设计：可被 AI Coding Agent 消费

普通 PRD 服务于"人类工程师 + Jira"。本 skill 的 PRD 必须额外满足：
1. **明确的 file ownership**（参考 vibeguard W-14）：哪些文件由哪个模块拥有
2. **acceptance test as code**：验收用例写成可执行的伪代码
3. **out-of-scope hard guard**：明确列出"明确不做"，防止 AI 越界
4. **verify_cmd**：每个核心功能有 60 秒内可跑的验证命令
5. **technology decisions**：技术栈/依赖/数据库明确指定，不留模糊

## 执行流程（无用户交互，纯生成）

### Step 1. 读取 state.json
合并 Stage 1-5 的所有结构化输出。

### Step 2. 读 `templates/prd-template.md`
作为输出骨架。

### Step 3. 填充模板
按 template 的占位符，从 state 提取值填入：
- `{{value_prop}}` ← state.stages.1.value_prop
- `{{target_user}}` ← state.stages.1.target_user
- `{{jtbd}}` ← state.stages.1.jtbd
- `{{mvp_features}}` ← state.stages.3.mvp_features
- `{{north_star}}` ← state.stages.3.north_star
- `{{journey}}` ← state.stages.4.journey
- `{{aha_moment}}` ← state.stages.4.aha_moment
- `{{dropoff_risks}}` ← state.stages.4.dropoff_risks
- `{{out_of_scope}}` ← state.stages.3.moscow.wont
- `{{known_compromises}}` ← state.stages.5.known_compromises
- `{{competitors}}` ← state.stages.2.competitors
- `{{risks}}` ← state.stages.2.risks

### Step 4. 生成验收用例（每个 MVP 功能 1-2 个）
对每个 `mvp_features` 生成：
```
Given <前置条件>
When <用户动作>
Then <可验证的系统响应>
Verify: <60 秒内可跑的命令或可观察的现象>
```

### Step 5. 生成技术栈建议
基于 mvp_features + journey 推断：
- 前端框架（Vanilla / React / Svelte 等）
- 后端是否需要（很多 MVP 不需要）
- 数据库（如果需要）
- 第三方 API

**默认偏好**：能用 vanilla HTML+JS 解决就不用 React；能用 localStorage 就不上 backend。

### Step 6. 写文件
落盘到 `.idea/<slug>/prd.md`。

### Step 7. 用户确认
向用户展示生成的 PRD 摘要（前 50 行 + 章节标题），询问：
> PRD 已生成在 `.idea/<slug>/prd.md`。
> 看一眼？如果要调整任何章节告诉我。否则进 Stage 7（HTML 原型）。

## 输出 schema（写入 state.stages.6）

```json
{
  "prd_path": ".idea/<slug>/prd.md",
  "sections_count": <数字>,
  "acceptance_tests_count": <数字>,
  "tech_stack": {
    "frontend": "<选择>",
    "backend": "<选择 / none>",
    "storage": "<选择>",
    "third_party": ["<API 1>"]
  },
  "user_approved": true,
  "completed_at": "<ISO 8601>"
}
```

## 完成判定

- [ ] prd.md 文件存在
- [ ] 模板中所有占位符已填充（无 `{{xxx}}` 残留）
- [ ] 每个 MVP 功能有 ≥1 验收用例
- [ ] tech_stack 明确指定，不留 "TBD"

## 反模式

- ❌ 占位符没填完就落盘——必须 grep 确认无 `{{` 残留
- ❌ 验收用例写成"用户能用"——必须可观察
- ❌ 技术栈写"看情况"——必须明确选型
- ❌ out-of-scope 章节空着——必须从 moscow.wont 填进去
- ❌ 跳过用户确认直接进 Stage 7——给用户最后一次回炉机会

## 进度报数模板

```
Stage 6/7 | 阶段: {读 state → Read template → 填占位 → 生成验收 → 写 prd.md → 用户确认}
```

> ⚠️ 进入 Stage 6 之前必须 Read `templates/prd-template.md`。这是 progressive disclosure 路标，不读模板直接生成 = PRD 结构失控。

## Pre-Stage 7 checklist（必须全勾才能进 Stage 7）

- [ ] `.idea/<slug>/prd.md` 文件存在
- [ ] `grep '{{' .idea/<slug>/prd.md` **无任何残留占位符**
- [ ] 每个 `mvp_features` 至少有 1 条验收用例（Given/When/Then/Verify 完整）
- [ ] `tech_stack` 明确指定（无 "TBD" / "看情况"）
- [ ] `out_of_scope` 章节非空（从 `moscow.wont` 填进去）
- [ ] 用户已明确确认 PRD（在对话里收到 "OK" / "进下一步" 等）
- [ ] `state.stages.6` 已写入，`state.current_stage` 已 +1
