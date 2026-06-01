# Skill Format Policy

Spellbook supports two installable skill layouts:

| Format | Path | Use for |
|---|---|---|
| Directory skill | `skills/<name>/SKILL.md` | Default for new skills, progressive disclosure, and skills with support files. |
| File skill | `skills/<name>.SKILL.md` | Small, self-contained skills kept for compatibility and low-overhead authoring. |

The directory format is canonical for new work. Use it whenever a skill has or may soon need `references/`, `templates/`, `scripts/`, `agents/`, `assets/`, `evals/`, or other companion files.

File skills remain valid when the full instruction is short and self-contained. Do not convert existing file skills only for cosmetic consistency; migrate them when they grow, need support files, or are already being edited for content structure.

## Installer Behavior

`install.sh` installs both layouts into each selected runtime target:

| Source | Installed as |
|---|---|
| `skills/<name>/SKILL.md` | `<runtime-skills-dir>/<name>` symlinked to the source directory |
| `skills/<name>.SKILL.md` | `<runtime-skills-dir>/<name>/SKILL.md` symlinked to the source file |

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
