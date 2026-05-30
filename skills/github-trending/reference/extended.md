# GitHub Trending 深度参考（Extended）

**本文件被 SKILL.md 通过「Extended Reference」按需加载**。日常使用只需读 SKILL.md + 运行脚本；只有做深度分析、定制模板、维护 scraper 时才读这里。

**核心原则（2026 版）**：
- GitHub Trending 是 **hype 晴雨表**，不是质量榜（Karpathy 等反复强调 AI slop 泛滥）。
- 本 skill 的唯一价值 = **数据 → 过滤 → 写出真实 angle**，而非再列一次 list。
- 永远用脚本拿结构化数据，绝不让 LLM 直接吞原始 HTML。

---

## 1. 数据源（推荐优先级）

### Primary（必用）
- `scripts/fetch_trending.py`（本 skill 提供）
  - 输出干净 JSON
  - 支持 since / language / spoken / developers
  - 容错解析当前 GitHub HTML（2026 仍以 article.Box-row + h2.h3 为主）

### Secondary（可选 enrich）
- GitHub Search API（需 token 时用）
  - 最近创建高星：`created:>2026-01-01 stars:>500`
  - 最近活跃高星：`pushed:>2026-04-01 stars:>1000`
- https://star-history.com（增长曲线可视化，判断是否真实爆发）
- https://ossinsight.io（官方洞察）

### 辅助信号（判断是否真火）
- Hacker News Show HN 评论质量
- X/Twitter 讨论密度（用 multi-ai-research 或 opencli 快速交叉）
- 实际 fork / 依赖数（比 star 更可信）
- 维护者历史（是否持续贡献 vs 一次性营销）

**自托管备选**（生产/高频使用推荐）：
- https://github.com/NiklasTiede/Github-Trending-API（Python+FastAPI，2026-04 仍有更新）
- https://github.com/antonkomarev/github-trending-api（Rust，轻量）

---

## 2. 项目评估维度（筛选 + 分析必读）

### 基础指标（必须看）
- Stars + **stars_today**（脚本已提供）
- Forks / Contributors
- 最近提交频率（可后续用 API 补）
- Issue / PR 响应（社区健康）

### 质量信号（区分 hype vs 真实）
**强正面**：
- README 有清晰问题陈述 + 真实使用案例
- 有测试、CI、License
- 多个活跃维护者或公司背书
- 被其他知名项目依赖

**强负面（Hype 红旗）**：
- 只有 README，代码极少
- Star 多但 fork 极少（营销驱动）
- Issue 积压严重，单个维护者
- 描述全是 buzzword，无具体 benchmark / 案例
- 24h 内 star 暴涨但随后归零（典型 X 推广 spike）

### 趋势类型（帮助写 angle）
1. **爆发型 (Viral)**：1 天 1000+ star，通常 HN/Reddit/X 首页 + 解决方案热点
2. **稳定增长型 (Steady)**：每天 10-80 star，口碑驱动，值得长期跟踪
3. **周期型**：面试题、年度总结类，有固定窗口
4. **长尾型**：低调但持续被用，生产力工具

**写 angle 时优先挑 Steady + 有真实痛点解决的**。

---

## 3. 趋势解读模板（推荐结构）

### 单项目卡片（用于 TOP N）
```markdown
### {rank}. {full_name} ⭐ {stars} (+{stars_today} today)
> {description}

- **语言**: {language} | **License**: (后续 enrich)
- **为什么值得关注**: {1-2 句痛点 + 解法}
- **真实信号**: {forks / 最近活跃 / 被谁引用}
- **潜在风险**: {hype 迹象 or 成熟度问题}
- **适合人群**: {新手 / 生产 / 研究}
```

### 完整日报结尾必须有「今日观察 / Angle」
这是本 skill 的灵魂。**没有 angle 的输出 = 失败**。

好 angle 示例：
- “今天 Rust 生态出现两个系统级重写工具，都在解决同一类高并发场景下的内存安全痛点，说明社区正在从‘能用’走向‘极致可靠’。”
- “AI Agent 类项目仍占 Trending 40%+，但真正有 star 增量且 fork 跟上的只有 3 个，说明市场已从‘概念验证’进入‘谁先有真实用户谁赢’的阶段。”

坏 angle 示例：
- “今天有几个 AI 项目上了榜，值得关注。”
- 纯复述 star 数 + 描述（没有洞察）。

---

## 4. 避免的陷阱（X 社区 2025-2026 共识）

- 不要只看 star 数（已被 X 营销严重污染）
- 不要把所有 “awesome-xxx” 当成趋势（它们是索引，不是创新）
- 不要忽略“star 今天暴涨但昨天也暴涨”的项目（通常是推广循环）
- 不要在日报里推荐你自己没看懂的项目
- 语言过滤时注意：GitHub trending 的“中文”内容经常是文档/教程，而非核心工具

---

## 5. 进阶用法

### 结合其他 skill
- 发现 2-3 个重点项目后 → 调用 `multi-ai-research` 做“这个项目在 X 上的真实讨论密度”
- 想发内容 → 把日报 JSON + angle 喂给 `scout-to-article` 或直接 `blog-write`
- 想长期跟踪 → 用 `loop` 技能每天跑一次，输出到固定目录

### 开发者榜特殊处理
开发者榜更适合“关注人”而非“关注项目”。适合场景：
- 找潜在合作者 / 导师
- 观察某个语言社区的意见领袖
- 招聘信号（高排名 + 频繁换工作 = 活跃人才）

---

## 6. Scraper 维护提示

GitHub 页面结构偶尔变化（通常是 class 重命名）。当脚本输出条目 < 3 时：

1. 手动打开 https://github.com/trending?since=daily 用浏览器检查元素
2. 更新 `parse_repository` / `parse_developer` 里的 select 选择器
3. 优先保持“多兜底 + 容错”而非精确 class
4. 考虑切换到自托管 API（更稳定）

当前（2026）主要选择器仍围绕：
- `article.Box-row`
- `h2.h3.lh-condensed a` （仓库名）
- `p.my-1, p.col-9` （描述）
- `a[href$='/stargazers']` （star）

---

**维护者提示**：每次重大 GitHub UI 改版后，跑一次 `--limit 3` 验证脚本是否还能产出 ≥3 条有效数据，并更新本节日期。

---

*本文件最后更新：2026-05（随 skill 优化同步）。所有日期示例均已移除，永远以脚本实时数据为准。*