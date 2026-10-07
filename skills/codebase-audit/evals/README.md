# Evals — Planted-Bug Fixture

`fixture/` is a deliberately buggy mini-project (Python backend, "sectionsvc"). Every bug is
intentional and catalogued in `expected-findings.json`. **Never "fix" fixture code** — it is eval
ground truth.

## Running an eval

1. Copy `fixture/` to an isolated directory outside this checkout. Run the skill against that
   copy (see `evals.json` prompts). Point agents at the copy only — they must not read
   `expected-findings.json` or this README (keep ground truth out of `{TARGET_DIR}`).
2. Score: match reported findings against `expected-findings.json` by **file + category**
   (line numbers may drift). Pass = ≥ 8 of the 10 `must_detect` findings.
3. Findings 9 (test-quality) and 10 (concurrency) require the optional dimensions; if the run
   didn't enable them, substitute bonus findings 11/12 into the must set per the notes.
4. Record the exact source commit, runtime/model, prompt, enabled dimensions, start/end time,
   actual token/cost fields when available, and before/after target hashes. Score only after
   the agent finishes. List matched findings, misses, unsupported claims and valid findings
   outside the catalogue separately. Catalogue absence alone does not make a finding false.
5. For a comparison, use the same target, prompt, model and verification conditions in both
   runs; load the skill only in the skill run. A single fixture run measures this task, not
   external adoption or general model improvement. Missing usage/cost is unknown, not zero.

To run the fixture's own tests in isolation:

```bash
cd /absolute/path/to/the/isolated-fixture-copy
PYTHONDONTWRITEBYTECODE=1 uv run --with-requirements requirements.txt python -m pytest -p no:cacheprovider tests
```

## Reports and repeat runs

Evals 1–3 explicitly override the skill's default report and ledger writes with a no-write
request. Save their returned report outside the target and confirm target hashes did not
change. A normal skill invocation permits reports under the target and `.audit/` ledger
updates. Never edit or delete files in the original fixture as cleanup.

Eval 4 requires an explicit request to persist a report and ledger in the isolated copy on
both runs. Give reports distinct paths (`audit-report-run-1.md` and `audit-report-run-2.md`)
even when the runs share a date. Preserve that copy and both reports for checking stable IDs, `first_seen`, and
`still-open` classifications. Do not interpret a missed finding as resolved without reading
the affected source. The historical agent-count/output wording is not an acceptance gate;
local passes and explicitly authorized agents follow the current skill contract.
