# Example of a Good Retrospective Output (Sanitized)

**Window:** Last 18 days, focused on the new Go service work.

## Evidence Inventory

- Scope: new Go service work, last 18 days.
- Sources checked: current AGENTS.md, service-specific skills, local session summaries, and three Codex session files.
- Evidence handles: sessions from May 4, May 9, May 12, and May 15; AGENTS.md "Core Implementation Principles"; service money-movement skill.

## Retrospective Summary

- Repeatedly started implementation before fully clarifying the exact failure modes the user cared about most (happened in at least 3 sessions).
- Strong pattern: when the user said "make it robust", Codex defaulted to broad retries instead of the specific idempotency + compensation model preferred here.
- User had to re-explain the "Money type + no raw amounts" rule twice in different files.
- Excellent results when Codex first wrote a tiny state machine sketch before coding — this pattern is worth encoding.

## Proposed AGENTS.md Updates

**Location:** Under "Core Implementation Principles" (new bullet)

```diff
+ - When the user asks for something to be "robust", "safe", or "production ready" in this service, first explicitly list the 2-4 concrete failure modes we are optimizing for before writing any code. Do not assume broad retries or circuit breakers are the answer.
```

## Proposed Tiny Skill

**File:** `skills/go-service-idempotency.md`

(Full small skill with frontmatter for handling money movements with explicit compensation. Omitted here for brevity — it was 2 focused sections + 1 example.)

## Rationale

The three sessions on May 4, May 9, and May 15 all had the same pattern: Codex jumped into "add retry + backoff" while the actual requirement was explicit ledger entries + compensation handlers. The Money type issue appeared in the May 9 and May 15 threads.

The state machine sketch technique from the May 12 session produced the cleanest result with the least back-and-forth.

## Application Plan

1. Apply the AGENTS.md addition first (low risk).
2. Review the extracted skill together.
3. In the next similar task, explicitly invoke the new skill when relevant.
4. Re-run a short retrospective in 10 days focused only on this area to measure improvement.
