# Codex Handoff Document Template

Use this structure when creating a handoff before archiving a valuable session with `codex-fluent`.

The goal of a handoff is **perfect continuity with minimal context**. A fresh Codex thread (or even Claude via the `codex` skill) should be able to read the repo + this document and continue productively without the old chat.

---

**Project / Ticket:**  
**Date of Handoff:**  
**Previous Session Context (optional):**  
**Handoff Author:** (usually Codex itself)

## Executive Summary (2-4 sentences)

What we were trying to achieve and the current state.

## Key Decisions & Rationale

- Decision: ...
  - Rationale: ...
  - Tradeoffs considered: ...

## Current Codebase State

List only the files that matter for continuation. One line each.

- `path/to/important/file.ts`: Current purpose + recent changes
- ...

## Environment & Commands

- How to run / test / build relevant parts
- Any special setup or env vars for this task

## What Has Been Completed

- [x] ...
- [x] ...

## Open Questions & Next Steps (Prioritized)

1. **High** — Specific task with clear success criteria
2. **Medium** — ...
3. **Low / Nice to have** — ...

## Constraints & Preferences (Very Important)

- Do not touch: ...
- User style notes: (e.g. "prefers early returns", "hates magic numbers in this file")
- Things we deliberately avoided and why

## Reactivation Prompt (Copy-Paste Ready)

```
We are continuing work from a previous Codex session. 

Read the handoff document at: docs/codex-handoffs/YYYY-MM-DD-topic.md (or wherever it was saved).

1. First, explore the current state of the repo to verify what still applies.
2. Read the handoff document completely.
3. Then continue from the "Open Questions & Next Steps" section.
4. Do not assume the previous chat history is available.

Start by confirming you have understood the current state and the next priority.
```

## Additional Notes for Future You

Anything that might be useful 2 weeks or 2 months from now.

---

**Save this file** in a stable location, for example:
- `docs/codex-handoffs/YYYY-MM-DD-short-topic.md`
- Or a project-specific handoff directory you already use.

After saving, you can safely archive the original heavy session using `codex-fluent`.