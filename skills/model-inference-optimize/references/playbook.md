# 专项优化方法

按实际瓶颈读取相关部分。这里提供实验方法，不要求把所有技术都试一遍；历史参数和收益不作为新模型默认值。

## 复现与后端迁移

恢复完整产品链：解码、resize/pad、归一化、权重与 adapter、scheduler、裁切、blend、颜色、时序状态及编码。裸网络准确性与整个产品 preset 效果分别验收。

1. 有参考实现时保存阶段输入/输出，从最早分歧处定位 VAE、conditioning、RoPE、attention、block、采样、decode 或 postprocess。
2. 对张量记录 shape/dtype/layout、max/mean absolute error、所需相似度及 NaN/Inf。阈值依据任务、精度和参考重复性事先确定，不把某次 cosine 当通用通过线。
3. 对 LoRA 合并核验 scale、目标层和权重来源；RNG 核对设备、dtype、框架版本和调用顺序。
4. 对 ONNX/TensorRT/OpenVINO 核对设备架构、engine/runtime、binding、动态 shape、插件和精度。在实际部署环境执行，不由文件名推断兼容性。
5. 从 provider 分配/trace 确认算子运行位置；import、provider 排第一、engine 存在均不能单独证明整图命中。
6. 递归视频检查状态传递与整片误差；微小首帧差异可能被 `hr_prev` 逐帧放大，需要全片和多场景回归。
7. 独立 runner 在干净环境检查依赖和权重解析，避免 App 私有模块/路径泄漏，遵守模型使用许可。

先区分 engine/依赖不兼容、路径未命中与模型语义错误，再调性能。对应脱敏案例：分阶段 oracle、恢复模型链路、时序模型产品链。

## 测量与瓶颈定位

先用已有 wall timing 找大阶段，再对热点使用框架 profiler、ORT trace 或 GPU profiler。带 profiler 的同步开销不进入最终成绩。

| 边界 | 包含内容 | 不得混淆 |
|---|---|---|
| 冷启动 | 下载/加载、engine build、compile、warmup 分列 | 不与热态直接算优化倍数 |
| kernel / GPU stage | 指定设备/stream 的完成时间 | 不是 CPU wall 或 HTTP |
| pipeline-return | 输出张量可用，明确同步 | 不自动含编码/文件写入 |
| 文件完成 | 编码、音频封装、真实写完 | 不自动含下载/上传/排队 |
| 服务请求 | 客户端发起至可用结果，说明网络与队列 | 不是持续吞吐或单 worker 实时 |

保存逐次值，计算中位数、范围和配对 A/B 差值；异质输入给逐样本结果，避免平均数掩盖回归。交错运行减少温度/时钟/负载漂移，共享 GPU 记录竞争情况。自托管 LLM 按需要拆 prefill/decode、TTFT、每 token 延迟及并发；固定任务和长度分布，防止短输出造成虚假提速。

## 显存与数据流

区分权重、activation、KV、workspace、allocator reserved、运行时 arena 和设备总占用。框架 peak allocated 与 `nvidia-smi` 总占用分别报告。

| 假设 | 最小实验 | 验收重点 |
|---|---|---|
| arena/workspace 预留过大 | 改单项策略，测典型与最大输入 | 是否每 session 生效、总并发 OOM、延迟变化 |
| tile/KV 留太多 | 改实际数量或释放无用状态 | 时域边界、上下文、接缝、重算代价 |
| crop/stitch 占 CPU | slicing/pad、批量布局、向量化或迁设备 | padding、tile 顺序、dtype、内存峰值 |
| 请求间反复搬权重 | 常驻热点组件，跨卡只传 conditioning | 总占用、并发容量、计费时长 |
| D2H 输出太大 | GPU 完成合法 clamp/round/像素转换后传输 | 范围、取整、颜色、编码格式；像素 uint8 不是模型 FP8 |
| I/O Binding 能消除搬运 | 先查 CPU island 再绑定 buffer/stream | fallback、stream 生命周期、隐式同步；绑定也可能更慢 |
| 并发更多就更快 | 有界测不同并发，按序拼接 | OOM、CPU 竞争、每路延迟、聚合吞吐 |

仅 profiler 表明存在重叠空间时再试 pinned memory、async copy、多 stream 或流水线，确认真正 overlap。不要仅改用 async API 就声称提速，不靠每请求 `empty_cache()` 掩盖生命周期问题。

## 算子与编译

1. 抽取热点真实 shape、stride/layout、dtype、mask 语义、典型与边界输入，先证明覆盖率和总占比。
2. 低精度先局部后整体，核验实际硬件/kernel、权重/activation/累积精度/scale，检查异常值及空权重路径。
3. RMSNorm/RoPE/SwiGLU、QKV、卷积融合都检验语义、布局和转换成本，合并不保证更快。
4. compile/CUDA Graph 记录首次成本、重编译/graph break、动态 shape 与常驻内存，完整收益覆盖现实 shape、warmup、换入换出。
5. 候选 kernel 串行占用同一设备做精确性/误差与交错重复。同卡竞争数字不作公平对比；只有用户要求时才多 agent 研究。
6. 局部胜者继续测模型、完整文件与请求。工具覆盖率低或 shape 错误时拒绝其全模型收益结论，保留失败证据。

严格 bool mask 可要求逐位一致，浮点算子按预先约定误差和模型回归验收。参考脱敏案例中的局部与整链收益差、CPU island、低精度算子替换。

## 近似推理

先明确允许的质量变化，再作为独立候选比较。

- 少 step/forward：匹配任务、蒸馏权重、adapter、scheduler 与训练步数。四步 adapter 跑两步只是消融，不证明具备两步模型能力。
- 稀疏 attention：确认 density、dense warmup、top-k/mask 参数生效；检查运动、细节、长序列和边界，历史参数不复制为默认。
- 跨步缓存：证明状态在复用条件下不变。双向 attention 的 conditioning KV 可能随 latent 更新，conditioning 输入固定不保证全步 KV 固定。
- FirstBlockCache 等阈值：控制输入、噪声与采样轨迹检查质量；不要事后放宽标准。
- 近似 decoder：同一 latent 分别用完整与近似 decoder 解码以隔离误差，再做完整生成检查。
- 模型/分辨率/时长变更：另列规格、质量、延迟和成本，不算原任务的等价提速。
- 自托管 LLM KV/prefix cache、speculative decoding：核验实际支持和实测 hit/acceptance，没有测量的历史讨论只作候选。

保留调参未见的最终验证样本，单 prompt/seed 不证明泛化。

## 质量评测

先核原生尺寸、帧数/FPS/时长、位深、色彩空间/范围、裁切、音轨和可解码性。对齐后再算指标；诊断性手动对齐需保存变换并注明，不得掩盖输出错位。

| 对象 | 对照与指标 | 结论边界 |
|---|---|---|
| 实现一致性 | 阶段张量、逐位/MAE/max error、递归误差 | 与参考一致不代表参考画质最好 |
| 有 HR 的 SR/恢复 | 配对 HR/LR、bicubic/Lanczos；PSNR/SSIM、LPIPS/DISTS 按需 | 明确 RGB/Y、crop、位深；fidelity/感知分报 |
| 无 HR 恢复 | source consistency、无参考指标、同步对比、人评 | BRISQUE/NIQE 不作唯一真值 |
| 视频 | 同步帧、运动/闪烁、接缝、场景切换、长片、音画同步 | 插帧与 SR 不作同一纯超分排名 |
| 生成 | prompt/参考集、身份/动作/构图/声音、盲看 | 单人/单 seed 为有限观察，不称 MOS |
| LLM | 同任务集、成功率、错误案例、上下文和输出长度 | token 速度不能替代任务质量 |

几何问题追 resize/pad/unpad；颜色问题做开关 A/B 并核输入输出色域。全局均值/方差匹配不保证肤色，丢帧路径要同步参考时间轴。提供同帧裁切、接触表或同步视频；可浏览评测复用已有页面工具，不默认做完整产品网站。

## 服务与成本

沿真实请求验证获取输入、加载、推理、编码、上传/响应和错误返回，核对运行版本、模型来源与 backend，必要时核分发哈希。代码、合并、部署、请求命中各自凭证据报告。保持项目错误契约，仅检查改动涉及的失败路径，不建立新错误码系统。

- GPU-hour = 各计费设备占用小时之和；同价设备同时占用才简化为 GPU 数 × 占用秒 / 3600。
- 成本 = 各设备 GPU-hour × 单价，加任务要求纳入的 CPU/存储/网络/重试等。价格注明来源/日期或假设。
- 每成功输出成本 = 批次总成本 / 成功输出数；按成功视频秒归一化时注明实际时长。
- 常驻实例按计费占用与实际吞吐分摊，不能用模型活跃秒冒充账单。冷启动/build 单列，按明确请求量摊销。
- 聚合吞吐用实际窗口完成量 / 窗口 wall time，不相加不同窗口的每路 fps；另报每路尾延迟、失败率、显存。

持续实时需连续请求和排队/资源证据。单条低分辨率热态预览快于播放，不证明高分辨率、冷启动、单卡或持续单 worker 实时。
