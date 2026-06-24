# Skills Directory Contract

This directory contains installable Spellbook skills. A skill should help an
agent decide when to act, how to act, when to escalate, and how to verify the
result.

## Before Editing

1. Search for an existing skill first:
   `python3 scripts/validate_skills.py search <topic>` and `rg <topic> skills`.
2. Read the relevant policy files:
   `docs/skill-format-policy.md`, `docs/skill-quality-playbook.md`, and
   `docs/spellbook-operating-contract.md`.
3. Inspect nearby skills with the same category or runtime target before adding
   new conventions.

## Layout

| Case | Layout |
|---|---|
| New skill | `skills/<name>/SKILL.md` |
| Existing tiny self-contained skill | `skills/<name>.SKILL.md` may remain |
| Skill with scripts, references, templates, assets, agents, or evals | Directory skill |

- Do not convert file skills to directory skills only for cosmetic consistency.
- When migrating a file skill because it needs support files, use `git mv` and
  update direct links.
- Frontmatter `name` must match the install name.
- Allowed frontmatter keys are defined by `scripts/validate_skills.py`; do not
  add new keys unless the validator and registry behavior are updated together.

## Skill Content

- Make `SKILL.md` the router, not the whole knowledge base.
- Put long examples, API tables, prompts, templates, assets, and extended
  guidance in support directories and load them only when relevant.
- Every mature workflow skill should include trigger boundaries, gotchas,
  autonomy boundaries, and done-when checks.
- Pair prohibitions with concrete alternatives: name the helper, script,
  reference file, or canonical path to use instead.
- Do not add tests for statically defined values or removed behavior.

## Validation

- After adding or materially changing a skill, run:
  `python3 scripts/validate_skills.py --check`.
- For content-quality changes, also run:
  `python3 scripts/audit_skill_quality.py <skill-name>`.
- If registry output is stale, run:
  `python3 scripts/validate_skills.py --write` and then rerun `--check`.
