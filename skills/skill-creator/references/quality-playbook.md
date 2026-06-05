# Skill Quality Playbook

Use this reference when creating or materially improving a skill. Keep the main
`SKILL.md` short; put large reference tables, scripts, templates, and examples
behind progressive disclosure.

## Pick One Primary Type

Choose the skill's main job before writing:

- Library/API reference: how to use a library, CLI, SDK, or internal platform.
- Product verification: scripts or tool flows that prove product behavior.
- Data fetching/analysis: canonical queries, dashboards, metric names, helpers.
- Business process automation: repeatable team workflow with required state.
- Code scaffolding/templates: boilerplate plus natural-language requirements.
- Code quality/review: deterministic style, review, testing, or policy checks.
- CI/CD/deployment: build, smoke test, deploy, monitor, rollback, PR babysitting.
- Runbook: symptom-driven investigation that returns a structured report.
- Infrastructure operations: guarded maintenance, especially risky actions.

If a draft has two or three primary types, split it or make `SKILL.md` a router
that points to narrower references.

## High-Signal Sections

- **Description**: Write for triggering, not summary. Include when to use the
  skill, user phrasing, symptoms, and near-boundary cases.
- **Gotchas**: Add observed failure modes, naming mismatches, false-success
  signals, risky defaults, and recovery checks.
- **Verification**: For objective workflows, include scripts, assertions, smoke
  tests, browser checks, health checks, or explicit done-when proof.
- **Support files**: Use `references/`, `scripts/`, `assets/`, `templates/`, and
  `evals/` when detail would otherwise bloat `SKILL.md`.
- **Setup**: If the skill needs user or environment context, describe a config
  file or setup flow instead of asking repeatedly.
- **Memory**: Repeated workflows can keep append-only logs, JSON, or SQLite state
  when previous runs change the next run.
- **Hooks**: Use on-demand hooks only for temporary guardrails that would be too
  annoying to run globally.

## Authoring Checks

Before calling a skill good, ask:

1. Would the model know to trigger this from the `description` alone?
2. Does the skill teach something non-obvious or repo/org-specific?
3. Are the common failure modes captured as gotchas?
4. Does `SKILL.md` point clearly to every support directory it expects to use?
5. Is there a concrete verification path for objective work?
6. Are risky or destructive actions guarded by confirmation or checks?

Run the repository-level audit when available:

```bash
python3 scripts/audit_skill_quality.py <skill-name>
```
