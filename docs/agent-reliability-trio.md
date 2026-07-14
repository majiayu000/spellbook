# Agent Reliability Trio

Spellbook treats reliable agent work as a three-part pattern:

1. `skill-lifeguard` keeps high-value skills self-maintaining.
2. `flowguard` keeps long sessions from drifting or losing important context.
3. `review-gate` stops agent-generated diffs from landing without a review pack
   and explicit human approval.

Use the trio for long-running, high-impact, multi-agent, or merge-capable work.
Do not split it into competing workflow fragments unless a narrower skill owns a
clearly different domain.

## Pattern Homes

| Pattern | Primary home | Supporting files |
| --- | --- | --- |
| Reliable Skill Contract | `skills/skill-lifeguard/` | `skills/skill-audit/`, `skills/skill-creator/`, `docs/skill-quality-playbook.md` |
| Context Engineering | `skills/flowguard/` | `skills/flowguard/references/state-contract.md` |
| Review Gate | `skills/review-gate/` | PR queue and delivery skills that need landing approval |

## End-To-End Example

```text
1. User asks to harden a long-running skill.
2. skill-lifeguard audits the target skill against the five contract elements.
3. flowguard records goal, constraints, done-when, and a five-step plan.
4. flowguard runs a context audit before handoff or compaction.
5. The agent patches the skill and runs validation.
6. review-gate produces a review pack and waits for explicit human approval
   before commit, push, PR, or merge.
7. The final handoff records modified files, verification, decisions, blockers,
   and drift signals that should feed the next skill patch.
```

## Failure Log To Skill Patch

When a repeated failure appears, promote it into the smallest durable home:

| Signal | Patch target |
| --- | --- |
| Same user correction repeats | Add a forbidden behavior and safer alternative. |
| Command output is repeatedly misread | Add a verification checkpoint or parser script. |
| Skill triggers in the wrong context | Tighten the frontmatter description. |
| Skill misses its primary use case | Add trigger phrases and a near-boundary rule. |
| False success reaches PR or merge | Add a Review Gate risk item and done condition. |

The manual workflow must pass on real tasks before it is promoted into
automation or scheduled hooks.
