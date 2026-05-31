# slides Extended Reference

This file preserves detailed material moved out of `SKILL.md` for progressive disclosure. Load it only when the current task needs the specific examples, commands, templates, or checklists below.

Moved content starts at: `## 工作流程`.

> 本文中的 `<设计系统目录>` 指你的设计系统 CSS 所在目录，使用时替换为绝对路径（例如 `~/Desktop/code/work/life/xhh`）。

## 工作流程

### 第一步：确认输入 + 判断内容类型

用户可能提供：
1. **讲稿文件**（.md/.txt）→ 读取内容，直接拆页
2. **主题关键词** → 先构思讲稿再拆页
3. **素材文件**（文章/changelog）→ 提炼要点后拆页

同时确认背景主题偏好（默认 warm）。

**⚠️ 必须判断内容类型**（人物型/教程型/新闻型/观点型），参考上方「内容类型」章节。内容类型决定封面和前 3 页的视觉策略，**在拆页前就要确定**。

判断方法：
- 讲稿/素材围绕某个人 → 人物型（找出此人最知名的身份标签）
- 讲稿教怎么做 → 教程型
- 讲稿报道事件/产品更新 → 新闻型
- 讲稿输出个人看法 → 观点型

### 第二步：构思讲稿（有现成讲稿可跳过）

如果用户只给了主题，先构思一份 3-8 分钟的口播讲稿：
- 用 WebSearch 搜索相关信息
- 口语化风格，像跟朋友聊天
- 结构：痛点开场 → 引出方案 → 分步讲解 → 总结/互动

**⚠️ 讲稿情感化规则（极其重要）：**

讲稿决定视频质量的 80%。不是传递信息，是制造情绪共鸣。

| 原则 | ❌ 信息传递（无人看） | ✅ 情感场景（有人看） |
|------|---------------------|---------------------|
| 开头 | "今天介绍一个AI工具" | "明天就是汇报日，指针滑过凌晨两点" |
| 描述功能 | "支持热更新预览" | "左边屏幕让AI改，右边立刻刷新，效率直接拉爆" |
| 引用数据 | "效率提升10倍" | "3个工程师，0行手写代码，五个月做出百万行产品" |
| 总结 | "综上所述，该工具值得使用" | "能写代码的AI到处都是，能决定写什么的人才稀缺" |

**文案公式：场景画面 → 情绪触发 → 观点输出**

```
✅ "你瞪着发亮的屏幕，PPT还有一半没做完"（场景）
✅ "想想都美啊"（情绪）
✅ "人类掌舵，Agent执行"（观点金句）

❌ "该工具能够自动生成PPT文件"（功能说明书）
❌ "支持多种格式导出"（参数罗列）
```

**每段讲稿自检**：闭上眼睛读这句话，脑子里能不能出现一个画面？如果只是一句抽象的话，重写。

### 第三步：拆页 + 标注颜色

将讲稿拆成 20-40 页，每页标注 CSS 类。这是核心步骤，严格遵守拆页规则。

**拆页思路**：
- 读一遍讲稿，标出每个"观点切换点"
- 每个切换点 = 一次翻页
- 强调词/工具名/步骤号 用对应语义色
- 补充说明用灰色 vo-sub

### 第三步半：生成封面（cover.html）

拆页完成后，**先生成封面**。封面是独立于 slide_01~XX 的文件，用 `cover.html` 命名。

**生成步骤**：
1. 从讲稿提取三层文字（理性钩 + 感性钩 + 降门槛钩），参考上方「感性钩的提取规则」
2. 选择钩子颜色（根据内容情绪，参考上方「封面钩子颜色」表）
3. 背景主题用和内页相同的主题，加 `vo-cover-bg-boost` 增强
4. 用 Write 工具写 `cover.html`
5. 截图 → `cover.png`

**封面和内页的关系**：
- `cover.png` 是视频的第一帧（缩略图），在 ffmpeg 合成时排在最前面
- `slide_01.html` 是视频正文第一页，封面之后立即出现
- 封面固定 3 秒，和 slide_01 **共享第一段音频**。语音从视频开头（t=0）就开始播放，不要有静音延迟
- 封面 3 秒 + slide_01 = 第一段音频时长。例如第一段音频 3.7 秒，则封面 3 秒 + slide_01 显示 0.7 秒

### 第四步：创建输出目录 + 逐页写 HTML

```bash
mkdir -p <设计系统目录>/voiceover/<slug>
```

先写 cover.html，然后用 Write 工具逐页生成 HTML 文件：`slide_01.html`, `slide_02.html`, ...

**并行写多个文件提高效率**（每次可以同时写 3-5 个）。

### 第五步：批量截图

用 Chrome headless 逐页截图。

**⚠️ 窗口尺寸必须用 1920,1200（不是 1920,1080）**，Chrome headless 有 87px 内部顶栏，直接用 1080 会导致底部白条。截图后用 Pillow 裁切到 1920×1080。

```bash
cd <输出目录>

# 1. 截图（封面 + 所有幻灯片，窗口加高到 1200）
for f in cover.html slide_*.html; do
  [ -f "$f" ] || continue
  raw="/tmp/vo_raw_${f%.html}.png"
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
    --window-size=1920,1200 \
    --screenshot="$raw" \
    "file://$(pwd)/$f" 2>/dev/null
done

# 2. 裁切到 1920×1080
python3 -c "
from PIL import Image
import glob, os
for html in sorted(glob.glob('cover.html')) + sorted(glob.glob('slide_*.html')):
    name = html.replace('.html', '')
    raw = f'/tmp/vo_raw_{name}.png'
    if os.path.exists(raw):
        Image.open(raw).crop((0, 0, 1920, 1080)).save(f'{name}.png')
print('裁切完成')
"
```

验证底部无白条：

```bash
python3 -c "
from PIL import Image; import numpy as np
arr = np.array(Image.open('slide_01.png'))
bottom = arr[-5:,:,:].mean(axis=(0,1)).astype(int)
print(f'底部5px RGB={bottom}')
assert not all(c > 250 for c in bottom), '底部有白条！'
print('✅ 无白条')
"
```

### 第六步：生成预览器 + 口播稿

**preview.html** — 箭头键翻页预览所有 PNG：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>口播幻灯片预览</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #111; display: flex; align-items: center; justify-content: center;
    height: 100vh; font-family: -apple-system, sans-serif; color: #fff; overflow: hidden;
  }
  .viewer { width: 90vw; max-width: 1440px; aspect-ratio: 16/9; }
  .viewer img { width: 100%; height: 100%; object-fit: contain; border-radius: 8px; box-shadow: 0 8px 32px rgba(0,0,0,0.5); }
  .controls {
    position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
    display: flex; align-items: center; gap: 16px;
    background: rgba(255,255,255,0.1); backdrop-filter: blur(8px);
    padding: 8px 20px; border-radius: 100px; font-size: 14px;
  }
  .controls button { background: none; border: 1px solid rgba(255,255,255,0.2); color: #fff; padding: 6px 16px; border-radius: 6px; cursor: pointer; }
  .controls button:hover { background: rgba(255,255,255,0.1); }
</style>
</head>
<body>
<div class="viewer"><img id="slide" src=""></div>
<div class="controls">
  <button onclick="prev()">&#8592;</button>
  <span id="counter"></span>
  <button onclick="next()">&#8594;</button>
</div>
<script>
const slides = [/* 替换为实际 PNG 文件名列表 */];
let cur = 0;
const img = document.getElementById('slide'), ctr = document.getElementById('counter');
function show(i) { cur = Math.max(0, Math.min(i, slides.length-1)); img.src = slides[cur]; ctr.textContent = (cur+1)+'/'+slides.length; }
function prev() { show(cur-1); } function next() { show(cur+1); }
document.addEventListener('keydown', e => { if(e.key==='ArrowLeft') prev(); if(e.key==='ArrowRight') next(); });
show(0);
</script>
</body>
</html>
```

**script_notes.md** — 每页对应的口播要点。

**voiceover_text.txt** — TTS 用的纯文本口播稿。每段用空行分隔，段数 = 页数（一段对应一页幻灯片）。

### 第七步：生成字幕（Pillow 烧入法）

**字幕对小红书视频极其重要** — 很多用户不开声音浏览。

**⚠️ 不要用 ffmpeg 的 `subtitles` 滤镜**，它依赖 libass，macOS homebrew 的 ffmpeg 默认不含此库。改用 Pillow 把字幕直接烧进幻灯片图片，再用 ffmpeg 拼接。

**原理**：每段口播按标点拆成短句，每句生成一张「原始幻灯片 + 底部字幕」的 PNG，按时长拼接成视频。

#### 7.1 生成 segments.json

TTS 音频生成后，记录每段音频的字节大小（同比特率下字节 ∝ 时长）：

```python
import json, os, glob
audio_files = sorted(glob.glob('audio/slide_*.mp3'))
segments = [os.path.getsize(f) for f in audio_files]
with open('segments.json', 'w') as f:
    json.dump(segments, f)
```

#### 7.2 生成字幕帧图片

```python
import json, subprocess, re, os
from PIL import Image, ImageDraw, ImageFont

text = open('voiceover_text.txt').read().strip()
paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
segments = json.loads(open('segments.json').read())
total_bytes = sum(segments)
r = subprocess.run(['ffprobe','-v','quiet','-show_entries','format=duration',
    '-of','csv=p=0','voiceover_volcano.mp3'], capture_output=True, text=True)
audio_duration = float(r.stdout.strip())
seg_durations = [s / total_bytes * audio_duration for s in segments]

# macOS 中文字体（按优先级尝试）
for fp in ['/Library/Fonts/Arial Unicode.ttf',
           '/System/Library/Fonts/STHeiti Medium.ttc']:
    if os.path.exists(fp):
        font = ImageFont.truetype(fp, 42)
        break

# 时间分配（封面 3s + slide_01 共享第一段音频）
cover_dur = 3.0
s01 = max(seg_durations[0] - cover_dur, 0.5)
durations = [cover_dur, s01] + seg_durations[1:]
slide_files = ['cover.png', 'slide_01.png'] + \
    [f'slide_{i+1:02d}.png' for i in range(1, len(segments))]
para_for_slide = [paragraphs[0], paragraphs[0]] + paragraphs[1:]

sub_dir = 'sub_slides'
os.makedirs(sub_dir, exist_ok=True)
concat_lines = []
img_idx = 0

for slide_i, (slide_file, dur) in enumerate(zip(slide_files, durations)):
    img = Image.open(slide_file)
    para = para_for_slide[slide_i]
    sentences = re.split(r'[，。！？、；\n]', para)
    sentences = [s.strip() for s in sentences if s.strip()] or ['']
    sent_dur = dur / len(sentences)

    for sent in sentences:
        frame = img.copy()
        if sent:
            draw = ImageDraw.Draw(frame)
            w, h = frame.size
            bbox = draw.textbbox((0, 0), sent, font=font)
            tw = bbox[2] - bbox[0]
            x, y = (w - tw) // 2, h - 100
            # 黑色描边（8 方向偏移 3px）
            for dx in [-3, 0, 3]:
                for dy in [-3, 0, 3]:
                    if dx or dy:
                        draw.text((x+dx, y+dy), sent, font=font, fill=(0,0,0))
            draw.text((x, y), sent, font=font, fill=(255,255,255))

        out_name = f'sub_{img_idx:04d}.png'
        frame.save(f'{sub_dir}/{out_name}')
        concat_lines.append(f"file '{sub_dir}/{out_name}'")
        concat_lines.append(f"duration {sent_dur:.3f}")
        img_idx += 1

# ffmpeg concat 需要最后一帧重复
concat_lines.append(f"file '{sub_dir}/sub_{img_idx-1:04d}.png'")
with open('concat_sub.txt', 'w') as f:
    f.write('\n'.join(concat_lines))
```

### 第八步：合成视频（带字幕）

**⚠️ 时长分配必须用音频段字节比例，不要用字数比例！** 字数和实际语速不成正比，按字数分配会导致后半段音画不同步。

```bash
cd <输出目录>

# 1. 用字幕帧图片生成静音视频
ffmpeg -y -f concat -safe 0 -i concat_sub.txt \
  -vf "scale=1920:1080,format=yuv420p" \
  -c:v libx264 -preset medium -crf 20 -r 30 -an silent.mp4

# 2. 合并音频（-c:v copy 不重新编码，速度快）
ffmpeg -y -i silent.mp4 -i voiceover_volcano.mp3 \
  -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart \
  output_sub.mp4

rm -f silent.mp4 concat_sub.txt
```

**字幕样式**：
- 字体：Arial Unicode MS 42px（白色，黑色描边 3px）
- 位置：底部居中，距底边 100px
- 暗底亮底都清晰

**两个输出文件**：
- `output.mp4` — 无字幕版（build_video.py 生成）
- `output_sub.mp4` — 带字幕版（本步骤生成）

### 第九步：展示结果

1. 读取几张关键 PNG（第 1 页、中间页、最后页）让用户预览效果
2. 告知输出目录路径
3. 提示 `open preview.html` 可在浏览器翻页预览
4. 视频已含字幕，可直接发布

## 文件组织

```
<工作目录>/voiceover/
└── <slug>/
    ├── cover.html + cover.png        # 封面（视频缩略图/第一帧）
    ├── slide_01.html ~ slide_XX.html
    ├── slide_01.png ~ slide_XX.png
    ├── script_notes.md
    └── preview.html
```

## 常见问题

### 字体加载
CSS 通过 Google Fonts CDN 加载 Noto Sans SC + Space Grotesk。Chrome headless 截图需要网络连接。如果字体没加载成功，截图会用默认字体（效果差）。

### 内容超出画布
每页最多 6 行 × 18 字。如果内容塞不下，拆成两页，不要缩字号。

### 主题切换
整套幻灯片通常用同一个主题。如果想在某几页切换主题，改那几页 HTML 的 body class 即可。

---

# 演示模式（Presentation）

信息密度高，带卡片、装饰层、品牌标记的正式 PPT。5-8 页。

## 设计系统

每页 HTML 引用两个 CSS 文件：

```html
<link rel="stylesheet" href="file://<设计系统目录>/design-system.css">
<link rel="stylesheet" href="file://<设计系统目录>/design-system-slides.css">
```

## 文件组织

```
<工作目录>/slides/
└── YYYYMMDD-<slug>/
    ├── slide_01.html ~ slide_XX.html
    ├── slide_01.png ~ slide_XX.png
    ├── script_notes.md
    └── preview.html
```

## 6 种主题色

| 主题 | CSS 类 | 适用内容 |
|------|--------|---------|
| Obsidian (暗色) | `.theme-obsidian` | 技术深度、产品发布 |
| Paper (浅色) | `.theme-paper` | 清单、总结、轻松内容 |
| Signal (强调色) | `.theme-signal` | 重大新闻、里程碑 |
| Aurora (极光) | `.theme-aurora` | AI 前沿、大模型 |
| Mist (薄雾) | `.theme-mist` | 工具推荐、科普 |
| Glacier (冰川) | `.theme-glacier` | 产品评测、App 推荐 |

## 4 种幻灯片类型

| 类型 | 布局 | CSS 类 | 参考模板 |
|------|------|--------|---------|
| title | 居中大标题+副标题+标签 | `.slide-title` | `templates/slides/title.html` |
| content | 左标题+右侧要点卡片 | `.slide-content` | `templates/slides/content.html` |
| data | 顶部标题+数据卡片网格 | `.slide-data` | `templates/slides/data.html` |
| ending | 居中总结+CTA+品牌 | `.slide-ending` | `templates/slides/ending.html` |

模板文件路径前缀：`<设计系统目录>/`

## 结构规则

- 第 1 页必须是 title，最后一页必须是 ending
- 中间自由组合 content 和 data
- 每页必须有品牌标记 `lif.` 和装饰层

## 视觉四层结构（每页必须满足）

| 层级 | 作用 | 实现 |
|------|------|------|
| L1 背景底色 | 定调 | `.theme-*` class |
| L2 装饰层 | 视觉丰富度 | `.deco-noise` + 主题装饰 |
| L3 内容容器 | 承载信息 | `.card-*` 卡片组件 |
| L4 文字/图标 | 信息传达 | 主题文字色 + SVG 图标 |

各主题装饰层：

| 主题 | L2 装饰层 |
|------|----------|
| Obsidian | `deco-noise` + `deco-dots` + `deco-bracket-tl/br` |
| Paper | `deco-noise` + `deco-hlines` + `deco-top-stripe` |
| Signal | `deco-noise` + `deco-stripes` + `deco-gradient-bottom` |
| Aurora | `deco-grain` + `deco-aurora` |
| Mist | `deco-noise` + `deco-mist-glow` + `deco-soft-dots` |
| Glacier | `deco-noise` + `deco-shimmer` + `deco-refraction` |

## 演示模式工作流程

1. **了解需求** — 主题、素材、主题色偏好、页数
2. **主题调研**（无素材时）— WebSearch 搜索整理事实清单
3. **规划结构** — 确定每页类型和核心信息
4. **逐页生成 HTML + 截图** — 读参考模板 → 替换内容 → Write 保存 → Chrome 截图
5. **生成口播稿** — `script_notes.md`
6. **生成预览器** — `preview.html`（同口播模式的预览器模板）
7. **展示结果** — 读 PNG 预览 + 告知路径

截图命令同口播模式（`--window-size=1920,1200` + 裁切到 1920×1080），见口播模式的第五步。

## SVG 图标库（演示模式用）

```html
<svg xmlns="http://www.w3.org/2000/svg" style="display:none">
  <symbol id="icon-bolt" viewBox="0 0 24 24"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></symbol>
  <symbol id="icon-code" viewBox="0 0 24 24"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></symbol>
  <symbol id="icon-chart" viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></symbol>
  <symbol id="icon-rocket" viewBox="0 0 24 24"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="M12 15l-3-3 7.5-7.5A12.71 12.71 0 0 1 22 2c0 2.35-1.1 6.58-4.5 10L15 12"/></symbol>
  <symbol id="icon-shield" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></symbol>
  <symbol id="icon-terminal" viewBox="0 0 24 24"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></symbol>
  <symbol id="icon-brain" viewBox="0 0 24 24"><path d="M12 2a6 6 0 0 0-6 6c0 2.2 1.2 4.1 3 5.2V20h6v-6.8c1.8-1.1 3-3 3-5.2a6 6 0 0 0-6-6z"/><line x1="9" y1="14" x2="9" y2="20"/><line x1="15" y1="14" x2="15" y2="20"/></symbol>
  <symbol id="icon-users" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></symbol>
  <symbol id="icon-fire" viewBox="0 0 24 24"><path d="M12 23c-4.97 0-9-2.69-9-6 0-4 4-8 4-8s.5 2 2 3c.47-.8 1.5-3 1-6 3.5 2.5 6 6 6 10 1.5-1 2-3.5 2-5 2.5 2.5 3 4.5 3 6 0 3.31-4.03 6-9 6z"/></symbol>
  <symbol id="icon-star" viewBox="0 0 24 24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></symbol>
  <symbol id="icon-lightbulb" viewBox="0 0 24 24"><path d="M9 21h6m-6-3h6m-3-18a7 7 0 0 0-4 12.7V17h8v-4.3A7 7 0 0 0 12 0z"/></symbol>
  <symbol id="icon-search" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></symbol>
  <symbol id="icon-download" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></symbol>
  <symbol id="icon-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></symbol>
  <symbol id="icon-link" viewBox="0 0 24 24"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></symbol>
</svg>
```

使用：`<svg class="icon icon-sm"><use href="#icon-bolt"/></svg>`
