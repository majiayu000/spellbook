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
  command -v jq >/dev/null 2>&1 || exit 1
  codex_skill_dir=${CODEX_SKILL_DIR:?set CODEX_SKILL_DIR to the installed codex skill}
  codex_artifacts=$(mktemp -d) || exit 1
  if python3 "$codex_skill_dir/scripts/run_with_timeout.py" 1800 codex exec \
    --config model_reasoning_effort="high" \
    --sandbox read-only \
    --json \
    "Analyze this Claude Code skill repository comprehensively..." \
    >"$codex_artifacts/events.jsonl" \
    2>"$codex_artifacts/stderr.log"; then
    codex_status=0
  else
    codex_status=$?
  fi

  extract_status=0
  jq -ser \
    '[.[] | select(.type == "item.completed" and .item.type == "agent_message") | .item.text] | last | select(type == "string" and length > 0) | .[0:4000]' \
    "$codex_artifacts/events.jsonl" || extract_status=$?
  jq -cse \
    '[.[] | select(.type == "turn.completed") | .usage] | last | select(type == "object" and length > 0)' \
    "$codex_artifacts/events.jsonl" || extract_status=$?
  tail -n 20 -- "$codex_artifacts/stderr.log" || extract_status=$?
  if [ "$codex_status" -eq 0 ] && [ "$extract_status" -eq 0 ]; then
    rm -R -- "$codex_artifacts" || exit $?
  else
    printf 'Codex artifacts retained: %s\n' "$codex_artifacts" >&2
  fi
  if [ "$codex_status" -ne 0 ]; then exit "$codex_status"; fi
  exit "$extract_status"
)
```

Large homogeneous batches first run one calibration tranche. The workflow projects total calls and tokens from measured usage, asks for approval of the concrete budget when needed, and starts a fresh bounded session for each tranche instead of repeatedly resending accumulated history.

**Result:**
Claude will summarize the Codex analysis output, highlighting key suggestions and asking if you'd like to continue with follow-up actions.

### Detailed Instructions
See `SKILL.md` for complete operational instructions, CLI options, and workflow guidance.
