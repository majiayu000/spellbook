---
name: structured-logging-lite
description: Design, audit, or implement application structured logging architecture from repository evidence. Use when a user asks whether or where to add logs, how to choose or migrate a logger, how to standardize events/fields/levels/redaction, how to add HTTP access or panic logs, or why production logs cannot answer an incident question. Do not use merely to tail platform logs or to design a full metrics, tracing, SLO, and incident-management program.
---

# Structured Logging Lite

Build the smallest logging contract that makes the target system diagnosable without leaking data, duplicating audit records, or forcing an unnecessary logging-library migration.

## Operating Contract

- **Direct actions:** Inspect repositories, manifests, runtime entrypoints, tests, deployment files, and existing logs. Make local logging changes only when the user asks to implement or upgrade them; treat design, review, and diagnosis requests as read-only.
- **Escalate before:** Ask before publishing, pushing, changing remote observability infrastructure, touching production, or expanding from application logging into a full observability rollout.
- **Evidence-backed pushback:** Challenge a requested library migration or log-everything plan only with repository evidence, a measured requirement, a concrete security/cardinality risk, or a smaller compatible alternative.
- **Feedback loop:** Promote repeated missing fields, false-success signals, secret leaks, or manual incident queries into the field contract, gotchas, validation tests, or a deterministic helper.
- Never print or persist credentials, tokens, cookies, signatures, request bodies, DSNs, private URLs, or secret values while investigating.
- Return errors through the existing error contract. A new log line never justifies swallowing, downgrading, or replacing an error.

## Workflow

1. **Search before proposing.** Read applicable repository instructions, check the worktree, then locate manifests, entrypoints, logger construction, log calls, request/context propagation, error mapping, panic handling, adapters, workers, audit records, metrics, tests, and deployment configuration.
2. **Classify the target.** Distinguish a reusable library, CLI/batch job, HTTP service, long-running worker, or multi-service system. Libraries should usually accept host-provided diagnostics rather than configure process-global output.
3. **Reconstruct current coverage.** Mark lifecycle, request, authentication, application milestones, external adapters, background jobs, degraded paths, panic/crash, and third-party library output as `covered`, `partial`, or `missing`.
4. **Name the operational questions.** Require each proposed event to answer a concrete debugging, security, support, or capacity question. Delete events that only narrate normal control flow.
5. **Choose boundaries before libraries.** Configure output at the composition root; observe requests at transport middleware; log effect failures at adapters; log worker batch outcomes at the worker owner; keep pure domain code free of logger dependencies.
6. **Keep or select the logger.** Prefer a working repository-standard logger or a language standard library. Recommend migration only with evidence such as missing required capability, measured overhead, ecosystem incompatibility, or unsafe behavior.
7. **Write the contract.** Define stable event names, required and conditional fields, level policy, error classification, correlation rules, redaction rules, retention/collection ownership, and low-cardinality metric labels.
8. **Implement incrementally when authorized.** Land P0 request/error/security coverage first, P1 adapter and worker telemetry next, and tracing or backend-specific integration only when the runtime needs it.
9. **Verify with fresh evidence.** Run repository-native build/tests plus log capture, secret-canary, route-normalization, panic, and streaming-response tests that match the change.

## Boundary Rules

- Treat logs, metrics, traces, and durable audit records as different contracts. Do not claim one replaces another.
- Emit one request-completion event per request. Add a second event only when it contains a distinct root cause or business outcome.
- Use route templates or operation names in metrics. Keep request IDs, user IDs, asset/order IDs, raw paths, URLs, and error strings out of metric and log-index labels.
- Include `trace_id` and `span_id` only when a real trace context exists. Do not invent IDs or require tracing as a prerequisite for useful logging.
- Prefer fixed error codes and reason enums over arbitrary error strings for aggregation. Preserve a safe cause for debugging without exposing upstream payloads.
- Exclude or sample high-volume health and readiness success logs. Never sample security failures or user-visible server errors without an explicit loss policy.
- Preserve optional response/stream interfaces when observing HTTP writers; a naive wrapper can break flushing, hijacking, streaming, or byte counts.

## Deliverable

For design or audit work, report:

```text
verdict:
current_evidence:
chosen_stack:
boundary_map:
event_and_field_contract:
privacy_and_cardinality:
coverage_gaps:
P0_P1_P2:
validation:
remaining_risks:
```

For implementation work, also report changed files, fresh verification commands, and any deployment or collector work that remains outside the repository.

## Gotchas

- Raw URL paths turn identifiers into unbounded labels and can leak query credentials.
- Logging every function entry/exit creates volume without diagnostic value.
- Logging both at every return site and again at the boundary duplicates the same failure.
- ORM defaults may print interpolated SQL, expected not-found errors, or non-JSON output.
- A logger hidden in generic context values becomes an implicit dependency; keep typed correlation data in context and logging ownership at boundaries.
- A successful fallback that changes user-visible output still needs an error signal and metric; `warn` plus silent degradation is not success.
- Access logs without status, duration, normalized route, and request ID rarely answer incident questions.
- Persistent audit events require transactional and retention guarantees that stdout logs do not provide.

## References

- Read [`references/full-guide.md`](references/full-guide.md) before designing a schema, level policy, rollout, or validation plan.
- For Go repositories, also read [`references/go.md`](references/go.md) before choosing a library or implementing HTTP, `slog`, or ORM integration.
- For a full observability/SLO/tracing program, route to `observability-sre` after the logging contract is clear.
