# Task Plan

## Linked Issue

GH-130

Covered issues: #127, #128, #129.

## Spec Packet

- Product: `product.md`
- Tech: `tech.md`

## Implementation Tasks

- [ ] `SP130-T1` Owner: coordinator. Done when: GH130 product, tech, and task specs explicitly cover #127, #128, and #129. Verify: SpecRail check for `specs/GH130`.
- [ ] `SP130-T2` Owner: skill-lifeguard lane. Done when: `skill-lifeguard` defines the 5-element Reliable Skill Contract, scoring output, examples, and log-to-patch loop. Verify: `python3 scripts/audit_skill_quality.py skill-lifeguard`.
- [ ] `SP130-T3` Owner: review-gate lane. Done when: `review-gate` defines review pack, human approval states, integration points, and forbidden self-approval. Verify: `python3 scripts/audit_skill_quality.py review-gate`.
- [ ] `SP130-T4` Owner: context guard lane. Done when: `flowguard` and `strategic-compact` include objective re-verify, context audit, compaction policy, and external scratchpad guidance. Verify: targeted diff review plus `python3 scripts/validate_skills.py --check`.
- [ ] `SP130-T5` Owner: docs lane. Done when: `skill-audit`, `skill-creator`, README, and docs expose the Agent Reliability Trio and new agent-workflow skill expectations. Verify: link/path review and generated registry check.
- [ ] `SP130-T6` Owner: verification owner. Done when: generated registry outputs are refreshed and all required commands pass. Verify: `python3 scripts/validate_skills.py --check` plus PR gate checks.

## Parallelization

Tasks `SP130-T2`, `SP130-T3`, and `SP130-T4` can be planned independently, but the coordinator owns all writes in this tranche to avoid conflicting generated registry updates and shared docs edits.

## Verification

- `python3 scripts/validate_skills.py --write`
- `python3 scripts/validate_skills.py --check`
- `python3 scripts/audit_skill_quality.py skill-lifeguard`
- `python3 scripts/audit_skill_quality.py review-gate`
- `python3 -m py_compile scripts/*.py`
- `env PYTHONDONTWRITEBYTECODE=1 python3 /Users/apple/Desktop/code/AI/tool/specrail/checks/check_workflow.py --repo /Users/apple/Desktop/code/AI/tool/specrail --spec-dir specs/GH130`

## Handoff Notes

This is a final umbrella tranche for #130 and closes #127, #128, and #129 only if every acceptance criterion in `product.md` is implemented and verified.
