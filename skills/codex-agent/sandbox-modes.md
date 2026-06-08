# Sandbox Modes

Codex CLI provides three sandbox security levels to control file system access.

## Mode Comparison

| Mode | Flag | File Writes | Use Case |
|------|------|-------------|----------|
| **Read-Only** | `-s read-only` | None | Code analysis, review, Q&A |
| **Workspace Write** | `-s workspace-write` | Workspace + /tmp | Safe file modifications |
| **Full Access** | `-s danger-full-access` | Unrestricted | Last resort after explicit approval |

## Read-Only Mode (Default)

```bash
codex exec -s read-only -C /project "Analyze code quality"
```

- Cannot create, modify, or delete files
- Safe for analysis and review tasks
- Recommended for most read operations

## Workspace Write Mode

```bash
codex exec -s workspace-write -C /project "Refactor the auth module"
```

- Write access limited to:
  - Current workspace directory
  - `/tmp` directory
- Cannot modify files outside workspace
- Recommended for safe code modifications

## Full Access Mode

```bash
codex exec -s danger-full-access -C /project "Update system config"
```

**Use with extreme caution:**
- Unrestricted file system access
- Can modify any file on the system
- Only use in isolated/sandboxed environments (VMs, containers)
- Requires explicit user approval for the exact command and target boundary

## Full Auto Mode

```bash
codex exec -s workspace-write --full-auto -C /project "Implement feature X"
```

Combines:
- `workspace-write` sandbox
- Automatic approval for actions (no prompts)
- Requires explicit user approval before use

## Approval Modes

Control when human approval is required:

| Flag | Behavior |
|------|----------|
| `-a untrusted` | Approve everything (most restrictive) |
| `-a on-failure` | Approve after failures |
| `-a on-request` | Approve when requested |
| `-a never` | Never require approval |

## Best Practices

1. **Start with read-only** - Default to analysis mode
2. **Use workspace-write for edits** - Contains changes to project
3. **Avoid full-access** - Only in truly isolated environments
4. **Review before commit** - Always verify Codex's changes
5. **Use `--add-dir`** - Grant specific directory access instead of full-access

```bash
# Better than danger-full-access:
codex exec --add-dir /path/to/other/dir -C /project "task"
```
