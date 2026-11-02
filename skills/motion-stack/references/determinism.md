# 让每个库都只看 t

原则：`setup()` 里把所有需要模拟的东西预先算好，`frame(t)` 只查表、插值、画。不要在场景里开 `requestAnimationFrame` 循环或 `setInterval`。

渲染器已经冻结了 `performance.now()`、`Date.now()`（等于当前帧时间），并给 `Math.random` 设了种子（`motion.seed`）。这能挡住大部分“偷偷读时钟”的库，但不能代替下面的做法。

| 库 | 做法 | 已验证 |
|---|---|---|
| Three.js | `new WebGLRenderer({ preserveDrawingBuffer: true })`，`setPixelRatio(1)`；`frame(t)` 末尾手动 `renderer.render()`。动画混合器用 `mixer.setTime(t)`，不要 `update(dt)` | ✅ |
| Matter.js | `setup()` 里用固定步长（如 1/240 s）跑完整段，记录每步位置和角度；`frame(t)` 取 `t/STEP` 两侧插值。碰撞事件同时记下来给声音用 | ✅ |
| Tone.js | 只用 `Tone.Offline(cb, duration, channels, sampleRate)`，事件时间写绝对秒数。用到噪声（`NoiseSynth`/`Noise`）时，`audio()` 开头先 `window.__seed?.(n)` 重设种子。实测：带 Freeverb + AMSynth 的混音两次渲染约万分之一的采样差 1 个最低位（≈ −90 dB，听不出），比对音频要留 1 LSB 容差 | ✅ drop、gravity |
| Rapier | 同 Matter：固定步长预算（`world.timestep = 1/120`）。用 `-compat` 包（wasm 内联），import map 指向 `dist/rapier.mjs`，`await RAPIER.init()` 放在 `setup()`。中途改重力直接赋 `world.gravity`，记得 `wakeUp()`。碰撞声用 `ActiveEvents.COLLISION_EVENTS` + `EventQueue`，速度取上一步的 `linvel` | ✅ gravity |
| anime.js | `autoplay: false`，`frame(t)` 里 `timeline.seek(t * 1000)` | 未验 |
| PixiJS | `new Application()` 后 `app.ticker.stop()`，`frame(t)` 设属性后 `app.renderer.render(app.stage)`；`preserveDrawingBuffer: true` | 未验 |
| p5.js | 实例模式，`setup` 里 `noLoop()`、`randomSeed()`、`noiseSeed()`；`frame(t)` 里先重设种子再 `redraw()`，绘制函数读 t 而不是 `frameCount` | 未验 |
| Paper.js | `paper.view.autoUpdate = false`，`frame(t)` 设路径后 `paper.view.update()`；不要用 `onFrame` | 未验 |
| tsParticles | 依赖内部状态，不能跳帧。要么从 0 逐帧推进到 t（慢），要么改为自己写粒子：每个粒子的位置写成 t 的函数 | 未验 |
| OGL | `new Renderer({ dpr: 1, preserveDrawingBuffer: true })`，import map 指向 `ogl/src/index.js`；全屏 `Triangle` + `Program`，uniform 只放 t 的函数（需要“累计位移”时在 JS 里写成 t 的闭式，不要 `swirl * t`） | ✅ gravity |
| GL Transitions | uniform 里传 `progress = clamp((t - start) / dur)`，不在着色器里累加 | 未验 |
| React Spring | 不要用它的帧循环。需要弹簧感时，用阻尼弹簧解析解 `x(t) = 1 - e^(-ζωt)(cos ωd t + …)` | 未验 |
| 视频素材 | `<video>` 按帧 seek 不稳定。先用 ffmpeg 拆成 PNG 序列，`frame(t)` 读第 `round(t*fps)` 张 | 未验 |
| Canvas 2D | **必须** `getContext('2d', { willReadFrequently: true })`（走 CPU 光栅）。GPU 加速的 2D 画布带 shadowBlur / 文字时，同一帧画面会随绘制顺序变化，`--pure` 会报错（gravity 实测） | ✅ gravity |
| 字体 | 用 `@fontsource/<名字>` 装进 node_modules，`@font-face` 指向其中的 woff2；`setup()` 里 `await document.fonts.load('700 230px "X"')`。不用 Google Fonts CDN，否则清单的 `remote_requests` 会报出来 | ✅ gravity |

验完一个库，就把“未验”改成 ✅，并写下哪部片子用过。
