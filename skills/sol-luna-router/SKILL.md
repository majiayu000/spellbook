---
name: sol-luna-router
description: Route coding or repository-review work so GPT-5.6 Sol remains the commander and verifier while a separate GPT-5.6 Luna Max Codex CLI session performs bounded implementation or read-only investigation. Use when the user asks for Sol to direct, plan, supervise, or review Luna work; when native Sol-to-Luna spawning is unavailable or incompatible; or when a task needs auditable agent ownership, budgeted verification, live progress, timeout recovery, usage telemetry, and a Sol review loop.
---

# Sol-Luna Router

Keep Sol responsible for decisions and final verification. Use Luna Max for one bounded
implementation or read-only investigation. Use the bundled runner instead of native
`spawn_agent`; current Sol and Luna releases can select different multi-agent backends.

## Boundaries

- Treat the current Sol thread as commander and reviewer. Do not edit target product files from
  this thread.
- Delegate concrete implementation, fixes, worker-owned tests, or bounded read-only investigation
  to Luna Max.
- Fix every new and resumed worker invocation to `gpt-5.6-luna` with reasoning effort `max`.
- Allow only one write-capable Luna worker in a worktree at a time. Parallelize read-only work, or
  use isolated worktrees with explicit, disjoint file ownership.
- Keep the parent approval and sandbox boundary intact. Never add bypass, full-access, force-push,
  credential, or secret-handling flags.
- Stop after three failed correction cycles on the same root cause and reassess the hypothesis.
- Never claim completion from the worker summary alone. Verify from the current session.
- Do not use worker timeout as a test budget. Select a profile and give every potentially expensive
  command an explicit bound before launch.

## Operating Contract

- Direct actions: inspect local state, create external task prompts, run Luna within scope, and perform read-only verification.
- Escalate before: expanding ownership or permissions, using new network or credentials, destructive recovery, publishing, pushing, merging, or changing products.
- Evidence-backed pushback: cite a diff, command, repository rule, run record, or capacity failure when the requested route is unsafe or cannot satisfy done-when conditions.
- Feedback loop: use aggregate ledger evidence and correction patterns for the smallest runner, test, profile, or gotcha update; never optimize from token totals alone.

## Workflow

### 1. Preflight

1. Confirm the target working directory and resolve its Git root.
2. Inspect dirty and untracked state without modifying it. Preserve user changes.
3. Read applicable `AGENTS.md` files and repository verification commands.
4. State the goal, constraints, allowed file ownership, done-when conditions, command budget, and
   verification commands.
5. If the task is ambiguous enough to change architecture or scope, clarify before delegation.

Select `implementation` for edits and focused tests (`workspace-write`, 1800s default). Select
`bounded-review` for investigation (`read-only`, 900s, at most 8 commands, no full suites).

Use `bounded-review` whenever repository mutation is not the deliverable. It instructs Luna to
return broader checks as `requires_commander_verification`; Sol decides whether to run them later.
The runner also disables Python bytecode writes and redirects common Python, Rust, Go, Node, Ruff,
and mypy caches to temporary storage for the duration of the worker.

### 2. Prepare the worker task

Write a temporary UTF-8 task file outside the target repository. Include only task-local context:

```text
Role: implementation worker.
Objective: <one bounded outcome>
Target repository: <absolute path>
Allowed files: <explicit paths or one narrow subtree>
Do not touch: <user changes and out-of-scope paths>
Constraints: <applicable requirements>
Reproduction or evidence: <fresh evidence>
Command budget: <count, per-command limit, and forbidden broad suites>
Done when: <observable conditions>
Verification: <repository commands to run>
Return: root cause, changed files, commands with outcomes, and remaining risks.
```

Do not leak an intended patch or diagnosis when Luna must independently determine the root cause.

### 3. Run Luna Max

For implementation, run the bundled script with an absolute target directory and task-file path:

```bash
python3 <skill-dir>/scripts/run_luna_worker.py run \
  --cwd /absolute/path/to/repo \
  --prompt-file /absolute/path/to/task.md \
  --sandbox workspace-write
```

For review or diagnosis, add `--profile bounded-review` to use the budgeted read-only profile.

The script fixes new and resumed workers to `gpt-5.6-luna` with
`model_reasoning_effort="max"`, disables native multi-agent tools for the worker, invokes Codex
without a shell, and returns one JSON object containing `thread_id`, `final_response`, usage,
profile, sandbox, duration, and repository metadata.

Every invocation also appends one privacy-safe record to
`$CODEX_HOME/state/sol-luna-router/runs.jsonl` (normally under `~/.codex`). It captures the
commander session ID, Luna thread ID, token usage, duration, profile, warnings or failure class,
and a prompt fingerprint, but not prompt text, final response text, or raw errors. The current
Codex session is detected from `CODEX_THREAD_ID`; use `--parent-session-id` only when an explicit
override is required. Use `--run-log` to select another absolute ledger or `--no-run-log` for an
intentional one-off opt-out. A ledger write failure is reported without discarding a successful
worker result. Read [references/run-log.md](references/run-log.md) before analyzing or exporting
the ledger.

Use `--allow-non-git` only when the user explicitly wants work outside a Git repository. Raw
events are off by default because they can contain task and answer content. Use
`--events-file /absolute/path/events.jsonl` only when a durable raw trace is explicitly needed.
The path must be absolute and new; the runner writes mode-0600 JSONL there while Luna runs and
emits a heartbeat to stderr every 30 seconds.

### 4. Verify and review

1. Inspect the actual diff and changed-file list; reject out-of-ownership edits.
2. For read-only work, inspect command side effects and use no-write settings, external caches, or a disposable copy.
3. Run required builds, type checks, and focused tests in the current session.
4. Run broader checks when Luna returns `requires_commander_verification`; never weaken tests.
5. Compare Git status before and after read-only verification; generated artifacts fail the no-mutation check.
6. Review correctness, security, data integrity, error handling, and missing coverage.
7. After verification, append the outcome using the `run_id` returned under `telemetry`:

```bash
python3 <skill-dir>/scripts/run_luna_worker.py annotate \
  --run-id <run_id> \
  --outcome verified
```

Use `needs_correction`, `blocked`, or `rejected` instead when that is the evidence-backed result.
The annotation is append-only and contains no free-text notes. If everything passes, summarize the
result and cite fresh verification output.

### 5. Request a correction

When verification or Sol review finds an actionable defect, write a new temporary prompt containing
the exact failure evidence. Annotate the original run as `needs_correction`, then resume the same
worker thread:

```bash
python3 <skill-dir>/scripts/run_luna_worker.py resume \
  --cwd /absolute/path/to/repo \
  --thread-id <thread_id> \
  --prompt-file /absolute/path/to/correction.md \
  --profile <original-profile>
```

The resume command reasserts Luna, Max reasoning, disabled native agents, and the selected sandbox;
it does not rely on the historical thread configuration. Repeat verification after every
correction. Do not open a new worker thread unless the previous thread is unavailable or the task
has materially changed.

## Gotchas and failure handling

- If the runner reports an incompatible or unavailable model, stop and report the exact error.
- If Luna requests broader ownership, network, or permissions, return it to the user or revise the plan; do not grant it silently.
- On timeout, retain the partial `thread_id` and events path; resume with a smaller prompt, or treat a run without a thread ID as unrecoverable.
- Treat `capacity_exhausted` as infrastructure capacity, not task quality; never lower Luna effort automatically.
- Treat malformed JSONL, nonzero exit, `turn.failed`, missing completion, or missing final response as failure; recovered transport errors remain warnings.
- If unrelated user changes block safe verification, report the boundary instead of reverting them.
- If `bounded-review` requests or starts an unbudgeted full suite, stop the run and tighten the
  task instead of increasing its timeout.
