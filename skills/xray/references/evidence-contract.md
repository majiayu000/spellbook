# Evidence Contract

The explainer may be simple; its evidence standard is not.

## Source Priority

For web research, prefer:

1. Standards, specifications, original papers, official documentation, source code, and first-party datasets.
2. Official release notes, engineering posts, issues, and pull requests.
3. High-quality secondary analysis that identifies its sources.
4. Community discussion as a lead or experience report.
5. Model output only as a search lead, never as evidence.

For repository work, prefer:

1. Current source, tests, schemas, configuration, runtime state, and generated contracts.
2. Current repository documentation.
3. Git history, issues, and pull requests for rationale.
4. Comments and names as hypotheses until verified by reachability or tests.

For incidents, prefer:

1. Persisted records, logs, metrics, request traces, and the running revision.
2. Configuration and source for that exact revision.
3. Design documents and expected behavior.
4. Browser memory or screenshots only when the UI itself is the disputed fact.

## Confidence Language

| Term | Meaning | Use |
|---|---|---|
| Observed | Directly present in the inspected artifact, source, runtime, or data | May be stated as fact with an anchor |
| Corroborated | Supported by independent authoritative evidence | May be stated as fact with sources |
| Inferred | Best causal explanation from observed evidence | Label as inference and show the reasoning |
| Unknown | Material evidence is missing or contradictory | Keep visible; do not fill the gap with a guess |

Use these terms only where uncertainty matters. Do not turn them into a badge system or require one status per paragraph. Agreement between models does not create corroboration because the outputs may share training data or repeat the same unsupported claim.

## Web Research Procedure

1. Search for the exact mechanism, specification, error, symbol, or version.
2. Open the authoritative page rather than citing a search result snippet.
3. Record publication or update dates and applicable versions where they affect the claim.
4. Corroborate behavior-changing or disputed claims with an independent primary source when possible.
5. Save the direct URL and a short note about the supported claim.
6. If sources conflict, identify whether they describe different versions, scopes, defaults, or implementations.

## Research Notes

Keep lightweight notes for pivotal claims before drawing. A compact form may be useful:

```text
claim: The retry happens before provider submission.
evidence: validation returns before submit_request is called.
anchor: services/gateway/request.go :: validateAndSubmit
status: observed
visual: validation gate before the provider boundary
```

This is a thinking aid, not a required schema or deliverable. Use another note shape when it fits the investigation better.

## Failure Rules

- Missing source for a pivotal claim: remove the claim or label it unknown.
- Broken or inaccessible source: find an authoritative replacement or disclose the limitation.
- Documentation disagrees with code: show the difference and identify which version is running.
- Runtime disagrees with local code: resolve the deployed revision before explaining the cause.
- Example not tested or observed: label it illustrative, not evidence.
