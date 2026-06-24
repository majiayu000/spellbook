# Prompt Patterns

Use these templates as raw material. Fill concrete repo paths, PR numbers, issue numbers, file ownership, and verification commands before dispatch.

## Root Orchestrator

```text
你看下这个库有哪些 issue 和 PR 应该怎么处理。
使用 Codex-native threads 分别作 plan、impl+PR提交、review+修改、merge reviewer。
先做完整规划，判断哪些可以并行，能并行的使用独立 worktree。
目标是做完整闭环：不合理的 issue/PR 可以建议关闭；合理的要实现、review、修复、验证；只有用户明确授权且 merge gate 通过时才 merge，默认停在 recommendation。

硬约束：
- 先查 repo 指令、git 状态、open issues、open PRs、CI、dirty worktree。
- 只有用户明确要求 Codex-native threads / 子 agent 编排，或 GitHub issue/PR queue 确实需要独立 lanes 时才使用本流程；不要用于 OS/language/chat/email/forum/API threads。
- 先写 capability_gate：native_subagents / tools_seen / explicit_thread_request / spawn_requirement / fallback_mode / no_spawn_reason / manual_orchestration_allowed；不能在 native subagents 不可用时声称开了 threads。
- 用户明确要求 threads/subagents 且 native_subagents=available 时，必须先 spawn 至少一个 native subagent，或在任何实现/评论/merge 前记录 `fallback_mode: single_agent` 和结构化 `no_spawn_reason`。
- `native_subagents: available` + `fallback_mode: none` 只有在 `native_thread_evidence.spawned_agents` 里有真实 agent/thread ID 时才成立；main coordinator 不能算 spawned thread。
- GitHub issue/PR queue 必须先输出 queue_gate 和 issue_to_pr_map，再输出 lane_map；不能只凭 MERGEABLE/CLEAN 或 open 列表开 worker。
- 先写 intent_contract：goal / non_goals / done_when / merge_policy / remote_truth_required / truth_level / queue_ledger / ci_truth_source / data_collection / queue_bounds / remote_refresh。
- merge_policy 默认 no_merge；只有用户在当前对话明确授权 merge，才允许 merge_after_gate。
- GitHub queue、多 lane、或会 push/comment/merge 的运行默认 `data_collection: local_jsonl`；只有很小的只读单 agent 任务或用户明确 opt out 才用 final_report-only，并记录 no_log_reason。
- 记录 active_skill_source：实际加载的 skill 路径和可发现的 source SHA；发现不了就写 unknown，不要猜。
- queue_gate 必须包含每个 open PR 的分类：merge_ready / review_thread_blocked / ci_failed / conflict_blocked / stale_or_superseded / needs_human_decision。
- queue_gate 必须包含 truth_level：A=GitHub API/GraphQL/head/check/reviewThreads 全新鲜；B=GraphQL 不可用但 REST 可用，禁止 merge；C=仅 local git，禁止 remote closure/merge；D=remote 不可靠，仅 plan/prompt pack。
- queue_gate 必须包含 remote_refresh：origin/main 当前 SHA、lane base SHA、是否 stale_base、处理策略。
- 输出 queue_ledger，并在每个 queue item 上记录 owner_lane、head_sha、ci_status、review_thread_state、acceptance_evidence、remote_checked_at。
- lane_map 每个 spawned lane 必须记录 `native_thread_id`；coordinator-only lane 必须写 `native_thread_id: none` 和需要时的 `no_spawn_reason`。
- issue_to_pr_map 必须先判断 open issue 是否已有覆盖 PR；优先收敛已有 PR，不要开竞争 PR。
- 如果覆盖 PR 来自 contributor 且 `maintainerCanModify=true`，优先更新该 PR；只有分支不可写、不安全或用户批准时才开 maintainer replacement PR。
- broad queue 默认只做一个 bounded tranche；没有明确预算时不要承诺处理所有 issue/PR。
- 默认 WIP limit：planning/research 最多 3 lanes；implementation 最多 2 个并发 writable lanes；每个 PR 最多 2 个 reviewers，除非用户明确给更大预算。
- 长队列执行期间只允许定期 `git fetch --prune origin` + stale-base 判断，不要自动 merge/rebase worker worktree。
- 不要把 Codex threads 路由到 OMX/tmux。
- 每个实现 lane 必须有 disjoint writable_files。
- shared-state verification（如 .git/hooks、HOME、global cache、daemon）必须由 verification_owner 串行执行，除非显式隔离。
- lane_map 必须写 `verification_scope`：`inspection_only` / `targeted` / `full_local` / `ci_only`。
- reviewer lane 默认只读 diff/code inspection，可跑 `git diff --check` 或便宜静态检查；只在需要 review confidence 时跑 touched behavior 的 targeted tests。
- reviewer lane 默认不跑 full project test suite；full suite 只能由一个明确 owner 跑，通常是 root orchestrator、verification_owner、merge_reviewer，或由当前 head SHA 的 fresh CI 提供。
- Cargo 测试过滤要合法：每个 `cargo test` 命令只传一个 filter，或使用 module/path 级 filter；不要把多个无关 test name 当多个 positional filters 传给同一条命令。
- review lane 只读。
- 完成的 subagent 要及时 close；长 issue/PR 队列完成一个 bounded tranche 后，记录 ledger/resume query，并考虑开新 parent thread 降低上下文负担。
- 高上下文文件 AGENTS.md/CLAUDE.md/settings/hooks 默认禁止修改。
- 每个 PR merge 前必须有独立 thread review。
- 当 native_subagents=available 时，merge 前的独立 review 必须来自 spawned native thread，并在 `native_thread_evidence` 记录 agent/thread ID、wait evidence、close evidence。
- merge 前必须 truth_level=A，并用 thread-aware GitHub 数据检查 reviewThreads.isResolved；open PR/issue 为空不等于评论闭环完成。
- 如果请求或预期有 GitHub/Codex review connector，merge 前必须有当前 head 的 connector 完成证据；只有确认当前 head 没有请求或预期 connector 时才允许记录 `no_connector_expected`。
- CI wait 必须有预算；无本地可行动失败时用 WAITING_CI 停止并给 resume 查询。
- review-thread fix/recheck 同类循环超过 2 次，用 REVIEW_LOOP 停止并报告 blocker。
- 输出 capability_gate、thread_dispatch_gate、native_thread_evidence、queue_gate、queue_ledger、issue_to_pr_map、lane_map、依赖图、执行顺序、验证命令、stop_conditions、threads_run_log。
```

## Queue Gate Thread

```text
只读 Queue Gate thread。
Repo: {{repo_path}}
GitHub repo: {{owner_repo}}
Target queue: {{queue_scope}}

不要修改文件，不要发 GitHub 评论，不要关闭 issue/PR。
请读取 repo 指令，并用当前 session 的 live remote state 完成队列门。

必须检查：
1. git fetch --prune 后的当前 branch、dirty files、unpushed commits、worktrees。
2. 可用 remote truth level：A/B/C/D，并说明缺失的工具或权限。
3. origin/main 当前 SHA、每个候选 lane 的 base_ref 是否 stale、是否需要 rebase/recreate/stop。
4. open PRs 和 open issues。
5. 每个 open PR 的 head SHA、merge state、check rollup。
6. GraphQL reviewThreads.isResolved / isOutdated；普通 PR comments 不足以证明闭环。
7. open issues 是否已有覆盖 PR、重复 PR、或 superseding work。
8. 覆盖 PR 是否来自 contributor，以及 `maintainerCanModify` 是否允许直接修该 PR。

输出：
1. open_prs_count / open_issues_count
2. PR classification table：
   - merge_ready
   - review_thread_blocked
   - ci_failed
   - conflict_blocked
   - stale_or_superseded
   - needs_human_decision
3. issue_to_pr_map：covered issue -> PR；uncovered issue -> still actionable/backlog reason
4. truth_level 和禁止动作：B/C/D 时必须明确 merge/closure claim 被禁止
5. queue_ledger：每个 issue/PR/review_thread 的 owner_lane、head_sha、ci_status、review_thread_state、acceptance_evidence、remote_checked_at
6. 推荐执行顺序，优先关闭已有 PR blocker；没有明确预算时只推荐第一个 bounded tranche
7. top 1-3 items 的第一批 lane prompts
8. stop_conditions

规则：
- MERGEABLE/CLEAN 不足以判定 merge_ready；必须同时有当前 head SHA、check rollup、merge state、GraphQL review-thread state。
- review-gated queue 默认一次收敛一个 blocker，除非 writable_files 明确不重叠且 PR 不 stacked。
- remote_refresh 只能 fetch 和比较；不要在 queue gate 自动 rebase/merge。
- GraphQL 不可用时最多 truth_level=B，允许 review/实现，不允许 merge。
- contributor PR 可维护修改时，不要默认开替代 PR。
```

## Read-Only Planning Thread

```text
只读 planning thread。
Repo: {{repo_path}}
GitHub repo: {{owner_repo}}
Target: {{issue_or_pr_or_queue}}

不要修改文件，不要发 GitHub 评论，不要关闭 issue/PR。
请读取 repo 指令、当前 origin/main、目标 issue/PR、相关代码和测试。

输出：
1. 目标摘要
2. capability_gate（native_subagents / tools_seen / explicit_thread_request / spawn_requirement / fallback_mode / no_spawn_reason）
3. native_thread_evidence：spawned_agents 的 lane_id、spawn_tool、agent_id_or_thread_id、wait_evidence、close_evidence、result_collected；若未 spawn，必须说明 no_spawn_reason / fallback_reason
4. intent_contract（含 merge_policy 默认 no_merge、truth_level、data_collection）
5. queue_gate、queue_ledger 和 issue_to_pr_map（GitHub queue 必填；非 queue 说明 N/A）
6. queue_bounds：max_items / time_budget / queue_tranche
7. remote_refresh：origin/main SHA、stale_base 判断、处理建议
8. 已完成映射和证据
9. 未完成/风险
10. 推荐处理动作和理由
11. 可并行 worktree 拆分
12. 每个 lane 的 writable_files、forbidden_files、exclusive_verification、verification_scope、native_thread_id
13. 必须运行的验证命令
14. 不应在本轮强做的范围
15. 建议的 failure_codes（如 stale_remote_state、duplicate_work_missed、missing_intent_contract、native_thread_not_spawned）
```

## Implementation Worker

```text
你负责实现 GitHub issue #{{issue_number}} 的最小可合并 slice。
工作目录必须使用现有 worktree：{{worktree_path}}
分支：{{branch_name}}
基线：{{base_ref}}

你不是唯一一个在代码库工作的人：
- 不要修改主 worktree。
- 不要 revert 他人改动。
- 不要 force push。
- 不要修改 AGENTS.md、CLAUDE.md、settings、hooks，除非先汇报 blocker。

你的写入所有权仅限：
{{writable_files}}

禁止触碰：
{{forbidden_files}}

任务：
{{concrete_scope}}

验证：
{{verification_commands}}
verification_scope:
{{verification_scope}}

Remote refresh:
- 在 push 前运行 git fetch --prune origin 并比较 origin/main 与 lane base_ref。
- 如果 origin/main 已前进，不要自动 rebase；汇报 stale_base、重叠文件和建议动作。
- shared-state verification 只有在你被指定为 verification_owner 时才运行。

完成后汇报：
- root cause or core claim
- changed files
- unauthorized_or_unassigned_changes: yes/no
- commits/PR if created
- verification commands and key output
- remaining risks

不要 merge。
```

## Read-Only Code Review

```text
请对 {{target_pr_or_worktree}} 做只读 code review，不要修改文件，不要提交，不要 merge。
目标：{{issue_or_pr_goal}}

验证范围：
- 默认 `verification_scope=inspection_only`：做 diff/code inspection。
- 可运行便宜静态检查，如 `git diff --check`，或与 touched behavior 直接相关的 targeted tests。
- 不要运行 full project test suite，除非 lane_map 明确指定你是 `verification_owner` 或 `merge_reviewer`。
- 如果需要 Cargo targeted tests，每条 `cargo test` 命令只传一个 test filter，或使用 module/path 级 filter；不要把多个无关 test name 放进同一条命令。
- 报告未运行的 full-suite 验证，并说明由谁负责：root orchestrator、verification_owner、merge_reviewer，或 fresh CI。

重点检查：
- security and injection risks
- logic regressions
- silent failure or silent degradation
- owner/project/scope mixups
- test integrity and missing critical coverage
- performance regressions
- high-context file mutations

输出 findings first，按严重程度排序，带文件/行号。
如果没有 blocking issue，明确写：No findings; safe to proceed.
说明残余风险和未运行的验证。
```

## Fix Worker After Review

```text
你是 PR #{{pr_number}} 修复线程。
工作目录：{{worktree_path}}
分支：{{branch_name}}

只修复以下 reviewer findings：
{{findings}}

不要扩大范围，不要修改未授权文件，不要 revert 他人改动。
修复后运行：
{{verification_commands}}

输出：
- evidence source: files/commands/PR threads inspected
- root cause
- changed files
- verification output
- whether reviewer should re-check
```

## Merge Reviewer

```text
请作为独立 merge reviewer 审查 PR #{{pr_number}} 的最新 head {{head_sha}}。
只审查，不要修改文件，不要提交，不要 merge。

检查：
1. PR 是否仍 open、非 draft、head 是否匹配 {{head_sha}}
2. 用户当前对话是否明确授权 merge；未授权时只给 recommendation
3. truth_level 是否为 A；低于 A 时禁止 merge
4. CI/checks 是否对当前 head 通过；MERGEABLE/CLEAN 或单个绿灯不足以证明可合并
5. diff 是否只包含声明范围
6. review findings 是否已解决
7. GraphQL reviewThreads 是否无 unresolved actionable thread；不要只看普通 PR comments
8. 如果请求或预期有 GitHub/Codex review connector，是否已有当前 head 的 connector 完成证据；若记录了 `no_connector_expected`，是否已确认当前 head 没有请求或预期 connector
9. 已修复的 review feedback 是否有对应回复或已 resolve thread
10. 是否存在 high-context file、test weakening、silent fallback、ownership 冲突
11. git fetch --prune 后 origin/main 是否前进；若 stale_base 且影响 PR 范围，不允许 merge
12. CI wait 是否在预算内；若只剩远端等待，返回 WAITING_CI 和 resume 查询
13. review-thread 同类修复循环是否超过 2 次；若超过，返回 REVIEW_LOOP
14. threads_run_log 是否记录了失败码、验证状态、truth_level、remote_refresh 和 closure 状态

如果无 blocking issue，返回：
No findings; safe to merge.

同时列出残余风险。
```

## Research/Spec Threads

```text
开 {{n}} 个只读 researcher threads。
每个 thread 负责一个不同角度，不要修改文件。

角度：
1. repo architecture and current implementation
2. public/external reference evidence
3. UX/product workflow
4. validation/eval/testing strategy
5. risk/security/maintainability

每个 researcher 输出：
- evidence with paths/URLs
- concrete gaps
- confidence
- recommended first PR or spec section
- claims requiring verification

主线程最后合并成：
- evidence table
- conflict table
- recommended architecture
- implementation spec
- umbrella issue plus child issues when gaps are heterogeneous
```

## Research-Only Threads

```text
开 {{n}} 个只读 researcher threads。
默认 n<=3。不要修改文件，不要开 PR，不要 merge。

先输出 thread_dispatch_gate：
- explicit_thread_request
- native_subagents
- spawn_requirement
- fallback_mode
- planned_native_threads（每个 lane 的 id/role/target/spawn_status/no_spawn_reason）
- native_thread_evidence.spawned_agents（每个实际 native thread 的 lane_id/spawn_tool/agent_id_or_thread_id/wait_evidence/close_evidence/result_collected）
- no_spawn_reason（仅未 spawn 时允许）

每个 thread 只负责一个明确角度：
{{angles}}

输出 evidence table、conflicts、risks、next recommended action。
```

## Review-Only Threads

```text
开最多 2 个只读 reviewer threads 审查 {{target_pr_or_diff}}。
不要修改文件，不要提交，不要 merge。
默认 verification_scope=inspection_only；只运行便宜静态检查或 touched behavior targeted tests。
不要运行 full project test suite，除非 lane_map 明确指定 reviewer 是 verification_owner 或 merge_reviewer。

先输出 thread_dispatch_gate：
- explicit_thread_request
- native_subagents
- spawn_requirement
- fallback_mode
- planned_native_threads（每个 lane 的 id/role/target/spawn_status/no_spawn_reason）
- native_thread_evidence.spawned_agents（每个实际 native thread 的 lane_id/spawn_tool/agent_id_or_thread_id/wait_evidence/close_evidence/result_collected）
- no_spawn_reason（仅未 spawn 时允许）

输出 findings first；如果没有 blocking issue，写 No findings; safe to proceed。
说明未验证项和残余风险。
```

## Implement Without Merge

```text
实现 {{scope}} 的最小可合并 slice，可提交或开 PR，但 merge_policy=no_merge。
必须先写 intent_contract、lane_map、writable_files、forbidden_files、verification。
完成后停在 PR ready/recommendation，不要 merge。
```

## Final Cleanup Audit

```text
请只读检查本地和远端是否还有残留：
- gh pr list
- gh issue list
- GraphQL reviewThreads.isResolved for touched PRs
- PR conversation comments, review comments, and whether fixed feedback has replies/resolution
- git fetch --prune
- git status --short --branch
- git log origin/main..HEAD
- git diff --stat origin/main...HEAD
- git worktree list
- dirty worktrees and stale branches
- origin/main 当前 SHA 与 touched branch base_ref 的 stale-base 状态
- active skill path/source SHA 和 run-log 写入状态

区分：
- remote truth
- local stale state
- dirty but already superseded work
- high-context untracked files
- actual missing PR work
- historical unresolved review threads that are outside the current queue

最后输出 threads_run_log JSON 草稿：
- mode
- repo
- lanes_total
- native_thread_evidence.spawned_agents
- no_spawn_reason
- failure_codes
- verification.fresh
- truth_level
- remote_truth.open_prs
- remote_truth.open_issues
- remote_truth.checked_review_threads
- local_state.dirty_worktrees
- local_state.stale_branches
- remote_closure.checked
- remote_refresh.origin_main_sha
- remote_refresh.stale_base
- active_skill_source.path
- active_skill_source.source_sha
- run_log.path
- run_log.write_status
- run_log.no_log_reason
- queue_bounds.queue_tranche
- outcome
```
