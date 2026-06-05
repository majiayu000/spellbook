# Writing And Operations Playbook

Use this reference after choosing a taxonomy category.

## High-Signal Content

Prefer content that changes the agent's behavior:

- Domain gotchas
- Non-obvious invariants
- Local file paths and tool names
- Validation commands
- Known bad patterns
- Setup and configuration requirements
- Output formats that must be preserved

Avoid content the model already knows, such as generic coding advice, common
framework summaries, or broad "be careful" statements without concrete failure
modes.

## Gotchas

Every skill should have at least one gotcha if it exists because the agent has
made mistakes before. Good gotchas are specific:

- Which field name is misleading
- Which API returns success before work is complete
- Which environment behaves differently
- Which file must be updated together with another file
- Which fallback is unsafe

## Description Design

The `description` field is a trigger contract. Write it for model discovery.

Include:
- What the skill does
- Concrete user phrases and task contexts
- File types, tools, products, or domains that should trigger it
- Strong signals for when to use it even if the user does not say "skill"

Avoid:
- Human-facing marketing language
- A vague summary that could apply to many skills
- Trigger details buried only in the body

## Setup

If the skill depends on user-specific context, design setup explicitly:

- Store non-secret config in a local config file when appropriate
- Ask only for missing information that cannot be inferred
- Keep secrets in env vars or the user's secret manager
- Document default behavior when config is missing

## Memory

Use memory only when history changes the next run:

- Append-only logs for recurring posts, recaps, queues, or reviews
- JSON state for processed IDs or last-run timestamps
- Stable data directories when the runtime provides them

Do not use memory to hide uncertainty or replace source-of-truth systems.

## Scripts

Add scripts when deterministic code is more reliable than instructions:

- Fetching or transforming structured data
- Validating generated files
- Creating templates or scaffolds
- Running repeatable checks

Keep scripts small, documented by usage examples, and covered by smoke tests.

## Hooks

Use on-demand hooks for temporary guardrails that should apply only while a
skill is active:

- Blocking destructive shell commands during production operations
- Restricting edits to an allowed directory during targeted debugging
- Logging usage or verification evidence during eval runs

Avoid always-on hooks for narrow workflows because they create noise outside the
skill's task.

## Distribution

Choose distribution by audience:

- Repo-local skill: best when knowledge is tied to one codebase or small team
- Shared plugin or marketplace: best when many teams can reuse it and choose
  whether to install it
- Sandbox folder or experimental branch: best before the skill has traction

Promote a skill after real use shows that it triggers correctly and improves
outcomes.

## Measurement

Track lightweight signals:

- Usage count
- Tasks where the skill should have triggered but did not
- Tasks where it triggered but was not useful
- Repeated gotchas added after failures
- Verification pass rate
- Time saved or reduction in review comments

Use these signals to decide whether to improve the description, split the skill,
add support files, or retire it.
