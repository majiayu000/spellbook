# Installation Guide

## Prerequisites

- Claude Code CLI installed
- Git

## Installing Plugins

### Method 1: Via Plugin Marketplace (Recommended)

```bash
# Add the plugin as a marketplace source
/plugin marketplace add https://github.com/majiayu000/claude-arsenal/plugins/<plugin-name>

# Install the plugin
/plugin install <plugin-name>
```

### Method 2: Local Installation

```bash
# Clone the repository
git clone https://github.com/majiayu000/claude-arsenal.git

# Add local plugin as marketplace
/plugin marketplace add /path/to/claude-arsenal/plugins/<plugin-name>

# Install
/plugin install <plugin-name>
```

## Installing Individual Components

### Skills

For marketplace-style installation, use:

```bash
npx skills add majiayu000/claude-arsenal
```

For repository-local installation, prefer `install.sh --skills <skill-name>` because it supports both repository layouts:

- Directory skills: `skills/<skill-name>/SKILL.md`
- File skills: `skills/<skill-name>.SKILL.md`

Use the generated [Skill Registry](./skill-registry.md) to check a skill's `format` and source path.

#### Directory skill

```bash
# Copy the full skill directory so references/templates/scripts stay available
cp -R skills/<skill-name> ~/.claude/skills/<skill-name>
```

#### File skill

```bash
# Create skill directory (each skill needs its own subdirectory)
mkdir -p ~/.claude/skills/<skill-name>

# Download a file-based skill
curl -o ~/.claude/skills/<skill-name>/SKILL.md \
  https://raw.githubusercontent.com/majiayu000/claude-arsenal/main/skills/<skill-name>.SKILL.md
```

### Commands

```bash
# Create commands directory if not exists
mkdir -p ~/.claude/commands

# Download a command
curl -o ~/.claude/commands/<command-name>.md \
  https://raw.githubusercontent.com/majiayu000/claude-arsenal/main/commands/<command-name>.md
```

### Agents

```bash
# Create agents directory if not exists
mkdir -p ~/.claude/agents

# Download an agent
curl -o ~/.claude/agents/<agent-name>.md \
  https://raw.githubusercontent.com/majiayu000/claude-arsenal/main/agents/<agent-name>.md
```

### CLAUDE.md Templates

```bash
# Download to your project root
curl -o ./CLAUDE.md \
  https://raw.githubusercontent.com/majiayu000/claude-arsenal/main/claude-md/<template-name>.md
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
