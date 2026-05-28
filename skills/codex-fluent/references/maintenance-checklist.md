# Codex Fluent — Safe Maintenance Checklist

Use this checklist when running `codex-fluent` in apply mode. Treat every step as mandatory unless you have a very good reason.

## Pre-Apply (Do This Every Time)

- [ ] Ran full diagnosis in report mode first
- [ ] Reviewed sizes and candidates
- [ ] Identified all active repo chats that still matter
- [ ] Created high-quality handoff documents + reactivation prompts for every chat you might want to continue later (see handoff-template.md)
- [ ] Confirmed Codex is not running (or explicitly accepted `--wait-for-codex-exit`)
- [ ] Understand that we only archive, never delete

## Backup Phase

- [ ] Triggered a timestamped backup (the skill does this automatically in apply mode)
- [ ] Know where the backup lives: `~/Documents/Codex/codex-backups/codex-fluent-...`
- [ ] (Optional but recommended) Manually copy the backup to an external drive for very large cleanups

## Archive Decisions

For each candidate the report surfaced, explicitly decide:

- [ ] This session/chat → archive (only after handoff exists)
- [ ] This worktree → archive (stale and not needed)
- [ ] This log → rotate/archive
- [ ] This config entry → safe to prune

## During Apply

- [ ] Skill is running with appropriate flags (usually `--archive-older-than-days X --worktree-older-than-days Y`)
- [ ] Watching for any warnings

## Post-Apply Verification

- [ ] Ran diagnosis again
- [ ] Confirmed active state is now significantly smaller
- [ ] Started a fresh test thread to verify "snappy" feel
- [ ] Can still find and read all archived material if needed
- [ ] (If using the optional metadata repair) Verified that full transcripts are still intact

## After First Successful Maintenance

- [ ] Asked the skill to generate a recurring **report-only** reminder prompt
- [ ] Scheduled it (weekly for heavy use, bi-weekly otherwise)
- [ ] Documented your personal policy (e.g. "archive non-pinned chats older than 10 days after handoff")

## Red Flags — Stop and Re-evaluate

- You feel pressure to archive something without a handoff "just this once"
- The skill suggests touching credentials or global skills you still actively use
- You haven't used the resulting handoff documents in practice yet (they might need improvement)
- Active state is still huge after archiving (there might be other causes — database bloat, many open sidebar threads, etc.)

Remember the goal: **Codex should feel like a sharp, lightweight tool again**, not a heavy application you have to fight. Handoff discipline is what makes aggressive archiving safe.