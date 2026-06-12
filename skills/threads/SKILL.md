---
name: threads
description: Coordinate Codex-native thread workflows when the user explicitly asks for $threads, Codex threads, open threads, 开几个 thread/子agent, or a repo issue/PR queue flow needing parallel lanes, worktrees, independent review, merge gates, review-thread/comment closure, final cleanup, or threads run-log data collection.
---

# Threads

Use this skill to turn a broad request into controlled Codex-native subthreads with explicit lanes, file ownership, review gates, and verifiable closure.

Native Codex threads are short-lived parallel work lines inside the Codex workflow. They are not the same as OMX/tmux workers. If native subagent tools are not visible, discover them with tool search. If no native subagent capability is available, produce the thread prompt pack and execution plan instead of pretending threads were launched.

## Decision

Choose one mode:

- **single_agent**: handle a small, well-scoped task locally with the same evidence gates.
- **plan_only**: map issues, PRs, risks, and parallelization without edits.
- **execute_direct**: run one or more bounded implementation lanes after planning.
- **review_only**: launch independent reviewers for PRs, diffs, or risky code.
- **research_spec**: split exploration by angle, then synthesize docs/spec/issues.
- **clarify_first**: ask only when repo, target queue, permission, or done-when is missing.

Prefer `single_agent` for one-file fixes, simple questions, or tasks where the next step depends on one immediate result. Use parallel lanes only when the work can be split by independent targets or disjoint writable files.

For any implementation mode, start with a lane map before spawning workers. For GitHub issue/PR queues, complete the Capability Gate and Queue Gate first; do not create worker lanes until `capability_gate`, `queue_gate`, `queue_ledger`, and `issue_to_pr_map` are written.

## Operating Contract

Before dispatch, record the operating contract:

```text
goal:
non_goals:
done_when:
merge_policy: no_merge | merge_after_gate | user_confirm_before_merge
remote_truth_required: yes | no
queue_ledger: required_for_queue | optional | none
ci_truth_source: discovered_workflow | user_supplied | language_default | none
data_collection: final_report | local_jsonl | none
queue_bounds:
  max_items:
  time_budget:
  queue_tranche:
remote_refresh:
  cadence:
  last_fetch:
  stale_base_policy:
```

Direct actions: inspect repo instructions, fetch remote state, map lanes, spawn bounded native subagents when useful, integrate results, verify, and report closure.

Escalate before: modifying high-context files, merging without fresh CI/review-thread truth, sharing writable files across workers, or switching to shell/tmux/OMX orchestration.

Evidence-backed pushback: choose `single_agent` when parallelism adds coordination risk without independent work; challenge vague worker output, stale remote state, or unverified completion claims.

Feedback loop: record notable failures in `threads_run_log`, classify the failure mode, tighten the lane prompt or split, then retry only after the hypothesis changes.

If the user asks for issue/PR queue handling, `remote_truth_required` is `yes`, `queue_ledger` is `required_for_queue`, and non-trivial queue runs default to `data_collection: local_jsonl` unless the user opts out or the log path is unavailable.

Broad queue requests such as "all issues and PRs" are bounded by default. If the user did not give an explicit long-run budget, choose one smallest mergeable tranche, record `max_items` / `time_budget` / `queue_tranche`, and leave the remaining queue for the next run with exact next actions.

## Capability Gate

Before dispatching lanes, record whether native Codex subagents are actually available:

```text
capability_gate:
- native_subagents: available | unavailable
- tools_seen:
- fallback_mode: single_agent | prompt_pack_only | none
- manual_orchestration_allowed: yes | no
```

Rules:

- If native subagents are unavailable, do not claim threads were launched.
- Do not switch to shell, tmux, OMX, Harness, or other manual orchestration unless the user explicitly asks for that fallback.
- If `fallback_mode` is `single_agent`, explain why parallelism was rejected.
- If `fallback_mode` is `prompt_pack_only`, output exact lane prompts and stop before implementation.

## Queue Gate

For GitHub issue/PR queue handling, write a `queue_gate` block before the lane map and before any implementation worker is launched. This is mandatory even when all open PRs look `MERGEABLE` or `CLEAN`.

The gate must use live state from the current session:

```text
queue_gate:
- fetched_remote:
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
- For review-gated queues, work one blocker or bounded tranche to closure unless writable file ownership is clearly disjoint and the PRs are not stacked.
- Keep remote truth separate from local stale or dirty worktree state.

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
  worktree:
  writable_files:
  forbidden_files:
  exclusive_verification:
  expected_output:
  verification:
```

Rules:

- Search first: inspect repo state, open issues/PRs, current branch, dirty files, and applicable instructions before assigning work.
- For GitHub queues, the lane map must be based on the preceding `queue_gate`; no worker lane may start from open issue/PR lists alone.
- Keep planners and reviewers read-only.
- Give implementation workers disjoint writable paths. Never assign two workers the same writable file.
- Put high-context files such as `AGENTS.md`, `CLAUDE.md`, settings, hooks, and setup scripts in `forbidden_files` unless the user explicitly asks to modify them.
- Prefer existing worktrees when they are already tied to the target branch. Otherwise create clean worktrees from `origin/main` or the requested base.
- Commands that mutate shared state such as `.git/hooks`, shared `$HOME` files, global caches, local daemons, or repo-level generated state belong to `verification_owner` and must not run in parallel lanes unless that mutable state is isolated.
- Require fresh verification from the worker or the verification owner before claiming success.
- For GitHub queues, treat comments and review threads as first-class remote state; open PR/issue lists alone are not enough.

## Dispatch

Use native subagents when available. If the multi-agent tool is not loaded, search for it using tool discovery. Do not use shell/tmux/OMX orchestration unless explicitly requested.

When `multi_agent_v1` tools are available, use `spawn_agent` for bounded sidecar lanes, `wait_agent` only when the next critical-path step needs that result, and `close_agent` after collecting completed output. Keep immediate blockers in the main thread.

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
blockers:
```

## Merge Gate

Do not merge from worker output alone. Merge only after:

- The PR/diff has at least one independent review lane.
- Blocking findings are fixed or explicitly ruled out with evidence.
- Required checks are fresh and tied to the current head SHA.
- Current merge state is clean. `MERGEABLE`, `CLEAN`, or a green check alone is not sufficient without the matching current head SHA, full check rollup, merge state, and GraphQL review-thread state.
- GitHub review-thread state is checked with a thread-aware source such as GraphQL `reviewThreads { isResolved isOutdated }`; flat PR comments are not sufficient.
- The PR has no unresolved actionable review threads, and any fixed review feedback has an explicit reply or resolved thread unless the user forbids GitHub writes.
- Check review threads after PR creation/update, after CI completes, and immediately before merge. If auto-review can arrive after marking a draft ready or after CI finishes, wait 60-120 seconds and re-check once.
- Stop with `REVIEW_LOOP` after two repeated fix/review cycles on the same class of review-thread finding unless the hypothesis changes.
- Use a bounded CI wait. After one complete CI cycle or the configured wait budget, stop with `WAITING_CI` when there is no actionable local failure. Report PR number, head SHA, pending checks, last observed status, and the exact resume query.
- Run a final remote refresh before merge review. If `origin/main` advanced and overlaps the PR scope, stop with `stale_remote_state` until the branch is rebased or recreated.
- The final answer can state exact PR numbers, commits, changed files, and verification commands.

If the user asked for “review then merge,” the merge reviewer should be a separate lane from the implementation worker.

## Run Log

For non-trivial runs, include a compact `threads_run_log` block in the final report. For issue/PR queues, append the same JSON object locally with `scripts/append_run_log.py` by default unless the user opts out or the environment cannot write the log. Read [run-log.md](references/run-log.md) before writing durable logs.

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

local_state:
- dirty_worktree:
- stale_worktree:
- high_context_file:

threads_run_log:
- mode:
- native_subagents:
- lanes_total:
- queue_items_total:
- queue_tranche:
- failure_codes:
- verification_fresh:
- closure_complete:
- log_path:
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
