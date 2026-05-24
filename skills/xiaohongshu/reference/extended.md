# xiaohongshu Extended Reference

This file preserves detailed material moved out of `SKILL.md` for progressive disclosure. Load it only when the current task needs the specific examples, commands, templates, or checklists below.

Moved content starts at: `## 高赞笔记数据库`.

## 高赞笔记数据库

本地维护一个高赞笔记数据库，持续积累竞品数据，为创作提供数据驱动的参考。

数据库路径：`<工作目录>/database/`（与 `posts/` 同级）
- `feeds.json` — 笔记原始数据 + 分析标注
- `summary.md` — 自动生成的分析摘要

### 采集流程

当用户要求「收集高赞笔记」「更新数据库」「分析竞品」时，执行以下流程：

**1. 搜索目标笔记**

```
mcp__xiaohongshu-mcp__search_feeds(keyword="[关键词]", filters={"sort_by": "最多点赞"})
```

**2. 获取高赞笔记详情**

对搜索结果中赞数较高的笔记（建议 TOP 5-10），逐个获取详情：

```
mcp__xiaohongshu-mcp__get_feed_detail(feed_id, xsec_token)
```

**3. 分析并标注**

对每篇笔记提取以下维度：

```json
{
  "feed_id": "笔记ID",
  "title": "标题",
  "author": "作者昵称",
  "author_id": "作者ID",
  "content": "正文全文",
  "likes": 157,
  "favorites": 152,
  "comments": 3,
  "images_count": 14,
  "domain": "科技",
  "keywords": ["Claude Code", "更新"],
  "xsec_token": "token",
  "analysis": {
    "title_type": "数字型|情绪型|热点型|混合型",
    "content_type": "图片流|正文详写|结构化长文",
    "image_style": "博客长图|推文截图|手写笔记卡片|文档卡片|深色科技卡片",
    "hook": "数字冲击|个人叙事|热点引入|痛点提问",
    "cta": "提问引导|行动号召|情感共鸣",
    "tags_used": ["ClaudeCode", "AI编程"],
    "fav_like_ratio": 0.97,
    "comment_like_ratio": 0.02,
    "key_elements": ["数字冲击标题", "14张图片干货", "个人使用经验"],
    "notes": "收藏率极高，图片即干货"
  }
}
```

**4. 写入数据库**

```bash
python3 ~/.claude/skills/xiaohongshu/scripts/feed_database.py  # 在工作目录下执行 add '<json>'
```

**5. 生成分析摘要**

采集完成后，运行分析命令自动生成 `summary.md`：

```bash
python3 ~/.claude/skills/xiaohongshu/scripts/feed_database.py  # 在工作目录下执行 analyze
```

### 数据库命令参考

| 命令 | 说明 | 示例 |
|------|------|------|
| `add '<json>'` | 添加/更新笔记（同 feed_id 自动更新） | `add '{"feed_id":"abc","title":"..."}'` |
| `list` | 列出所有笔记（按赞数降序） | `list --domain 科技 --min-likes 50` |
| `get <feed_id>` | 获取单条完整数据 | `get abc123` |
| `delete <feed_id>` | 删除一条 | `delete abc123` |
| `analyze` | 生成分析摘要到 summary.md | `analyze` |
| `stats` | 数据库统计 | `stats` |


这样每次创作都会让数据库越来越丰富，分析结论越来越准。

---

## 标签参考

参考 [tag-database.md](tag-database.md) 中的基础标签库

## 配图风格

配图风格完全由 **UI/UX Pro Max Skill** 驱动，不维护本地风格模板。

**数据库规模：**
- 67 种 UI 样式（Glassmorphism、Bento Grid、Cyberpunk、Neubrutalism...）
- 96 种行业配色方案
- 57 种字体配对
- 100 条行业推理规则（自动匹配最佳风格）

每次生成配图时调用 `search.py --design-system`，它会根据内容主题自动推荐样式+配色+字体+动效，确保每次风格都不一样。

---

## ⚠️ 防限流规则（必须遵守）

以下行为会导致笔记被限流，**发布前必须逐条检查**：

### 绝对禁止（触发即限流）

| 禁止行为 | 说明 |
|---------|------|
| 正文放安装命令/代码 | 安装命令、代码片段一律放评论区，正文写"见评论区" |
| 正文放外部链接/URL | 任何 http/https 链接、GitHub 地址都不能出现在正文 |
| 通篇产品功能罗列 | 不能整篇都在介绍产品功能，必须有场景叙事 |
| 提具体平台引流 | 不要写"GitHub 上 26K 星"，改为"超火的开源项目" |
| 绝对化用语 | "最""第一""唯一""100%"等 |

### 必须做到（提升推荐概率）

| 规则 | 说明 |
|------|------|
| 场景化叙事开头 | 先说痛点/个人经历，再自然引出产品 |
| 结尾必须提问 | 引导评论互动，系统看互动率决定是否继续推 |
| 正文结构：7-3 原则 | 70% 个人体验/场景描述，30% 产品介绍 |
| 安装/链接放评论区 | 正文只引导"安装方式见评论区"，具体命令发评论 |
| 封面简洁有焦点 | 1.5 秒内抓住重点，不要信息过载 |
| 搜索关键词布局 | 标题和正文包含用户会搜索的词 |

### 发布后必做

- 搜索笔记获取 feed_id，用 MCP 在评论区补充引导信息
- 搜索笔记确认可见
- 如果搜不到，可能已被限流，检查以上规则

### 评论区安全规则

评论同样会被过滤，以下内容**会被吞（仅自己可见）**：

| 会被吞的 | 安全替代 |
|---------|---------|
| `/plugin install xxx` 命令格式 | "搜 xxx 就能找到，两步装好" |
| `http://` 任何链接 | "搜xx关键词就行" |
| 完整安装路径/代码 | 做进配图里，评论说"看最后一张图" |
| "私信""私我""加我微信" | "看我主页" 或 "评论区聊" |
| 谐音/加密绕过 | 不要尝试，AI 能识别 |

**安全评论写法示例：**

```
# 引导安装（口语化，不带命令格式）
想装的：打开 Claude Code，搜 ui-ux-pro-max-skill 就能找到，两步就好

# 引导看图
安装方式在最后一张图里，超简单的

# 补充说明（拆成多条自然评论）
评论1: 装法超简单，搜插件名就行
评论2: 装完直接说"帮我做个落地页"就能用了
```

**评论发布流程：**
```
1. 搜索笔记获取 feed_id + xsec_token
   mcp__xiaohongshu-mcp__search_feeds(keyword="标题关键词", filters={"sort_by": "最新"})

2. 发布口语化评论（不含命令/链接/敏感词）
   mcp__xiaohongshu-mcp__post_comment_to_feed(feed_id, xsec_token, content)

3. 如有多条补充信息，拆成多条自然评论分别发
```

---

## 注意事项

1. 不用"最""第一"等绝对化用语
2. 软性种草，避免硬广
3. 结尾必须提问
4. 配图比例推荐 3:4 竖版（1080x1440）
5. 避免纯 AI 味，加入个人口吻
6. 功能描述要转化成用户价值（差："新增 pages 参数" → 好："大PDF不用全部加载了，省token"）
7. 发布失败最常见原因：标题超20字
8. MCP 发布后无法编辑/删除，发布前务必确认内容
