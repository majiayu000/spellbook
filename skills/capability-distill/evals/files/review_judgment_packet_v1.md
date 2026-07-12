# Redacted review judgment packet v1

```yaml
provenance:
  source_model:
  author:
  distilled_at: 2026-06-15
  evidence_ref: review_trajectory.md
```

## JR-001

- Scenario: a merge gate accepts a reviewer-source field.
- Observable signal: the field controls authorization but accepts arbitrary non-empty text.
- Default action: require a closed set and fail on missing or unknown values.
- Exception: none recorded.
- Stop or escalate: stop merge-readiness review when source evidence cannot be classified.
- Evidence: `review_trajectory.md` steps 1-4; focused negative fixture passed after the fix.

## JR-002

- Scenario: self-review evidence is offered for a merge gate.
- Observable signal: no failed independent reviewer lane is recorded.
- Default action: reject self-review as authorization evidence.
- Exception: accept only after a recorded lane failure and explicit human authorization.
- Stop or escalate: request the missing lane and authorization evidence before continuing.
- Evidence: `review_trajectory.md` steps 5-6; prerequisite negative fixture failed for the intended reason.
