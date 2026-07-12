# Approved incident skill inventory

These repository-relative summaries are approved for the overlap audit in this eval.

## `incident-response`

- Owns reversible canary mitigation and requires two stable observation windows before rollout.
- Owns the general rule that alert clearance alone is insufficient for incident closure.
- Does not describe retry-volume growth after latency recovery or how to distinguish it from a healthy recovery.

## `database-debugging`

- Owns comparing lock-wait, pool saturation, queue depth, and recent concurrency changes before restarting a database.
- Owns reducing application concurrency when pool capacity is the measured bottleneck.
- Does not cover client retry storms after the primary database symptom recovers.
