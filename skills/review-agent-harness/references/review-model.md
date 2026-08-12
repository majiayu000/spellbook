# Review Model

Use this model only after freezing the scope and evidence boundary.

## Evidence States

| State | Meaning |
| --- | --- |
| `present` | An owned mechanism or contract exists. |
| `reachable` | The relevant task or trigger can reach the mechanism. |
| `exercised` | A linked task used it and retained a result. |
| `outcome_supported` | A later comparable task supports the claimed effect. |
| `missing` | Inspection confirms a required mechanism or result is absent. |
| `unobserved` | The authorized evidence cannot decide. |
| `not_applicable` | Inspected scope proves the check does not apply. |

Evidence state is not a pass/fail label. An exercised route may expose a bug,
and a safe denial may be correct behavior. Static configuration proves no more
than `present` unless wiring is inspected.

## Snapshot And Target Truth

Freeze the reviewed snapshot before classification:

- `exact_git_root`: the supplied target is the repository root;
- `inside_git_worktree`: the target is a bounded path inside one repository;
- `contains_nested_git_root`: the supplied target is a container, not the
  repository; retarget before scoring;
- `non_git_directory`: review the explicit filesystem boundary and label it as
  such.

Use the current checkout or explicit filesystem state for current claims.
Historical reports and ledgers are candidate sources only: rerun the mapped
check before retaining, resolving, or reprioritizing a finding.

## Dimension Statuses

- `healthy`: applicable checks have reachable or stronger evidence and no
  unresolved material defect. `learning-retention` additionally requires
  `outcome_supported`.
- `constrained`: the route works partly, but an observed limitation or
  incomplete control reduces confidence.
- `blocked`: a required mechanism, decision, or result is missing.
- `unobserved`: the evidence boundary cannot decide.
- `not_applicable`: evidence proves the dimension or check does not apply.

## Five Dimensions

Each dimension contains exactly three stable checks:

| Dimension | Stable checks |
| --- | --- |
| `task-contract` | `goal-understanding`, `relevant-context`, `scope-boundary` |
| `execution-control` | `instruction-led-start`, `supported-operation`, `permission-boundary` |
| `verification-closure` | `relevant-check`, `failure-repair`, `validate-again` |
| `delivery-safety` | `acceptance-evidence`, `high-risk-approval`, `rollback-recovery` |
| `learning-retention` | `lifecycle-repeat-detection`, `loop-engineering`, `later-validation` |

### Task Contract

Judge whether the task retains one recoverable goal, acceptance boundary,
authoritative context chain, and scope/effect boundary. Plans prove intent, not
delivery. A vague prompt alone is not a finding unless it caused an observed
wrong result or conflicts with an explicit owner.

### Execution Control

Judge reproducible startup, supported operation, and permission boundaries.
Look for project-owned commands, runtime pins, failures, cleanup, sandbox or
approval decisions, and protected external effects. A settings file without an
observed or inspected route proves presence only.

### Verification Closure

Map the final change to the smallest relevant check. Preserve failure,
diagnosis, repair, and final rerun as separate facts. Older output, a broad
unrelated suite, or a check before the last edit does not close verification.

### Delivery Safety

Judge acceptance at the real delivery boundary, risk-appropriate approval, and
rollback or recovery. Local tests cannot prove a deploy, release, merge, or
production recovery result.

### Learning Retention

Judge whether repeated demand becomes a durable Rule, Skill, Hook, script,
test, or owner and remains accurate. Creation or same-window use proves at most
`exercised`; only a later comparable improved result proves
`outcome_supported`.

## Evidence-Bounded Scores

Assign one integer score from 0 through 100 per dimension after resolving its
three checks. Apply the lowest ceiling among applicable checks:

| Check evidence state | Maximum dimension score |
| --- | ---: |
| `present` | 74 |
| `reachable` | 84 |
| `exercised` | 94 |
| `outcome_supported` | 100 |
| `missing` or `unobserved` | 59 |

`not_applicable` checks do not lower the ceiling unless all three checks are
not applicable, in which case the score remains capped at 59. A score is a
compact summary of bounded evidence; it cannot create a finding, prove
effectiveness, or replace the status and rationale. Never compute an overall
score.

## Reconciliation Rules

- Resolve each dimension independently; finding counts do not set status.
- Preserve disagreements and unavailable evidence at lower confidence.
- Emit every distinct eligible causal problem; cap only priority moves at
  three.
- Keep provider-specific claims provider-labelled.
- Do not manufacture a clean result when a required pass did not complete.
- Trace the smallest owner through caller, configuration, and produced output;
  proximity to a failing artifact does not prove ownership.
