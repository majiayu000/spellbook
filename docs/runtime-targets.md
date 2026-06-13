# Runtime Targets

Spellbook is a source library for reusable agent skills. The same skill source can be installed into different coding-agent runtimes.

## Supported Targets

| Target | Skills | Agents | Notes |
|--------|--------|--------|-------|
| Claude Code | `~/.claude/skills` | `~/.claude/agents` | Full existing support, including Claude Code plugins |
| Codex | `~/.agents/skills` | Not installed | Skills are installed as `SKILL.md`; restart Codex after install |

Older Spellbook releases installed Codex skills under `~/.codex/skills`. New
installs use the current Codex user-level skill path, `$HOME/.agents/skills`.

## Install Examples

```bash
# Install everything for Claude Code and Codex
./install.sh --target all --all

# Install selected skills into Codex only
./install.sh --target codex --skills rust-project,codebase-audit

# Keep the legacy Claude-only behavior
./install.sh --target claude --all
```

## Migration Note

Spellbook was formerly Claude Arsenal. Claude Code remains a first-class target, but new work should avoid assuming a skill belongs to only one runtime unless the skill explicitly depends on runtime-specific tools, directories, or commands.

Runtime-specific adapters should live at the installer or packaging layer. The skill body should stay portable whenever that is practical.
