# Finding Contract

## Contents

- [Eligibility](#eligibility)
- [Stable Identity](#stable-identity)
- [Required JSON Shape](#required-json-shape)
- [Reconciliation](#reconciliation)
- [Verification](#verification)

## Eligibility

Promote a candidate only when it has all of these:

1. An observed consequence or exact violated governing requirement.
2. A bounded file, command, artifact, policy, runtime, or Session-fact
   reference.
3. A causal explanation and smallest owner.
4. A repair route using discovered project or provider capabilities.
5. A verifier that can distinguish repaired from unrepaired state.

Do not promote counts, search absence without a requirement, similarity,
unavailable evidence, theoretical risk, stale reports, or inventory presence.

## Stable Identity

Build `id` from primary dimension, smallest owner, and root-cause phrase:

```text
verification-closure--test-owner--final-state-not-rechecked
```

Use lowercase slugs with at least three `--`-separated components. Never put a
line number, date, severity, Session id, or transient branch name in the id.

## Required JSON Shape

```json
{
  "schema_version": 1,
  "kind": "agent-harness-findings",
  "overview": "The harness exposes task routes but does not close final-state verification.",
  "scope": {
    "target": "example-project",
    "snapshot": {
      "baseline": "current_checkout",
      "target_relation": "exact_git_root"
    },
    "mode": "static",
    "locale": "en",
    "providers": ["none"],
    "decision": "Assess whether the harness closes the task loop.",
    "acceptance_boundary": "Resolve all five dimensions with bounded evidence states.",
    "output_mode": "durable"
  },
  "evidence_boundary": {
    "included": ["repository-static-evidence"],
    "excluded": ["user-home-discovery", "memory-bodies", "raw-transcripts", "secret-values", "stable-session-identifiers"],
    "unavailable": ["session-evidence:not_authorized"]
  },
  "dimensions": [
    {
      "id": "task-contract",
      "status": "healthy",
      "evidence_state": "reachable",
      "confidence": "medium",
      "score": 80,
      "score_rationale": "All three checks have reachable project-owned routes.",
      "summary": "The repository routes tasks to scoped instructions.",
      "evidence_refs": [
        {
          "kind": "file",
          "locator": "AGENTS.md:1",
          "claim": "The root file declares the task routing boundary."
        }
      ]
    }
  ],
  "checks": [
    {
      "id": "goal-understanding",
      "dimension": "task-contract",
      "status": "healthy",
      "evidence_state": "reachable",
      "confidence": "medium",
      "summary": "The task contract retains a recoverable goal.",
      "evidence_refs": [
        {
          "kind": "file",
          "locator": "AGENTS.md:1",
          "claim": "The root contract defines the task boundary."
        }
      ],
      "finding_refs": []
    }
  ],
  "verification_runs": [
    {
      "id": "targeted-test",
      "purpose": "targeted_reproduction",
      "result": "supports",
      "exit_code": 1,
      "final_state": true,
      "summary": "The final-state reproduction confirms the validation gap."
    }
  ],
  "findings": [
    {
      "id": "verification-closure--test-owner--final-state-not-rechecked",
      "title": "The final edit was not rechecked",
      "severity": "high",
      "confidence": "high",
      "primary_dimension": "verification-closure",
      "primary_check": "validate-again",
      "evidence_state": "exercised",
      "consequence": "Completion was reported without validation on the final state.",
      "root_cause": "The mapped check ran before the last material edit.",
      "owner": "project test workflow",
      "evidence_refs": [
        {
          "kind": "command",
          "locator": "targeted-test",
          "claim": "The retained pass predates the final edit."
        }
      ],
      "repair_route": "Run the mapped check on the final state.",
      "verifier": "The mapped check passes after the last material edit.",
      "verification_state": "confirmed",
      "repair_state": "not_started"
    }
  ],
  "priority_moves": [
    "verification-closure--test-owner--final-state-not-rechecked"
  ]
}
```

The real document must contain all five dimensions exactly once. Valid values
are enforced by `scripts/validate_findings.py`. It must also contain all 15
stable checks exactly once. Each finding names one `primary_check`, and that
check reverse-links the finding id through `finding_refs`.

Each dimension requires `score` and `score_rationale`. The score cannot exceed
the weakest applicable check's evidence ceiling from
[Review Model](review-model.md), and no overall score is permitted. A numeric
score never establishes finding eligibility.

Every executed verifier belongs in `verification_runs`. Critical and High
findings may use `confirmed` only when a command evidence locator matches a
final-state `candidate_refutation` or `targeted_reproduction` run whose result
is `supports`. Preserve both a failing child/subcheck and the aggregate exit
code when diagnosing false-green test wrappers.

For `learning-retention: outcome_supported`, evidence references must cover five
unique purposes: `baseline_episode`, `later_episode`, `route_mapping`,
`outcome_check`, and `guardrail_check`. Baseline and later references use
`kind: session_fact` plus the same `comparison_basis` and
`mechanism_category`. Route mapping uses `file` or `policy`; result and guardrail
checks use `command`, `artifact`, or `runtime`.

The validator also requires exactly two collector-produced evidence envelopes
for this state. They must bind to the same longitudinal findings scope, contain
unique baseline/later roles, share comparison basis and mechanism category, use
a named supported provider, and show the later mechanism was exercised.

## Reconciliation

Keep findings separate when consequence, root cause, owner, or verifier differ.
Merge only duplicate evidence for the same causal problem. Do not delete an
eligible finding to reach a presentation target. Rank at most three ids in
`priority_moves`.

## Verification

Actively try to refute Critical and High findings by opening the named owner and
its caller, guard, config, or final output. Use `confirmed` only when the claim
survives. Use `unverified` or `unavailable` otherwise and keep that limitation
visible. A verifier result is evidence, not permission to repair. Prior reports
are leads only; repeat the mapped check against `scope.snapshot` before using
them as current evidence.
