# Scoped AGENTS.md Scaffold Guide

Use this reference when the user asks to generate or update `AGENTS.md` files
from repository evidence.

## Principle

Generate the smallest instruction stack that changes agent behavior. A useful
`AGENTS.md` file routes work, names real commands, defines high-risk boundaries,
and points to deeper context. It should not repeat README marketing copy,
general coding advice, or every architecture detail.

## Discovery Inputs

Collect these before writing:

- Existing high-context files: `AGENTS.md`, `CLAUDE.md`, `WARP.md`,
  `.claude/instructions.md`, `.github/copilot-instructions.md`
- Repo commands from manifests, CI workflows, Makefiles, package scripts, or
  documented developer setup
- Generated files and their source-of-truth generators
- High-risk areas: migrations, auth, payments, secrets, deployment, production
  scripts, generated clients, lockfiles, registry metadata
- Directory-specific conventions that differ from root rules

The scanner can provide a first pass:

```bash
python3 scripts/scan_repo_context.py <repo-root>
python3 scripts/scan_repo_context.py <repo-root> --json
```

Treat scanner output as evidence, not authority. Inspect important files before
writing.

## Candidate Selection

| Repo evidence | Scaffold decision |
|---|---|
| No short top-level router and no coherent equivalent | Add root `AGENTS.md`. |
| Good `CLAUDE.md` or `WARP.md` already exists | Add a short `AGENTS.md` pointer only if cross-runtime routing is useful. |
| One huge top-level instruction file | Propose splitting into root router plus references or scoped files. |
| Directory has generated files and a clear generator | Add scoped `AGENTS.md` naming source of truth and validation. |
| Directory has distinct safety or workflow rules | Add scoped `AGENTS.md`. |
| Directory only contains ordinary implementation files | Keep rules in root unless conventions truly differ. |
| Several packages have identical rules | Prefer one parent scoped file over repeated child files. |
| Small repo with clear README and tests | Avoid ceremony; maybe add only root commands. |

## Root AGENTS.md Shape

Root should normally include:

- Scope and precedence
- Start-here steps
- Exact build, typecheck, test, lint, and format commands when discoverable
- When to plan first, spec first, or ask
- Generated-file boundaries
- High-risk rules such as auth, migrations, secrets, deploys, and UI
  verification
- Pointers to nested `AGENTS.md`, local skills, specs, or docs

Avoid:

- long architecture tours
- duplicated README content
- vague rules without concrete alternatives
- commands that were guessed without evidence

## Scoped AGENTS.md Shape

Each nested file should answer:

1. What this directory owns.
2. What to inspect before editing.
3. What not to change directly.
4. Which local helper, generator, or existing pattern to use instead.
5. Which command proves this directory's changes.

Keep nested files shorter than root when possible. If a scoped file needs long
examples or policy tables, move those into references or existing docs and point
to them.

## Common Scoped Templates

### Scripts or Tools

```markdown
# Scripts Contract

Scripts in this directory are operational entry points. Preserve existing CLI
interfaces unless the user asks for a breaking change.

## Before Editing

- Search for existing parsers, validators, and callers.
- Inspect tests and CI references for the changed command.

## Rules

- Do not silently swallow errors.
- Keep generated output deterministic.
- Do not hardcode secrets or local-only absolute paths.

## Validation

- `<syntax check>`
- `<targeted script command>`
```

### Generated Metadata

````markdown
# Generated Metadata Contract

This directory contains generated or derived files. Change the source of truth
and regenerate instead of editing outputs directly.

## Sources Of Truth

| Need | Edit |
|---|---|
| <derived field> | `<source path>` |
| <render behavior> | `<generator path>` |

## Validation

```bash
<regenerate command>
<check command>
```
````

### Skill Library

```markdown
# Skills Contract

This directory contains installable skills. Search for an existing skill before
creating a new one.

## Layout

| Case | Layout |
|---|---|
| New skill | `<skill-dir>/SKILL.md` |
| Small self-contained skill | `<name>.SKILL.md` may remain if supported |

## Rules

- Keep `SKILL.md` as the router.
- Put long references, scripts, templates, assets, or evals in support dirs.
- Frontmatter names must match install names.

## Validation

- `<registry check>`
- `<quality audit>`
```

### Tests

```markdown
# Tests Contract

Tests in this directory should prove behavior, not implementation trivia.

## Rules

- Prefer regression tests for fixed bugs.
- Use existing fixtures and helpers before adding new ones.
- Do not weaken assertions to make production bugs pass.

## Validation

- `<focused test command>`
- `<full test command when required>`
```

## Output Format Before Editing

When proposing a scaffold, report:

```markdown
## Scoped AGENTS Plan

| Path | Why here | Rules to include | Validation |
|---|---|---|---|
| `AGENTS.md` | <evidence> | <root routing topics> | `<command>` |
| `<dir>/AGENTS.md` | <evidence> | <directory-specific topics> | `<command>` |

## Files To Preserve

- `<existing high-context file>` - <how it will be referenced or left alone>

## Open Facts

- <only list missing commands or ownership facts that cannot be inferred>
```

Only write files after the user approves the plan or explicitly asks to apply
the scaffold.
