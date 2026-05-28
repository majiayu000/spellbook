# Example: Typical Before/After Report (Anonymized)

## Before (Heavy Use for 6 Weeks)

- Active sessions: ~47 GB total (many long debugging threads + old feature work)
- Largest active chat: 8.2 GB (one particularly painful auth + infra incident)
- Stale worktrees: 14 (some over 3 weeks old)
- Large logs: several `logs_2.sqlite*` files > 1.2 GB each
- Thread metadata bloat detected: 3 threads with title/preview > 80k characters each
- Feeling: "Codex takes 12–15 seconds to start and feels heavy when switching anything"

## Actions Taken

1. Created handoff documents for the 4 active repos the user actually cared about continuing.
2. Archived 38 old sessions (everything non-pinned older than 12 days after handoffs).
3. Moved 11 stale worktrees.
4. Rotated oversized logs.
5. Cleaned dead project entries in config.

## After (Same Day)

- Active sessions: 2.8 GB (mostly current 2–3 active threads)
- Archived sessions: 41 GB (still fully accessible, just not loaded)
- Startup time: subjectively "instant" again
- Switching between current threads: fast and pleasant
- Mental load: much lower — user knows exactly which work is "hot" and which is safely in handoff + archive

## Key Lesson

The 8 GB incident thread was archived after a 40-minute handoff document was written. Two weeks later the user needed to look something up from it — they used the handoff + quick `grep` in the archived transcript instead of reopening the giant chat. Much better experience.

This pattern repeated across multiple cleanups.