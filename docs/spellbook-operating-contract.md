# Spellbook Operating Contract

Spellbook is a skill library, not a prompt dump. Its skills should help an
agent decide when to act, when to escalate, how to verify the result, and how to
turn repeated failures into reusable guidance.

Use this contract when creating, reviewing, or materially changing a skill.

## Mission

Spellbook skills should package workflow knowledge that is hard to infer from
general model behavior:

- Trigger conditions and near-boundary cases.
- Non-obvious domain rules, failure modes, and recovery paths.
- Deterministic scripts, templates, assets, examples, or evals.
- Done-when checks that prove the workflow produced the intended state.

If the content only says "be careful" or repeats general best practices, it does
not belong in a skill yet.

## Autonomy Boundary

A skill should say which actions the agent may take directly and which actions
require escalation. Prefer concrete boundary lists over vague caution.

| Action type | Default behavior |
|---|---|
| Read-only inspection, local validation, draft generation | Execute directly and report evidence. |
| Local docs or skill refactors within the requested scope | Execute directly after checking existing files first. |
| Publishing, billing, credential, permission, or remote production changes | Escalate before acting unless the user already gave explicit approval. |
| Destructive local changes such as deleting files or rewriting history | Escalate before acting and name the reversible alternative. |
| Missing required data or unsupported runtime capability | Fail loud with the blocker; do not invent fields, APIs, or fallback output. |

## Evidence-Backed Pushback

Skills should permit the agent to challenge the user's proposed path when the
repo evidence points elsewhere. Pushback must include at least one of:

- A file, command, issue, PR, or source citation.
- A concrete risk such as data loss, security exposure, broken validation, or
  maintenance drift.
- A smaller alternative that preserves the user's goal.

Do not encode personality-based resistance. The useful rule is not "be bold";
it is "push back only when the evidence changes the safest next action."

## Feedback Loop

Repeated corrections should change the skill, not only the current answer. When
the same issue appears again, choose the smallest durable home:

| Signal | Durable home |
|---|---|
| User corrects a repeated mistake | Add a gotcha or near-boundary trigger. |
| A command is run manually in several sessions | Add or update a script. |
| A workflow result cannot be checked objectively | Add a done-when check or eval prompt. |
| A long section is only needed for one variant | Move it to `references/` with a load-when pointer. |
| A safety decision keeps recurring | Add an autonomy boundary or escalation rule. |

## End-State Check

Every workflow skill should define what "done" means. For objective work, prefer
fresh command output over narrative claims:

- Registry and install changes: `python3 scripts/validate_skills.py --check`.
- Skill quality changes: `python3 scripts/audit_skill_quality.py`.
- Script changes: syntax checks, targeted unit tests, and representative sample
  runs.
- Documentation-only changes: link checks when available, plus a review of
  affected generated docs or indexes.

If verification is impossible in the current environment, report the missing
precondition and the command that should be run later.

## Relationship To Other Docs

- [Skill Format Policy](./skill-format-policy.md) defines where files live.
- [Skill Quality Playbook](./skill-quality-playbook.md) defines what makes a
  skill useful.
- This operating contract defines how a skill should guide agent behavior during
  real work.
