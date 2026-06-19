---
name: codex-agent
description: Use when you want a second-opinion review via Codex CLI, cross-verification after another agent implements changes, debugging help, or alternative implementation proposals. Requires Codex CLI to be installed and authenticated.
compatibility: {runtimes: [claude_code]}
allowed-tools:
  - Bash(REPORT=*)
  - Bash(DIFF_REPORT=*)
  - Bash(codex:*)
  - Bash(mktemp:*)
  - Bash(cat:*)
  - Bash(git diff:*)
  - Read
  - Edit
  - Grep
  - Glob
---

# Codex Agent Collaboration Skill

This skill enables Claude Code to collaborate with OpenAI's Codex CLI agent for second-opinion review, cross-verification, debugging analysis, and alternative implementation proposals.

Default posture: Codex reviews in `read-only`; the primary agent applies changes only when the user asked for fixes or approved them after reading the review.

## Optional Codex Review Workflow

Use this workflow when the user asks for Codex review, wants a second opinion, or needs cross-verification from a separate coding agent.

### Step 1: Call Codex and Read Feedback

```bash
REPORT="$(mktemp -t codex-review.XXXXXX.md)"
codex exec -C <project_path> -s read-only -o "$REPORT" \
  "Review the code in <file_or_directory>. Check for:
   - Security vulnerabilities
   - Performance issues
   - Code quality and best practices
   - Potential bugs and edge cases
   - Naming and readability
   Provide specific, actionable feedback with file paths and line numbers."

cat "$REPORT"
```

Keep the write and read in the same Bash call, or pass a concrete report path
between calls; shell variables do not persist across tool calls.

### Step 2: Apply Fixes Based on Codex Feedback

When the user asked to apply fixes, handle each issue identified by Codex:
1. Read the relevant file
2. Apply the fix using Edit tool
3. Verify the fix addresses Codex's concern

If the user only asked for a review or second opinion, report findings without editing files.

### Step 3: Re-verify with Codex (Optional)

```bash
codex exec -C <project_path> -s read-only \
  "Verify the fixes applied to <files>. Confirm issues are resolved."
```

## Workflow Examples

### Example 1: Review and Fix a Single File

```bash
# Step 1: Get Codex review
REPORT="$(mktemp -t codex-review.XXXXXX.md)"
codex exec -C /project -s read-only -o "$REPORT" \
  "Review src/auth/login.ts for security vulnerabilities and code quality issues. Provide specific line numbers and fixes."

# Step 2: Read the feedback
cat "$REPORT"
```

Then the primary agent reads the feedback, applies fixes with Edit tool, and optionally re-verifies.

### Example 2: Review Recent Changes

```bash
# Get diff of recent changes
DIFF_REPORT="$(mktemp -t recent-changes.XXXXXX.diff)"
git diff HEAD~1 > "$DIFF_REPORT"

# Step 1: Have Codex review the diff
REPORT="$(mktemp -t codex-review.XXXXXX.md)"
codex exec -C /project -s read-only -o "$REPORT" \
  "Review the changes saved at $DIFF_REPORT. Check for bugs, security issues, and improvements needed."

# Step 2: Read and apply fixes
cat "$REPORT"
```

### Example 3: Full Project Review

```bash
# Step 1: Comprehensive review
REPORT="$(mktemp -t codex-review.XXXXXX.md)"
codex exec -C /project -s read-only -o "$REPORT" \
  "Perform a comprehensive code review of src/. Focus on:
   1. Security vulnerabilities (OWASP Top 10)
   2. Error handling patterns
   3. Performance bottlenecks
   4. Code duplication
   Prioritize issues by severity (critical/high/medium/low)."

# Step 2: Read prioritized feedback
cat "$REPORT"
```

## Review Request Format

When asking Codex for review, include:

```
Review <target_files_or_directory>.

Context:
- Project type: <TypeScript/Python/etc>
- Framework: <Express/React/etc>
- Focus areas: <security/performance/quality>

Check for:
1. Security vulnerabilities
2. Performance issues
3. Error handling
4. Code quality
5. Edge cases

Output format:
For each issue:
- File: <path>
- Line: <number>
- Severity: critical/high/medium/low
- Issue: <description>
- Fix: <specific code change>
```

## Applying Fixes

After receiving Codex feedback, apply fixes systematically:

1. **Parse the review** - Extract each issue with file, line, severity
2. **Prioritize** - Fix critical/high issues first
3. **Read file** - Use Read tool to see current code
4. **Apply fix** - Use Edit tool with precise old_string/new_string
5. **Track progress** - Mark each issue as fixed

## Prerequisites

Codex CLI must be installed and authenticated:

```bash
# Install via npm
npm install -g @openai/codex

# Or via Homebrew (macOS)
brew install --cask codex

# Authenticate
codex login
```

## Command Reference

### Basic Command Pattern

```bash
codex exec [options] "<task_description>"
```

### Core Options

| Option | Description |
|--------|-------------|
| `"<task>"` | Task description (positional, must be quoted) |
| `-C <dir>` | Working directory (use absolute path) |
| `-s read-only` | Read-only sandbox (use for reviews) |
| `-o <path>` | Save output to file |
| `--json` | Output as JSON Lines |

### AI-to-AI Communication

When communicating with Codex, PRIORITIZE ACCURACY AND PRECISION:
- Use structured data and exact technical terms
- Provide full file paths and precise details
- Include relevant context from the current codebase
- NO conversational formatting needed

## Other Use Cases

### Cross-Verification (after Claude implements)

```bash
codex exec -C /project -s read-only \
  "Verify the implementation in src/feature/. Check correctness and edge cases."
```

### Get Alternative Implementation

```bash
REPORT="$(mktemp -t codex-alternative.XXXXXX.md)"
codex exec -C /project -s read-only -o "$REPORT" \
  "Propose an alternative implementation for the caching in src/cache/manager.ts"
cat "$REPORT"
```

### Debugging Assistance

```bash
codex exec -C /project -s read-only \
  "Debug: tests in tests/auth.test.ts failing with timeout. Analyze root cause."
```

## Session Management

For multi-turn reviews:

```bash
# Initial review
codex exec -C /project -s read-only "Review src/api/ for security issues"
# Note session ID from output

# Follow-up after fixes
codex exec resume <session_id> "I've applied the fixes. Please re-verify."
```

## Helper Scripts

- `scripts/check-codex.sh` checks whether the Codex CLI is installed and authenticated.
- `scripts/codex-wrapper.sh` is optional. Use it only when you need a small CLI wrapper; it executes Codex through shell arrays and must not use `eval`.

## Gotchas

- Do not write reviews to fixed paths such as `/tmp/codex-review.md`; use `mktemp` or a project-specific private report path so concurrent projects cannot overwrite or read stale feedback.
- Keep Codex review commands in `read-only` unless the user explicitly asked Codex itself to edit.
- Treat `danger-full-access`, `--dangerously-bypass-approvals-and-sandbox`, `--dangerously-bypass-hook-trust`, and `--skip-git-repo-check` as high-impact flags. Ask before using them.
- Do not blindly apply every Codex suggestion. Re-read the target file, confirm the root cause, and verify the final behavior.

## Troubleshooting

### Authentication Issues

```bash
codex logout
codex login
```

### Check Installation

```bash
codex --version
which codex
```

## See Also

- [scripts/check-codex.sh](scripts/check-codex.sh) - Local Codex CLI availability check
- [scripts/codex-wrapper.sh](scripts/codex-wrapper.sh) - Wrapper for repeatable Codex CLI invocation
- [sandbox-modes.md](sandbox-modes.md) - Sandbox security levels
- [examples.md](examples.md) - More usage examples
- [advanced.md](advanced.md) - Advanced configuration
