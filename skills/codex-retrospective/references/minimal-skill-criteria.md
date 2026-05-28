# Criteria for Extracting a Tiny Skill During Retrospective

The bar for creating a new skill file from a retrospective is intentionally high.

## Must Meet All of These

- The pattern appeared in at least two meaningfully different sessions in the review window (or one extremely high-cost incident).
- Encoding it as a small skill would have saved the user noticeable time, context, or corrections.
- The skill is small and focused (ideally under 80–100 lines when first created).
- It has a clear, natural trigger phrase the user is likely to say or that Codex can reliably recognize.
- It is more valuable as a standalone file than as a short section in AGENTS.md.

## Should Usually Be Rejected If

- It only saves one or two minor steps.
- It is very specific to a single project or temporary situation.
- It duplicates logic that already exists in AGENTS.md or another skill.
- It would require frequent updates (better to keep in AGENTS.md for now).
- The main value is "reminding Codex of something" rather than providing a reusable procedure or checklist.

## Good Examples of Tiny Skills Worth Extracting

- A specific debugging ritual for a tricky class of production incidents in one service.
- A strict code review checklist for security-sensitive changes that the team cares about.
- A reliable way to produce high-quality handoff documents for a particular type of long-running work.
- A pattern for safely introducing a new database migration in this specific stack.

## Anti-Examples

- "Be more careful with error handling" → too vague.
- A 300-line "perfect Go web service generator" → way too big for a retrospective extraction.
- Something that only applied to last week's incident.

## Final Test

After writing the tiny skill, ask: "If I had this skill two weeks ago, would at least one of the painful sessions in this retrospective have gone clearly better?"

If the honest answer is no or "maybe a little", do not create the file. Put the insight in AGENTS.md instead.