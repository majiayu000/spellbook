# Threads Run Governance Spec

## Status

Draft for the `threads` skill governance cleanup. This spec is based on
`origin/main` at `5ba135e` and the current `skills/threads` directory layout.

## Problem

Recent Codex sessions show that native subagents are being used successfully for
parallel review, research, and GitHub queue work, but the evidence is hard to
audit after the fact. The durable run log is optional, the active skill source
is often implicit, and some fields required by `SKILL.md` are not accepted or
validated by `append_run_log.py`.

The goal is not to make every small read-only task noisy. The goal is to make
non-trivial `threads` runs reproducible enough to answer:

- Was a native subagent really spawned?
- Which lane owned each decision or file scope?
- Was `origin/main` fresh for the branch or PR?
- Were GitHub issues, PRs, CI, and review threads checked with current data?
- Did the run write a compact, private, project-scoped audit record?

## Non-Goals

- Do not replace Codex native subagents with tmux, shell loops, or external
  orchestration.
- Do not log raw prompts, private messages, command output dumps, tokens,
  cookies, or credential material.
- Do not merge PRs automatically. The `threads` merge gate remains explicit and
  user-authorized.
- Do not split `append_run_log.py` in the first cleanup PR. It is approaching
  the size where a split may be worthwhile, but this tranche should stay
  localized.

## Contract

### Dispatch Evidence

Any explicit `threads` request that reaches `plan_only`, `execute_direct`,
`review_only`, or `research_spec` must record a `thread_dispatch_gate`.

When native subagents are available and spawning is required:

- `fallback_mode: none` is valid only with at least one real spawned agent.
- The coordinator lane does not count as a spawned native thread.
- Every planned native lane must either have matching spawned evidence or a
  lane-level `no_spawn_reason`.
- Completed native agents must be closed after their result is collected.

### Remote State Ownership

`git fetch --prune origin` mutates Git metadata even when it does not alter the
worktree. For shared repo queues, the coordinator or `verification_owner` owns
remote refresh and passes a snapshot into read-only lanes. A lane may fetch only
when it works in an isolated worktree and its lane map says so.

### Run Log Defaults

Durable JSONL logging defaults to `local_jsonl` for:

- GitHub issue or PR queue runs.
- Multi-lane runs.
- Runs that may push, comment, mark ready, close, or merge.

Tiny read-only or truly single-agent runs may remain final-report-only, but
must record `no_log_reason` when a log would otherwise be expected.

### Canonical Fields

`SKILL.md`, `references/run-log.md`, prompt templates, and
`scripts/append_run_log.py` must use the same canonical field names. `queue_gate`
is a first-class field because `SKILL.md` requires it before GitHub queue worker
lanes begin.

The append script should reject unknown enum values for the fields it can check
cheaply:

- `native_subagents`
- `spawn_requirement`
- `data_collection`
- `outcome`
- `failure_codes`
- `remote_refresh.owner_lane`
- `remote_refresh.policy`
- `queue_gate.pr_classification[].classification`
- lane `role`
- lane `verification_scope`

## First PR Scope

The first implementation PR should:

- Add this spec.
- Accept `queue_gate` in the run-log allowlist.
- Add lightweight enum validation for common top-level and lane fields.
- Require a `remote_refresh` owner and base snapshot when `queue_gate` is
  logged.
- Add `--print-path` and `--validate-only` to support installed-skill and CI
  workflows.
- Tighten existing log file permissions to `0600` on append.
- Redact `KEY=value` style secret assignments in free-form strings.
- Update `run-log.md` to explain installed skill script paths and missing-file
  safe analysis queries.
- Update prompt templates so read-only lanes do not own shared remote refresh
  by default.
- Add targeted unit tests for the above.

## Follow-Up Issues

1. Require evidence-bearing `single_agent` fallback objects for explicit
   threads requests after a compatibility window.
2. Split run-log schema constants out of `append_run_log.py` if the file keeps
   growing or if multiple tools need the same field contract.
3. Add a small local analysis helper that scans Codex JSONL and durable
   threads run logs together, so missing durable records can be found without
   broad raw greps.
4. Add deeper shape validation for `queue_ledger`, `remote_closure`,
   `connector_review`, and `lane_map`.

## Acceptance

The first PR is complete when these commands pass from a branch based on fresh
`origin/main`:

```bash
python3 -m unittest tests.test_threads_run_log
python3 scripts/validate_skills.py --check
python3 scripts/audit_skill_quality.py threads
```

The PR body must include:

- `origin/main` SHA used as base.
- Created GitHub issue numbers.
- Native subagent ids used for planning or review.
- Fresh verification command output.
- Whether durable run-log writing was performed for the PR run.
