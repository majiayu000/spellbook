# Installation Guide

## Prerequisites

- Claude Code CLI and/or Codex installed
- Git

## One Command Install

```bash
# Install skills for both Claude Code and Codex
curl -fsSL https://raw.githubusercontent.com/majiayu000/spellbook/main/install.sh | bash -s -- --target all

# Install only for Claude Code
curl -fsSL https://raw.githubusercontent.com/majiayu000/spellbook/main/install.sh | bash -s -- --target claude

# Install only for Codex
curl -fsSL https://raw.githubusercontent.com/majiayu000/spellbook/main/install.sh | bash -s -- --target codex
```

Target paths:

| Target | Skills | Agents |
|--------|--------|--------|
| Claude Code | `~/.claude/skills` | `~/.claude/agents` |
| Codex | `~/.codex/skills` | Not supported by this installer |

## Installing Plugins

Plugins are currently Claude Code-specific because they use the `.claude-plugin` manifest format.

### Method 1: Via Plugin Marketplace (Recommended)

```bash
# Add the plugin as a marketplace source
/plugin marketplace add https://github.com/majiayu000/spellbook/plugins/<plugin-name>

# Install the plugin
/plugin install <plugin-name>
```

### Method 2: Local Installation

```bash
# Clone the repository
git clone https://github.com/majiayu000/spellbook.git

# Add local plugin as marketplace
/plugin marketplace add /path/to/spellbook/plugins/<plugin-name>

# Install
/plugin install <plugin-name>
```

## Installing Individual Components

### Skills

For repository-local installation, prefer `install.sh --skills <skill-name>` because it supports both source layouts and both runtime targets:

- Directory skills: `skills/<skill-name>/SKILL.md`
- File skills: `skills/<skill-name>.SKILL.md`

Use the generated [Skill Registry](./skill-registry.md) to check a skill's `format` and source path.

#### Directory skill

```bash
# Claude Code
cp -R skills/<skill-name> ~/.claude/skills/<skill-name>

# Codex
cp -R skills/<skill-name> ~/.codex/skills/<skill-name>
```

#### File skill

```bash
# Claude Code: create skill directory (each skill needs its own subdirectory)
mkdir -p ~/.claude/skills/<skill-name>

# Claude Code: download a skill
curl -o ~/.claude/skills/<skill-name>/SKILL.md \
  https://raw.githubusercontent.com/majiayu000/spellbook/main/skills/<skill-name>.SKILL.md

# Codex: create skill directory and download the same source
mkdir -p ~/.codex/skills/<skill-name>
curl -o ~/.codex/skills/<skill-name>/SKILL.md \
  https://raw.githubusercontent.com/majiayu000/spellbook/main/skills/<skill-name>.SKILL.md
```

### Commands

```bash
# Create commands directory if not exists
mkdir -p ~/.claude/commands

# Download a command
curl -o ~/.claude/commands/<command-name>.md \
  https://raw.githubusercontent.com/majiayu000/spellbook/main/commands/<command-name>.md
```

### Agents

```bash
# Create agents directory if not exists
mkdir -p ~/.claude/agents

# Download an agent
curl -o ~/.claude/agents/<agent-name>.md \
  https://raw.githubusercontent.com/majiayu000/spellbook/main/agents/<agent-name>.md
```

### CLAUDE.md Templates

```bash
# Download to your project root
curl -o ./CLAUDE.md \
  https://raw.githubusercontent.com/majiayu000/spellbook/main/claude-md/<template-name>.md
```

## Verification

After installation, verify components are loaded:

```bash
# Check installed plugins
/plugin list

# Check available commands
/help

# Ask Claude about available skills
"What skills do you have available?"

# Codex
# Restart Codex so it reloads ~/.codex/skills.
```

## Uninstallation

```bash
# Uninstall a plugin
/plugin uninstall <plugin-name>

# Remove a skill
rm -rf ~/.claude/skills/<skill-name>

# Remove a command
rm ~/.claude/commands/<command-name>.md
```
