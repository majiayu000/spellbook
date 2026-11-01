---
name: code-film
description: 用纯代码（three.js 离线渲染 + 合成音频）做有故事、有电影质感的动画短片并导出 MP4。当用户想做短片、动画片、宣传片、角色动画、循环视频、片头、产品故事片，或者说“用代码做个视频”“做一个有趣的短片”“帮我设计个小动画”“make a short film / animated video / motion piece with code”时使用，即使没提 three.js。也用于继续修改这类片子。写实真人、实拍感、AI 视频生成、普通视频剪辑不适用。
---

# Code Film

用一个 HTML 文件生成整部短片：画面和声音都是时间 `t` 的纯函数，离线逐帧渲染成 MP4，不用任何外部素材。

**核心是一个有魅力的角色演一个看得懂的故事**，渲染只是保证质量不掉。优先级：角色 > 表演 > 故事逻辑 > 世界 > 渲染。

这套做法适合风格化角色、微缩玩具感、动态图形、把抽象概念做成实物的片子。真人、写实表情和实拍质感做不好，遇到时直接告诉用户，并建议用拍摄、Blender 或 AI 视频模型。

下面命令里的 `<skill-dir>` 是本 skill 的安装目录：Claude Code 通常是 `~/.claude/skills/code-film`，Codex 通常是 `~/.agents/skills/code-film`。

## 工作流

按顺序走。每一步都有一个用户能看的东西，这样方向错了能尽早发现。

### 1. 先把用户定下的东西列出来

角色、品牌、题材、风格、时长，用户提到的都算定了。用户说“更有趣”“脱离原来的”，指的通常是内容，不是换主角。想改用户定下的东西时，先单独问，不要写进方案里默认通过。

### 2. 角色定稿

**默认主角是 Clawd。** 用户没指定角色时就用它，直接进入第 3 步，不换、不重新设计，也不用为了避开品牌问题而替换。它的标准图在 `assets/characters/clawd-sheets/`。

只有用户明确要新角色时，才读 [references/character.md](references/character.md)，单独把角色做到位，出造型图、表情表和走路测试，发给用户确认。新角色确认前不写故事、不搭场景，因为后续工作都建立在它上面，返工最贵。

### 3. 设计故事，先给方案再动手

读 [references/story.md](references/story.md)，用一张时间表给出方案：标题、片长、角色、每场发生什么、保留和去掉的东西。检查因果：每个道具和角色为什么在这里、观众凭什么看懂。

用户确认后才开工。

### 4. 做 15 到 20 秒样片，用最终画质

选最难的两段，直接按成片标准做。**不做灰模。** 用户拿上一部的质量当基准，灰模看起来就是退步，而且模板已经带好了全部画质能力，灰模省不了多少事。

```bash
cp <skill-dir>/assets/film-template.html <folder>/<film>.html
```

用 `scripts/use_character.py` 放入定稿角色，再改模板里 `WORLD`、`PERFORMANCE`、`SHOTS`、`SOUND` 这几节，渲染和后期不用动。模板本身就是一部能渲染的 7 秒小片，默认主角是 Clawd。做世界时读 [references/craft.md](references/craft.md)。

如果片子有真实概念（代码、数学、科学），先把它跑通再搭景。上一部的报错、堆栈、修复结果都是真实程序的输出，这比编造的更有趣，也更可信。

### 5. 每轮抽帧检查

```bash
uv run --with playwright --python 3.12 python -I <skill-dir>/scripts/stills.py <film.html> <outdir> 1.5,4.2,7.6,12 8
```

然后用 Read 看 `<outdir>/sheet0.jpg`。一张图 12 格。逐格问：观众看得懂吗？角色完整吗？脸露出来了吗？主角和背景分得开吗？列出问题，一次修一批，再看。

### 6. 给用户看样片，再做全片

样片确认后才扩展。全片沿用样片的世界和时间轴，新场景放在同一文件里，用 `T1`、`T2` 这样的分段常量切换。

循环片要让最后一帧的所有状态等于第一帧：物体位置、地面颜色、镜头、文字朝向都要对上，用 `check.py --loop` 量。

### 7. 渲染、核对、交付

```bash
uv run --with playwright --python 3.12 python -I <skill-dir>/scripts/render.py <film.html> <film.mp4>
uv run --with playwright --python 3.12 python -I <skill-dir>/scripts/check.py <film.html> <film.mp4> --loop --level 全片:0-20
```

长片放后台跑，1080p 60 fps 每帧 16 次采样约 0.17 到 0.25 秒一帧（M2 Max），50 秒的片子约 9 分钟。

MP4 是主要交付物，实时网页版的景深边缘明显更差，不要拿它当成片。用户要在线看时，页面直接播放视频。

### 8. 如实汇报

说清楚验证过什么、没验证什么。你只能抽帧，不能连续看片，也听不到声音，所以节奏和音色要交给用户判断。列出自己觉得还不够好的地方。

## 质量底线

| 项 | 标准 |
|---|---|
| 分辨率和帧率 | 1920×1080，60 fps |
| 采样 | 每帧 16 次 |
| 压缩 | 默认 CRF 17（约 11 到 13 Mbps）。这个片子里 CRF 15 有 43 Mbps，CRF 20 只有 3 Mbps |
| 响度 | 约 -16 到 -19 LUFS，峰值低于 -2 dBFS |
| 视觉 | 物理材质、环境反射、景深、接触阴影、表面纹理，一样都不能少 |

## 参考

- [references/character.md](references/character.md)：角色设计原则、文件约定和定稿流程，第 2 步读。
- `assets/characters/`：角色文件。`clawd.js` 是默认主角，不能删除或替换；`sprout.js` 是原创角色，也是设计新角色的起点。
- [references/story.md](references/story.md)：故事结构和逻辑检查，构思时读。
- [references/craft.md](references/craft.md)：世界、灯光、镜头、声音的做法和踩过的坑，搭景时读。
- [examples/last-bug/](examples/last-bug/)：一部完整的 50 秒循环片和它真实运行的程序，主角是 Clawd。要参考多场景结构或积木世界时打开。
- `assets/vendor/three.min.js`：three.js r160，脚本渲染时自动使用，不依赖网络。
