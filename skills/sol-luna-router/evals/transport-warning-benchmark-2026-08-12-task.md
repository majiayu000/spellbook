# Task: preserve recovered transport warnings

The `sol-luna-router` runner consumes Codex JSONL events. A transport-level `error`
event or an `item.completed` event whose item type is `error` can be transient: Codex
may reconnect and later emit a valid final agent message and `turn.completed`.

Implement the following behavior:

1. A run that exits zero and ultimately contains a thread id, final agent message, and
   `turn.completed` must succeed even if transient error events appeared earlier.
2. Preserve those recovered error messages, in event order, in a `warnings` list in the
   parsed result.
3. `turn.failed` remains fatal even if later completion-looking events are present.
4. A nonzero process exit remains fatal and should surface the best available error.
5. A recovered error followed by an incomplete event stream or no final agent message
   must still fail closed for the missing completion evidence.
6. Add focused regression tests for the new behavior without weakening existing tests.

Allowed files:

- `skills/sol-luna-router/scripts/run_luna_worker.py`
- `skills/sol-luna-router/scripts/test_run_luna_worker.py`
- `skills/sol-luna-router/SKILL.md` only if the observable contract needs documentation

Do not inspect other checkouts, external repositories, remote history, or commits beyond
this isolated repository. Do not change generated registries or unrelated files.

Verification:

```bash
python3 skills/sol-luna-router/scripts/test_run_luna_worker.py
python3 -m py_compile skills/sol-luna-router/scripts/run_luna_worker.py
```

Return the root cause, changed files, verification outcomes, and remaining risks.
