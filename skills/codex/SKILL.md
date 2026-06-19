---
name: codex
description: Use when the user asks to run Codex CLI (codex exec, codex resume) or references OpenAI Codex for code analysis, refactoring, or automated editing
compatibility: {runtimes: [claude_code]}
---

# Codex Skill Guide

## Running a Task
1. If the user did not specify a model or reasoning effort, use the installed Codex default or ask once with the available user-question mechanism. Do not hardcode a model list; model names change over time.
2. Select the sandbox mode required for the task; default to `--sandbox read-only` unless edits or network access are necessary.
3. Run `codex --version` first. Stop and report the failure if Codex is unavailable.
4. Assemble the command with the appropriate options:
   - `-m, --model <MODEL>`
   - `--config model_reasoning_effort="<xhigh|high|medium|low>"`
   - `--sandbox <read-only|workspace-write|danger-full-access>`; only use other modes when `codex exec --help` lists them
   - `-C, --cd <DIR>`
   - `--add-dir <DIR>`
   - `--skip-git-repo-check`
   - `--dangerously-bypass-approvals-and-sandbox`
5. Do not use `--skip-git-repo-check` by default. Use it only when the user explicitly asks to run outside a Git repository or has approved that boundary bypass for this command.
6. When continuing a previous session, use `codex exec resume --last` via stdin. Do not add model, reasoning, or sandbox flags on resume unless the user explicitly requests an override.
7. **IMPORTANT**: By default, append `2>/dev/null` to `codex exec` commands to suppress thinking tokens (stderr). Only show stderr if the user explicitly requests it or if debugging is needed.
8. Run the command, capture stdout/stderr (filtered as appropriate), and summarize the outcome for the user.
9. **After Codex completes**, inform the user: "You can resume this Codex session at any time by saying 'codex resume' or asking me to continue with additional analysis or changes."

### Safe Prompt Passing

Do not build Codex commands with `echo "user prompt" | ...`; user text can contain quotes, substitutions, or newlines. Prefer a quoted heredoc so the shell never reinterprets prompt contents:

```bash
codex exec resume --last 2>/dev/null <<'EOF'
Your follow-up prompt goes here.
EOF
```

### Quick Reference
| Use case | Sandbox mode | Key flags |
| --- | --- | --- |
| Read-only review or analysis | `read-only` | `--sandbox read-only 2>/dev/null` |
| Apply local edits | `workspace-write` | `--sandbox workspace-write 2>/dev/null` |
| Apply edits that need network access | `workspace-write` plus config | `--sandbox workspace-write -c 'sandbox_workspace_write.network_access=true' 2>/dev/null` |
| Permit extra write scope | Prefer `--add-dir` | Ask before adding extra writable directories |
| Permit broad file access | `danger-full-access` only after approval | Ask before adding `--sandbox danger-full-access` |
| Resume recent session | Inherited from original | `codex exec resume --last 2>/dev/null <<'EOF'` + prompt + `EOF` |
| Run from another directory | Match task needs | `-C <DIR>` plus other flags `2>/dev/null` |

## Following Up
- After every `codex` command, use the available user-question mechanism to confirm next steps, collect clarifications, or decide whether to resume with `codex exec resume --last`.
- When resuming, pass the new prompt through stdin using a quoted heredoc. The resumed session automatically uses the same model, reasoning effort, and sandbox mode from the original session.
- Restate the chosen model, reasoning effort, and sandbox mode when proposing follow-up actions.

## Error Handling
- Stop and report failures whenever `codex --version` or a `codex exec` command exits non-zero; request direction before retrying.
- Before you use high-impact flags (`--sandbox danger-full-access`, `--dangerously-bypass-approvals-and-sandbox`, `--dangerously-bypass-hook-trust`, `--skip-git-repo-check`) ask the user for permission using AskUserQuestion unless it was already given.
- When output includes warnings or partial results, summarize them and ask how to adjust using `AskUserQuestion`.

## Gotchas

- `--skip-git-repo-check` bypasses an important cwd/worktree guard. Treat it like a boundary exception, not a default.
- `danger-full-access` and the `--dangerously-*` bypass flags are high-impact modes. Prefer `read-only`, then `workspace-write`, then modes explicitly listed by the installed CLI, then specific `--add-dir` grants before considering full access.
- If a prompt came from the user or another model, pass it as stdin or as a single already-quoted CLI argument. Never interpolate it into a shell string.
