# Stage 7 — HTML 原型生成

## 目标
生成一个 **自包含、零依赖、可点击** 的单文件 HTML 原型，浏览器双击即可打开。落地到 `.idea/<slug>/prototype.html`。

## 硬约束（不可妥协）

1. **单文件**：CSS + JS 全部 inline 进 `<style>` 和 `<script>`
2. **零外部依赖**：禁止 CDN（无 React/Vue/Tailwind/jQuery/Bootstrap/Font Awesome 等）
3. **离线可用**：双击文件用 file:// 协议也能完整跑
4. **不依赖 design-html skill**：本 stage 自包含生成
5. **真能交互**：核心 MVP 功能至少要能模拟一次完整流程（即使是 mock 数据）
6. **响应式**：单一 HTML 文件在手机 / 平板 / 桌面三种宽度都能看

## 执行流程

### Step 1. 读 state.json + templates/prototype-skeleton.html

### Step 2. 决定原型类型
基于 state.stages.6.tech_stack.frontend 和 mvp_features 数量：
- **single-screen**：1 个核心动作 → 单屏原型
- **multi-screen**：2-3 个核心动作 → 用 `<section>` + JS show/hide 模拟路由
- **dashboard**：含数据展示 → 多 widget 布局

### Step 3. 生成内容

#### 3.1 首屏（来自 Stage 4 的 first_screen）
- 顶部：产品名（来自 raw_idea 派生）+ 一句话价值主张（来自 value_prop）
- 主区：首要 CTA 按钮（来自 first_screen.primary_cta）
- 必须能在 3 次点击内到达核心动作

#### 3.2 核心流程（来自 Stage 4 的 journey）
为 journey 每一步生成对应的界面或交互：
- 每步用一个 `<section data-step="N">`
- 点击 CTA 按钮 → JS 切换 active section
- 用 mock 数据但要看起来像真实数据

#### 3.3 Aha 时刻
journey 中 aha_moment 那一步要"有戏"：
- 加载动画
- 渐显结果
- 微动效（CSS transition 即可，无需 JS 动画库）

#### 3.4 友好性体现（来自 Stage 5）
把 Stage 5 的 fail_fixes 都体现出来：
- N1 状态可见性 → 用 progress bar 或步骤指示
- N3 用户控制 → 每屏可回退
- N9 错误恢复 → 至少一处错误状态的友好提示
- D2 反馈 → 按钮点击有立即反馈

### Step 4. 设计风格默认

| 元素 | 默认值 |
|---|---|
| 字体 | system-ui, -apple-system, sans-serif |
| 主色 | #111827（深灰）+ 1 个 accent（用户可选或随机生成） |
| 圆角 | border-radius: 8px |
| 间距 | 8/16/24/32 px 阶梯 |
| 暗色模式 | @media (prefers-color-scheme: dark) 内嵌支持 |
| 移动端 | @media (max-width: 640px) 重排 |

### Step 5. 写文件
落盘到 `.idea/<slug>/prototype.html`。

### Step 6. 自检
在落盘前自检：
- [ ] 无任何 `<script src="...">` 外链
- [ ] 无任何 `<link rel="stylesheet" href="...">` 外链
- [ ] 至少一个 `addEventListener` 让原型可交互
- [ ] 包含 `@media (prefers-color-scheme: dark)` 块
- [ ] 文件大小 ≤ 80KB（防止 AI 失控生成几百 KB 的怪物）

如果自检失败 → 修复后再写，不允许带病落盘。

### Step 7. 给用户的最终交付话术

```
✅ 全部完成。产物：

  📄 PRD:    .idea/<slug>/prd.md
  🎨 原型:   .idea/<slug>/prototype.html
  🗺️ 旅程:   .idea/<slug>/journey.md
  💾 状态:   .idea/<slug>/state.json

下一步建议（按优先级）：

1. 浏览器双击打开 prototype.html，自己点 5 分钟
2. 找 3 个目标用户给他们看，**别解释**，看他们点哪里、说什么
3. PRD 看一眼，调整有把握的部分
4. 用 /init 起项目骨架，或把 prd.md 内容直接喂给 Claude Code 开写

需要现在 open 浏览器吗？(macOS: `open .idea/<slug>/prototype.html`)
```

## 输出 schema（写入 state.stages.7）

```json
{
  "prototype_path": ".idea/<slug>/prototype.html",
  "prototype_type": "single-screen|multi-screen|dashboard",
  "size_bytes": <数字>,
  "self_check_passed": true,
  "completed_at": "<ISO 8601>"
}
```

## 反模式

- ❌ 用 CDN 引入 Tailwind / React / 任何 UI 库
- ❌ Mock 数据明显假（"Lorem ipsum"、"test1"、"foo bar"）—— 必须看起来像真实场景
- ❌ 文件 > 200KB —— 单文件原型不该这么大
- ❌ 不响应式 —— 强制要求三宽度可用
- ❌ 跳过自检直接落盘 —— 自检失败要修
- ❌ 暗色模式没做 —— 现代用户期待，必须有

## 进度报数模板

```
Stage 7/7 | 阶段: {Read skeleton → 决定类型 → 生成 sections → 自检 → 写 prototype.html}
```

> ⚠️ 进入 Stage 7 之前必须 Read `templates/prototype-skeleton.html`。

## 最终交付 checklist（必须全勾才算完）

- [ ] `.idea/<slug>/prototype.html` 文件存在
- [ ] `grep -E 'script src=|link rel="stylesheet" href=' prototype.html` **无任何外链**
- [ ] 包含 `@media (prefers-color-scheme: dark)` 块
- [ ] 文件大小 ≤ 80KB（`wc -c prototype.html`）
- [ ] 至少一个 `addEventListener` 让原型可交互
- [ ] 包含 `@media (max-width: 640px)` 响应式块
- [ ] `state.stages.7` 已写入，`state.current_stage` = 7（已完成）
- [ ] 向用户输出 4 个产物路径 + 下一步建议
