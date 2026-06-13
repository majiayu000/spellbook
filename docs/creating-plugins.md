# Creating Plugins Guide

## Plugin Structure

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json      # Required: Plugin manifest
├── skills/              # Optional: plugin skill files
├── commands/            # Legacy/optional: Slash commands when the target runtime supports them
├── agents/              # Optional: Agent definitions
└── hooks/               # Optional: Hook configurations
```

## plugin.json Format

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "What this plugin does",
  "author": {
    "name": "Your Name",
    "url": "https://github.com/username"
  },
  "repository": "https://github.com/username/repo",
  "license": "MIT",
  "keywords": ["keyword1", "keyword2"]
}
```

### Required Fields

| Field | Description |
|-------|-------------|
| `name` | Unique identifier, kebab-case |

### Optional Fields

| Field | Description |
|-------|-------------|
| `version` | Semantic version (e.g., 1.0.0) |
| `description` | Brief description |
| `author` | Author info (name, email, url) |
| `repository` | Source code URL |
| `license` | License type |
| `keywords` | Search keywords |

## Creating Skills

Plugin packages in this repository currently use file skills under `skills/*.SKILL.md`.
Use this layout for plugin marketplace compatibility unless the plugin runtime you target documents directory skill support.

For the top-level Spellbook catalog installed by `install.sh`, see [Skill Format Policy](./skill-format-policy.md). New catalog skills should generally use the directory layout when they need progressive disclosure, templates, scripts, evals, or other companion files.

Plugin skill files use this frontmatter:

```markdown
---
name: skill-name
description: When to use this skill (max 1024 chars)
allowed-tools: Read, Grep, Glob, Edit
---

# Skill Title

## Instructions

What Claude should do when this skill is activated...

## Examples

- Example trigger: "Do X"
- Example trigger: "Help me with Y"
```

## Creating Commands

Prefer skills for new reusable behavior. Add `*.md` files in the `commands/`
directory only when the target plugin runtime explicitly supports slash command
packaging and a command shortcut is still the right UX:

```markdown
---
description: What this command does
---

# Command Name

Instructions for Claude when this command is invoked...
```

## Creating Agents

Place `*.md` files in the `agents/` directory:

```markdown
---
name: agent-name
description: Agent specialization
tools: ["Read", "Grep", "Glob"]
---

# Agent Title

Agent behavior and instructions...
```

## Testing Locally

```bash
# Add your plugin as a local marketplace
/plugin marketplace add /path/to/my-plugin

# Install it
/plugin install my-plugin

# Test functionality
# ...

# Uninstall when done testing
/plugin uninstall my-plugin
```

## Publishing

1. Push to GitHub
2. Share the installation command:
   ```
   /plugin marketplace add https://github.com/username/repo
   /plugin install my-plugin
   ```
