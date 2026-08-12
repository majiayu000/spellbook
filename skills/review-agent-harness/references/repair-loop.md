# Repair Loop

Keep three claims separate:

1. **Finding exists**: reviewed evidence supports the causal problem.
2. **Repair verified**: a targeted check passes on the repaired final state.
3. **Later effect supported**: a comparable later Episode uses the route and
   improves the outcome without a guardrail regression.

## Finding-Bound Repair

Lock the pre-fix finding id, consequence, owner, evidence, repair route, and
verifier. Route implementation to the smallest owner skill or project workflow.
Do not broaden the repair because neighboring improvements look convenient.

After the edit, run the exact verifier or a justified equivalent on the final
state. Set `repair_state` to:

- `verified` when the target-owned check passes;
- `partial` when only part of the causal chain is repaired;
- `blocked` when the named precondition remains unavailable;
- `not_started` before implementation.

Repair verification does not delete the finding or rewrite its original
severity.

## Longitudinal Effect

Update `learning-retention` to `outcome_supported` only when a later comparable
Episode shows all of these:

- the repaired mechanism was selected through its supported route;
- the task actually exercised it;
- the relevant result improved;
- safety, scope, and delivery guardrails did not regress.

Same-window reruns, configuration presence, Skill installation, and repair
completion are not later outcomes.

For a tool-backed repair, declare `--mechanism-category edit` or `validation`
while collecting both Episodes. Label them `--episode-role baseline` and
`--episode-role later` with the same explicit `--comparison-basis`. The matching
adapter count establishes only coarse exercise; bounded file or policy evidence
must map that category to the repaired route. Establish improvement and
non-regression with target-owned command or artifact references. Tool counts,
failure counts, request summaries, and collection timestamps are never
sufficient outcome evidence by themselves.

## Ledger Safety

Stable ids survive line movement, severity changes, and file renames when the
causal owner remains the same. The ledger marks an omitted open finding
`recheck_required`; only a targeted spot-check may confirm resolution. A
resolution-confirmations document must retain the verifier and bounded evidence
reference. Its verifier must exactly match the verifier locked into the first
ledger entry; changing the verifier requires a new finding identity or an
explicit review of the causal contract. A confirmed resolved id that reappears
is a regression.

```json
{
  "schema_version": 1,
  "kind": "agent-harness-resolution-confirmations",
  "confirmations": [{
    "id": "verification-closure--test-owner--final-state-not-rechecked",
    "verifier": "The targeted final-state check passed.",
    "evidence_ref": {
      "kind": "command",
      "locator": "targeted-test-final-state",
      "claim": "The mapped check passed after the final edit."
    }
  }]
}
```
