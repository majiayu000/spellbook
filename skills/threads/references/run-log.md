# Threads Run Log

Use this reference when the user asks to collect problems encountered by the `threads` skill, or when a non-trivial run should leave a compact diagnostic trail. For issue/PR queue runs, write this log by default unless the user opts out or the environment cannot write the file.

## Purpose

Collect enough structured data to answer:

- Which trigger caused the skill to run?
- Did the task need multiple lanes, or should it have stayed single-agent?
- Did any lane drift outside its role or writable files?
- Were GitHub, worktree, CI, and review-thread states checked with fresh evidence?
- Did the run refresh `origin/main` often enough to notice stale bases?
- Was the queue bounded to an explicit tranche instead of expanding indefinitely?
- Which failure modes repeat across runs?

## Storage

Default local path:

```text
~/.codex/threads-run-log.jsonl
```

Override with:

```text
CODEX_THREADS_RUN_LOG=/path/to/threads-run-log.jsonl
```

Append one JSON object per run:

```bash
python3 skills/threads/scripts/append_run_log.py <<'JSON'
{
  "skill": "threads",
  "mode": "execute_direct",
  "repo": "/abs/repo/path",
  "trigger_summary": "user asked to process issue and PR queue with threads",
  "goal": "fix and merge actionable PR queue",
  "native_subagents": "available",
  "fallback_mode": "none",
  "queue_bounds": {
    "max_items": 1,
    "time_budget": "30m",
    "queue_tranche": "first merge-ready blocker"
  },
  "lanes_total": 4,
  "failure_codes": ["review_thread_missed"],
  "remote_refresh": {
    "origin_main_sha": "abc123",
    "stale_base": false,
    "refreshes": 3
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
  "skill": "threads",
  "skill_source": "local|spellbook|unknown",
  "mode": "single_agent|plan_only|execute_direct|review_only|research_spec",
  "repo": "/absolute/repo/path",
  "base_ref": "origin/main",
  "trigger_summary": "short summary, not the raw prompt",
  "goal": "short goal",
  "non_goals": ["out of scope item"],
  "native_subagents": "available|unavailable",
  "fallback_mode": "none|single_agent|prompt_pack_only",
  "queue_bounds": {
    "max_items": 1,
    "time_budget": "30m",
    "queue_tranche": "first blocker"
  },
  "remote_refresh": {
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
  "lanes_total": 0,
  "lanes": [
    {
      "id": "worker-1",
      "role": "worker",
      "target": "issue #123",
      "worktree": "/tmp/repo-worker-1",
      "writable_files": ["src/example.rs"],
      "files_changed": ["src/example.rs"],
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
  "ci_wait": {
    "duration_seconds": 0,
    "budget_exhausted": false,
    "pending_checks": []
  },
  "review_loop": {
    "cycles": 0,
    "outcome": "resolved|review_loop|not_applicable"
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

## Failure Codes

Use stable codes so later analysis can aggregate them:

- `trigger_too_broad`: skill activated for a task that did not need threads.
- `missing_intent_contract`: goal, non-goals, done-when, or merge policy was unclear.
- `source_drift`: local installed skill and Spellbook/source version differed.
- `stale_remote_state`: PR, issue, branch, or CI state was not freshly fetched.
- `stale_base`: `origin/main` advanced under a lane and may invalidate its base.
- `duplicate_work_missed`: existing PR/issue/branch already covered the task.
- `role_drift`: planner/reviewer/worker acted outside its lane role.
- `write_scope_violation`: worker touched unassigned or forbidden files.
- `vague_lane_output`: lane returned claims without commands, files, or evidence.
- `verification_gap`: completion was claimed without fresh command output.
- `review_thread_missed`: inline review thread/comment state was not checked.
- `review_loop`: repeated review-thread fix cycles hit the configured limit.
- `waiting_ci`: only remote CI remained and the wait budget was exhausted.
- `merge_gate_bypass`: merge happened without independent review or closure audit.
- `tool_unavailable`: native subagent, GitHub, or validation tool was unavailable.
- `environment_mismatch`: wrong cwd, worktree, binary, branch, or runtime was used.
- `context_loss`: compaction/resume lost required state.
- `user_interrupt`: user redirected or stopped the run before closure.

## Analysis Queries

Common local checks:

```bash
jq -r '.failure_codes[]?' ~/.codex/threads-run-log.jsonl | sort | uniq -c | sort -nr
jq -r 'select(.outcome!="success") | [.recorded_at_utc,.repo,.mode,.failure_codes|join(",")] | @tsv' ~/.codex/threads-run-log.jsonl
jq -r 'select(.verification.fresh==false) | [.recorded_at_utc,.repo,.goal] | @tsv' ~/.codex/threads-run-log.jsonl
```

## Privacy

Do not log secrets, tokens, cookies, private messages, raw prompts, or full command output. Log concise summaries and stable evidence identifiers instead: file paths, command names, PR/issue numbers, head SHAs, and failure codes.
