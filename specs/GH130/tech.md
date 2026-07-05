# Tech Spec

## Linked Issue

GH-130

Covered issues: #127, #128, #129.

## Product Spec

Link to `product.md`.

## Codebase Context

| Area | Files | Current behavior | Why relevant |
| --- | --- | --- | --- |
| Skill reliability design | `skills/skill-audit/`, `skills/skill-creator/`, `docs/skill-quality-playbook.md`, `docs/spellbook-operating-contract.md` | Skill quality exists, but no named Reliable Skill Contract or 5-element score. | Covers #127. |
| Context guard flows | `skills/flowguard/`, `skills/strategic-compact/` | Guardrails and compaction exist, but context audit and objective re-verify are not explicit enough. | Covers #128. |
| Landing review | new `skills/review-gate/`, `skills/flowguard/` integration | PR review exists through other workflows, but no first-class review-pack + human gate skill. | Covers #129. |
| Discovery | `README.md`, `README_CN.md`, `docs/` | Core agent workflow table lists existing skills, but not the reliability trio. | Covers #130. |
| Registry | `scripts/validate_skills.py`, generated registry files | New skills default to Uncategorized unless source mapping is updated. | Keeps generated metadata consistent. |

## Proposed Design

- Add `skills/skill-lifeguard/SKILL.md` with the Reliable Skill Contract and an examples reference.
- Add `skills/review-gate/SKILL.md` with a reusable review pack template asset.
- Enhance `flowguard` to call objective re-verify, context audit, and Review Gate at landing points.
- Expand `strategic-compact` from compaction-only guidance into a small Context Engineering guard without creating a competing new skill.
- Update `skill-audit`, `skill-creator`, and docs so new or audited agent-workflow skills are checked against the contract.
- Update `scripts/validate_skills.py` category source so new skills land in AI & Agent Workflow, then regenerate registry outputs with `--write`.

## Product-to-Test Mapping

| Product invariant | Implementation area | Verification |
| --- | --- | --- |
| P1 | `skills/skill-lifeguard/`, docs | `python3 scripts/audit_skill_quality.py skill-lifeguard` |
| P2 | `skills/flowguard/`, `skills/strategic-compact/` | targeted content review plus `python3 scripts/validate_skills.py --check` |
| P3 | `skills/review-gate/` | `python3 scripts/audit_skill_quality.py review-gate` |
| P4 | docs/README integration | `python3 scripts/validate_skills.py --check` and manual link/path review |
| P5 | generated registry | `python3 scripts/validate_skills.py --write` then `--check` |

## Data Flow

Inputs are user requests, repo diffs, run logs, handoffs, and skill files. Outputs are skill instructions, review packs, spec files, and generated registry docs. No secrets, credentials, network writes, or runtime persistence are introduced by the implementation itself.

## Alternatives Considered

- Create a standalone `context-engineering` skill. Rejected for this tranche because #130 explicitly warns against fragmentation; `strategic-compact` and `flowguard` are the existing homes.
- Fold Review Gate into `flowguard` only. Rejected because #129 asks for an easy-to-invoke first-class review gate.
- Create separate specs for #127, #128, #129. Rejected because #130 is the coordination issue and its acceptance explicitly includes the three patterns.

## Risks

- Security: Review Gate must not become a way to self-approve sensitive changes; it records explicit human approval only.
- Compatibility: New skills must use existing frontmatter and directory layout.
- Performance: No runtime performance impact.
- Maintenance: Too many overlapping guard skills could confuse triggering; docs must state the primary homes.

## Test Plan

- [ ] Unit tests: not applicable; no production library behavior changes.
- [ ] Integration tests: `python3 scripts/validate_skills.py --check`.
- [ ] Advisory audits: `python3 scripts/audit_skill_quality.py skill-lifeguard` and `python3 scripts/audit_skill_quality.py review-gate`.
- [ ] SpecRail: `env PYTHONDONTWRITEBYTECODE=1 python3 /Users/apple/Desktop/code/AI/tool/specrail/checks/check_workflow.py --repo /Users/apple/Desktop/code/AI/tool/specrail --spec-dir specs/GH130`.

## Rollback Plan

Revert the implementation PR. Generated registry files should be regenerated after reverting so skill counts and indexes return to the previous state.
