# Codex Agent Skill

A Spellbook skill for optional Codex-based second-opinion reviews, cross-verification, debugging, and alternative implementation proposals.

## Core Workflow

```
Code Review Request
       ↓
   ┌───────────────────┐
   │  Codex Reviews    │  ← Primary agent calls Codex CLI
   │  (read-only)      │
   └───────────────────┘
       ↓
   ┌───────────────────┐
   │  Codex Feedback   │  ← Issues with file:line:severity
   └───────────────────┘
       ↓
   ┌───────────────────┐
   │  Primary Agent    │  ← Primary agent fixes code using Edit tool
   │  Fixes            │
   └───────────────────┘
       ↓
   ┌───────────────────┐
   │  (Optional)       │  ← Codex re-verifies
   │  Re-verify        │
   └───────────────────┘
```

## Features

- **Second-Opinion Review**: Use Codex when you want an independent review pass
- **Guided Fixes**: Apply fixes based on Codex's specific feedback
- **Structured Output**: Codex provides file paths, line numbers, and severity levels
- **Re-verification**: Optional second pass to confirm fixes

## Prerequisites

### Install Codex CLI

```bash
# Via npm
npm install -g @openai/codex

# Via Homebrew (macOS)
brew install --cask codex
```

### Authenticate

```bash
codex login
```

## Installation

### Option 1: User-level (all projects)

```bash
cp -r codex-agent ~/.claude/skills/codex-agent
cp -r codex-agent ~/.agents/skills/codex-agent
```

### Option 2: Project-level

```bash
mkdir -p .claude/skills
cp -r codex-agent .claude/skills/codex-agent

mkdir -p .agents/skills
cp -r codex-agent .agents/skills/codex-agent
```

## Usage

When you ask for a Codex second opinion, the primary agent will:

1. **Call Codex** to perform the review
2. **Parse feedback** from Codex (file, line, severity, issue, fix)
3. **Apply fixes** using Edit tool only when the user asked for fixes
4. **Optionally re-verify** with Codex

### Example Prompts

```
Review my authentication code and fix any issues
```

```
Do a security review of src/api/ and apply the fixes
```

```
Review the recent changes and fix problems Codex finds
```

## Workflow Details

### Step 1: Codex Review

The primary agent executes:
```bash
REPORT="$(mktemp -t codex-review.XXXXXX.md)"
codex exec -C /project -s read-only -o "$REPORT" \
  "Review src/auth/. Check for security, performance, code quality.
   Provide file paths, line numbers, and specific fixes."
cat "$REPORT"
```

### Step 2: Parse Feedback

Codex outputs structured feedback:
```
- File: src/auth/login.ts
- Line: 45
- Severity: high
- Issue: SQL injection vulnerability
- Fix: Use parameterized query instead of string concatenation
```

### Step 3: Primary Agent Applies Fixes

The primary agent reads the file, applies the fix with Edit tool:
```
old_string: `SELECT * FROM users WHERE id = '${userId}'`
new_string: `SELECT * FROM users WHERE id = $1`, [userId]
```

### Step 4: Re-verify (Optional)

```bash
codex exec -C /project -s read-only \
  "Verify fixes in src/auth/login.ts. Confirm SQL injection is resolved."
```

## File Structure

```
codex-agent/
├── SKILL.md           # Main skill with optional Codex review workflow
├── sandbox-modes.md   # Sandbox security documentation
├── examples.md        # Usage examples
├── advanced.md        # Advanced configuration
├── scripts/
│   ├── codex-wrapper.sh   # Helper wrapper script
│   └── check-codex.sh     # Installation checker
└── README.md          # This file
```

## Configuration

### Recommended Permissions

Add to `.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(REPORT=*)",
      "Bash(DIFF_REPORT=*)",
      "Bash(codex:*)",
      "Bash(mktemp:*)",
      "Bash(cat:*)"
    ]
  }
}
```

## Sandbox Modes

| Mode | Description |
|------|-------------|
| `read-only` | No file writes (used for reviews) |
| `workspace-write` | Write to project directory |
| `danger-full-access` | Unrestricted (use with caution) |

Use `read-only` for review and re-verification by default. Treat
`danger-full-access`, `--dangerously-bypass-approvals-and-sandbox`,
`--dangerously-bypass-hook-trust`, and `--skip-git-repo-check` as high-impact
options that need explicit user approval.

## Troubleshooting

### Codex not found

```bash
npm install -g @openai/codex
```

### Authentication issues

```bash
codex logout
codex login
```

## License

MIT

## References

- [OpenAI Codex CLI](https://github.com/openai/codex)
- [Claude Code Skills](https://code.claude.com/docs/en/skills)
- [Codex Documentation](https://developers.openai.com/codex)
