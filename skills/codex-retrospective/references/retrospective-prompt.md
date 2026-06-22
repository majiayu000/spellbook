# Codex Retrospective Prompt Template

This is the core prompt used by the `codex-retrospective` skill. It is deliberately strict.

---

You are performing a high-signal retrospective on your own recent usage history as Codex.

**Time window:** [user specifies, e.g. last 14 days / the auth and payments work from May]

**Your goal:** Make yourself meaningfully better at working with this user by identifying the smallest number of high-leverage changes to AGENTS.md and/or tiny new skills.

**Strict rules you must follow:**

1. Only propose changes when you have clear, repeated evidence from the history.
2. Every proposal must be the *minimal* useful intervention.
3. Prefer updating or slightly extending existing rules over adding new ones.
4. Only extract a new skill if the pattern is genuinely reusable and would have saved significant time/friction in multiple places.
5. If you cannot find strong evidence for a useful change, say so honestly.
6. Do not propose changes until you have listed the evidence sources checked and concrete handles for the evidence you rely on.

**Process:**

First, define the scope and build an evidence inventory:

- Scope: repo/project, time window, and focus area.
- Sources checked: current AGENTS.md, relevant existing skills, repo docs, Memories/Chronicle, and local Codex session files when available.
- Evidence handles: session IDs, memory IDs, file paths, PR/issue numbers, or dated incidents that can be checked later.
- Runtime availability: distinguish "skill exists in source" from "skill is installed and triggerable in the active runtime" when that matters.

Then deeply review the relevant session history, any available Memories or Chronicle, and the current AGENTS.md + skills.

Then output **exactly** in this structure:

## 0. Evidence Inventory

- Scope reviewed.
- Sources checked.
- Concrete evidence handles used for the proposals.
- Any source/runtime availability distinctions that matter.

If this section cannot list enough evidence for a high-confidence change, stop after section 1 with a clear no-change recommendation.

## 1. Retrospective Summary

- 3–6 bullet points of the most important patterns observed (both problems and strong successes).
- For each point, reference specific sessions or time periods.

## 2. Proposed AGENTS.md Updates

Only include this section if you have high-confidence minimal changes.

For each change:
- Exact location (or "append at the end of section X")
- The precise text to add or replace (as a clean diff or quoted block)
- One-sentence rationale tied to observed history

## 3. Proposed New or Updated Tiny Skills (0–2 maximum)

For each:
- Suggested filename (e.g. `skills/codex-payment-idempotency.md`)
- Complete YAML frontmatter + content
- Why this tiny skill is worth the cost of another file

## 4. Evidence & Rationale

For every proposal above, point to the concrete patterns in history that justify it.
Map every proposed AGENTS.md update or tiny skill to at least one evidence handle from section 0.

## 5. Application Recommendation

- Suggested order of applying changes
- Any verification steps the user should do afterward
- Whether a follow-up retrospective in 2 weeks would be useful

Remember: Your future self (and the user) will thank you for ruthless minimalism. Large or speculative changes are worse than no change.
