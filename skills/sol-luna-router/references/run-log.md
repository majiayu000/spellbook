# Run ledger

The runner writes one `run` JSON object per invocation to a local JSONL ledger. Sol can append a
separate `evaluation` object after verification. The default path is:

```text
$CODEX_HOME/state/sol-luna-router/runs.jsonl
```

When `CODEX_HOME` is unset, it uses `~/.codex/state/sol-luna-router/runs.jsonl`. The ledger file is
mode `0600`, and its dedicated parent directory is mode `0700` where permissions allow.

## Privacy boundary

Run records intentionally include operational metadata:

- schema and runner version, `run_id`, timestamps, duration, command, profile, sandbox, and fixed model/effort;
- `parent_session_id`, `worker_thread_id`, and `resumed_thread_id` for joining correction cycles;
- Git root and working directory;
- prompt SHA-256 and UTF-8 byte count for equality checks without storing the prompt;
- token usage reported by Codex, event count, warning count, and normalized failure class;
- whether a separate raw events file was retained.

It intentionally excludes prompt text, prompt-file path, final response text, warning text, raw
errors, credentials, and raw event bodies. Paths and session IDs are still sensitive metadata; do
not publish the ledger or commit it to a repository.

Evaluation records contain `evaluation_id`, the target `run_id`, timestamp, parent session ID,
passed/failed check counts, and one controlled outcome: `verified`, `needs_correction`, `blocked`,
or `rejected`. `verified` requires at least one passed check and zero failed checks.

Raw event capture is a separate explicit option:

```bash
--events-file /absolute/private/path/run.jsonl
```

Raw events can contain task and answer content. Use them only for a targeted investigation, then
delete them according to the user's retention policy.

## Fields and interpretation

`status` is `success` or `failed`. Successful records include the exact non-negative integer token
fields emitted by Codex under `usage`; the runner does not estimate billing or infer prices.
Failures include a stable `failure_code` and exclude raw error messages. Important codes include:

- `capacity_exhausted`: rate, quota, usage, credit, or spend capacity prevented completion;
- `timeout`: the bounded worker runtime expired;
- `codex_exit` or `turn_failed`: Codex terminated unsuccessfully;
- `invalid_jsonl`, `incomplete_turn`, `missing_thread_id`, `missing_final_response`;
- `invalid_input`, `invalid_profile`, `non_git_target`, and `artifact_exists`.

The result JSON includes `telemetry.status`: `written`, `disabled`, or `write_failed`. A successful
worker remains successful when its ledger append fails, but the failure is visible on stderr and in
the result so missing data is never silent.

## Evidence report

Generate a deterministic local summary without exposing prompts or answers:

```bash
python3 <skill-dir>/scripts/analyze_run_log.py --format json
```

The report separates three questions:

- Reliability: worker success rate, warnings, and normalized failure codes.
- Quality: evaluation coverage, verified rate, first-pass verified rate, check evidence coverage,
  and controlled outcome counts.
- Efficiency: exact token totals, average input/output tokens per successful run, resume count,
  median duration, and p95 duration.

Token fields come from the Luna worker event stream. They do not include Sol commander tokens, so
they measure worker efficiency rather than total routed-task cost. The `parent_session_id` is kept
for a later authorized join with parent-session analytics; the local ledger does not read or copy
the parent transcript.

Multiple annotations for one run are allowed because the ledger is append-only; the latest
annotation wins and `evaluation_overwrites` makes revisions visible. Orphan annotations and
malformed JSONL fail or surface explicitly instead of being silently ignored.

Use the aggregates to compare similar bounded task cohorts and correction rates. The report states
its claim boundary: this ledger is observational evidence, not a causal benchmark. To demonstrate
improvement, replay the same hidden-test task from the same snapshot against Sol-only and Sol+Luna,
then compare quality gates, total commander-plus-worker credits, and wall time.
