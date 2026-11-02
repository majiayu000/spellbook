# 20 个库怎么选

来源：eigen（@e1genqq）2026-10-26 的推文清单。版本和许可证在 2026-10-26 用 `npm view` / PyPI 查过；“实测”一列只记在本流程里真跑过的。

## 画面

| 库 | 包名 @ 版本 | 许可证 | 什么时候选 | 实测 |
|---|---|---|---|---|
| Three.js | `three@0.186.1` | MIT | 3D 场景、产品转台、灯光阴影。默认的 3D 选择 | ✅ examples/drop |
| OGL | `ogl@1.0.11` | Unlicense | 只要一个全屏着色器或很轻的 WebGL，不想引入 Three.js | ✅ gravity |
| PixiJS | `pixi.js@8.22.0` | MIT | 大量 2D 精灵、文字、滤镜，需要 GPU | — |
| p5.js | `p5@2.3.4` | LGPL-2.1 | 生成艺术、噪声场、草图式视觉 | — |
| Paper.js | `paper@0.16.0` | MIT | 矢量路径：描边生长、布尔运算、路径变形 | — |
| tsParticles | `tsparticles@4.5.0` | MIT | 现成的粒子预设（彩带、星空）。要精确控制时自己写粒子更可靠 | — |
| 纯 Canvas / SVG / CSS | 无 | — | 文字排版、UI 演示、简单图形。很多片子其实只需要这个 | — |

## 动画曲线

| 库 | 包名 @ 版本 | 许可证 | 什么时候选 |
|---|---|---|---|
| anime.js | `animejs@4.5.0` | MIT | 多元素时间轴编排；用 `autoplay: false` + `seek(ms)` 接到 `frame(t)` |
| React Spring | `@react-spring/web@10.1.2` | MIT | 只在 React/Remotion 项目里用；弹簧是按帧迭代的，单独用时改写成弹簧解析解更稳 |

## 物理

| 库 | 包名 @ 版本 | 许可证 | 什么时候选 | 实测 |
|---|---|---|---|---|
| Matter.js | `matter-js@0.20.0` | MIT | 2D 刚体：掉落、堆叠、弹跳。最后发布是 2024-06 | ✅ examples/drop |
| Rapier | `@dimforge/rapier3d-compat@0.21.0`（2D 用 `rapier2d-compat`） | Apache-2.0 | 3D 碰撞，或要求跨平台确定性；2D 用 `@dimforge/rapier2d-compat@0.21.0` | ✅ gravity（2D） |

## 转场与素材

| 库 | 包名 @ 版本 | 许可证 | 用法 |
|---|---|---|---|
| GL Transitions | `gl-transitions@2.0.0` | MIT | 一组 GLSL 转场，`progress` 由 t 算出，用 OGL/Three.js 的全屏四边形跑 |
| glTF Transform | `@gltf-transform/cli@4.5.1` | MIT | 渲染前压缩 3D 模型：`npx gltf-transform optimize in.glb out.glb` |

## 声音与字幕（在场景外或离线生成）

| 工具 | 包名 @ 版本 | 许可证 | 用法 | 实测 |
|---|---|---|---|---|
| Tone.js | `tone@15.1.22` | MIT | 合成器和音效；在 `audio()` 里用 `Tone.Offline` 离线渲染，事件时间和画面共用一张表 | ✅ drop、gravity |
| Chatterbox | PyPI `chatterbox-tts@0.1.7` | MIT | 开源配音；先生成 WAV，用 `--audio` 或在场景里读入 | — |
| faster-whisper | PyPI `faster-whisper`（版本未查到） | MIT | 给配音做逐词时间戳，生成字幕 JSON 给场景读 | — |

## 整套渲染器（和本 kit 二选一）

| 工具 | 包名 @ 版本 | 许可证 | 什么时候选 |
|---|---|---|---|
| Remotion | `remotion@4.0.538` | 自有许可：个人和 ≤3 人公司免费，更大的公司要买 | 团队已经写 React，要多镜头剪辑、参数化批量出片 |
| HyperFrames | `hyperframes@0.8.202` | Apache-2.0 | HeyGen 出品的 HTML 转视频，适合 agent 直接写 HTML 片段 |

## 交付与剪辑（应用，不进场景）

| 工具 | 用途 |
|---|---|
| FFmpeg | 本 kit 已用它编码；另可转码、拼接、加音轨、出 GIF |
| OBS Studio | 录真实软件操作画面，当素材读进场景 |
| OpenCut | 开源时间轴剪辑，多个镜头拼成片时用；也可以直接用剪映 |
