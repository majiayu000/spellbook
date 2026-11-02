---
name: hud-interface
description: "游戏 HUD 式界面：黑白纸墨加一个薄荷强调色，斜切黑标签、空心巨型数字、粗黑汉字标题、环形转动文字、歪着摆的纸卡片、黑色底栏大斜体计数和条形表，背后是流动的液体大理石着色器；可选用 HTML-in-Canvas 把真实 DOM 面板画进 WebGL 再做玻璃折射和色散（Chrome 实验开关，不支持时自动退回普通 DOM）。带噪音档位 quiet / normal / loud，默认 quiet。适合拆解台、零件清单、机器人或任务控制台这类要有「仪表感」的页面。当用户说「游戏 HUD 风格」「做成仪表板那种酷炫界面」「HTML-in-Canvas」「把 DOM 画进 WebGL」「液体大理石背景」「斜切标签 / 巨型数字 / 环形文字」时使用。只在明确请求时触发，忽略顺带提及。"
---

# HUD 式界面

把一个页面做成游戏 HUD 的样子。分三层，前两层任何浏览器都能用，第三层是可选增强：

| 层 | 内容 | 依赖 |
|---|---|---|
| 版式 | 斜切标签、巨型数字、导航反白块、环形文字、歪卡片、清单表、黑底栏、刻度尺、条形码、等宽小字 | `hud.css`，纯 CSS 和 SVG |
| 背景 | 液体大理石：域扭曲 fbm，纸底、墨线、边缘积一点强调色 | WebGL2；没有时用 CSS 渐变 |
| 玻璃 | 把一个 DOM 面板画进 WebGL 贴图，边缘折射、色散，指针下有放大镜 | HTML-in-Canvas（Chrome 实验开关）；没有时面板保持普通 DOM |

## 文件

- `assets/hud.css`：颜色变量（`--hud-paper` `--hud-ink` `--hud-tint` `--hud-signal`）、字体变量和全部组件类。
- `assets/hud.js`：`window.Hud`，包括 `backdrop(canvas)`、`glass(panel)`、`glassSupported()`、`ring(el, text, {size, font})`、`barcode(el, seed)`、`level()`。没有依赖。
- `assets/demo.html`：一个机械键盘拆解台。左边是分区导航，中间是步骤卡片，右边是日期和零件清单（玻璃面板），底部是计数。右上角切换噪音档位。
- `scripts/check.mjs`：无头验收，跑默认 Chrome 和打开实验开关两种情况（截图存进 `--out`）。

## 步骤

1. **定内容，再套壳**。先列清楚页面真正要显示什么：分区、清单、计数、正在进行的那一项。HUD 只是外壳，内容必须是真实的结构，不要为了填满版面去造装饰数据。
2. **复制 `hud.css` 和 `hud.js`**，引入字体（Barlow Condensed、JetBrains Mono、Noto Sans SC，Google Fonts；离线会退到系统字体）。从 `demo.html` 搬需要的块。
3. **选一个面板做玻璃**，最多一两个，一般选主清单：`Hud.glass(panel)`。整页都做成玻璃会糊，也会很慢。
4. **背景**：放一个 `<canvas class="hud-backdrop">`，调用 `Hud.backdrop(canvas)`。颜色从 CSS 变量读，改 `--hud-tint` 就能换强调色。
5. **噪音档位**：在 `<html data-hud-level>` 上设置，默认 `quiet`。`loud` 会让色散、扫光、背景墨线都变强，带 `.hud-loud-only` 的装饰也只在非 quiet 档出现。
6. **验收**：`node scripts/check.mjs page.html --out dir [--glass-panel "#panel"] [--click "选择器"]`，全部 ✓ 才算完成，然后自己看截图。

## 硬规则

- **只学手法**：不照搬参考作品的布局、文案、角色和标题字。
- **噪音预算**：同屏只有一个强调色。`--hud-signal`（红）只给 LIVE、错误、待确认这类需要警示的东西。旋转和闪烁加起来最多一处，默认是环形文字。原作者自己都说"太吵"，所以默认 quiet。
- **逻辑在 DOM**：玻璃面板里的按钮、焦点、选中状态都是真实元素，着色器只负责画面。不支持 HTML-in-Canvas 时，页面必须照常可用，验收第 1 组专门测这一点。
- **字要能读**：玻璃的折射只出现在边缘约 5% 的宽度里，色散在 quiet 档几乎看不出。正文不要放在面板最边上。
- **触控和键盘**：导航和清单行最小高度 44px，`:focus-visible` 有描边，当前项用 `aria-current` 或 `aria-pressed` 标出。
- **减少动态效果**：`prefers-reduced-motion` 下，背景只画一帧，环形文字停转，过渡全部关掉。
- **手机宽度**：390px 下不能横向溢出；环形文字、竖排字和侧栏的次要信息要隐藏。

## HTML-in-Canvas 实测要点（Chrome 156，2026-10-27）

接口还在变，官方说明和实际实现不一致。以下以本机实测为准：

- **开启**：`chrome://flags/#canvas-draw-element`，命令行是 `--enable-blink-features=CanvasDrawElement`。默认不开，普通用户看到的是退回后的 DOM 版本。
- **两种属性拼写都写上**：`<canvas content="drawable" layoutsubtree>`，子元素加 `drawable`。
- **WebGL 只接受不可变存储**：先 `texStorage2D(TEXTURE_2D, 1, RGBA8, w, h)`，再 `texElementSubImage2D(TEXTURE_2D, 0, 0, 0, el, {width, height})`。直接用 `texElementImage2D` 会报 internalformat 错误；按说明里的参数顺序传，会报 "not of type Element"。尺寸变化时要重新分配贴图。
- **在 `paint` 事件里上传贴图**。尺寸变化后调用 `canvas.requestPaint()`。
- **点击要对准**：3D 上下文不会自动定位元素，每次 paint 后调用 `canvas.updateElementGeometry(el, {canvasTransform: new DOMMatrix().scale(dpr)})`，dpr 为 1 和 2 都已验过。
- **画布高度不会跟着子元素变**：要观察面板尺寸，把高度同步给 canvas（`hud.js` 已处理）。
- 跨源图片、系统颜色、拼写标记、visited 链接、次像素抗锯齿都不会被画进去。

## 拆解用法

拆东西时，零件清单放进玻璃面板，步骤做成卡片，底栏显示已拆、已装袋、待确认的进度。`demo.html` 就是这个结构，直接换成你的零件和步骤即可。

## 验收记录

2026-10-27，`demo.html`，Playwright Chromium 156 软件渲染：18/18 通过。

- 默认浏览器：背景是 WebGL2，玻璃退回 DOM，点击清单行生效。
- 打开实验开关：dpr 为 1 和 2 时玻璃都生效，画布高度等于面板高度，面板像素确实画出来了（深色占约 15%），按行的位置点击能选中那一行。
- 390px 宽：没有横向溢出。
- 减少动态效果：前后两张截图一致（时钟遮掉）。
- Playwright WebKit 26.0（Safari 内核）：背景是 WebGL2，玻璃退回 DOM，点击生效，没有报错。

没验的：
- 真实 GPU 上的帧率：软件渲染下背景约 13fps，没有参考价值。
- 真机 Safari 和 Firefox 没打开过。
- WebGPU 路径没做，用的是 WebGL2。
