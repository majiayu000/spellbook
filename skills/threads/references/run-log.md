# Threads Run Log

Use this reference when the user asks to collect problems encountered by the `threads` skill, or when a non-trivial run should leave a compact diagnostic trail. Validate a preflight record before dispatch, then append a final record after collection. Durable JSONL logging defaults to `data_collection: local_jsonl` for GitHub queues, multi-lane runs, or runs that may push/comment/merge. Use final-report-only for tiny read-only/single-agent runs or explicit user opt-out, and record `no_log_reason`.

## Purpose

Collect enough structured data to answer:

- Which trigger caused the skill to run?
- Did the task need multiple lanes, or should it have stayed single-agent?
- Did any lane drift outside its role or writable files?
- Were GitHub, worktree, CI, and review-thread states checked with fresh evidence?
- What remote `truth_level` was available, and which actions were forbidden by that level?
- Did the run refresh `origin/main` often enough to notice stale bases?
- Was the queue bounded to an explicit tranche instead of expanding indefinitely?
- Which failure modes repeat across runs?

## Storage

Default local path is project-scoped and kept out of tracked worktree content
when the current directory is inside a Git repository:

```text
<git-dir>/codex/threads/run-log.jsonl
```

Override with:

```text
CODEX_THREADS_RUN_LOG=/path/to/threads-run-log.jsonl
```

The script discovers the project by walking up from the current working
directory until it finds `.git`. For a normal checkout, `<git-dir>` is
`<project>/.git`; for a linked worktree, it is the metadata directory referenced
by the `.git` file. This keeps durable logging per project without adding
untracked `.codex/` files to the repository. If no Git project is found, the
fallback path is `<current-directory>/.codex/threads/run-log.jsonl`.

Do not use a global log file by default; different repositories should not
share durable threads telemetry unless the user explicitly sets
`CODEX_THREADS_RUN_LOG`.

In the Spellbook source checkout the script is
available at `skills/threads/scripts/append_run_log.py`. In an installed skill,
resolve the script relative to the loaded `threads` skill directory; do not
assume the target repository contains a `skills/threads` path.

Before spawning, submit the planned record with `run_phase: preflight` and
`--validate-only`. A successful preflight exits zero without writing a line.
It does not require completed native-thread evidence, but it does require at
least one planned lane and concrete queue bounds:

```bash
THREADS_SKILL_DIR=${THREADS_SKILL_DIR:-skills/threads}
python3 "$THREADS_SKILL_DIR/scripts/append_run_log.py" --validate-only <<'JSON'
{
  "run_phase": "preflight",
  "skill": "threads",
  "mode": "execute_direct",
  "thread_dispatch_gate": {
    "native_subagents": "available",
    "explicit_thread_request": true,
    "spawn_requirement": "required",
    "fallback_mode": "none",
    "planned_native_threads": [{"id": "calibration", "role": "researcher"}]
  },
  "queue_bounds": {
    "max_items": 100,
    "max_model_calls": 2,
    "time_budget": "30m",
    "checkpoint_every_items": 50,
    "queue_tranche": "one calibration tranche"
  }
}
JSON
```

After collection, append one final JSON object:

```bash
THREADS_SKILL_DIR=${THREADS_SKILL_DIR:-skills/threads}
python3 "$THREADS_SKILL_DIR/scripts/append_run_log.py" <<'JSON'
{
  "run_phase": "final",
  "skill": "threads",
  "mode": "execute_direct",
  "repo": "/abs/repo/path",
  "trigger_summary": "user asked to process issue and PR queue with threads",
  "goal": "fix and merge actionable PR queue",
  "intent_contract": {
    "merge_policy": "no_merge",
    "remote_truth_required": true,
    "data_collection": "local_jsonl"
  },
  "truth_level": "A",
  "native_subagents": "available",
  "explicit_thread_request": true,
  "spawn_requirement": "required",
  "fallback_mode": "none",
  "native_thread_evidence": {
    "spawned_agents": [
      {
        "lane_id": "merge-reviewer",
        "spawn_tool": "multi_agent_v1.spawn_agent",
        "agent_id_or_thread_id": "agent-123",
        "wait_evidence": "wait_agent completed",
        "close_evidence": "close_agent completed",
        "result_collected": true
      }
    ]
  },
  "queue_bounds": {
    "max_items": 1,
    "max_model_calls": 4,
    "time_budget": "30m",
    "elapsed_seconds": 180,
    "checkpoint_every_items": 1,
    "queue_tranche": "first merge-ready blocker"
  },
  "context_budget": {
    "window_tokens": 258400,
    "soft_stop_ratio": 0.5,
    "hard_stop_ratio": 0.65,
    "critical_stop_ratio": 0.75,
    "current_usage_signal": "below_soft_stop"
  },
  "output_firewall": {
    "raw_log_policy": "file_only",
    "max_parent_stdout_lines": 150,
    "max_subagent_final_lines": 150,
    "artifact_root": "artifacts/logs/tranche-001",
    "evidence_paths": ["artifacts/logs/tranche-001/cargo-test.log"]
  },
  "lanes_total": 4,
  "failure_codes": ["review_thread_missed"],
  "remote_refresh": {
    "owner_lane": "coordinator",
    "origin_main_sha": "abc123",
    "local_base_sha": "abc123",
    "stale_base": false,
    "refreshes": 3,
    "policy": "continue"
  },
  "remote_truth": {
    "open_prs": 0,
    "open_issues": 0
  },
  "local_state": {
    "dirty_worktree": false
  },
  "outcome": "partial",
  "verification": {
    "fresh": true,
    "commands": ["python3 scripts/validate_skills.py --check"]
  }
}
JSON
```

## Schema

Recommended fields:

```json
{
  "schema_version": 1,
  "recorded_at_utc": "auto-filled by script",
  "run_phase": "preflight|final",
  "skill": "threads",
  "skill_source": "local|spellbook|unknown",
  "active_skill_source": {
    "path": "/Users/example/.spellbook/skills/threads",
    "source_sha": "abc123"
  },
  "mode": "single_agent|plan_only|execute_direct|review_only|research_spec|clarify_first",
  "repo": "/absolute/repo/path",
  "base_ref": "origin/main",
  "trigger_summary": "short summary, not the raw prompt",
  "goal": "short goal",
  "non_goals": ["out of scope item"],
  "intent_contract": {
    "authorized_actions": ["read repository", "edit assigned worktree files"],
    "fresh_confirmation_required": ["cross-repo writes", "install or restart"],
    "merge_policy": "no_merge|merge_after_gate|user_confirm_before_merge",
    "remote_truth_required": true,
    "data_collection": "final_report|local_jsonl|none"
  },
  "truth_level": "A|B|C|D",
  "native_subagents": "available|unavailable",
  "explicit_thread_request": true,
  "spawn_requirement": "required|optional|unavailable",
  "fallback_mode": "none|single_agent|prompt_pack_only",
  "no_spawn_reason": "required when an explicit threads run falls back to single_agent; use no_independent_lanes|sequential_dependency|shared_writable_files|tool_unavailable|user_requested_single_agent",
  "single_agent_justification": {
    "reason": "no_independent_lanes|sequential_dependency|shared_writable_files|tool_unavailable|user_requested_single_agent",
    "evidence": "short evidence summary"
  },
  "native_thread_evidence": {
    "spawned_agents": [
      {
        "lane_id": "review-pr",
        "spawn_tool": "multi_agent_v1.spawn_agent",
        "agent_id_or_thread_id": "agent-123",
        "wait_evidence": "completed status collected",
        "close_evidence": "closed after collection",
        "result_collected": true
      }
    ],
    "fallback_reason": ""
  },
  "queue_bounds": {
    "max_items": 1,
    "max_model_calls": 4,
    "time_budget": "30m",
    "elapsed_seconds": 180,
    "checkpoint_every_items": 1,
    "queue_tranche": "first blocker"
  },
  "context_budget": {
    "window_tokens": 258400,
    "soft_stop_ratio": 0.5,
    "hard_stop_ratio": 0.65,
    "critical_stop_ratio": 0.75,
    "current_usage_signal": "below_soft_stop",
    "override_reason": ""
  },
  "output_firewall": {
    "raw_log_policy": "file_only",
    "max_parent_stdout_lines": 150,
    "max_subagent_final_lines": 150,
    "artifact_root": "artifacts/logs/tranche-001",
    "evidence_paths": []
  },
  "remote_refresh": {
    "owner_lane": "coordinator",
    "cadence": "queue_start|before_lane|before_push|before_merge|after_ci_wait",
    "origin_main_sha": "abc123",
    "local_base_sha": "def456",
    "stale_base": false,
    "refreshes": 1,
    "policy": "continue|rebase|required_stop"
  },
  "queue_ledger": {
    "items_total": 0,
    "items_closed": 0,
    "items_deferred": 0,
    "superseded_items": []
  },
  "queue_gate": {
    "fetched_remote": true,
    "truth_level": "A",
    "pr_classification": [],
    "open_prs": [],
    "open_issues": []
  },
  "lanes_total": 0,
  "lanes": [
    {
      "id": "worker-1",
      "role": "worker",
      "target": "issue #123",
      "worktree": "/tmp/repo-worker-1",
      "writable_files": ["src/example.rs"],
      "files_changed": ["src/example.rs"],
      "native_thread_id": "agent-123",
      "verification_scope": "targeted",
      "verification": ["cargo test example"],
      "result": "passed|blocked|failed"
    }
  ],
  "failure_codes": [],
  "remote_closure": {
    "checked": true,
    "open_prs": 0,
    "open_issues": 0,
    "unresolved_review_threads": 0
  },
  "connector_review": {
    "expected": false,
    "status": "completed|no_connector_expected|pending|unknown",
    "head_sha": "abc123",
    "evidence": "short current-head connector evidence"
  },
  "remote_truth": {
    "open_prs": 0,
    "open_issues": 0,
    "checked_pr_heads": [],
    "checked_review_threads": [],
    "checked_ci": [],
    "origin_main_sha": "abc123",
    "stale_base": false
  },
  "local_state": {
    "dirty_worktree": false,
    "stale_worktree": false,
    "high_context_file": false
  },
  "ci_wait": {
    "duration_seconds": 0,
    "budget_exhausted": false,
    "pending_checks": []
  },
  "review_loop": {
    "cycles": 0,
    "outcome": "resolved|review_loop|not_applicable"
  },
  "run_log": {
    "path": "<git-dir>/codex/threads/run-log.jsonl",
    "write_status": "written|not_written|not_applicable",
    "no_log_reason": ""
  },
  "exclusive_verification": {
    "serialized_commands": [],
    "reason": ""
  },
  "verification": {
    "fresh": true,
    "commands": ["cargo test"],
    "failed_commands": []
  },
  "outcome": "success|partial|blocked|failed",
  "notes": "short diagnostic note"
}
```

Truth levels:

- `A`: git fetch plus GitHub API or GraphQL can prove current PR head, checks, merge state, and review-thread state.
- `B`: git fetch plus REST PR/review/comment data is available, but GraphQL review-thread state is unavailable; merge is forbidden.
- `C`: only local git state is reliable; remote closure and merge claims are forbidden.
- `D`: no reliable repo or remote state is available; only plan or prompt-pack output is allowed.

The append script enforces an allowlist of top-level fields by default. Use `--allow-extra` only for local debugging when extra fields are needed; sensitive keys and common token patterns are still redacted.

`time_budget` must be a positive integer followed by `s`, `m`, or `h`. Preflight, multi-lane, queue-ledger, and final records containing planned or spawned work require positive `max_items`, `max_model_calls`, and `checkpoint_every_items`; this includes coordinator-only queues and one-child tranches. The checkpoint cannot exceed `max_items`. Final bounded records also require non-negative `elapsed_seconds`, which cannot exceed `time_budget`. A final record may preserve approved ceilings in `intent_contract.queue_bounds` and add elapsed evidence in top-level `queue_bounds`; all shared fields must still match. The processed item audit uses the larger of the queue-ledger status counters and nested `items` length. Free text such as `not pre-budgeted` is rejected.

Safety limits:

- maximum input size: 64 KiB
- maximum string length: 4000 characters
- maximum nesting depth: 8
- maximum array items retained: 100
- new log files are created with `0600` permissions
- existing log files are tightened to `0600` before append
- append uses a POSIX file lock when available

When `queue_gate` is present, include a `remote_refresh` contract with
`owner_lane`, `origin_main_sha`, `local_base_sha`, `stale_base`, and `policy`.
Allowed owners are `coordinator` and `verification_owner`; read-only lanes should
consume this snapshot unless they are explicitly isolated.

## Failure Codes

Use stable codes so later analysis can aggregate them:

- `trigger_too_broad`: skill activated for a task that did not need threads.
- `missing_intent_contract`: goal, non-goals, done-when, or merge policy was unclear.
- `durable_log_skipped`: a queue, multi-lane, push/comment, or merge-capable run did not write a durable log and lacked explicit opt-out.
- `truth_level_too_low`: requested action required a higher remote truth level.
- `source_drift`: local installed skill and Spellbook/source version differed.
- `active_skill_source_unknown`: active skill path or source revision could not be established for a major run.
- `stale_remote_state`: PR, issue, branch, or CI state was not freshly fetched.
- `stale_base`: `origin/main` advanced under a lane and may invalidate its base.
- `duplicate_work_missed`: existing PR/issue/branch already covered the task.
- `contributor_pr_replaced_unnecessarily`: a maintainer replacement PR was opened instead of updating a writable contributor PR.
- `role_drift`: planner/reviewer/worker acted outside its lane role.
- `write_scope_violation`: worker touched unassigned or forbidden files.
- `vague_lane_output`: lane returned claims without commands, files, or evidence.
- `verification_gap`: completion was claimed without fresh command output.
- `raw_output_blocked`: raw logs, long command output, broad search output, or session JSONL attempted to enter the parent instead of an artifact.
- `parent_context_hard_stop`: parent context budget hit the hard or critical stop and the run had to checkpoint or hand off.
- `review_thread_missed`: inline review thread/comment state was not checked.
- `connector_review_incomplete`: a requested or expected GitHub/Codex connector review was not complete on the current head.
- `review_loop`: repeated review-thread fix cycles hit the configured limit.
- `native_thread_not_spawned`: explicit threads run did not spawn a native subagent and did not record a valid fallback.
- `waiting_ci`: only remote CI remained and the wait budget was exhausted.
- `merge_gate_bypass`: merge happened without independent review or closure audit.
- `tool_unavailable`: native subagent, GitHub, or validation tool was unavailable.
- `environment_mismatch`: wrong cwd, worktree, binary, branch, or runtime was used.
- `context_loss`: compaction/resume lost required state.
- `user_interrupt`: user redirected or stopped the run before closure.

## Analysis Queries

Common local checks:

```bash
LOG="$(git rev-parse --git-dir)/codex/threads/run-log.jsonl"
test -f "$LOG" && jq -r '.failure_codes[]?' "$LOG" | sort | uniq -c | sort -nr
test -f "$LOG" && jq -r 'select(.outcome!="success") | [.recorded_at_utc,.repo,.mode,((.failure_codes // [])|join(","))] | @tsv' "$LOG"
test -f "$LOG" && jq -r 'select(.verification.fresh==false) | [.recorded_at_utc,.repo,.goal] | @tsv' "$LOG"
```

## Privacy

Do not log secrets, tokens, cookies, private messages, raw prompts, raw session JSONL, or full command output. Log concise summaries and stable evidence identifiers instead: file paths, command names, PR/issue numbers, head SHAs, artifact paths, and failure codes. Unknown top-level fields are rejected unless `--allow-extra` is supplied.
