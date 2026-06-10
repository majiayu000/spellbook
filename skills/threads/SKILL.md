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

For any implementation mode, start with a lane map before spawning workers.

## Operating Contract

Before dispatch, record the operating contract:

```text
goal:
non_goals:
done_when:
merge_policy: no_merge | merge_after_gate | user_confirm_before_merge
remote_truth_required: yes | no
data_collection: final_report | local_jsonl | none
```

Direct actions: inspect repo instructions, fetch remote state, map lanes, spawn bounded native subagents when useful, integrate results, verify, and report closure.

Escalate before: modifying high-context files, merging without fresh CI/review-thread truth, sharing writable files across workers, or switching to shell/tmux/OMX orchestration.

Evidence-backed pushback: choose `single_agent` when parallelism adds coordination risk without independent work; challenge vague worker output, stale remote state, or unverified completion claims.

Feedback loop: record notable failures in `threads_run_log`, classify the failure mode, tighten the lane prompt or split, then retry only after the hypothesis changes.

If the user asks for issue/PR queue handling, `remote_truth_required` is `yes`: run `git fetch --prune`, inspect open PRs/issues, and search for duplicate or superseding work before planning lanes.

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
  worktree:
  writable_files:
  forbidden_files:
  expected_output:
  verification:
```

Rules:

- Search first: inspect repo state, open issues/PRs, current branch, dirty files, and applicable instructions before assigning work.
- Keep planners and reviewers read-only.
- Give implementation workers disjoint writable paths. Never assign two workers the same writable file.
- Put high-context files such as `AGENTS.md`, `CLAUDE.md`, settings, hooks, and setup scripts in `forbidden_files` unless the user explicitly asks to modify them.
- Prefer existing worktrees when they are already tied to the target branch. Otherwise create clean worktrees from `origin/main` or the requested base.
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
- Required checks are fresh and tied to the current head.
- GitHub review-thread state is checked with a thread-aware source such as GraphQL `reviewThreads { isResolved isOutdated }`; flat PR comments are not sufficient.
- The PR has no unresolved actionable review threads, and any fixed review feedback has an explicit reply or resolved thread unless the user forbids GitHub writes.
- If auto-review can arrive after marking a draft ready or after CI finishes, wait briefly and re-check comments/review threads before merging.
- The final answer can state exact PR numbers, commits, changed files, and verification commands.

If the user asked for “review then merge,” the merge reviewer should be a separate lane from the implementation worker.

## Run Log

For non-trivial runs, include a compact `threads_run_log` block in the final report. If the user asks to collect this skill's problems, append the same JSON object locally with `scripts/append_run_log.py`. Read [run-log.md](references/run-log.md) before writing durable logs.

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

local_state:
- dirty_worktree:
- stale_worktree:
- high_context_file:

threads_run_log:
- mode:
- lanes_total:
- failure_codes:
- verification_fresh:
- closure_complete:
- log_path:
```

Separate remote truth from local machine state. State when a branch is merged remotely but local main is stale, dirty, or diverged.

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
- If no native subagent capability is available, return the lane map and exact prompts so the user can launch them manually.
