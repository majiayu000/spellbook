---
name: codex
description: Use when the user asks to run Codex CLI (codex exec, codex resume) or references OpenAI Codex for code analysis, refactoring, or automated editing
compatibility: {runtimes: [claude_code]}
---

# Codex Skill Guide

## Operating Contract
1. Run `codex --version` and `codex exec --help` first. Stop if Codex is unavailable, and only use flags shown by the installed CLI.
2. If the user did not specify a model or reasoning effort, use the installed default. Do not hardcode a model list; model names and supported reasoning levels change over time.
3. Select the smallest sandbox needed: `--sandbox read-only` for inspection and `--sandbox workspace-write` for requested local edits. Network access, extra writable roots, and broader modes are separate grants.
4. Assemble the command from supported options such as:
   - `-m, --model <MODEL>`
   - `--config model_reasoning_effort="<LEVEL>"`
   - `--sandbox <read-only|workspace-write|danger-full-access>`
   - `-C, --cd <DIR>`
   - `--add-dir <DIR>`
   - `--json`
   - `--ephemeral`
   - `--skip-git-repo-check`
   - `--dangerously-bypass-approvals-and-sandbox`
5. Do not use `--skip-git-repo-check` by default. Use it only when the user explicitly asks to run outside a Git repository or has approved that boundary bypass for this command.
6. Do not use deprecated compatibility shortcuts such as `--full-auto`; use the explicit sandbox shown by current help.
7. Preserve stderr. Keep it out of the parent context by writing it to a bounded artifact and reading only the exit status, short tail, or targeted diagnostics. Never redirect it to `/dev/null`.
8. For automation, batch work, cost investigation, or any run that needs measured usage, add `--json` and save stdout as JSONL. Read the final usage event and report input, cached input, output, and reasoning tokens when present.
9. Enforce a hard wall-clock timeout with the supervising runtime. Stop on non-zero exit or timeout; do not automatically retry an expensive run.
10. When continuing a genuinely conversational task, use `codex exec resume --last` via stdin. Do not resume a session for homogeneous record batches; start a fresh bounded `--ephemeral` run per tranche so accumulated history is not resent on every model call.

### Safe Prompt Passing

Do not build Codex commands with `echo "user prompt" | ...`; user text can contain quotes, substitutions, or newlines. Prefer a quoted heredoc so the shell never reinterprets prompt contents:

```bash
(
codex_skill_dir=${CODEX_SKILL_DIR:?set CODEX_SKILL_DIR to the installed codex skill}
codex_artifacts=$(mktemp -d) || exit 1
if python3 "$codex_skill_dir/scripts/run_with_timeout.py" 1800 \
  codex exec resume --last \
  2>"$codex_artifacts/stderr.log" <<'EOF'
Your follow-up prompt goes here.
EOF
then
  codex_status=0
else
  codex_status=$?
fi
tail -n 20 -- "$codex_artifacts/stderr.log"
tail_status=$?
if [ "$codex_status" -eq 0 ] && [ "$tail_status" -eq 0 ]; then
  rm -R -- "$codex_artifacts" || exit $?
else
  printf 'Codex artifacts retained: %s\n' "$codex_artifacts" >&2
fi
if [ "$codex_status" -ne 0 ]; then exit "$codex_status"; fi
exit "$tail_status"
)
```

### Quick Reference
| Use case | Sandbox mode | Key flags |
| --- | --- | --- |
| Read-only review or analysis | `read-only` | `--sandbox read-only` |
| Apply local edits | `workspace-write` | `--sandbox workspace-write` |
| Apply edits that need network access | `workspace-write` plus config | `--sandbox workspace-write -c 'sandbox_workspace_write.network_access=true'` after approval |
| Machine-readable usage | Match task | `--json`; save JSONL stdout and stderr separately |
| Independent batch tranche | Match task | `--ephemeral --json`; do not resume the previous tranche |
| Permit extra write scope | Prefer `--add-dir` | Ask before adding extra writable directories |
| Permit broad file access | `danger-full-access` only after approval | Ask before adding `--sandbox danger-full-access` |
| Resume a conversational task | Inherited from original | `codex exec resume --last` via quoted heredoc |
| Run from another directory | Match task needs | `-C <DIR>` plus other flags |

## Batch Cost Gate

Before more than one similar model call:

1. Define a small calibration ceiling for records, model calls, wall-clock time, and checkpoint cadence; ask for confirmation first when the user has not authorized even that bounded calibration.
2. Run one representative calibration tranche with `--json` inside that ceiling.
3. Measure actual usage from the JSONL event stream; do not estimate from record count alone.
4. Project the remaining calls and tokens from the measured tranche.
5. State the full-run maximum calls, maximum records, wall-clock budget, and checkpoint cadence.
6. Ask for confirmation when the projected full run is materially larger than the calibration or the user did not already authorize that concrete budget.

Stop at every checkpoint if measured usage exceeds the projection. Cached input is still token usage: a high cached-input share usually means the same large prefix or accumulated session context is being sent repeatedly, not that the run is free.

## Following Up
- Resume only when prior conversational context is necessary. For independent records, pass only the tranche instructions and compact artifacts needed for that tranche.
- Restate the model, reasoning effort, sandbox, measured usage, and remaining budget before proposing another costly tranche.
- Reaching the requested `done_when` condition ends the run. A blocker is not permission to install, upgrade, restart services, migrate or reindex data, edit global config/hooks, write to another repository, or perform GitHub writes unless the current request explicitly authorizes that action.

## Error Handling
- Stop and report failures whenever `codex --version` or a `codex exec` command exits non-zero; request direction before retrying.
- Before you use high-impact flags (`--sandbox danger-full-access`, `--dangerously-bypass-approvals-and-sandbox`, `--dangerously-bypass-hook-trust`, `--skip-git-repo-check`) ask the user for permission using AskUserQuestion unless it was already given.
- When output includes warnings, partial results, missing usage, or a timeout, preserve the evidence and ask how to adjust. Do not silently degrade to an unmetered or broader run.

## Gotchas

- `--skip-git-repo-check` bypasses an important cwd/worktree guard. Treat it like a boundary exception, not a default.
- `danger-full-access` and the `--dangerously-*` bypass flags are high-impact modes. Prefer `read-only`, then `workspace-write`, then modes explicitly listed by the installed CLI, then specific `--add-dir` grants before considering full access.
- If a prompt came from the user or another model, pass it as stdin or as a single already-quoted CLI argument. Never interpolate it into a shell string.
- Suppressing stderr hides failure and progress evidence; pasting all stderr into the parent wastes context. Save it, then inspect a bounded tail.
- A small output does not imply a cheap run. Repeated large cached prefixes can dominate usage across many short calls.
