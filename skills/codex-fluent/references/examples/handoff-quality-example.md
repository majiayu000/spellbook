# Example of a High-Quality Handoff (Shortened)

(This is what good handoffs produced with `codex-fluent` tend to look like.)

**Project:** Internal billing service refactor  
**Date:** 2026-05-12

## Executive Summary
We were extracting the billing calculation logic into a dedicated service with proper idempotency and retry semantics. The core happy path + two main failure modes are implemented and tested. The remaining work is around partial failure compensation and observability.

## Key Decisions
- Use event-sourced ledger for all money movements (decided after comparing with outbox pattern).
- All compensation must be explicit and logged; no implicit rollback.
- Idempotency keys are required on every public mutation.

## Current State
- `internal/billing/ledger.go` — the new event source, well tested
- `internal/billing/calculator.go` — pure functions + property tests
- API handlers still call the old monolith code in some paths (flagged for next step)

## Next 5 Steps (Prioritized)
1. Implement the two compensation flows for the "payment succeeded but downstream failed" case.
2. Add structured logging + trace IDs across the new service.
3. Wire the new service behind a feature flag in staging.
4. Write the migration script for historical ledger entries (read-only first).
5. ...

## Constraints & Style
- Prefer early returns and small functions in this package.
- All money values must go through the `Money` type (never raw int64 in business logic).
- Do not touch the legacy `billing_v1` package unless explicitly asked.

## Reactivation Prompt
```
Read docs/codex-handoffs/2026-05-12-billing-service.md.

Explore the current state of the repo, especially the billing directory.

Continue from the "Next 5 Steps" section. Start by confirming the current status of step 1.
```
