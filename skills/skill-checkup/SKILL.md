---
name: skill-checkup
description: "Read-only checkup of installed agent skills across Claude Code and Codex: broken links or files, same-name copies that drifted apart, descriptions that compete or miss requests their skill already handles, and skills loaded by both agents but used by only one. Use when the user asks to check, audit or tidy their skills, compare Claude Code and Codex skills, asks why a skill did not trigger, or wants to test a reworded description against past requests. For unused Claude Code skills and token cost alone, Claude Code's /skill-doctor is enough. Not for agent config health or raw usage rankings (skill-usage-stats) or policy-driven ownership, exposure and retirement repairs (skill-ecosystem-doctor)."
---

# Skill Checkup

A thin entry point for [skill-checkup](https://github.com/majiayu000/skill-checkup), a
read-only, offline Python tool with no dependencies. It reads installed skill folders
(`~/.claude/skills`, `~/.agents/skills`, `~/.codex/skills`, the current project's
`.claude/skills` and `.agents/skills`, and enabled Claude Code plugins) and local Claude
Code and Codex session logs.

## Operating Contract

- Direct actions: run the checkup, summarize it, and explain the top actions.
- Escalate before: editing, merging, moving or archiving any skill. The tool never does this; only change a skill when the user names that change.
- Evidence-backed pushback: similarity findings and the silent appendix are lexical matches over past requests. Present them as candidates, not verdicts, and check one or two by reading the skill before recommending a change.
- Feedback loop: after an approved wording change, rerun `replay` for that skill and report both rows.

## Run

From the user's current project, so project-level skills are included:

```bash
uvx --from git+https://github.com/majiayu000/skill-checkup@v0.2.1 skill-checkup
```

Without `uvx`: `pipx run --spec git+https://github.com/majiayu000/skill-checkup@v0.2.1 skill-checkup`.

It prints a summary table and the top five actions, and writes the full report to
`./skill-checkup-report.md`. The first run reads up to 90 days of logs and can take a
minute; later runs use a cache in `~/.cache/skill-checkup`.

Useful options:

- `--lang zh` or `--lang en` to match the conversation.
- `--show-examples` only when the user wants to see which of their own requests were matched. Those quotes stay on the machine.
- `--context-tokens 1000000` when the user's model has a 1M-token window; the default assumes 200k.
- `--summary-json summary.json --anonymize` for a counts-only file the user can share.

## Check a reworded description

```bash
uvx --from git+https://github.com/majiayu000/skill-checkup@v0.2.1 skill-checkup replay <skill> --description "<new wording>"
```

Compare the `current` and `new` rows: higher hit@3 with similar steals@1 is better. The
numbers are a lexical proxy, so compare rows rather than reading absolute values.

## Reading the report

| Section | What to do with it |
|---|---|
| Broken | Fix first. Diverged copies: compare, keep one source, make the others identical. |
| Competing | Merge, or rewrite both descriptions so their boundaries differ. |
| One-sided | Loaded by both agents, used by one. Delete the idle copy only when the report says it's safe; when it says the copy is shared, turn the skill off in Claude Code's `/skills` menu instead. Copies in `~/.agents/skills` may also serve Cursor or Gemini CLI. |
| Unused | Archive candidates. Keep emergency tools even if unused. In Claude Code, `/skill-doctor` gives the same list with token costs. |
| Heavy | An estimate; `/context` shows the measured listing size. On a 1M-token model it rarely matters. |
| New skill candidates | Repeated requests worth a skill; confirm with the user before writing one. An item marked "already handled in the body of X" means rewording X's description, not a new skill. |
| Appendix (silent) | Low confidence: mentions and requests look alike. Treat as leads only. |

## Gotchas

- Sessions started by `claude -p`, Agent SDK hosts or `codex exec` count as usage but are excluded from request analysis.
- A Codex turn that reads 8+ skills is treated as an inventory sweep and not counted as use.
- "Unused" only means no use in this machine's logs in the window.
- The default budget estimate assumes a 200k-token window; pass `--context-tokens 1000000` for 1M-token models.
- Optional config `~/.config/skill-checkup/config.json` can list deprecated directories and accepted known issues.
