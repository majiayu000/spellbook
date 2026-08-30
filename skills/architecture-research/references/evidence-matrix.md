# Evidence Matrix and Decision Template

Use only the sections needed for the decision. Keep cells concise and link each
decision-relevant claim to its evidence ledger entry.

## 1. Capability brief

```markdown
## Capability brief

- User outcome:
- Capability the system must own:
- Decision question:
- Current boundary:
- Missing layer:
- Required now:
- Explicit non-goals:
- Constraints: scale, freshness, latency, quality, privacy, deployment, budget,
  licensing, data ownership
- No-change cost:
- Quality scenarios:
  - When <stimulus> occurs under <condition>, the system must <response>,
    measured by <outcome>.
```

## 2. Candidate map

```markdown
| Candidate | Type | Comparable boundary | Non-comparable boundary | Possible reuse unit | Why included |
|---|---|---|---|---|---|
| Current system | baseline | | | retain / replace | |
| Candidate A | direct / adjacent / component | | | whole / component / protocol / pattern | |
| Candidate B | commercial / open source / standard | | | | |
```

Use `non-comparable` when a product only shares the interface. Do not compare a
browser to a search index or a scraping API to a global discovery system without
making that boundary visible.

## 3. Evidence ledger

```markdown
| ID | Claim | Status | Primary source | Date or revision | Notes / confidence |
|---|---|---|---|---|---|
| E1 | | verified | | | |
| E2 | | inferred | | | reasoning; confidence |
| E3 | | unknown | none public | checked on date | evidence needed |
```

Rules:

- One row may support several matrix cells, but do not cite a source that only
  mentions a feature as proof of its hidden implementation.
- Source code evidence should identify a stable release, commit, or exact path.
- A vendor claim remains a vendor claim unless independently measured.
- Preserve contradictions; explain them instead of selecting the convenient one.

## 4. Architecture and capability comparison

Remove irrelevant rows rather than filling them with guesses.

```markdown
| Layer | Current system | Candidate A | Candidate B | Decision impact |
|---|---|---|---|---|
| Discovery / input acquisition | | | | |
| Frontier / scheduling / queues | | | | |
| Fetch / render | | | | |
| Parse / normalize / extract | | | | |
| Canonicalize / deduplicate | | | | |
| Raw and derived storage | | | | |
| Lexical / vector / graph indexes | | | | |
| Models / features / ranking | | | | |
| Query planning / serving / cache | | | | |
| Freshness / quality evaluation | | | | |
| Abuse resistance / compliance | | | | |
| Deployment / operations | | | | |
| Data ownership / dependencies | | | | |
| License / cost / lock-in | | | | |
```

For any capability that materially affects the decision, add its evidence level:

```markdown
| Capability | Declared | Implemented | Wired | Exercised | Measured | Evidence / gap |
|---|---|---|---|---|---|---|
| | yes/no/unknown | | | | | |
```

Do not collapse the maturity columns into a score. Their purpose is to expose a
missing live path, validation loop, or quality measure.

## 5. Ownership and dependency map

```markdown
request
  -> interface owned by us
  -> processing owned by us or named dependency
  -> data/index owned by us or named provider
  -> ranking owned by us or opaque provider
  -> result and provenance
```

Mark every external runtime dependency. “Self-hosted” is not equivalent to
“independent” when discovery, data, models, or control-plane services still come
from another provider.

For stateful systems, also record authority and recovery:

```markdown
| State | Authority | Durable or ephemeral | Derived from | Restart behavior | Reconciliation |
|---|---|---|---|---|---|
| | | | | | |
```

## 6. Comparable test record

```markdown
## Test record

- Question the test answers:
- Candidate versions:
- Corpus or query set:
- Expected result and scoring rule:
- Environment and hardware:
- Commands or requests:
- Raw result location:
- Result:
- Limitations:
```

If no fair test ran, replace the section with the exact blocker and the future
test that would remove the uncertainty.

## 7. Adoption viability

Include this section when the recommendation introduces an open-source project,
vendor, hosted service, or other externally governed dependency.

```markdown
| Area | Evidence | Risk / decision impact |
|---|---|---|
| Maintenance and releases | | |
| Governance and contributor concentration | | |
| Tests, security, and release provenance | | |
| License and distribution | | |
| Upgrade, operations, and support | | |
| Switching cost and exit path | | |
```

Automated health or security scores are inputs, not acceptance decisions. Check
whether each underlying heuristic applies to this project and workload.

## 8. Decision record

```markdown
## Decision

- Disposition: adopt / adapt / build / defer / retain
- Selected direction:
- Why it fits the current capability brief:
- Reuse unit: whole system / subsystem / component / protocol / data model / pattern
- Quality trade-offs accepted:
- What not to copy:
- Rejected alternatives and reasons:
- Accepted risks:
- Unknowns that remain:
- Evidence that would reverse the decision:
- Smallest validation milestone:
- Verification command or observable success condition:
- Exit path or review trigger:
- Handoff to architecture-foundation: selected components, constraints,
  ownership decisions, unresolved questions, prohibited dependencies
```

Avoid a score that implies false precision. When weighted scoring is truly
useful, ask the user to confirm the criteria and weights before calculating it.
