# Architecture Research Lenses

Use only the lenses that can affect the current decision. They are questions for
investigation, not a checklist that every report must reproduce.

## 1. Boundary and ownership

Separate a system's visible interface from the capability underneath it.

- What outcome does the system produce, and where does its responsibility end?
- Which inputs, datasets, indexes, models, queues, and control services are
  owned, licensed, hosted, or supplied by somebody else?
- Is the candidate a whole system, an orchestration layer, a component, a
  protocol implementation, or only a client?
- Does self-hosting remove an external dependency, or merely relocate the
  interface and scheduler?
- Which layer is differentiating enough that ownership is a requirement?

Trace three paths when they exist:

```text
data path:       input -> acquisition -> transform -> state -> result
control path:    intent -> schedule/policy -> execution -> retry/reconcile
operations path: deploy -> observe -> recover -> upgrade -> retire
```

## 2. Authority, state, and recovery

Persistent data is not automatically authoritative or sufficient for recovery.

- What is the source of truth for intent and current state?
- Which stores are authoritative, cached, projected, historical, or ephemeral?
- Can two stores disagree? Which one wins, and how is divergence detected?
- What exact state and input must survive a restart to continue safely?
- Does recovery replay events, resume a checkpoint, reconstruct from an external
  tracker, or start a new equivalent task?
- What reconciliation loop corrects stale local state against live remote truth?
- Are transitions idempotent, and what prevents duplicate work or false
  completion?

Use failure scenarios, not only normal diagrams: process crash, partial write,
stale checkpoint, provider timeout, retry after side effect, unavailable
dependency, schema change, and rollback.

## 3. Capability maturity

Do not count a capability merely because a type, trait, module, configuration,
or document exists. Record the highest level supported by evidence:

1. **Declared**: named in docs, types, interfaces, or configuration.
2. **Implemented**: working code exists behind the declaration.
3. **Wired**: the supported runtime path invokes it with real inputs.
4. **Exercised**: tests or runtime evidence cover the intended path and failures.
5. **Measured**: quality and operations are observed against a defined target.

This ladder is not a numeric product score. Use it to expose missing links. For
example, a provider adapter may be implemented but absent from the registry; a
learning pipeline may collect events but lack attribution, decision state, and
outcome verification.

## 4. End-to-end lifecycle

Trace the complete lifecycle rather than stopping at the interesting algorithm:

```text
discover/acquire
  -> validate/normalize
  -> persist/index
  -> decide/rank/execute
  -> deliver
  -> observe/evaluate
  -> correct/learn/retire
```

At every stage ask:

- What is the input contract and failure contract?
- Where is provenance retained or lost?
- How are freshness, duplication, ordering, and partial success handled?
- Who owns quality, and what closes the feedback loop?
- Is the stage online, batch, human-gated, or only described in a prompt?

An architecture is incomplete for the named capability when an essential stage
has no owner, input, state transition, or validation path.

## 5. Quality scenarios and trade-offs

Turn vague goals into scenarios:

```text
When <stimulus> occurs
under <operating condition>,
the system must <response>
measured by <threshold or observable outcome>.
```

Examples include restart recovery, sudden load, provider failure, data deletion,
new model integration, regional outage, or a tenfold corpus increase.

For each high-priority scenario identify:

- Architectural decisions that enable the response.
- **Sensitivity points** where a small design change materially affects a
  quality attribute.
- **Trade-off points** where improving one quality worsens another.
- Risks, non-risks, and the evidence needed to validate the response.

This adapts the scenario and trade-off discipline of the
[CMU SEI Architecture Tradeoff Analysis Method](https://www.sei.cmu.edu/library/architecture-tradeoff-analysis-method-collection/)
without requiring a formal multi-day ATAM review for every decision.

## 6. Operational and economic reality

- What are steady-state and failure-state operational burdens?
- Which queues, rate limits, retries, caches, and backpressure controls exist?
- What are the unit economics at the current workload and next credible scale?
- Which complexity is intrinsic to the capability, and which came from another
  organization's history or hyperscale constraints?
- What skills, on-call ownership, observability, and incident response are
  required?
- Is the build path staged so each milestone is independently useful?

Compare the current scale horizon, not an imagined maximum. Record the trigger
that would justify a more complex design later.

## 7. Adoption viability

Technical fit is necessary but not sufficient for adopting a third-party system.

- Is the project maintained, released, documented, tested, and upgradeable?
- Is governance concentrated, stable, or vulnerable to a single sponsor?
- Are security reporting, dependency updates, CI, code review, and release
  provenance appropriate for this use?
- What license, hosting, data, and vendor terms constrain use or redistribution?
- Can the team operate, patch, fork, or replace it if upstream stalls?

[OpenSSF Scorecard](https://github.com/ossf/scorecard) can supply reproducible
security-health signals, but its own check documentation notes detection limits
and context-dependent applicability. Treat each check as evidence to inspect,
not a universal acceptance threshold.

## 8. Reversibility and review

- Is the choice a reversible component decision or a one-way data/control-plane
  commitment?
- What data export, compatibility boundary, or replacement seam makes exit
  possible?
- What is the smallest validation milestone before deeper commitment?
- Which assumption, metric, price, license, maintenance event, or scale threshold
  should trigger a new review?
- What evidence would reverse the recommendation?

Architecture changes over time. The
[AWS Well-Architected review guidance](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html)
recommends deeper inspection for hard-to-reverse decisions and lightweight,
continuous review as systems evolve. Store the decision date and review trigger
when the evidence is likely to change.
