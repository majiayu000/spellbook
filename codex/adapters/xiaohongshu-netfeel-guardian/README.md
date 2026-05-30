# Codex Adapter for xiaohongshu-netfeel-guardian

**Real Skill (Source of Truth):** `skills/xiaohongshu-netfeel-guardian/`

This adapter allows Codex to use the logic and capabilities of the real skill for protecting Chinese content creator voice (anti English-thinking / translation tone).

## How to Use in Codex

1. Copy the content of `skills/xiaohongshu-netfeel-guardian/SKILL.md` and relevant references/ (especially the 守护协议 and 平台适配器) into your Codex context or custom instructions.

2. Use the Codex-optimized prompt below (in codex-adapter.md) as your system prompt or per-session instructions when working on Xiaohongshu, WeChat, video scripts, or other Chinese content creation.

3. The adapter is derived from the real skill but tailored for Codex's style.

## Relationship

- Real skill = full implementation, evals, detailed references.
- This adapter = Codex-friendly way to apply the same voice protection logic.

When the real skill is updated, update this adapter accordingly.