Leave a star ⭐ if you like it 😘

# Codex Integration for Claude Code

<img width="2288" height="808" alt="skillcodex" src="https://github.com/user-attachments/assets/85336a9f-4680-479e-b3fe-d6a68cadc051" />


## Purpose
Enable Claude Code to invoke the Codex CLI (`codex exec` and session resumes) for automated code analysis, refactoring, and editing workflows.

## Prerequisites
- `codex` CLI installed and available on `PATH`.
- Codex configured with valid credentials and settings.
- Confirm the installation by running `codex --version`; resolve any errors before using the skill.

## Installation

Install through Spellbook from the repository root:

```bash
./install.sh --target claude --skills codex
```

## Usage

### Diagnostics and Usage
The skill preserves stderr as a bounded artifact instead of discarding it or pasting it into Claude Code's context. For automated, batch, or cost-sensitive work it uses `codex exec --json`, saves the JSONL event stream, and reports measured input, cached-input, output, and reasoning usage when available.

### Example Workflow

**User prompt:**
```
Use codex to analyze this repository and suggest improvements for my claude code skill.
```

**Claude Code response:**
Claude will activate the Codex skill and:
1. Use the installed Codex default model, or ask once if you requested a specific model choice.
2. Use the installed default reasoning effort unless you requested a specific level.
3. Select appropriate sandbox mode (defaults to `read-only` for analysis)
4. Avoid high-impact flags such as `danger-full-access`, `--dangerously-bypass-approvals-and-sandbox`, or `--skip-git-repo-check` unless the user explicitly approves them.
5. Run a command like:
```bash
(
  set -o pipefail
  for required_command in jq python3 head wc mkfifo; do
    command -v "$required_command" >/dev/null 2>&1 || {
      printf 'Missing required command: %s\n' "$required_command" >&2
      exit 127
    }
  done
  codex_skill_dir=${CODEX_SKILL_DIR:-$HOME/.claude/skills/codex}
  [ -f "$codex_skill_dir/scripts/run_with_timeout.py" ] || {
    printf 'Missing Codex timeout helper: %s\n' \
      "$codex_skill_dir/scripts/run_with_timeout.py" >&2
    exit 1
  }
  codex_artifacts=$(mktemp -d) || exit 1
  codex_events_max_bytes=16777216
  codex_stderr_max_bytes=1048576
  codex_stderr_pipe="$codex_artifacts/stderr.pipe"
  mkfifo "$codex_stderr_pipe" || exit 1
  head -c "$codex_stderr_max_bytes" <"$codex_stderr_pipe" \
    >"$codex_artifacts/stderr.log" &
  codex_stderr_limiter_pid=$!
  if python3 "$codex_skill_dir/scripts/run_with_timeout.py" 1800 codex exec \
    --sandbox read-only \
    --json \
    "Analyze this Claude Code skill repository comprehensively..." \
    2>"$codex_stderr_pipe" \
    | head -c "$codex_events_max_bytes" >"$codex_artifacts/events.jsonl"; then
    codex_status=0
  else
    codex_status=$?
  fi
  stderr_limiter_status=0
  wait "$codex_stderr_limiter_pid" || stderr_limiter_status=$?
  rm -- "$codex_stderr_pipe" || exit 1

  artifact_status=0
  events_bytes=$(wc -c <"$codex_artifacts/events.jsonl") || exit 1
  stderr_bytes=$(wc -c <"$codex_artifacts/stderr.log") || exit 1
  if [ "$events_bytes" -ge "$codex_events_max_bytes" ]; then
    printf 'Codex JSONL reached its %s-byte artifact limit\n' \
      "$codex_events_max_bytes" >&2
    artifact_status=125
  fi
  if [ "$stderr_bytes" -ge "$codex_stderr_max_bytes" ]; then
    printf 'Codex stderr reached its %s-byte artifact limit\n' \
      "$codex_stderr_max_bytes" >&2
    artifact_status=125
  fi
  if [ "$stderr_limiter_status" -ne 0 ]; then artifact_status=$stderr_limiter_status; fi

  extract_status=0
  jq -ner \
    'reduce inputs as $event (null; if ($event.type == "item.completed" and $event.item.type == "agent_message") then $event.item.text else . end) | select(type == "string" and length > 0) | .[0:4000]' \
    "$codex_artifacts/events.jsonl" || extract_status=$?
  jq -nce \
    'reduce inputs as $event (null; if $event.type == "turn.completed" then $event.usage else . end) | select(type == "object" and length > 0)' \
    "$codex_artifacts/events.jsonl" || extract_status=$?
  tail -c 4000 -- "$codex_artifacts/stderr.log" || extract_status=$?
  if [ "$codex_status" -eq 0 ] && [ "$artifact_status" -eq 0 ] && [ "$extract_status" -eq 0 ]; then
    rm -R -- "$codex_artifacts" || exit $?
  else
    printf 'Codex artifacts retained: %s\n' "$codex_artifacts" >&2
  fi
  if [ "$codex_status" -ne 0 ]; then exit "$codex_status"; fi
  if [ "$artifact_status" -ne 0 ]; then exit "$artifact_status"; fi
  exit "$extract_status"
)
```

Large homogeneous batches first run one calibration tranche. The workflow projects total calls and tokens from measured usage, asks for approval of the concrete budget when needed, and starts a fresh bounded session for each tranche instead of repeatedly resending accumulated history.

**Result:**
Claude will summarize the Codex analysis output, highlighting key suggestions and asking if you'd like to continue with follow-up actions.

### Detailed Instructions
See `SKILL.md` for complete operational instructions, CLI options, and workflow guidance.
