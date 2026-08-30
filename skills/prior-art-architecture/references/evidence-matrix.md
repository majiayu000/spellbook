# Evidence Matrix and Decision Template

Use only the sections needed for the decision. Keep cells concise and link each
decision-relevant claim to its evidence ledger entry.

## 1. Capability brief

```markdown
## Capability brief

- User outcome:
- Capability the system must own:
- Current boundary:
- Missing layer:
- Required now:
- Explicit non-goals:
- Constraints: scale, freshness, latency, quality, privacy, deployment, budget,
  licensing, data ownership
- Decision to make:
```

## 2. Candidate map

```markdown
| Candidate | Type | Comparable boundary | Non-comparable boundary | Why included |
|---|---|---|---|---|
| Current system | baseline | | | |
| Candidate A | direct / adjacent / component | | | |
| Candidate B | commercial / open source / standard | | | |
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

## 4. Architecture comparison

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

## 7. Decision record

```markdown
## Decision

- Disposition: adopt / adapt / build / defer
- Selected direction:
- Why it fits the current capability brief:
- Ideas or components to reuse:
- What not to copy:
- Rejected alternatives and reasons:
- Accepted risks:
- Unknowns that remain:
- Evidence that would reverse the decision:
- Smallest validation milestone:
- Verification command or observable success condition:
```

Avoid a score that implies false precision. When weighted scoring is truly
useful, ask the user to confirm the criteria and weights before calculating it.
