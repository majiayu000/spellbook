---
name: github-trending
description: GitHub Trending 探索与分析。用于发现热门开源项目、技术趋势、开发者偏好，帮助理解技术社区的兴趣走向。使用场景包括“看看今天 GitHub 什么火了”、“Rust 最近热门项目”、“AI 领域趋势日报”、“这个方向有没有值得关注的开源项目”、“帮我做个 GitHub trending 分析”。
---

# GitHub Trending 探索

**2026 版核心认知**：GitHub Trending 已是严重被 hype 和 AI slop 污染的榜单（Karpathy 等反复确认）。**本 skill 的唯一价值是「结构化数据 + 严格过滤 + 写出真实 angle」**，而不是再输出一份 list。

**职责边界**（严格遵守）：
- 只负责**发现 + 趋势分析 + 日报/洞察报告**
- **不负责**把结果加工成公众号/小红书/X 帖（用 `/scout-to-article` 或 `/blog-write`）
- **不负责**多 AI 深度竞品/社区反应调研（用 `/multi-ai-research`）

---

## 何时触发（推荐触发词）

- 探索今日/本周热门
- “Rust / Python / Go 最近有什么好项目”
- “AI / Agent / LLM 领域现在 trending 什么”
- “帮我看看 GitHub trending，有没有类似 X 的项目”
- “最近什么技术在快速增长，值得关注”
- “做个 GitHub trending 日报 / 周报”
- 想过滤 hype、要真实增长信号时

**不适合**：纯快速事实查询（直接让 Claude 回答即可）。

---

## 完整工作流（必须按顺序，不要跳步）

1. **拿干净数据（优先用脚本）**
   ```bash
   # 在 skill 目录执行；如果 skill 已安装到 ~/.claude/skills，也可以换成对应安装路径
   cd /path/to/spellbook/skills/github-trending

   # 今日总榜 TOP 8
   python3 scripts/fetch_trending.py --since daily --limit 8

   # Rust 周榜
   python3 scripts/fetch_trending.py --since weekly --language Rust --limit 6

   # 开发者榜
   python3 scripts/fetch_trending.py --developers --since daily --limit 10
   ```
   脚本输出结构化 JSON，**绝不直接 WebFetch 原始 HTML**。

2. **筛 TOP N + 过滤 hype**
   - 默认 5-8 个
   - 优先选 **stars_today 有真实增量 + forks 跟上 + 不是纯 awesome-list** 的
   - 参考 `reference/extended.md` 中的「Hype 红旗」快速排除

3. **必要时轻度 enrich**
   - 只对最终入榜的 2-3 个项目，必要时再用 WebFetch 看 README 头部或 Releases
   - 不要一上来就读全量 README

4. **套模板 + 必写 Angle**
   - 用参考模板组织
   - **最后必须有独立一段「今日观察 / Angle」**，这是产出价值所在

5. **输出 + 归档（可选）**
   - 普通用户：直接给 Markdown 日报
   - 想后续发文：把 JSON + angle 结构喂给下游 skill

---

## 脚本安装与依赖

首次使用执行：
```bash
python3 -m pip install -r requirements.txt
```

如果没有 `requirements.txt`，手动安装：
```bash
python3 -m pip install requests beautifulsoup4 lxml
```

脚本位置：`scripts/fetch_trending.py`（相对本 skill 目录）。

支持参数见脚本 `--help`。所有错误都会以清晰 JSON 返回，绝不静默失败。

---

## 输出硬性要求

**日报结尾必须包含「Angle」段**，否则视为不合格输出。

好 Angle 特征：
- 指出 1-2 个跨项目模式（技术演进、社区偏好、 hype 信号）
- 给出可行动建议（“这个方向值得跟进，但优先看 fork 增长”）
- 基于**今日真实数据**，不复述旧知识

---

## 进阶场景

- **领域深度报告**：先用脚本按 language 拉月榜，再结合 `reference/extended.md` 里的评估框架写对比表。
- **长期跟踪**：用 `/loop` 技能每天定时跑脚本 + 分析，输出到固定目录。
- **想知道社区真实反应**：对重点项目再调用 `/multi-ai-research`。
- **想发内容**：把结构化结果 + angle 交给 `scout-to-article`。

---

## Extended Reference

所有详细框架（数据源、评估维度、hype 识别、趋势分类、好/坏 Angle 示例、scraper 维护提示、2026 社区共识）已移至 [`reference/extended.md`](reference/extended.md)。

日常触发时**不需要**读它。只有你要定制模板、维护脚本、或做高精度分析时再加载。

---

**更新记录**：2026-05 完整重构（引入可靠 scraper 层 + 严格 pipeline + 拆分 reference + 移除所有硬编码日期/旧趋势列表）。数据永远以脚本实时输出为准。
