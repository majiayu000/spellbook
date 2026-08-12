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

`status` is `success` or `failed`. Run records include the exact normalized token fields emitted by
Codex under `usage` when available, including on a failed exit or failed turn; absent usage is not
written as zero. The runner does not estimate billing or infer prices. Failures include a stable
`failure_code` and exclude raw error messages. Important codes include:

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
the default report measures worker efficiency rather than total routed-task cost. The
`parent_session_id` is kept for a later authorized join with parent-session analytics; the local
ledger does not read or copy the parent transcript.

## Historical credit estimates

Credit estimation is deliberately opt-in. Add the bundled machine-readable card when a dated
benchmark estimate is wanted:

```bash
python3 <skill-dir>/scripts/analyze_run_log.py \
  --run-log /absolute/private/runs.jsonl \
  --rate-card <skill-dir>/references/rate-card-2026-08-05.json \
  --format json
```

The card is labeled `historical benchmark estimate`, has `as_of` `2026-08-05`, and must not be
described as current pricing. Its units are credits per 1M tokens. Luna cost uses exact integer
`input_tokens`, `cached_input_tokens`, and `output_tokens`; cached input is included in input, and
uncached input is `input_tokens - cached_input_tokens`. Every run, including failed runs, is
costed only when exact valid usage exists. Missing usage is unresolved rather than zero; malformed,
negative, or inconsistent usage is excluded and reported under worker unresolved-usage reasons.
The report exposes `worker_runs_total`, `worker_runs_costed`, `worker_runs_unresolved`,
`worker_cost_coverage`, `worker_estimate_complete`, and partial worker credits.

The worker-only normalized fields are null when worker usage coverage is incomplete. The total-scope
fields `credits_per_verified_run`, `credits_per_first_pass_verified_run`, and
`commander_credit_share` require both complete worker coverage and complete commander-window
coverage. With no join, complete worker-only metrics may be reported under the explicit
`worker_only` scope; a commander-plus-worker total is never inferred.

## Explicit parent-session join

Commander usage remains off unless a caller supplies a local Codex sessions root:

```bash
python3 <skill-dir>/scripts/analyze_run_log.py \
  --run-log /absolute/private/runs.jsonl \
  --rate-card <skill-dir>/references/rate-card-2026-08-05.json \
  --codex-sessions-root /absolute/private/.codex/sessions \
  --format json
```

The analyzer resolves only unique, non-empty `parent_session_id` values from the ledger. It assumes
the matching rollout JSONL has a `session_meta` record with `payload.id`, and later
`event_msg`/`payload.type == "token_count"` records with top-level `timestamp` and
`payload.info.total_token_usage`. It strictly parses ledger `started_at`/`completed_at` and event
timestamps, merges overlapping run windows per parent, then subtracts the last cumulative snapshot
at or before each merged window start from the first snapshot at or after its end. It uses only
token metadata, never prompt/response text. The report makes shared-window de-duplication, missing
baselines/endpoints, counter decreases/resets, malformed files or usage, ambiguous duplicate
matches, and unique-ID / run-reference / window coverage visible. Sol preflight before run start
and work after run completion are outside the commander-window attribution. Resolved partial
commander components may be shown, but commander-plus-worker totals and total-scope normalized
metrics are null until every required parent window resolves. Complete total attribution also
requires every ledger run to have valid worker usage. Failed runs with exact usage are included;
failed runs without usage remain unresolved. Controlled A/B remains the causal total-cost proof.

Multiple annotations for one run are allowed because the ledger is append-only; the latest
annotation wins and `evaluation_overwrites` makes revisions visible. Orphan annotations and
malformed JSONL fail or surface explicitly instead of being silently ignored.

Use the aggregates to compare similar bounded task cohorts and correction rates. The report states
its claim boundary: this ledger is observational evidence, not a causal benchmark. To demonstrate
improvement, replay the same hidden-test task from the same snapshot against Sol-only and Sol+Luna,
then compare quality gates, total commander-plus-worker credits, and wall time.
