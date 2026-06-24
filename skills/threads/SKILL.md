---
name: threads
description: Use when the user explicitly asks for $threads, Codex-native subagents, 开几个子 agent, or a GitHub issue/PR queue needing parallel lanes, worktrees, review/merge gates, and closure audit. Do not use for OS/language threads, chat/email/forum threads, or Assistants product threads unless Codex workflow orchestration is explicit.
compatibility: {runtimes: [codex]}
---

# Threads

Use this skill to turn a broad request into controlled Codex-native subthreads with explicit lanes, file ownership, review gates, and verifiable closure.

Native Codex threads are short-lived parallel work lines inside the Codex workflow. They are not the same as OMX/tmux workers. If native subagent tools are not visible, discover them with tool search. If no native subagent capability is available, produce the thread prompt pack and execution plan instead of pretending threads were launched.

## Do Not Use For

Do not use this skill for generic uses of "thread" unless the user explicitly means Codex workflow orchestration:

- operating-system threads, language concurrency, or async programming models
- chat, email, forum, Slack, GitHub discussion, or comment threads
- OpenAI Assistants API threads or other product APIs
- ordinary single-agent repo work where there are no independent lanes

## Decision

Choose one mode:

- **single_agent**: handle a small, well-scoped task locally with the same evidence gates.
- **plan_only**: map issues, PRs, risks, and parallelization without edits.
- **execute_direct**: run one or more bounded implementation lanes after planning.
- **review_only**: launch independent reviewers for PRs, diffs, or risky code.
- **research_spec**: split exploration by angle, then synthesize docs/spec/issues.
- **clarify_first**: ask only when repo, target queue, permission, or done-when is missing.

Use `single_agent` only for one-file fixes, simple questions, or tasks where the next step depends on one immediate result. If the user explicitly asks for threads, subagents, or a GitHub issue/PR queue and native subagents are available, do not silently choose `single_agent`; record a concrete `no_spawn_reason` before implementation work begins.

For any implementation mode, start with a lane map before spawning workers. For GitHub issue/PR queues, complete the Capability Gate and Queue Gate first; do not create worker lanes until `capability_gate`, `queue_gate`, `queue_ledger`, and `issue_to_pr_map` are written.

## Explicit Thread Dispatch Gate

When the user explicitly asks for threads, subagents, "开几个子 agent", or a GitHub issue/PR queue that the skill classifies as `plan_only`, `execute_direct`, `review_only`, or `research_spec`, native dispatch is required whenever native subagent tools are available.

Record this gate before implementation, review, or merge work:

```text
thread_dispatch_gate:
- explicit_thread_request: yes | no
- native_subagents: available | unavailable
- spawn_requirement: required | optional | unavailable
- fallback_mode: single_agent | prompt_pack_only | none
- planned_native_threads:
  - id:
    role:
    target:
    write_scope: read_only | disjoint_writable | none
    spawn_status: planned | spawned | skipped
    no_spawn_reason:
- native_thread_evidence:
    user_requested_native_threads: yes | no
    spawned_agents:
      - lane_id:
        spawn_tool:
        agent_id_or_thread_id:
        wait_evidence:
        close_evidence:
        result_collected: yes | no
    fallback_reason:
- no_spawn_reason:
```

Rules:

- If `explicit_thread_request: yes`, `native_subagents: available`, and `spawn_requirement: required`, spawn at least one bounded native subagent before claiming the run is using threads.
- `native_subagents: available` plus `fallback_mode: none` is valid only when `native_thread_evidence.spawned_agents` contains at least one real agent/thread ID.
- Every `planned_native_threads` lane must have a matching `native_thread_evidence.spawned_agents[].lane_id` or a lane-level `no_spawn_reason`; spawning one native thread does not justify running the remaining planned lanes serially.
- A main-thread lane is a coordinator lane, not a native thread. Do not count the coordinator as `native_thread_evidence.spawned_agents`.
- If no native thread is spawned, set `fallback_mode: single_agent` and write `no_spawn_reason` before editing files, commenting on GitHub, or merging. Valid reasons are narrow: task is tiny and truly sequential, all possible writable lanes overlap, native tools are unavailable, or the user explicitly asks not to spawn.
- For GitHub PR merge work, at least one read-only reviewer or merge-reviewer native thread is required when native subagents are available. A self-review by the coordinator does not satisfy the independent review lane.
- If native tools are unavailable, produce a prompt pack or continue as `single_agent` only after saying that no native threads were launched.

## Operating Contract

Before dispatch, record this block as `intent_contract`:

```text
intent_contract:
  goal:
  non_goals:
  done_when:
  merge_policy: no_merge | merge_after_gate | user_confirm_before_merge
  remote_truth_required: yes | no
  truth_level: A | B | C | D
  queue_ledger: required_for_queue | optional | none
  ci_truth_source: discovered_workflow | user_supplied | language_default | none
  data_collection: final_report | local_jsonl | none
  active_skill_source: path | source_sha | unknown
  queue_bounds:
    max_items:
    time_budget:
    queue_tranche:
  remote_refresh:
    cadence:
    last_fetch:
    stale_base_policy:
  thread_dispatch:
    explicit_thread_request:
    spawn_requirement:
    no_spawn_reason:
```

Defaults:

- `merge_policy` is `no_merge` unless the user explicitly authorizes merging in the current conversation.
- `data_collection` is `local_jsonl` for GitHub issue/PR queues, multi-lane runs, or any run that may push/comment/merge; use `final_report` only for tiny read-only/single-agent runs or explicit user opt-out.
- Record the active skill path and source revision when discoverable; record `unknown` rather than guessing.
- If merge permission is ambiguous, stop after merge review and report the exact recommendation or merge command instead of merging.

Direct actions: inspect repo instructions, fetch remote state, map lanes, apply the Explicit Thread Dispatch Gate, spawn required bounded native subagents, integrate results, verify, and report closure.

Escalate before: modifying high-context files, merging without fresh CI/review-thread truth, sharing writable files across workers, or switching to shell/tmux/OMX orchestration.

Evidence-backed pushback: choose `single_agent` only when parallelism adds coordination risk without independent work, and record the `no_spawn_reason`; challenge vague worker output, stale remote state, or unverified completion claims.

Feedback loop: record notable failures in `threads_run_log`, classify the failure mode, tighten the lane prompt or split, then retry only after the hypothesis changes.

If the user asks for issue/PR queue handling, `remote_truth_required` is `yes` and `queue_ledger` is `required_for_queue`.

Broad queue requests such as "all issues and PRs" are bounded by default. If the user did not give an explicit long-run budget, choose one smallest mergeable tranche, record `max_items` / `time_budget` / `queue_tranche`, and leave the remaining queue for the next run with exact next actions.

## Capability Gate

Before dispatching lanes, record whether native Codex subagents are actually available:

```text
capability_gate:
- native_subagents: available | unavailable
- tools_seen:
- explicit_thread_request: yes | no
- spawn_requirement: required | optional | unavailable
- fallback_mode: single_agent | prompt_pack_only | none
- no_spawn_reason:
- manual_orchestration_allowed: yes | no
```

Rules:

- If native subagents are unavailable, do not claim threads were launched.
- If native subagents are available and `spawn_requirement` is `required`, do not proceed past planning until at least one native subagent is spawned or `fallback_mode` and `no_spawn_reason` are recorded.
- Do not switch to shell, tmux, OMX, Harness, or other manual orchestration unless the user explicitly asks for that fallback.
- If `fallback_mode` is `single_agent`, explain why parallelism was rejected.
- If `fallback_mode` is `prompt_pack_only`, output exact lane prompts and stop before implementation.

## Queue Gate

For GitHub issue/PR queue handling, write a `queue_gate` block before the lane map and before any implementation worker is launched. This is mandatory even when all open PRs look `MERGEABLE` or `CLEAN`.

The gate must use live state from the current session:

```text
queue_gate:
- fetched_remote:
- truth_level:
- remote_refresh:
    base_ref:
    origin_main_sha:
    local_base_sha:
    stale_base:
    policy:
- current_branch:
- dirty_files:
- unpushed_commits:
- worktrees:
- open_prs:
- open_issues:
- pr_classification:
  - PR:
    head_sha:
    merge_state:
    check_rollup:
    review_threads:
    classification:
    reason:
- issue_to_pr_map:
  - issue:
    covering_pr:
    status: covered | uncovered | stale_or_superseded | needs_human_decision
    reason:
- recommended_order:
- stop_conditions:
```

Classify every open PR as exactly one of:

- `merge_ready`
- `review_thread_blocked`
- `ci_failed`
- `conflict_blocked`
- `stale_or_superseded`
- `needs_human_decision`

Rules:

- `MERGEABLE` or `CLEAN` is never sufficient by itself. A PR is `merge_ready` only when the current head SHA, check rollup, merge state, and GraphQL review-thread state are all fresh and clean.
- Query review threads with a thread-aware source such as GraphQL `reviewThreads { isResolved isOutdated }`; flat PR comments are not sufficient.
- Map open issues to existing PRs before opening new implementation lanes. Prefer fixing, reviewing, or merging an existing covering PR over opening a competing PR.
- If an existing covering contributor PR has `maintainerCanModify: true`, update that PR before opening a maintainer replacement unless the branch is unsafe, unwritable, or the user approves replacement.
- For review-gated queues, work one blocker or bounded tranche to closure unless writable file ownership is clearly disjoint and the PRs are not stacked.
- Keep remote truth separate from local stale or dirty worktree state.

## Remote Truth Levels

Use the highest truth level available from the current session and record it in `intent_contract`, `queue_gate`, and `threads_run_log`:

- **A**: `git fetch` plus GitHub API or GraphQL can prove current PR head, check rollup, merge state, and review-thread state. Implementation, review, and merge gates may proceed if all other conditions pass.
- **B**: `git fetch` plus REST PR/review/comment data is available, but GraphQL review-thread state is unavailable. Implementation and review may proceed; merge is forbidden.
- **C**: only local git state is reliable. Local implementation and review may proceed; PR closure, merge readiness, and remote cleanup claims are forbidden.
- **D**: no reliable repo or remote state is available. Use `plan_only` or `prompt_pack_only`; do not implement, push, merge, or claim closure.

Never fabricate remote state to reach a higher level. If the tool or permission gap matters, report the lower level and the blocked operation.

## Queue Ledger

For issue/PR queues, keep a live queue ledger from discovery through final closure. The ledger can be a concise table in the conversation, a local durable log, or both, but it must survive handoff and compaction when the run is long.

Use these fields:

```text
queue_ledger:
- item:
  type: issue | pr | review_thread | local_task
  remote_state:
  owner_lane:
  dependencies:
  base_ref:
  branch:
  worktree:
  writable_files:
  pr:
  head_sha:
  ci_status:
  review_thread_state:
  acceptance_evidence:
  merge_sha:
  closed_by:
  remote_checked_at:
```

Rules:

- Update the ledger after initial remote discovery, after queue gate classification, after each PR open/update, before merge, after merge/close, and before the final report.
- Keep dependency edges explicit. If a lane depends on another PR or a newer `origin/main`, rebase or recreate the lane only after recording the dependency and checking for changed files.
- Do not claim `Fixes #...` or close an issue until each meaningful acceptance point is mapped to evidence: changed files, tests, commands, PR, commit, or remote state.
- If a queue item is superseded by another PR or issue, record the superseding item instead of silently dropping it.

## Remote Refresh

Long queue runs must refresh remote state without mutating worker worktrees:

- Run `git fetch --prune origin` at queue start, before opening a new lane, before pushing, before merge review, and after long waits such as CI polling. For runs longer than one focused tranche, refresh at least every 20-30 minutes.
- Compare the current `origin/main` SHA with each lane's recorded `base_ref`. Do not automatically merge or rebase during a lane.
- If `origin/main` advanced, record `stale_base: yes` in `queue_gate`, `queue_ledger`, and `threads_run_log`.
- Continue without rebase only when changed upstream files are disjoint from the lane's writable files and verification remains meaningful.
- Rebase, recreate the worktree, or stop with `stale_remote_state` when upstream changes overlap the lane, alter CI, or invalidate the acceptance evidence.
- Remote refresh is not required for tiny `single_agent` tasks unless the task touches GitHub remote state.

## Lane Map

Write a short lane map before dispatch:

```text
mode:
repo:
base_ref:
global_constraints:
verification_owner:
stop_conditions:
lanes:
- id:
  role: planner | worker | reviewer | merge_reviewer | researcher
  target:
  depends_on:
  execution_mode: parallel | serial_after_dependency | read_only_until_dependency
  base_gate:
  worktree:
  writable_files:
  forbidden_files:
  exclusive_verification:
  verification_scope: inspection_only | targeted | full_local | ci_only
  expected_output:
  verification:
  native_thread_id:
  no_spawn_reason:
```

Rules:

- Search first: inspect repo state, open issues/PRs, current branch, dirty files, and applicable instructions before assigning work.
- For GitHub queues, the lane map must be based on the preceding `queue_gate`; no worker lane may start from open issue/PR lists alone.
- Build a dependency graph before spawning writable workers. Lanes with no dependency edge and disjoint writable files may run in parallel; lanes with dependency edges must run serially after their upstream lane is stable.
- For stacked PRs or issue chains, set downstream writable lanes to `read_only_until_dependency` until the upstream head is pushed and the `base_gate` is satisfied. Downstream planners may inspect and prepare a patch plan in parallel, but they must not edit files before the gate opens.
- `base_gate` must name the upstream condition that makes a downstream writable lane safe to start: current head SHA recorded, upstream CI/targeted verification status known, dirty upstream worktree absent or committed, and overlapping files checked.
- Keep planners and reviewers read-only.
- Mark coordinator-only lanes with `native_thread_id: none`; every spawned lane must record the returned native tool agent ID.
- Give implementation workers disjoint writable paths. Never assign two workers the same writable file.
- Do not start two writable workers when either lane depends on the other's branch, PR, generated output, or verification result. Dependency means serial execution even if the writable file lists appear disjoint.
- Put high-context files such as `AGENTS.md`, `CLAUDE.md`, settings, hooks, and setup scripts in `forbidden_files` unless the user explicitly asks to modify them.
- Prefer existing worktrees when they are already tied to the target branch. Otherwise create clean worktrees from `origin/main` or the requested base.
- Prefer creating downstream worktrees only after the upstream `base_gate` opens. Avoid starting writable downstream work on a stale base; if early exploration is useful, use a read-only planner lane instead.
- Commands that mutate shared state such as `.git/hooks`, shared `$HOME` files, global caches, local daemons, or repo-level generated state belong to `verification_owner` and must not run in parallel lanes unless that mutable state is isolated.
- Require fresh verification from the worker or the verification owner before claiming success.
- For GitHub queues, treat comments and review threads as first-class remote state; open PR/issue lists alone are not enough.
- Default WIP limit: at most 3 planning/research lanes, 2 concurrent writable implementation lanes, and 2 reviewers per PR unless the user explicitly grants a larger budget.

## Dependency-Aware Dispatch

Choose parallelism on demand after the lane map, not by default.

Use **parallel writable workers** only when all are true:

- no `depends_on` edge exists between the lanes
- writable files and generated outputs are disjoint
- verification does not mutate shared state
- neither lane's branch, PR, or acceptance evidence depends on the other's result

Use **serial writable workers** when any lane depends on another lane's branch, PR, generated output, CI result, review result, schema migration, shared setup/install behavior, or version bump. In that case, run the upstream writable lane first, record its head SHA and verification, then create or rebase the downstream worktree from that stable head.

Use **parallel read-only planners/reviewers** for dependent work only when they do not edit files or mutate GitHub state. Their output should be a patch plan, risk map, or review findings that can be applied after the upstream gate opens.

For stacked PRs:

- Model the stack as a serial pipeline, not a parallel writable queue.
- Do not spawn a downstream writable worker until the upstream branch has a recorded stable head and any required CI or targeted verification has completed or been deliberately deferred.
- If the upstream head changes while a downstream worker has uncommitted changes, stop that downstream lane and require a handoff artifact: committed WIP SHA, patch file, or explicit abandon/recreate decision.
- The coordinator must not edit a worker-owned dirty downstream worktree. Recreate from the stable upstream head and apply a reviewed patch when possible.
- Record `stale_base` and the recovery decision in `queue_ledger` and `threads_run_log`.

## Verification Budget

Use `verification_scope` to keep review evidence useful without duplicating expensive full-suite work:

- `inspection_only`: read-only diff/code inspection. Cheap static checks such as `git diff --check` are allowed when they are relevant.
- `targeted`: focused tests or linters for touched behavior only.
- `full_local`: one owner runs the project-wide local suite for the tranche, usually the root orchestrator, `verification_owner`, or a `merge_reviewer`.
- `ci_only`: fresh CI tied to the current head SHA is the full-suite truth source.

Rules:

- Assign at most one full-suite owner per tranche. If fresh CI is the full-suite truth source, do not also ask every reviewer to repeat the local full suite.
- Reviewer lanes default to `inspection_only` or `targeted`. They must not run full project test suites unless the lane map explicitly names them as `verification_owner` or `merge_reviewer`.
- Targeted reviewer checks should be command-valid for the language/tool. For Cargo, pass one test filter per `cargo test` command, or use a broader module/path filter; do not pass several unrelated test names as positional filters in one command.
- If a targeted check touches shared state, global caches, local daemons, or repo-level generated state, move it to the serialized `verification_owner` lane.

## Dispatch

Use native subagents when available. If the multi-agent tool is not loaded, search for it using tool discovery. Do not use shell/tmux/OMX orchestration unless explicitly requested.

When `multi_agent_v1` tools are available, use `spawn_agent` for required bounded sidecar lanes, `wait_agent` only when the next critical-path step needs that result, and `close_agent` after collecting completed output. Keep immediate blockers in the main thread, but do not count the main thread as a spawned native thread.

Close completed subagents as soon as their evidence has been collected. For long issue/PR queues, finish a bounded tranche, record the ledger and resume query, and consider starting a fresh parent thread instead of carrying oversized context forward.

Use these lane types:

- **Planner**: read issues/PRs/code and output dependency graph, worktree plan, file ownership, and risk.
- **Worker**: implement the smallest mergeable slice in one worktree; do not merge.
- **Reviewer**: inspect one PR/diff/worktree read-only; return findings first.
- **Fix Worker**: address concrete reviewer findings in the original worker worktree.
- **Merge Reviewer**: independently verify the final head and CI before merge.
- **Closure Auditor**: read remote truth after merge or close; verify issue/PR state, review threads, comments, branch cleanup, and local stale state.
- **Researcher**: inspect one external/source angle and return evidence with uncertainty.

Load [prompt-patterns.md](references/prompt-patterns.md) when you need ready-to-use prompts for planners, workers, reviewers, or research lanes.

Every lane output must be evidence-bearing:

```text
lane:
root_cause_or_claim:
files_read:
files_changed:
unauthorized_or_unassigned_changes:
commands_run:
head_sha_or_artifact:
native_thread_id:
blockers:
```

## Merge Gate

Do not merge from worker output alone. Merge only after:

- `merge_policy` is `merge_after_gate` or `user_confirm_before_merge` with explicit authorization from the current conversation.
- `truth_level` is `A`; lower truth levels may produce recommendations but must not merge.
- The PR/diff has at least one independent review lane.
- When native subagents are available, the independent review lane must be a spawned native thread with a recorded tool agent ID.
- Blocking findings are fixed or explicitly ruled out with evidence.
- Required checks are fresh and tied to the current head SHA.
- Current merge state is clean. `MERGEABLE`, `CLEAN`, or a green check alone is not sufficient without the matching current head SHA, full check rollup, merge state, and GraphQL review-thread state.
- GitHub review-thread state is checked with a thread-aware source such as GraphQL `reviewThreads { isResolved isOutdated }`; flat PR comments are not sufficient.
- The PR has no unresolved actionable review threads, and any fixed review feedback has an explicit reply or resolved thread unless the user forbids GitHub writes.
- Check review threads after PR creation/update, after CI completes, and immediately before merge. After marking a draft ready or after CI finishes, wait 60-120 seconds and re-check once before treating an empty `reviewThreads` result as clean. If a GitHub/Codex review connector was requested or is expected, do not merge until current-head connector completion is proven. Record `no_connector_expected` only after checking that no connector was requested or expected for the current head.
- Stop with `REVIEW_LOOP` after two repeated fix/review cycles on the same class of review-thread finding unless the hypothesis changes.
- Use a bounded CI wait. After one complete CI cycle or the configured wait budget, stop with `WAITING_CI` when there is no actionable local failure. Report PR number, head SHA, pending checks, last observed status, and the exact resume query.
- Run a final remote refresh before merge review. If `origin/main` advanced and overlaps the PR scope, stop with `stale_remote_state` until the branch is rebased or recreated.
- The final answer can state exact PR numbers, commits, changed files, and verification commands.

If the user asked for “review then merge,” the merge reviewer should be a separate lane from the implementation worker.

## Run Log

For non-trivial runs, include a compact `threads_run_log` block in the final report. For GitHub queues, multi-lane runs, or any run that may push/comment/merge, append the same JSON object locally with `scripts/append_run_log.py` unless the user opts out; record `no_log_reason` when final-report-only is used. Read [run-log.md](references/run-log.md) before writing durable logs.

Run logs are observational. Do not record secrets, credentials, full prompts, or private user data. Prefer short summaries, file paths, PR/issue numbers, command names, failure codes, and verification outcomes.

## Final Report

End with a compact status table:

```text
completed:
- lane:
  result:
  artifact:
  verification:

merged:
- PR:
  commit:

remaining:
- blocker_or_risk:
  next_action:

remote_truth:
- open_prs:
- open_issues:
- checked_pr_heads:
- checked_review_threads:
- checked_ci:
- origin_main_sha:
- stale_base:
- remote_refreshes:

active_skill_source:
- path:
- source_sha:

local_state:
- dirty_worktree:
- stale_worktree:
- high_context_file:

threads_run_log:
- mode:
- native_subagents:
- explicit_thread_request:
- spawn_requirement:
- native_thread_evidence:
    spawned_agents:
- no_spawn_reason:
- truth_level:
- lanes_total:
- queue_items_total:
- queue_bounds:
    queue_tranche:
- failure_codes:
- verification:
    fresh:
- remote_closure:
    checked:
- run_log:
    path:
    write_status:
    no_log_reason:
```

Separate remote truth from local machine state in all GitHub queue final reports. State when a branch is merged remotely but local main is stale, dirty, diverged, or a worktree branch is no longer tied to an open remote branch.

For GitHub queue work, include remote closure fields:

```text
remote_closure:
- open_prs:
- open_issues:
- touched_pr_unresolved_review_threads:
- touched_pr_unanswered_review_comments:
- historical_unresolved_review_threads:
- deleted_remote_branches:
- local_cleanup_left:
```

## Gotchas and Failure Rules

- If a subthread returns vague output, ask for evidence or redo that lane with a stricter prompt.
- If a worker touches unassigned files, stop that lane and audit before proceeding.
- If three attempts fail on the same problem, stop and challenge the hypothesis or split the issue differently.
- If a hook/UI status looks stuck, verify process/log evidence before calling the task stuck.
- Classify failures as specification/system design, inter-agent misalignment, or verification/termination before retrying.
- If long-running remote state changes underneath a lane, record `stale_remote_state` and refresh/rebase only through an explicit gate; do not silently continue on a stale base.
- If no native subagent capability is available, return the lane map and exact prompts so the user can launch them manually.
