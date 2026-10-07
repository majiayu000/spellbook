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

Cleanup and uninstall remove only links to the managed checkout. A file skill's
wrapper directory is removed only when empty; notes, resources, and other user
files alongside `SKILL.md` are preserved. If those files prevent a directory
layout replacement, the installer reports the remaining path and skips that
skill. Existing unmanaged files, directories, and symlinks are also reported as
conflicts and are not counted as installed skills.

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

## Runtime Compatibility

The [Agent Skills specification](https://agentskills.io/specification) reserves
`compatibility` for environment-requirement text (1–500 characters). Spellbook
keeps its machine-readable runtime filter in the string-valued metadata extension
`spellbook-runtimes`:

```yaml
compatibility: Requires Codex with native subagent support.
metadata:
  spellbook-runtimes: "codex"
```

Use space-separated IDs from `claude_code`, `codex`, and `portable`. Unknown,
duplicate, empty, or `unspecified` declarations are errors. Human-readable
`compatibility` text alone is never interpreted as a runtime filter. Omitted
runtime metadata remains `unspecified`, permits existing installation behavior,
and is not a portability guarantee.

Legacy `compatibility: {runtimes: [codex]}` mappings remain readable by Spellbook
for existing custom skills, but do not conform to the public string-field
contract. Migrate those mappings to the example above before distributing them
to standard consumers. Do not declare both forms together. The registry's
existing `compatibility.runtimes` JSON object, ordering, search output, and runtime
filtering stay unchanged; the registry is not SKILL.md frontmatter.

Frontmatter parsing requires PyYAML; missing PyYAML is a validation error.
CI installs this dependency before validation. Standard conformance is a format check,
not proof that every host loads or executes a skill successfully.
