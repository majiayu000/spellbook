# Prompt Patterns

Use these templates as raw material. Fill concrete repo paths, PR numbers, issue numbers, file ownership, and verification commands before dispatch.

## Root Orchestrator

```text
你看下这个库有哪些 issue 和 PR 应该怎么处理。
使用 Codex-native threads 分别作 plan、impl+PR提交、review+修改、merge reviewer。
先做完整规划，判断哪些可以并行，能并行的使用独立 worktree。
目标是做完整闭环：不合理的 issue/PR 可以建议关闭；合理的要实现、review、修复、验证、必要时 merge。

硬约束：
- 先查 repo 指令、git 状态、open issues、open PRs、CI、dirty worktree。
- 不要把 Codex threads 路由到 OMX/tmux。
- 每个实现 lane 必须有 disjoint writable_files。
- review lane 只读。
- 高上下文文件 AGENTS.md/CLAUDE.md/settings/hooks 默认禁止修改。
- 每个 PR merge 前必须有独立 thread review。
- merge 前必须用 thread-aware GitHub 数据检查 reviewThreads.isResolved；open PR/issue 为空不等于评论闭环完成。
- 输出 lane_map、依赖图、执行顺序、验证命令、stop_conditions。
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
2. 已完成映射和证据
3. 未完成/风险
4. 推荐处理动作和理由
5. 可并行 worktree 拆分
6. 每个 lane 的 writable_files 和 forbidden_files
7. 必须运行的验证命令
8. 不应在本轮强做的范围
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

完成后汇报：
- changed files
- commits/PR if created
- verification commands and key output
- remaining risks

不要 merge。
```

## Read-Only Code Review

```text
请对 {{target_pr_or_worktree}} 做只读 code review，不要修改文件，不要提交，不要 merge。
目标：{{issue_or_pr_goal}}

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
2. CI/checks 是否对当前 head 通过
3. diff 是否只包含声明范围
4. review findings 是否已解决
5. GraphQL reviewThreads 是否无 unresolved actionable thread；不要只看普通 PR comments
6. 已修复的 review feedback 是否有对应回复或已 resolve thread
7. 是否存在 high-context file、test weakening、silent fallback、ownership 冲突

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

区分：
- remote truth
- local stale state
- dirty but already superseded work
- high-context untracked files
- actual missing PR work
- historical unresolved review threads that are outside the current queue
```
