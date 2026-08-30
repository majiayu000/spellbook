# 2026-08-12 transport-warning benchmark

The companion JSON records a sanitized benchmark result for the Luna Max
transport-warning task. The measured scope is deliberately narrow: one
`gpt-5.6-luna` worker at reasoning effort `max`, followed by isolated
`gpt-5.6-sol` verification at `medium`.

What the record reports and validates:

- Luna usage was 371,636 input tokens (302,080 cached and 69,556 uncached),
  12,210 output tokens, and 7,108 reasoning-output tokens over 259.353 seconds.
- Isolated Sol usage was 39,922 input tokens (30,208 cached and 9,714 uncached),
  341 output tokens, and 38 reasoning-output tokens over 38.940 seconds.
- The measured sequential stages sum to 298.293 seconds and 2.712720 estimated
  credits using `references/rate-card-2026-08-05.json`.
- Worker tests, held-out tests, compilation, and diff checks passed; scope
  violations and correction cycles were zero.
- The corresponding published source change is independently resolvable in
  this repository: implementation commit `3aef0df62c7739ae3c568b594f37c7bbcda36117`
  has baseline parent `f3a68b17159ccf14b75d1c074380971a93c55901`,
  and the validator checks both trees and the three-file change scope.
- Package-local evidence validation always runs separately; published-source Git
  provenance is verified in the Spellbook checkout and explicitly skipped as a
  separate test when an installed copy has no repository context.
- The three listed implementation paths are benchmark result metadata, not
  current PR changed files.

What it does not establish:

- `complete_routed_task_cost` is false. Root-session preflight and dispatch are
  outside the measured scope, as are two invalid nested-CLI transport failures
  and one invalid read-only verification attempt.
- The rate card is a historical estimate, not current pricing. The two
  2026-08-05 entries are historical comparators on the same baseline tree, not
  current-pricing claims or proof that the scoped Max two-stage cost is a
  complete end-to-end result.
- This sample does not establish global optimality or generalize beyond this
  task. The held-out evaluator is represented only by its SHA-256; its contents
  are not included.
- The isolated snapshot commit and tree are retained as historical run
  identifiers, but their Git objects are not included in this repository. Use
  `published_source` for independently resolvable code provenance.
- The validator checks record integrity, arithmetic, published code provenance,
  and privacy. Because raw ledgers and the held-out evaluator contents are
  excluded, it cannot independently replay the historical usage or quality
  results.

Validate the package with:

```text
python3 skills/sol-luna-router/scripts/test_benchmark_evidence.py
```
