# Redacted incident timeline

All service, customer, host, and credential identifiers have been removed.

- 09:05 — API latency and connection wait time rose together. Candidate causes were database lock contention, pool exhaustion, or a dependency outage.
- 09:08 — Lock-wait metrics stayed flat while every application pool was saturated and request queues grew. The responder chose to inspect concurrency and pool limits instead of restarting the database.
- 09:12 — The preceding deploy had increased worker concurrency without changing pool capacity. The responder capped concurrency on one canary instance. Rollout would continue only if pool use stayed below 80% and queue depth declined for two observation windows.
- 09:18 — The canary met both signals, so the cap was rolled out. Median latency recovered and the main alert cleared.
- 09:24 — Retry volume continued rising even though latency looked normal. The responder treated the cleared alert as a false-success signal and paused closure.
- 09:28 — A client retry policy was amplifying intermittent timeouts. The responder reduced retry concurrency on a canary, requiring retry volume and error rate to fall without queue growth.
- 09:36 — Both canary checks held for two windows, the change was rolled out, and the incident was closed with follow-up work for capacity testing.

Outcome: no database restart occurred; the two canary changes were reversible and restored stable service.
