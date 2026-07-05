# Skill Quality Playbook

This playbook captures practical quality rules for Spellbook skills. It is
intended to complement [Skill Format Policy](./skill-format-policy.md): format
policy says where files live, while this playbook says what makes a skill useful
after the model discovers it.

Source context: Anthropic's June 2026 post, "Lessons from building Claude Code:
How we use skills", describes skills as folders of instructions, scripts, and
resources, not just markdown files. It also highlights trigger descriptions,
gotchas, progressive disclosure, verification scripts, setup state, persistent
memory, hooks, distribution, composition, and usage measurement.

## Skill Types

Pick one primary type before writing or expanding a skill. Skills that straddle
several types tend to confuse the model.

| Type | Best use |
|---|---|
| Library and API reference | Correct use of a library, CLI, SDK, internal platform, or common footguns. |
| Product verification | Browser, CLI, tmux, API, or state checks that prove the product works. |
| Data fetching and analysis | Canonical queries, dashboards, metric names, and analysis helpers. |
| Business process automation | Repeatable team workflow with required fields, previous-state logs, or handoffs. |
| Code scaffolding and templates | Boilerplate where natural-language requirements still matter. |
| Code quality and review | Deterministic style, review, testing, or policy checks. |
| CI/CD and deployment | Build, smoke test, deploy, monitor, rollback, or PR babysitting. |
| Runbooks | Symptom-driven investigation across tools that returns a structured report. |
| Infrastructure operations | Guarded maintenance workflows, especially destructive or costly operations. |

## Quality Bar

Every new or materially changed skill should satisfy these checks:

- **Trigger description**: `description` is written for the model, not humans. It
  says when to use the skill, includes user phrasing or symptoms, and names near
  boundaries when mis-triggering is likely.
- **Non-obvious value**: `SKILL.md` should not restate what the model can infer
  by reading the repo or general documentation. Put scarce knowledge first.
- **Gotchas**: Mature skills include real failure modes, naming mismatches,
  false-success signals, risky defaults, or common recovery paths.
- **Progressive disclosure**: Keep `SKILL.md` as the router. Move detailed API
  tables, long examples, templates, scripts, evals, and assets into support
  directories and reference them from `SKILL.md`.
- **Verification**: Workflow skills should include checks that prove completion:
  scripts, assertions, smoke tests, browser checks, health checks, or explicit
  done-when signals.
- **Autonomy boundary**: Skills that can touch user files, remote services,
  credentials, billing, publishing, or production state should say which actions
  can be performed directly and which require escalation.
- **Evidence-backed pushback**: Skills should tell the agent when to challenge a
  proposed path, but only with concrete evidence, a named risk, or a smaller
  alternative.
- **Feedback loop**: Repeated corrections, false-success signals, or manual
  recovery steps should be promoted into gotchas, scripts, evals, references, or
  done-when checks instead of staying as session-only memory.
- **Setup state**: Skills that need user or environment context should define a
  config file or setup flow instead of asking repeatedly.
- **Memory**: Repeated business workflows may store append-only logs, JSON, or a
  small database in the plugin data directory when history changes the next run.
- **Hooks**: Use on-demand hooks only for cases where temporary guardrails are
  valuable, such as production operations or frozen edit scopes.

## Reliable Skill Contract

High-value workflow skills should pass the `skill-lifeguard` contract before
they are treated as mature:

| Element | What To Look For |
|---|---|
| Explicit negative examples | Forbidden behaviors paired with safer alternatives. |
| Verification checkpoints | Pass/fail checks after important phases. |
| Machine-checkable done conditions | Fresh commands, assertions, artifacts, or state queries. |
| Replay or smoke hooks | A small way to rerun the workflow and feed logs back into patches. |
| Drift signal detection | Signs of undertriggering, overtriggering, stale commands, or false success. |

Manual workflows may document deferred elements, but they should not be promoted
to automation until the manual version has passed on real tasks.

For library-level behavior rules, see
[Spellbook Operating Contract](./spellbook-operating-contract.md).

## Review Workflow

Use the lightweight audit before opening a PR:

```bash
python3 scripts/audit_skill_quality.py
```

Scope it to a changed skill when working incrementally:

```bash
python3 scripts/audit_skill_quality.py skill-creator
```

Use warnings as review prompts, not as automatic blockers. A warning can be
acceptable when the skill is intentionally tiny, subjective, or still in manual
validation. For release gates, opt in explicitly:

```bash
python3 scripts/audit_skill_quality.py --fail-on-warn
```

The existing registry validation remains the required correctness gate:

```bash
python3 scripts/validate_skills.py --check
```

## Artifact Checks

Spellbook splits artifact checks into strict validation and advisory audit:

| Tool | Level | Checks |
|---|---|---|
| `python3 scripts/validate_skills.py --check` | Strict | parseable frontmatter, matching non-empty `name` and `description`, duplicate names, generated registry drift, current README counts, missing local support files referenced from `SKILL.md`, unsafe support paths, and unresolved runtime placeholders such as `{SCRIPT}`, `{ARGS}`, `{ARGUMENTS}`, or `<TODO>`. |
| `python3 scripts/audit_skill_quality.py` | Advisory | trigger wording, gotchas, verification cues, operating contract signals, progressive disclosure, unreferenced support directories, missing support files with actionable paths, legacy argument-token usage, and referenced scripts that are neither executable nor shebang-marked. |

Strict failures should block release or installation changes. Advisory findings
should be reviewed in PRs and may be accepted when the skill is intentionally
small, still in manual validation, or documenting a literal template syntax.
