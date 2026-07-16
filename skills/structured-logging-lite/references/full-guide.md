# Structured Logging Design Guide

Use this reference after repository discovery. It defines the decisions and validation needed for a production logging contract; it does not prescribe a universal library or backend.

## Contents

1. [Start With Questions](#start-with-questions)
2. [Telemetry Boundaries](#telemetry-boundaries)
3. [Coverage Matrix](#coverage-matrix)
4. [Event Schema](#event-schema)
5. [Levels And Failure Semantics](#levels-and-failure-semantics)
6. [HTTP And Async Contracts](#http-and-async-contracts)
7. [Sensitive Data And Cardinality](#sensitive-data-and-cardinality)
8. [Library And Backend Selection](#library-and-backend-selection)
9. [Rollout](#rollout)
10. [Verification](#verification)

## Start With Questions

A useful event exists because an operator needs to answer a question. Capture the question before adding the event.

| Question | Best primary signal |
|---|---|
| Is the service failing or slow? | Request-rate, error-rate, and latency metrics |
| Why did this request fail? | Request-correlated error and boundary logs |
| Which dependency caused the failure? | Adapter event plus trace when available |
| Who changed a protected resource? | Durable audit record |
| Is a queue or worker stuck? | Queue/last-success metrics plus batch logs |
| What exact path did one request take? | Distributed trace |

Reject “log everything” as a requirement. It has no done condition and usually increases cost faster than diagnostic value.

## Telemetry Boundaries

```text
composition root
  owns format, destination, global fields, level, and shutdown

transport / command boundary
  owns request or invocation completion, status, duration, and correlation

application runtime
  owns meaningful workflow transitions, not function narration

adapters
  own safe dependency operation, latency, retry, and failure classification

workers / schedulers
  own batch identity, claimed/succeeded/retried/failed counts, and lifecycle

domain
  returns typed errors and decisions; normally owns no logger
```

For a reusable library, do not configure stdout, files, global loggers, or vendor exporters. Accept a small optional diagnostic interface only when consumers need library events, or return enough typed information for the host to observe at its boundary.

### Separate The Contracts

| Contract | Optimized for | Durability | Cardinality |
|---|---|---|---|
| Logs | Explanation and search | Collector-dependent | High-cardinality fields may stay in the body |
| Metrics | Aggregation and alerting | Time-series store | Labels must be bounded |
| Traces | Per-request causality and timing | Trace-store-dependent | IDs identify individual traces |
| Audit records | Accountability and compliance | Application/database guarantee | Queryable domain identifiers |

Do not use application logs as the source of truth for authorization, billing, asset ownership, or compliance history.

## Coverage Matrix

Build this matrix from code and tests before proposing work:

| Area | Evidence to inspect | Minimum useful outcome |
|---|---|---|
| Startup/shutdown | composition root and signal handling | configuration mode, version, ready, stop reason, shutdown failure |
| Request/command | middleware or command runner | operation, outcome, duration, correlation ID |
| Authentication | resolver/middleware and typed errors | fixed auth mode/result/reason without credential material |
| Error boundary | error-to-response/exit mapping | public code, safe internal class, retryability |
| External adapters | DB, object store, provider, filesystem | operation, dependency role, duration, safe failure class |
| Workers | scheduler loop and queue/store | batch outcome counts and last-success signal |
| Degraded paths | fallback, retry, cache, partial response | explicit degraded/error event and counter |
| Panic/crash | recovery and process server logger | correlation, panic type, stack where safe, stable failure response |
| Third-party output | ORM/SDK logger configuration | consistent format, level, and parameter redaction |
| Audit | transactional persistence path | actor/action/resource/request attribution |

Mark an area `covered` only when a fresh test or runtime example proves the event and required fields.

## Event Schema

Use snake_case field names unless an external ingestion contract requires otherwise.

### Common Fields

| Field | Rule |
|---|---|
| `timestamp` | RFC 3339/ISO 8601 in UTC; normally emitted by the logger |
| `level` | Stable severity name |
| `message` | Short human-readable statement, not the only query key |
| `event` | Stable machine-readable event name such as `http_request_completed` |
| `service` | Stable deployed service name |
| `environment` | Bounded deployment environment |
| `version` | Build or release version when available |

### Conditional Fields

| Scope | Fields |
|---|---|
| Request | `request_id`, `method`, `route`, `status_code`, `duration_ms`, `response_bytes` |
| Trace | `trace_id`, `span_id` only from an active trace |
| Error | `error_code`, `error_class`, `retryable`; safe `error_message` only when needed |
| Adapter | `dependency`, `operation`, `duration_ms`, fixed `result` |
| Worker | `worker`, `batch_id`, `claimed`, `succeeded`, `retried`, `failed` |
| Resource | one relevant opaque ID in the log body, not in an index/metric label |

Prefer a small required schema and event-specific fields. Large universal schemas produce empty values and encourage accidental PII capture.

### Event Naming

Use past-tense outcomes for completed events and explicit failure/degradation names:

```text
service_started
http_request_completed
authentication_failed
object_operation_failed
worker_batch_completed
display_url_degraded
```

Do not generate event names from exception text, route paths, model names, customer IDs, or other unbounded data.

## Levels And Failure Semantics

| Level | Contract |
|---|---|
| `debug` | Disabled-by-default diagnostic detail with no operational action |
| `info` | Normal lifecycle, request completion, or meaningful business milestone |
| `warn` | Unexpected but correctly handled condition; output and state remain valid |
| `error` | Failed operation, user-visible server failure, unsafe degradation, or exhausted retry |

Use process exit plus an error log for unrecoverable startup failures. Do not require `fatal` or `panic` logger APIs; they often hide control flow and complicate deferred cleanup and tests.

Classify errors before logging:

- **Expected client/domain rejection:** capture outcome and fixed error code; avoid a stack trace.
- **Dependency or server failure:** log once at the boundary with a safe cause and correlation.
- **Retry:** log final exhaustion at `error`; intermediate attempts belong at `debug` or a sampled/fixed worker event unless each attempt changes state.
- **Cancellation/shutdown:** do not report expected cancellation as an error.
- **Fallback:** if the fallback changes visible output or correctness, emit `error` plus a metric; otherwise use `warn` only when the result remains valid.

## HTTP And Async Contracts

### HTTP Middleware Order

The exact framework composition varies, but observation must cover authentication failures and recovered panics:

```text
request_id
  -> request completion capture
    -> panic recovery
      -> authentication / authorization
        -> route handler
```

The completion event should include normalized `route`, not the raw URL path or query. Record the final status, duration, and successfully written response bytes. Exclude or sample successful health/readiness events.

Validate inbound request IDs for length and allowed characters. Generate one when absent. Do not accept an unbounded caller value merely because JSON encoding escapes control characters.

When wrapping a response writer, preserve every optional interface used by the server or framework. Streaming downloads, flushes, WebSockets, HTTP/2 push, and direct `ReadFrom` paths are common failure points.

### Panic Recovery

Return the service's standard internal-error response when headers are not committed. Log correlation, operation, panic type, and a stack trace where internal policy permits. Avoid logging an arbitrary panic value when it may contain request or secret data.

Configure the HTTP server's own error logger so protocol and connection errors use the same format and global fields.

### Workers And Scheduled Jobs

Log batch outcomes rather than each idle poll or each item success. Pair logs with metrics for:

- claimed, succeeded, retried, and failed item totals;
- last successful batch timestamp;
- queue depth or oldest-item age when available;
- final retry exhaustion.

Give every spawned worker a cancellation, shutdown, and final error owner. Logging does not repair an orphaned goroutine or a dropped worker error.

## Sensitive Data And Cardinality

### Default-Deny Data

Never log these by default:

- authorization, service-auth, cookie, signature, API-key, or secret headers;
- request or response bodies;
- prompts, uploaded file contents, private filenames, or user-entered free text;
- DSNs, connection strings, private keys, environment values, or secret-manager payloads;
- full signed/pre-signed URLs or URL query strings;
- raw third-party error payloads without an adapter-owned safe-error contract.

Use an explicit allowlist of log fields. A key-name redactor is defense in depth, not permission to log arbitrary structs or headers.

Operational logs should usually omit direct personal identifiers. Correlate through `request_id` and durable audit data. If cross-request identity correlation is required, define an approved pseudonymization policy with a dedicated key; do not reuse authentication keys.

### Cardinality Rules

Metric and log-index labels must have a bounded, reviewed value set. Good candidates include environment, service, method, normalized route, status class, dependency role, operation, and fixed result.

Keep these only in the log body or trace store:

```text
request_id
trace_id
user_id
account_id
asset_id / order_id / job_id
raw path or URL
error message
```

Cardinality is about the number of distinct label-value combinations, not a magic count of label keys. Estimate the product of possible values before adding a label.

## Library And Backend Selection

### Selection Order

1. Keep the repository's working structured logger when it meets the contract.
2. Prefer the language standard library when it provides structured fields, levels, handlers, and context-aware calls.
3. Add a mature library when a required capability is missing: framework integration, proven throughput, async buffering, redaction, sampling, or ecosystem compatibility.
4. Migrate only after measuring the existing path or proving an integration blocker.

Compare candidates on API stability, structured output, contextual fields, redaction, handler interoperability, test capture, performance under the actual workload, and maintenance cost. “Fastest” or “zero allocation” without a workload benchmark is not a decision.

### Output And Collection

Containerized services should normally emit JSON to stdout/stderr and let the platform own collection, buffering, retention, and backend routing. Do not make application success depend on direct Loki/Elasticsearch/Datadog delivery unless that delivery is an explicit product requirement with backpressure and shutdown semantics.

Keep logging vendor-neutral at the application boundary. Select Loki, Elasticsearch, or a hosted backend only after confirming the existing platform, search patterns, retention, compliance, and cost constraints.

## Rollout

### P0: Diagnostic Safety

- central logger configuration and stable global fields;
- request/command completion, error boundary, and panic coverage;
- request ID validation and propagation;
- secret allowlist/redaction tests;
- normalized route and fixed error/reason enums;
- explicit third-party logger configuration.

### P1: Effect And Worker Coverage

- adapter failures and latency;
- worker batch results, retries, and last success;
- meaningful application milestones and degraded paths;
- paired low-cardinality metrics for alertable events.

### P2: Cross-Service Operations

- real trace context and log correlation;
- collector/backend integration and retention;
- dashboards, SLOs, burn-rate alerts, and sampling based on observed volume.

Do not block P0 logging on P2 tracing or backend work.

## Verification

Run the repository's native formatter, static checks, build, and test suite. Add targeted checks proportional to the change:

1. **Capture test:** emit representative events into an in-memory sink and parse the structured records.
2. **Required-field test:** assert event name, level, service, request ID, normalized route, outcome, and duration type without pinning timestamps.
3. **Secret-canary test:** send unique canaries through headers, query, body, config, and upstream errors; assert no output contains them.
4. **Failure-level test:** prove expected rejections, server failures, cancellations, retries, and degraded responses use the declared levels and codes.
5. **Panic test:** prove a panic creates one safe error event and the standard failure response.
6. **Route-cardinality test:** use multiple resource IDs and prove they map to one route/operation label.
7. **Streaming test:** prove flush, status, bytes, and streaming behavior remain intact after middleware wrapping.
8. **Third-party test:** trigger expected not-found and real DB/provider failures; verify formatting and parameter policy.

Done means fresh output proves the requested event contract, no secret canary appears, existing error semantics remain intact, and all repository gates pass. A logger that compiles but cannot answer the target operational question is not complete.

## Report Template

```text
verdict: add / complete / consolidate / remove
current evidence: concrete files, events, and missing paths
chosen stack: keep or migrate, with evidence
boundaries: composition / transport / application / adapters / workers / domain
schema: common fields plus event-specific fields
security: allowlist, forbidden data, pseudonymization, retention owner
cardinality: normalized dimensions and high-cardinality body fields
rollout: P0 / P1 / P2
validation: fresh commands and targeted behavioral checks
remaining risks: collector, production access, volume, or external ownership
```
