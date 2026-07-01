# Spellbook Agent Contract

Spellbook is a cross-runtime skill library, not a prompt dump. Keep this file
short: path-scoped `AGENTS.md` files carry directory-specific rules.

## Routing

- Search before creating a new skill, script, registry entry, or support file.
  Prefer `rg`, `rg --files`, and `python3 scripts/validate_skills.py search`.
- For skill authoring or refactors, read `docs/skill-format-policy.md`,
  `docs/skill-quality-playbook.md`, and
  `docs/spellbook-operating-contract.md` before editing.
- For generated registry or install metadata, change the source of truth and
  regenerate; do not hand-edit generated outputs.
- For high-context files such as `AGENTS.md`, `CLAUDE.md`, and skill
  `SKILL.md` files, keep changes intentional, scoped, and visible in the final
  summary.

## Scope Rules

- Do exactly the requested change. Do not add opportunistic migrations,
  rewrites, or broad cleanup.
- Prefer existing scripts, validators, parsers, and local conventions over new
  helper code.
- Do not invent metadata fields, registry fields, runtime targets, install
  behavior, or API surfaces. No data means blank or blocked.
- Do not silently swallow validation errors. Fix the root cause or report the
  blocker.
- Never commit secrets, tokens, private keys, or credential material.

## Threads Long-Run Guardrails

- Generic context-budget and output-firewall policy for Codex subagent
  orchestration belongs in `skills/threads/`; repository-specific queue policy
  belongs in the consumer workflow pack.
- For long queues or multi-lane runs, keep parent context thin: raw logs, broad
  searches, CI output, and session JSONL must go to artifacts or stay out of
  parent context.
- `threads` run-log schema, `SKILL.md`, and `references/run-log.md` must stay in
  sync when adding fields, failure codes, or lane contracts.
- Installed copies under `~/.agents/skills/threads` and `~/.spellbook/skills/threads`
  should be synced and hash-checked when local runtime behavior matters.

## Validation

- Skill, registry, install, or README count changes:
  `python3 scripts/validate_skills.py --check`.
- Material skill content changes:
  `python3 scripts/audit_skill_quality.py <skill-name>`.
- Registry regeneration:
  `python3 scripts/validate_skills.py --write` followed by
  `python3 scripts/validate_skills.py --check`.
- Python script changes: run targeted tests when present; otherwise run
  `python3 -m py_compile scripts/*.py` plus the relevant workflow command.
- If verification cannot run in the current environment, report the missing
  precondition and the exact command to run later.

## Generated Files

These files are generated or derived and should not be manually edited unless
the generator itself is being repaired:

- `registry/skills.json`
- `registry/tags.json`
- `docs/skill-registry.md`

## Decision Defaults

| Situation | Default |
|---|---|
| New installable skill | Use `skills/<name>/SKILL.md`. |
| Small existing file skill | Keep it as `skills/<name>.SKILL.md` unless it needs support files. |
| Long examples, templates, or references | Move them under the skill's support directories and link from `SKILL.md`. |
| Repeated manual command | Prefer adding or updating a script after the workflow is proven manually. |
| Destructive, remote production, publishing, billing, or credential action | Ask before acting unless the user already gave explicit approval. |

## VibeGuard Summary

- L1: Search first before creating anything new.
- L2: Use snake_case internally; preserve camelCase only at API boundaries.
- L3: Do not use `Any`-style public APIs or silent exception swallowing.
- L4: Do not invent undeclared data, fields, APIs, or fallback output.
- L5: Keep to the requested scope.
- L6: Route work as execute directly, plan first, or clarify first based on
  risk and missing inputs.
- L7: Do not submit keys, force-push, or hide high-context changes.
