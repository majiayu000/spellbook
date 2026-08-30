---
name: prior-art-architecture
description: "Evidence-driven technical prior-art and competitor architecture research before building a new tool, service, subsystem, or major capability. Use when choosing or replacing foundational technology, deciding build vs buy, comparing open-source and commercial implementations, or when the user asks 技术选型, 竞品架构, 同类方案, 开源替代, 商业方案, how is X built, or whether to adopt/adapt/build. Do not use for small mechanical edits, market-only product discovery, or a technology already fixed by the user or repository."
---

# Prior-Art Architecture

Research how comparable systems actually work before committing to a technical
direction. The output is a decision artifact backed by inspectable evidence,
not a feature checklist or a collection of vendor claims.

Read [the evidence matrix and decision template](references/evidence-matrix.md)
before producing the final comparison.

## Operating boundary

Execute read-only discovery, source inspection, local experiments, and drafting
directly. Respect the user's requested access path and repository instructions.

Ask before paid API usage, creating accounts, accepting new legal terms,
publishing findings, changing remote systems, or making a production technology
commitment that the user did not already authorize. Never expose credentials or
copy non-public implementation details into the report.

Do not delay these tasks with this workflow:

- A small bug fix, rename, formatting change, or routine dependency use.
- Work whose foundational technology is explicitly fixed by the user or nearest
  repository instructions.
- Market sizing or customer validation without a technical selection question;
  use a product-discovery workflow instead.

If the requested change is architecturally significant and no comparison exists,
complete the decision artifact before production implementation. If the user
explicitly asks to implement immediately, research only enough to expose the
material alternatives and risks, then proceed within that direction.

## Workflow

### 1. Frame the capability

Write a short capability brief before searching:

- The user outcome and the exact capability the system must own.
- Current system boundary and the missing layer.
- Non-goals, scale horizon, freshness, latency, quality, privacy, deployment,
  budget, licensing, and data-ownership constraints that matter now.
- The decision being made. Examples: library choice, service architecture,
  provider replacement, self-hosted versus managed, or build versus buy.

Challenge category errors early. A browser, API wrapper, scraper, search index,
and answer engine may share a UI but solve different layers.

### 2. Find representative alternatives

Search before proposing architecture. Include the alternatives that materially
change the decision, drawing from:

- Maintained open-source implementations whose source and deployment can be
  inspected.
- Commercial systems with authoritative technical material.
- Standards, public datasets, and lower-level components that enable a build.
- The current system and the option to make no change.

Do not force an arbitrary competitor count or pad the matrix with weak matches.
Classify every candidate as direct, adjacent, component, or non-comparable and
explain why.

### 3. Build an evidence ledger

Prefer primary sources in this order:

1. Source code, tests, manifests, schemas, and reproducible releases.
2. Official technical documentation, papers, patents, and engineering posts.
3. Official product and pricing pages for product-level claims.
4. Independent benchmarks or analysis when methodology and date are available.

For current products, dependencies, pricing, licenses, or architecture, browse
and record the source date or revision. For technical web research, rely on
primary sources for core claims; use secondary sources only to identify leads or
to add clearly attributed independent evaluation.

Tag every decision-relevant statement:

- **Verified**: directly supported by cited code, documentation, or measurement.
- **Inferred**: the evidence supports the conclusion, but the vendor does not
  state it. Include the reasoning and confidence.
- **Unknown**: the public record does not reveal it. State what test or access
  would resolve it.

Never convert marketing language into an architecture fact. A public SDK or MCP
server does not make the search index, crawler fleet, ranking model, or hosted
control plane open source.

### 4. Trace each real architecture

Inspect the path from input to user-visible result. Compare only relevant layers:

- Discovery and input acquisition.
- Scheduling, queues, rate limits, retries, and politeness.
- Fetching, browser rendering, parsing, extraction, and normalization.
- Canonicalization, deduplication, provenance, raw and derived storage.
- Indexes, models, feature generation, ranking, filtering, and reranking.
- Query planning, serving, caching, observability, and failure behavior.
- Quality evaluation, freshness measurement, abuse resistance, and operations.
- Data ownership, external dependencies, deployment model, license, unit cost,
  switching cost, and lock-in.

For open source, inspect the implementation and self-host path rather than only
the README. For closed systems, draw a boundary around what is public and leave
the hidden core unknown.

### 5. Test comparable claims

When practical, run the same small, representative workload against viable
options. Define the query set, corpus, expected result, hardware, version, and
measurement before running it. Measure the property relevant to the decision,
such as coverage, accuracy, freshness, extraction fidelity, latency, throughput,
resource use, or recovery behavior.

Do not present vendor benchmarks or an unrepeatable demo as local proof. If a
fair test cannot be run, state the missing credential, dataset, environment, or
budget and retain the uncertainty.

### 6. Make the decision

Choose one disposition for each useful idea:

- **Adopt**: use the existing solution substantially as supplied.
- **Adapt**: reuse a component or pattern while owning the differentiating layer.
- **Build**: implement the capability because ownership is itself a requirement
  or alternatives fail a named constraint.
- **Defer**: evidence is insufficient or the capability is not needed now.

Tie the recommendation to the capability brief. State what not to copy, which
trade-off is being accepted, what evidence would reverse the choice, and the
smallest validation milestone. A long-term ambition may justify a staged build,
but it does not justify speculative layers in the current implementation.

## Common failure modes

- Comparing feature names instead of system boundaries.
- Treating self-hostable orchestration as ownership of its upstream data source.
- Assuming a commercial product's public client repository contains its core.
- Copying hyperscale architecture before proving a bounded workload.
- Ignoring data acquisition, labeling, freshness, and evaluation while focusing
  only on model or database choice.
- Ranking options with invented precision or weights not supplied by the user.
- Reporting a benchmark without versions, dataset, expected output, and run log.
- Hiding unknowns behind confident prose or silently falling back when research
  access fails.

## Done when

The work is complete only when the decision artifact contains:

- A bounded capability brief and candidate classification.
- An evidence ledger with citations and verified/inferred/unknown labels.
- A layer-by-layer architecture comparison and ownership/dependency map.
- Comparable test evidence, or an explicit explanation of why it is unavailable.
- An adopt/adapt/build/defer decision, rejected alternatives, accepted risks,
  reversal conditions, and a smallest validation milestone.

Before claiming completion, re-open every cited source needed for the decision,
check dates and revisions, and run any repository-provided validation required
for files changed during the task.
