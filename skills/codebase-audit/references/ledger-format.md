# Findings Ledger Format

Path: `<target>/.audit/findings.json`. Written after every audit (full and quick). Enables
resolved / still-open / new tracking across audits. Suggest gitignoring `.audit/` if the repo is
tracked (do not edit `.gitignore` yourself).

## Schema

```json
{
  "version": 1,
  "audits": [
    { "date": "2026-07-02", "mode": "full", "dimensions": ["contract", "dataflow", "errors", "arch", "config"] }
  ],
  "findings": [
    {
      "id": "errors--app-handlers-py--warning-plus-default-fallback",
      "category": "silent-degradation",
      "severity": "high",
      "file": "app/handlers.py",
      "line": 14,
      "summary": "load_section catches all exceptions and returns DEFAULT_SECTION at warning level",
      "status": "open",
      "verified": true,
      "first_seen": "2026-07-02",
      "last_seen": "2026-07-02"
    }
  ]
}
```

Field notes:
- `id`: stable slug built from `category + file + short root-cause phrase`. Never include line numbers in the id.
- `status`: `open` | `resolved`. Resolved entries stay in the ledger (with their resolution date in `last_seen`) so regressions are detectable.
- `line`: informational only — update it freely on re-audit, never match on it.
- `verified`: `true` (survived adversarial verify) | `false` (refuted — refuted findings are NOT stored in the ledger) | `null` (unverified: medium severity or quick mode).

## Matching rules (previous ledger ↔ current findings)

1. Match on **(category, file)** first; disambiguate multiple candidates by root-cause summary similarity. NEVER match by line number.
2. Current finding matches a previous `open` entry → `still-open`: keep `id` and `first_seen`, update `line`/`last_seen`/`severity`.
3. Current finding has no previous match → `new`: mint an id, `first_seen` = today.
4. Previous `open` entry has no current match → before marking `resolved`, open the file and spot-check: if the issue is actually still present (the finder just missed it), re-add it as `still-open` and note the miss in the report.
5. Current finding matches a previous `resolved` entry → regression: reopen it (`status: open`), keep the original `first_seen`, and flag it as a **regression** in the report.
6. File was renamed/moved → if an unmatched previous entry and an unmatched new finding share category + near-identical summary, treat as the same finding (rename), keep the id.
