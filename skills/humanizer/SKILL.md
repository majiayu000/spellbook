---
name: humanizer
description: 'Remove signs of AI-generated writing from text. Use when editing or
  reviewing

  text to make it sound more natural and human-written. Based on Wikipedia''s

  comprehensive "Signs of AI writing" guide. Detects and fixes patterns including:

  inflated symbolism, promotional language, superficial -ing analyses, vague

  attributions, em dash overuse, rule of three, AI vocabulary words, negative

  parallelisms, and excessive conjunctive phrases.

  '
allowed-tools:
- Read
- Write
- Edit
- Grep
- Glob
- AskUserQuestion
metadata:
  version: 2.2.0
---

# Humanizer

Use this skill to remove AI-writing artifacts while preserving the author's meaning, factual claims, and intended voice.

## Routing

- Start here to confirm scope, safety boundaries, and the minimum workflow.
- Load `references/full-guide.md` before executing detailed commands, applying templates, or relying on examples from this skill.
- Keep the work limited to the user-requested target; do not add adjacent improvements unless the user asks.

## Quick Workflow

1. Confirm the target, available context, constraints, and done-when signal.
2. Read the relevant section of `references/full-guide.md` for task-specific details.
3. Execute the smallest reversible action that satisfies the request.
4. Verify that meaning is preserved, claims are not added, and the revised text no longer uses the targeted AI-writing patterns.
5. Report changed files, commands run, evidence collected, and any remaining risk.

## References

- `references/full-guide.md` - complete command patterns, examples, checklists, and edge cases.
