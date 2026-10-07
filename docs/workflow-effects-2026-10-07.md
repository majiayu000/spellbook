# 两组维护工作流的实际验收 · 2026-10-07

此次固定验收 `codebase-audit` 与 `typescript-project`，分别回答“能找到什么问题”和
“能完成什么任务”。Registry 保持发现与归档边界；Loom 仅验证现有安装和投影流程。
没有增加 skill 数量，也没有改变三个项目的定位。

完整源码、锁文件、报告、人工评分与实际命令日志在
[证据包](evidence/workflow-effects-2026-10-07.tar.gz)。解压后保留原文件；复跑使用新的目录。
模型结果由真实 Agent 执行产生；审计项目是故意预埋问题的合成夹具，TODO 是临时模型实现
案例，两者都不能代表生产缺陷、外部维护者采用或真人效果。

## 代码库审计

代码版本：Spellbook `414b597ec113b9c8d37c8de912ef80f92d9ad2f3`。两组独立审计者继承
同一父会话模型，不共享报告或预埋答案；都审阅完整 Python 项目，启用测试与并发维度。
技能组读取现有 skill 与 references，无技能组不读取 skill。两组都只读目标源码。
评分在报告完成后按现有 `expected-findings.json` 的文件与类别人工匹配。

| 观察 | 无技能组 | 技能组 |
|---|---:|---:|
| 必检项命中 | 8/10 | 10/10 |
| 必检项漏报 | #4 缓存版本维度、#8 缺失 retry_limit 配置 | 无 |
| Bonus 项 | #11、#12 | #11、#12 |
| 实际耗时（含环境准备、探针与报告） | 244 秒 | 432 秒 |
| token / 模型费用 | 未知 | 未知 |
| 源码改动 | 无 | 无 |

对应证据：`audit-baseline-report.md`、`audit-skill-report.md`、`audit-scoring.json`。
技能组补出了缓存键缺少生成/序列化版本、配置使用未声明的 `retry_limit` 两项。
无技能组已找到注册表缺项、静默失败、字段丢弃、未接入配置、弱测试和事件循环阻塞等。
#6 在无技能组只明确报告未知字段删除，未单独说明显式 null 删除；它属于命中项中的
不完整解释。两组均把硬编码凭据判为测试占位值，没有将它说成真实凭据泄漏。

额外发现逐条核对，未因它们不在目录中就判为误报。快照非原子写入、整数 ID 经 JSON
往返改变类型、未实现上传、共享 fallback 等有源码/探针证据。没有确认条件说明之下的
错误断言，但这不是独立盲评的“误报率为零”：技能组 M17 的多线程竞争探针失败，仍为
未证实风险；无技能组多进程 ID 冲突的部署影响也依赖尚未提供的多进程条件。

技能组 heartbeat 在约 2.034 秒才恢复，确认同步 sleep 阻塞共享 event loop；这是夹具
运行结果。不能把仅见“计数器未加锁”直接当成单线程协程已发生竞争。

依赖版本相同：Python 3.12.14、Pydantic 2.13.5、PyYAML 6.0.3、pytest 9.1.1。
环境准备方法与报告保存条件不同，耗时不能纯粹归因于 skill。两组各一次，不能据此
声称普遍提效。`pip-audit` 未安装，技能组明确跳过依赖审计；没有“依赖安全”的结论。
fixture 的测试自身只有 `1 passed, 1 skipped`，不作为审计质量或产品正确性的通过证据。

## TypeScript TODO API

真实 Agent 读取安装到隔离 Codex 目录的 `typescript-project`，完成内存 TODO HTTP API。
任务限定创建、列表、删除以及输入与错误处理，不需要数据库或 LLM 功能。

- 运行时间：14:09:43–14:12:21 UTC，158 秒；模型 token 与费用未知。
- 版本：Bun 1.3.14、TypeScript 7.0.2、Zod 4.6.5、`@types/bun` 1.4.2；锁文件已保存。
- `bun test`：5 项通过，79 个断言；`bun run typecheck` 退出 0。
- 独立真实 HTTP 服务仅提供 `PORT=0`，没有外部 API 凭据；创建/列表/删除分别为
  201/200/204，畸形 JSON 和无效输入为 400，未知 ID/路由为 404，错误方法为 405。
- 验证无效输入不改变已有状态，删除后列表为空；服务已停止。
- 仅创建临时任务项目中的七个文件；原项目与用户配置没有修改。

Bun、Zod、ESM 与严格类型检查是激活观察。API 的行为、状态和错误响应才是任务完成
证据。这个案例没有无技能组，因此不能给出收益差值。完整输入条件、源码、测试和
原始验收记录见证据包的 `typescript-case/EVIDENCE.md`。

```bash
cd typescript-case
bun install --frozen-lockfile
bun test
bun run typecheck
PORT=3000 bun run src/index.ts
# 另一终端请求 POST/GET /todos 和 DELETE /todos/:id；完成后停止服务。
```

已有模板也单独实例化并安装依赖。修复前服务测试 9 项通过，但 `tsc --noEmit` 报
`TS6133: getEnvBool is declared but its value is never read`。本次只删除这个未用 helper，
保留既有错误合同；修复后 9 项测试、类型检查和构建全部通过。
对应 `typescript-template-*` 日志及完整 `typescript-template/` 项目。使用 `latest` 的
模板只支持这些实际记录过的依赖版本，不能代替跨平台兼容性结果。

LiteLLM URL/SDK 偏好与真实模型调用分开。Claude CLI 连通性返回未登录，Codex 原生 CLI
返回真实 `WORKFLOW_EVAL_READY`；这些不能替代 proxy 的生成、取消或错误行为验收。
本案例没有测试 LiteLLM/provider；真实 provider 集成、Windows/Linux 与外部用户效果
仍需对应环境与实际运行，不用模拟输出补齐。
对模板默认 `127.0.0.1:4000/health/readiness` 的独立连通性检查返回连接拒绝
（HTTP 000）；日志为 `litellm-default-health.*`。这只证明默认本机 endpoint 未运行，
不推断其他 proxy 或模型服务不可用。真实集成需要明确可用 proxy、模型与授权凭据。

## Registry 与 Loom 的现有边界

Registry 的正确主仓 remote 为 `majiayu000/claude-skill-registry`；本机
`AI/code-agent/claude-skill-registry` 是旧 checkout 且有大量既有改动，保持原样。
本次使用实际公开发布 provenance，而不是在主仓手工修生成文件：

- Core SHA：`e07268e1e647192b96ceb51d53c113a1b25c2c3b`。
- Data SHA：`8dc0adab6588e963b72e8ce43538e6f6bf8d121e`。
- `publish-status.json` 的状态为 `passed`，run ID 为 `37575723185`；这是发布方记录，
  不冒充本次重新发布。Registry summary 记录 268939 项，不表示它们都验证过任务效果。
- 当前 Core 的发布边界与 pipeline 定向测试：139 项通过。

原文要求 Loom 沿停止新增功能方向维护，本次没有新增功能。当前检出的远端提交为
`4444a488178b370621ac43eaf21e45cc125f73af`；仓库仍有 Roadmap，不能据此说远端已正式
进入 maintenance-only 状态。本次验证现有 `v0.2.0` 安装与 CLI 工作流：

- 官方安装脚本实际下载并校验 Apple Silicon 发布包，安装至隔离 bin/data 目录。
- `loom --version` 为 `0.2.0`；官方 e2e 脚本六个场景 A–F 全部通过。
- 当前源代码 `make fmt-check` 通过；CLI-only 定向测试 38 项通过、1 项忽略。
- 测试中的 mock/Codex trace 夹具只算合同回归，不称为真实模型效果。
- 未修改 Loom；没有验证 Panel、桌面 UI、其他平台或完整 CI。

已有维护修复也已核对并复用其验收证据，没有重复实现：
[恢复保留文件与恢复副本 #719](https://github.com/majiayu000/loom/pull/719) 的 head
`a355fab33ebcc17b451dbe9aa578f103e3727404`、
[同一路径重复编辑的 debounce #728](https://github.com/majiayu000/loom/pull/728) 的 head
`5d67a9530a1059b34795d2b6dabd1a2591883c6e`，对应 CI 与 Team App runs 均已通过。
这是 GitHub 连接器对指定 head 的实际查询结果；两个 PR 仍为 draft、尚未合并，不能
算进本次 main 或已发布版本。记录见证据包 `loom-existing-pr-checks.json`。

## 交付与后续维护

按任务安装既有两个 skill 到隔离 Claude/Codex 目录成功，安装路径指向正确源文件。
Spellbook 修改前完整测试为 532 项通过、136 个 subtest 通过。修改后运行 registry
检查、两项 skill 质量审查、模板测试/类型检查/构建及 eval JSON 解析；详细结果以日志为准。
既有 `threads` 长度提示和 TypeScript Operating Contract 的信息提示仍保留。

实际更新限于模板 helper、测试指南、两个技能的 eval/已知注意事项及本证据记录。
今后这两组工作流按上述任务与条件复跑，保留发现、漏报、未证实风险和实际费用；不把
继续增加技能数量作为完成度。Git CLI 推送缺少 HTTPS 凭据，`gh` 返回 401/403；
已连接的 GitHub API 有写权限，可用于交付审查分支与 draft PR。新的 PR/CI 状态以
对应 GitHub 记录为准，不能从本地通过推断远端通过或已发布。

| 本次范围 | 状态 | 验收与缺项 |
|---|---|---|
| 既有任务安装、eval、Registry 来源/归档/发布边界 | 已完成 | 隔离安装、provenance、Core 139 项定向检查；未改镜像 |
| 少量主推工作流效果 | 已完成 | 完整审计对照、真实 TODO HTTP 案例；仅覆盖这些任务 |
| 激活与效果分开、维护案例 | 已完成 | 测试指南、模板最小修复、已知注意事项与证据包 |
| Loom 沿现有方向维护 | 已完成 | 发布包实际安装、六项 CLI e2e、38 项源代码检查；未新增功能 |
| 真实 LiteLLM/provider、其他 runtime、外部用户 | 受阻/待验证 | 默认 endpoint 拒绝连接、Claude 未登录；尚无对应环境或真人结果 |
| 新 PR、远端 CI 与发布 | 已实现待验证 | 通过已连接 API 准备审查交付；远端 CI、合并与发布分别核对 |

审计仅执行这次 full 模式对照；quick 模式和持久化 ledger 的重复审计未执行。
它们仍是现有 eval 的后续用例，不列为本次已通过结果。
