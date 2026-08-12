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

Evaluation records contain only `evaluation_id`, the target `run_id`, timestamp, parent session ID,
and one controlled outcome: `verified`, `needs_correction`, `blocked`, or `rejected`.

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

## Analysis examples

Inspect recent records without exposing prompts or answers:

```bash
jq -s 'sort_by(.started_at) | reverse | .[:20]' \
  "$CODEX_HOME/state/sol-luna-router/runs.jsonl"
```

Measure completion rate and token totals by profile:

```bash
jq -s '
  map(select(.record_type == "run"))
  | group_by(.profile)
  | map(. as $runs | {
      profile: .[0].profile,
      runs: length,
      success_rate: (($runs | map(select(.status == "success")) | length) / ($runs | length)),
      input_tokens: (map(.usage.input_tokens // 0) | add),
      output_tokens: (map(.usage.output_tokens // 0) | add),
      median_seconds: (map(.duration_seconds) | sort | .[length / 2 | floor])
    })' "$CODEX_HOME/state/sol-luna-router/runs.jsonl"
```

Count failure classes and correction depth by parent session:

```bash
jq -s '{
  failures: ([.[] | select(.record_type == "run" and .status == "failed") | .failure_code] | group_by(.) | map({code: .[0], count: length})),
  outcomes: ([.[] | select(.record_type == "evaluation") | .outcome] | group_by(.) | map({outcome: .[0], count: length})),
  sessions: ([.[] | select(.record_type == "run")] | group_by(.parent_session_id) | map({parent_session_id: .[0].parent_session_id, runs: length}))
}' "$CODEX_HOME/state/sol-luna-router/runs.jsonl"
```

Use these aggregates to compare bounded task shapes and correction rates. Do not interpret Max
token use alone as quality: pair it with completion, verification outcome, corrections, failures,
and elapsed time.
