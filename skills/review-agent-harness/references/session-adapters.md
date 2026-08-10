# Session Adapters

The MVP supports Codex and Claude Code JSONL through
`scripts/collect_evidence.py`. Both adapters consume only explicit files or
explicit roots and emit the same privacy-safe facts envelope.

## Codex

The adapter recognizes `response_item` message, function-call, custom-tool-call,
and tool-output records. It counts user turns, tool calls, edit calls,
validation calls, failures, malformed lines, and unsupported lines. It never emits call ids,
arguments, raw outputs, or source paths.

## Claude Code

The adapter recognizes `user` and `assistant` message records, `tool_use`
blocks, and error-marked `tool_result` blocks. It emits the same normalized
counts as the Codex adapter and never emits tool-use ids or raw inputs.

## Selection

- Use one provider per evidence envelope.
- Prefer exact `--session-file` values.
- Use `--session-root` only for an explicitly authorized recursive boundary.
- The root adapter caps discovery with `--max-session-files`; omitted files
  remain counted.
- Use `--include-request-summaries` only when the decision requires task intent.

These adapters are evidence collectors, not outcome classifiers. Counts and
sanitized summaries route review; the lead still decides whether an observed
Episode supports a finding or dimension state.

For tool-backed later-effect review, `--mechanism-category edit` or
`validation` declares the coarse count being examined. Pair `--episode-role`
with an explicit `--comparison-basis` so baseline and later envelopes state the
comparison instead of inferring it from collection time. The envelope does not
claim that the mechanism caused a result; route mapping and target-owned result
evidence remain required.

## Unsupported Or Drifted Input

Malformed JSONL increments `malformed_lines`; valid but unknown records increment
`unsupported_lines`. Both produce anonymous warnings. A source with no
recognized records is `unobserved`, not present. If a provider changes its
record shape, update synthetic fixtures and patch the adapter before trusting
the new source.
