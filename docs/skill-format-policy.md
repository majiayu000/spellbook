# Skill Format Policy

Claude Arsenal supports two installable skill layouts:

| Format | Path | Use for |
|---|---|---|
| Directory skill | `skills/<name>/SKILL.md` | Default for new skills, progressive disclosure, and any skill with support files. |
| File skill | `skills/<name>.SKILL.md` | Small, self-contained skills kept for compatibility and low-overhead authoring. |

The directory format is the canonical format for new work. Use it whenever a skill has or may soon need `references/`, `templates/`, `scripts/`, `agents/`, `assets/`, `evals/`, or other companion files. It is also the better choice when the main `SKILL.md` is large enough that detailed material should move behind progressive disclosure.

File skills remain valid when the full instruction is short and self-contained. Do not convert existing file skills only for cosmetic consistency; migrate them when they grow, need support files, or are already being edited for content structure.

## Installer Behavior

`install.sh` installs both layouts into Claude Code's expected runtime shape:

| Source | Installed as |
|---|---|
| `skills/<name>/SKILL.md` | `~/.claude/skills/<name>` symlinked to the source directory |
| `skills/<name>.SKILL.md` | `~/.claude/skills/<name>/SKILL.md` symlinked to the source file |

The install name is always `<name>`. A directory skill and file skill with the same install name are invalid.

## Registry Behavior

`scripts/validate_skills.py` discovers both layouts and records the layout in the generated registry `format` field:

- `directory` for `skills/<name>/SKILL.md`
- `file` for `skills/<name>.SKILL.md`

The frontmatter `name` must match the install name for both layouts.

## Migration

When a file skill needs progressive disclosure or support files, migrate it to the directory layout:

```bash
mkdir -p skills/<name>
git mv skills/<name>.SKILL.md skills/<name>/SKILL.md
python3 scripts/validate_skills.py --write
python3 scripts/validate_skills.py --check
bash -n install.sh
```

After migration, update any direct links that pointed to `skills/<name>.SKILL.md`.
