---
name: codex-retrospective
description: Use when you want Codex to review its own recent history (last N days or specific period) and improve its behavior. Produces minimal, high-signal updates to AGENTS.md and tiny reusable skills. The goal is long-term fluency — Codex gradually becomes better at your specific style, constraints, and workflows.
---

# Codex Retrospective

A structured self-improvement loop for Codex.

This skill turns Codex from a one-off collaborator into a system that **gets meaningfully better at working with you** over time by systematically eating its own usage history.

## Why This Exists

Most people improve their agent usage by manually maintaining `AGENTS.md` or skills when they notice problems. This skill makes that process deliberate, regular, and high-leverage.

It is directly inspired by strong practices from heavy users (especially Greg Brockman's emphasis on updating the "constitution" from real failures and friction), but executed as a repeatable arsenal-style workflow.

## Core Principle

**Minimal effective change, grounded in evidence from actual history.**

Every output must be:
- The smallest possible useful addition or edit
- Backed by specific patterns observed in recent sessions
- Designed to prevent repetition of the same friction

## When to Trigger

- After a painful or repetitive session ("Codex should have known better by now")
- Periodically (weekly or monthly): "Do a retrospective on the last 7/30 days of my Codex usage"
- When `codex-fluent` reports that Codex is constantly re-asking for the same context or preferences
- After you have manually corrected the same class of mistake multiple times

## The Retrospective Process

### 1. Scope Definition

You specify the time window or focus area:
- "Last 14 days"
- "The three big auth + payments threads from last month"
- "All sessions involving the new Go service"

### 2. Evidence Collection Preflight

Before proposing any AGENTS.md update or tiny skill, Codex must build a small
evidence inventory:

- Scope: repo/project, time window, and focus area.
- Sources checked: current AGENTS.md, relevant existing skills, repo docs, Memories/Chronicle, and local Codex session files when available.
- Evidence handles: session IDs, memory IDs, file paths, PR/issue numbers, or dated incidents that can be checked later.
- Runtime availability: distinguish "skill exists in source" from "skill is installed and triggerable in the active runtime" when that matters.
- No-change path: if evidence is weak, stop with a concise "no high-confidence change" result instead of manufacturing proposals.

Every proposed update must map back to at least one concrete evidence handle.

### 3. History Analysis (The Skill Guides Codex)

Codex is instructed to look for:
- Recurring mistakes or inefficient patterns
- Things the user had to explain or correct repeatedly
- High-friction moments (lots of back-and-forth, context loss, wrong assumptions)
- Successful patterns worth encoding so they happen by default
- Opportunities to extract tiny, reusable skills

### 4. Output — Strict Format

The skill forces Codex to produce output in this order:

0. **Evidence Inventory** (scope, sources checked, and concrete handles)
1. **Retrospective Summary** (short, evidence-based)
2. **Proposed AGENTS.md Updates** (exact diff or append text only)
3. **New or Refined Minimal Skills** (at most 1-2 tiny ones, full SKILL.md with frontmatter)
4. **Rationale + Evidence** (which sessions/patterns drove each proposal)
5. **Application Plan** (how to safely apply the changes)

### 5. Human Gate + Application

You review. The skill then helps you apply the minimal changes cleanly (never blindly overwriting large sections of AGENTS.md).

## Relationship with codex-fluent

These two skills are designed to be used together:

- `codex-retrospective` finds **behavioral and knowledge** improvements (better defaults, new rules, extracted skills).
- `codex-fluent` finds **state and context** hygiene improvements (session bloat, missing handoffs, archive opportunities).

A good monthly ritual for serious users:
1. Run `codex-retrospective` on the last 30 days.
2. Run `codex-fluent` diagnosis.
3. Apply the best changes from both.

## Hard Constraints on Output

- Never propose large rewrites of AGENTS.md.
- Never create big new skills. Tiny, focused, high-ROI only.
- Every proposal must reference concrete history ("In the payment retry thread on May 3rd and the similar incident on May 18th...").
- Do not propose changes until the evidence inventory exists and each proposal maps to a concrete handle.
- If nothing high-confidence was found, say so clearly instead of manufacturing improvements.

## Gotchas

- Do not turn a single annoying session into a permanent rule unless it was
  unusually high impact. Prefer "no change" over a weak constitution update.
- Do not rely on memory vibes. Each proposed update needs a concrete session,
  date range, file, PR, or repeated correction pattern that can be checked.
- Keep generated AGENTS.md text short. If the proposed rule needs multiple
  paragraphs, it probably belongs in a tiny skill or a project doc instead.
- Application is gated by the user. The retrospective can propose exact diffs,
  but it must not silently rewrite AGENTS.md or existing skills.

## References

- `references/retrospective-prompt.md` — The core prompt template used to drive Codex's self-analysis
- `references/agents-md-update-rules.md` — Strict rules for what kind of changes are acceptable
- `references/minimal-skill-criteria.md` — What qualifies as a "tiny useful skill" worth extracting
- `references/examples/` — Real (sanitized) retrospective outputs and the resulting AGENTS.md diffs

## Success Looks Like

After 4–8 weeks of regular use:
- Codex makes fewer basic assumption errors in your domain
- You spend less time re-explaining preferences and constraints
- Your AGENTS.md and skills folder feel like they were written by someone who has worked with you for a long time (because they were)
- New projects ramp up faster because the constitution already encodes hard-won lessons

Start with a focused 7- or 14-day retrospective on a project where you've felt the most friction recently. The pattern will become natural quickly.
