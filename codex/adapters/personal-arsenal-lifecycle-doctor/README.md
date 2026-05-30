# Codex Adapter for personal-arsenal-lifecycle-doctor

**Real Skill (Source of Truth):** `skills/personal-arsenal-lifecycle-doctor/`

This adapter allows Codex to use the logic and capabilities of the real skill.

## How to Use in Codex

1. Copy the content of `skills/personal-arsenal-lifecycle-doctor/SKILL.md` and relevant references/ into your Codex context or custom instructions.

2. Use the Codex-optimized prompt below (in codex-adapter.md) as your system prompt or per-session instructions when you want Codex to perform personal skill health diagnosis, rot detection, upgrade compatibility checks, etc.

3. The adapter is derived from the real skill but tailored for Codex's prompting style (shorter, more direct, Codex-specific examples).

## Relationship

- Real skill = canonical implementation + full details + evals.
- This adapter = Codex-friendly consumption layer.

When the real skill is updated, regenerate or update this adapter accordingly.

For full details, always refer back to the real skill in `skills/`.