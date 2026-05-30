# Claude Arsenal Is Now Spellbook

Spellbook is the new name for Claude Arsenal.

The project started as a Claude Code skill library. It is now expanding into a cross-runtime skill library for Claude Code, Codex, and multi-agent workflows.

## What Changed

| Before | Now |
|--------|-----|
| `majiayu000/claude-arsenal` | `majiayu000/spellbook` |
| Claude Code-only positioning | Claude Code, Codex, and cross-runtime skills |
| `~/.claude/skills` install target | `--target claude`, `--target codex`, or `--target all` |

GitHub redirects the old repository URL to the new one, so existing links and stars are preserved.

## What Stayed The Same

- Claude Code remains a first-class runtime.
- Existing Claude Code skills and agents remain supported.
- Existing skill names and paths remain stable.
- The installer keeps a legacy fallback for the old repository URL during the transition.

## New Install Commands

```bash
# Install for Claude Code and Codex
curl -fsSL https://raw.githubusercontent.com/majiayu000/spellbook/main/install.sh | bash -s -- --target all

# Install for Claude Code only
curl -fsSL https://raw.githubusercontent.com/majiayu000/spellbook/main/install.sh | bash -s -- --target claude

# Install for Codex only
curl -fsSL https://raw.githubusercontent.com/majiayu000/spellbook/main/install.sh | bash -s -- --target codex
```

## Why The Name Changed

The old name, Claude Arsenal, was useful for discovery when the library was centered on Claude Code. The new name, Spellbook, keeps the skill-library metaphor while making room for reusable skills that can move across coding agents.

This is not a move away from Claude Code. It is a move toward skills as portable building blocks.
