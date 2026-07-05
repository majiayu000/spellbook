# Reliable Skill Contract Examples

Use these examples as patterns, not as text to paste blindly.

## Workflow Skill

```text
Forbidden behavior:
- Do not claim PR readiness from green CI alone.

Required alternative:
- Query current head SHA, check rollup, merge state, and GraphQL reviewThreads.

Checkpoint:
- Before merge, rerun the PR gate against the current head.

Done condition:
- Merge command uses --match-head-commit and post-merge PR state is MERGED.

Replay hook:
- Run the PR gate against a known fixture PR and record any false positives.

Drift signal:
- Review comments ask for the same missing evidence twice.
```

## Content Skill

```text
Forbidden behavior:
- Do not invent source facts when the input has no data.

Required alternative:
- Return a blank section or ask for the missing source.

Checkpoint:
- Before final output, scan every factual claim back to an input note or citation.

Done condition:
- Output includes the required sections and no unsupported claims.

Replay hook:
- Run one empty-input fixture and one noisy-input fixture.

Drift signal:
- The skill starts producing generic filler when input is sparse.
```

## Failure Log To Patch

```text
failure_signal:
- User corrected that explicit --extra-root paths were silently ignored.

root_cause:
- The skill documented explicit scanning but the helper filtered missing paths.

patch:
- Add a fail-loud validation checkpoint for explicit paths.

verification:
- Fixture command exits non-zero for a missing explicit path.
```
