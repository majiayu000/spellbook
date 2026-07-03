# Evals — Planted-Bug Fixture

`fixture/` is a deliberately buggy mini-project (Python backend, "sectionsvc"). Every bug is
intentional and catalogued in `expected-findings.json`. **Never "fix" fixture code** — it is eval
ground truth.

## Running an eval

1. Run the skill against the fixture directory (see `evals.json` prompts). Point agents at
   `fixture/` only — they must not read `expected-findings.json` or this README (keep ground truth
   out of `{TARGET_DIR}`).
2. Score: match reported findings against `expected-findings.json` by **file + category**
   (line numbers may drift). Pass = ≥ 8 of the 10 `must_detect` findings.
3. Findings 9 (test-quality) and 10 (concurrency) require the optional dimensions; if the run
   didn't enable them, substitute bonus findings 11/12 into the must set per the notes.

To run the fixture's own tests in isolation:

```bash
cd fixture
uv run --with-requirements requirements.txt python -m pytest tests
```

## Cleanup after a run

The audit writes into the target — delete these from `fixture/` afterwards so the fixture stays
pristine:

```bash
rm -rf fixture/.audit fixture/audit-report-*.md
```
