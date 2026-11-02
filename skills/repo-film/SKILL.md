---
name: repo-film
description: 把一个 git 仓库在一段时间里的真实提交做成 15–25 秒的炫酷短片：主线和各条分支按真实分叉、合并同时生长成流程图，越长越快再拉远看全景；仓库有 you-are-here 项目地图时，整张网会收拢成地图里的阻塞链，再沿地图讲卡点、当前位置和一句话总结，最后接可改的结尾卡片。一行命令出 MP4，基于 motion-stack 渲染器。当用户说「把这个仓库这周 / 昨晚做的事做成视频」「做个项目进展短片」「git 记录做成流程图动画」「给 you-are-here / 某项目做宣传视频」「像上次 Keepline 那个视频一样做一个」时使用。只在明确请求时触发，忽略顺带提及。
---

# repo-film：仓库的一段时间 → 一条短片

**要支撑的决定**：任何仓库的任何一段时间，能不能一行命令、不改场景代码就出一条能发的片子。
**放弃条件**：到 2026-12-15 为止，除 Keepline 和 Spellbook 两次验收外没有再用过；或者连续两个新仓库都得改 `template/scene.html` 才能出片。满足任一条就停用，把分支布局脚本并进 motion-stack 的示例。每做完一部，在下方“做过的片子”表里记一行。

## 用法

```bash
node <本 skill 目录>/scripts/make.mjs \
  --repo <仓库路径> --since "2026-11-01 20:00" --until "2026-11-02 06:00" \
  [--branch main] [--map auto|none|<地图 html>] [--config film.json] [--out <目录>] [--sheet-only]
```

- 先加 `--sheet-only` 只出关键帧拼图（`out/beats.png`），自己看一遍再出片。
- 成片在 `<out>/out/<仓库名>-film.mp4`，1920×1080、30fps，响度约 -14 LUFS。没有地图约 13 秒，有地图约 24 秒。
- `--out` 默认是 `~/Videos/repo-film/<目录名>-<开始日期>`，里面就是完整工程，可以直接改 `scene.html` 或 `<out>/assets/film.js` 再用 motion-stack 的 `render.mjs` 重渲。
- 依赖：motion-stack skill（装在本 skill 旁边，或在 `~/.claude/skills`、`~/.codex/skills`、`~/.agents/skills` 里，也可以用 `MOTION_KIT` 指向它的 `kit/`；第一次要在 `kit/` 里 `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install`）、python3、ffmpeg。Tone.js 优先复用 motion-stack 示例的 `node_modules`，没有才 `npm install`。

## 流水线

1. `scripts/lanes.py`：只读 git（`--all`，所以本地分支也算）。`--branch` 的 first-parent 链是主线（第 0 道），其余提交按 first-parent 串成分支段；每段从分叉点到合并点占一个区间，区间重叠的段分到不同的道（上下交替）。分支名从 `Merge branch 'x' into y` 里读，读不到就不标。超过 `--max`（默认 400）只留最新的。
2. `scripts/capture.mjs`：有地图时，把地图临时排成单栏（阻塞链不再横向滚动，能完整显示），截 2 倍图，并记下各区块位置和阻塞链每条连线的路径。只改截图时的样式，不改地图文件。
3. `make.mjs` 按数据生成字幕和结尾卡片，写进 `<out>/assets/film.js`，再用 `--config` 覆盖。
4. 渲染：关键帧拼图 → 纯度检查（正放和倒放必须一致）→ MP4。响度由 motion-stack 渲染器自动调到 -14 LUFS，数值在成片旁的 `.manifest.json` 里。

## film.json（全部可选）

```json
{
  "captions": [["你离开了。", "You step away."], ["agent 们接着干。", "The agents keep going."],
               ["一夜，51 个提交，8 条分支。", "One night. 51 commits. 8 branches."], ["回来，打开一页。", "Come back. Open one page."]],
  "sub": "KEEPLINE · 11-01 20:01 → 11-02 04:34",
  "startLabel": "20:00 开工",
  "end": { "title": "you-are-here", "tagline": "…", "taglineEn": "…",
           "lines": ["/plugin marketplace add majiayu000/you-are-here"], "meta": "github.com/…" }
}
```

字幕四个位置分别是 0.6 秒、3 秒、7.6 秒（全景）和 8.65 秒（只在有地图时出现，引出地图）。`end.lines` 以 `/` 或 `$` 开头的部分会着色，适合放安装命令。

## 公开前检查

- **提交说明会原样上屏**（截到 40 个字）。先 `git log` 看一遍那段时间有没有不该公开的项目名、人名、内部链接。
- **地图**：优先用 `.project-map/index.public.html`（去掉本机路径的版本）。脚本发现地图里有 `/Users/` 这类路径会警告；右上角的仓库名标签和 GitHub 链接会带用户名。
- 字体用本机的 SF 字体渲染，只复制进工程目录，不要连工程一起公开。

## 做过的片子

| 片子 | 结果 |
|---|---|
| Keepline 11-01 20:00 → 11-02 04:34，带地图（you-are-here 宣传片） | 51 提交、8 条分支；一行命令复现手工版，结尾换成 you-are-here 文案 |
| Spellbook 10-01 → 10-08，无地图 | 48 提交、14 条分支，未改场景代码出片 13.5 秒；暴露并修了两处：片名用了 worktree 目录名（改读 origin 地址），道多时上下分支出画（镜头改为同时跟纵向并按道数拉远） |

## 没验过的

- 竖版 9:16：地图镜头和卡片在竖屏里太小，需要另做排版。
- 很长的时间段（几百个提交、几十条分支）：只验到 51 个提交、14 条分支。卡片会变得很密，可能要改成只显示圆点。
- 阻塞链为空的地图：代码里会退回到落在一句话总结那几行上，没有实际跑过。
- 连续播放的观感和音效：只看过关键帧，靠用户看片验收。
