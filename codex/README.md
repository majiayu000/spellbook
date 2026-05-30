# Codex Adapters

This directory contains **Codex adapters** for real skills in the `skills/` directory.

## Architecture

- **Source of truth**: Real skills live in `skills/<skill-name>/` (standard Claude Code Skill format with SKILL.md, references/, evals/, etc.).
- **Codex consumption**: Each real skill that needs Codex support gets a corresponding adapter in `codex/adapters/<skill-name>/`.

The adapter provides:
- A Codex-optimized prompt / instruction set derived from the real skill.
- Instructions on how Codex users can effectively use the real skill's logic and capabilities.
- Any Codex-specific examples or adaptations.

## Why this structure?

- Keeps the canonical, well-tested logic in one place (the real skill).
- Allows Codex to "adapt" and benefit from the same high-quality skills without duplicating maintenance.
- When a real skill is improved, the adapter can be updated accordingly.

## Current Adapters

- `personal-arsenal-lifecycle-doctor/` — for long-term personal skill health and rot detection (PAIN-1001).
- `xiaohongshu-netfeel-guardian/` — for protecting authentic Chinese creator voice against English-thinking pollution (PAIN-301).

See the README inside each adapter for usage details.

## Relationship to Loose Prompts

Previous experimental standalone prompts (if any) have been consolidated into this structured adapter format. Always prefer the adapter + real skill combination over ad-hoc prompts.
