# Privacy Boundary

## Default Boundary

Static mode reads only the authorized target repository. It does not discover
user-home Sessions, global settings, installed Plugins, Memory, browser data,
credentials, or sibling repositories.

Session-informed mode requires explicit authorization for each file or exact
root and one named provider. Authorization to inspect Codex does not authorize
Claude Code, and a project review does not authorize global Memory bodies.

## Durable Output Rules

Never persist:

- raw Prompt, assistant response, tool input, or tool output;
- secret values, environment dumps, credential files, or private keys;
- absolute user-home paths or private cache layouts;
- stable Session, thread, task, or tool-call identifiers;
- Memory titles, paths, or bodies;
- source JSONL file names.

The adapters may retain bounded counts, anonymous aliases, sanitized first
request summaries when explicitly enabled, and coarse tool categories such as
edit or validation. They must not retain raw commands.

Durable target binding uses only collector-produced hashes of local directory
identity and bounded target metadata. It never persists the absolute target
path. Rendering and ledger updates require the caller to supply `--target` so
the scripts can recompute the binding before writing.

## Redaction And Failure

Redact secrets, home paths, UUIDs, stable ids, Markdown destinations, and
injected context before evidence enters reconciliation. The findings validator
and renderer scan reader output again.

Malformed or provider-unsupported lines remain visible as anonymous counts and
warnings. If every authorized source is unreadable, malformed, or unsupported,
mark the Session stage `unobserved` or stop; do not replace it with a broader
search.

## Authority Escalation

Ask before:

- adding a Session root after exact files were authorized;
- enabling request summaries;
- reading Memory metadata or bodies;
- reading user-global Rules, Skills, Plugins, or Hooks;
- copying evidence outside the local target or environment-owned scratch.

Separate analysis authority from mutation authority. Reading a Hook or Skill
does not authorize editing, installing, disabling, or deleting it.
