---
name: codex-log-guard
description: Diagnose excessive Codex local SQLite diagnostic log writes with read-only evidence by default. Use when a user mentions logs_2.sqlite, logs_2.sqlite-wal, block_log_inserts, SSD/TBW wear, or explicitly asks to protect, clean up, verify, or restore Codex diagnostic logging.
---

# Codex Log Guard

## Overview

Diagnose Codex persistent diagnostic logging from local evidence, then give a concise conclusion and the safest next action. Do not make the user choose from a command menu.

## Operating Contract

Select one mode from the current user request:

- `diagnose_only` is the default for check, inspect, explain, or verify requests. It is read-only.
- `protect` requires an explicit request to stop or mitigate log writes. It may install and verify `block_log_inserts`, but it does not delete rows or vacuum files.
- `cleanup` requires an explicit current request to reclaim disk space or clean up logs. It first installs protection when needed, creates and verifies a timestamped backup, and only then deletes log rows and vacuums.
- `restore` requires an explicit request to resume diagnostic logging. It may drop only the known `block_log_inserts` trigger.

Generic wording such as "处理", "修一下", or "止血" selects `protect`, not `cleanup`. Prior approval does not carry into a later run. If the requested write mode is ambiguous, return the `diagnose_only` report and the exact proposed mutation without applying it.

Direct actions:

- Run local read-only file, SQLite schema, row, and open-process checks.
- Apply only the mutation authorized by the selected mode and verify its result.

Escalate before:

- Touching any database outside the two declared Codex log paths, deleting a backup, killing a process, or changing remote telemetry or credentials.

Evidence-backed pushback:

- Reject cleanup when protection is unverified, the backup check failed, or sampled row IDs still move. Cite the exact database path and failed command instead of treating file size as proof.

Feedback loop:

- When a new schema, active path, or false-success signal is confirmed more than once, update this Skill's diagnosis rules and a focused contract test before automating that case.

`agents/openai.yaml` contains discovery UI metadata only; it is not an operational instruction source.

## Default Flow

When the user asks to "check", "看看", "诊断", or asks whether the local machine is affected:

1. Inspect all candidate live database files and schemas:
   - `~/.codex/logs_2.sqlite`
   - `~/.codex/sqlite/logs_2.sqlite`
2. Identify which candidate database is currently held by Codex processes.
3. Check whether `block_log_inserts` already exists on each candidate with a `logs` table.
4. Measure whether `logs` is still being written using `COUNT(*), MIN(id), MAX(id)` samples.
   Treat `MAX(id)` or `MIN(id)` movement with stable `COUNT(*)` as active churn, not necessarily disk growth.
4. Inspect low-level log volume with `TRACE`/`DEBUG` counts and top noisy targets.
5. Check which Codex processes currently hold each candidate database.
6. Return a diagnosis with:
   - current state: healthy / protected / affected historically / actively writing / actively growing on disk / missing database / blocked
   - evidence: file sizes, trigger state, row/min-id/max-id samples, level distribution, active path
   - recommended next action: do nothing / install trigger / cleanup later / cleanup now / restore logging
7. Do not ask the user which command to run. Choose the diagnosis path from the evidence.

In `protect` mode:

1. Install `block_log_inserts` first.
2. Verify that `COUNT(*), MAX(id)` stops growing.
3. Report the protected database path and fresh samples. Do not delete or vacuum rows.

In `cleanup` mode:

1. Complete and verify protection first.
2. Create a timestamped SQLite `.backup` and require a non-empty file plus a successful `PRAGMA quick_check` result.
3. Delete log rows, vacuum, and checkpoint the WAL.
4. Report the backup path and final file sizes.

In `restore` mode:

1. Drop `block_log_inserts`.
2. Sample `COUNT(*), MAX(id)` to confirm logging resumes or stays quiet.

## Evidence Commands

Run direct shell/SQLite commands. Use only the needed subset for the user's request; do not paste a menu back to the user.

Inspect files:

```bash
for db in ~/.codex/logs_2.sqlite ~/.codex/sqlite/logs_2.sqlite; do
  ls -lh "$db"* 2>/dev/null
  du -h "$db"* 2>/dev/null
done
```

After `lsof` identifies the active candidate, validate the selected path in the
same shell command before running any later SQLite snippet:

```bash
: "${CODEX_LOG_DB:?set CODEX_LOG_DB to the verified active candidate}"
case "$CODEX_LOG_DB" in
  "$HOME/.codex/logs_2.sqlite"|"$HOME/.codex/sqlite/logs_2.sqlite") ;;
  *) echo "refusing unexpected Codex log database path" >&2; exit 2 ;;
esac
readonly db="$CODEX_LOG_DB"
```

Do not supply a default. If no active path can be proven, stay in
`diagnose_only` and report the ambiguity.

Check schema and trigger:

```bash
sqlite3 "$db" ".tables"
sqlite3 "$db" "PRAGMA table_info(logs);"
sqlite3 "$db" "SELECT name, tbl_name, sql FROM sqlite_master WHERE type='trigger' AND name='block_log_inserts';"
```

Sample writes and growth:

```bash
for i in 1 2 3; do
  date '+%F %T'
  sqlite3 "$db" "SELECT COUNT(*) AS rows, MIN(id) AS min_id, MAX(id) AS max_id FROM logs;"
  stat -f '%N %z bytes mtime=%Sm' "$db" "$db-wal" "$db-shm" 2>/dev/null
  sleep 10
done
```

Inspect levels and noisy targets:

```bash
sqlite3 "$db" "SELECT level, COUNT(*) AS n, ROUND(SUM(estimated_bytes)/1024.0/1024.0, 1) AS estimated_mib FROM logs GROUP BY level ORDER BY n DESC;"
sqlite3 "$db" "SELECT target, level, COUNT(*) AS n, ROUND(SUM(estimated_bytes)/1024.0/1024.0, 1) AS estimated_mib FROM logs GROUP BY target, level ORDER BY n DESC LIMIT 15;"
```

Check open processes:

```bash
lsof ~/.codex/logs_2.sqlite ~/.codex/logs_2.sqlite-wal ~/.codex/logs_2.sqlite-shm \
     ~/.codex/sqlite/logs_2.sqlite ~/.codex/sqlite/logs_2.sqlite-wal ~/.codex/sqlite/logs_2.sqlite-shm 2>/dev/null
```

Install protection:

```bash
sqlite3 "$db" "PRAGMA busy_timeout=10000; CREATE TRIGGER IF NOT EXISTS block_log_inserts BEFORE INSERT ON logs BEGIN SELECT RAISE(IGNORE); END;"
```

Clean up after protection:

```bash
backup="$db.bak.$(date +%Y%m%d-%H%M%S)"
sqlite3 "$db" ".backup '$backup'"
test -s "$backup"
test "$(sqlite3 "$backup" 'PRAGMA quick_check;')" = "ok"
sqlite3 "$db" "PRAGMA busy_timeout=10000; PRAGMA wal_checkpoint(TRUNCATE); DELETE FROM logs; VACUUM; PRAGMA wal_checkpoint(TRUNCATE);"
echo "$backup"
```

Restore persistent logging:

```bash
sqlite3 "$db" "DROP TRIGGER IF EXISTS block_log_inserts;"
```

## Diagnosis Rules

- Missing all candidate `logs_2.sqlite` files: healthy/not applicable unless the user expects Codex to have run.
- If multiple candidates exist, call out the active path from `lsof`; do not assume the top-level path is the only live database.
- Trigger present and `COUNT/MIN(id)/MAX(id)` stable: protected.
- Trigger absent and `MIN(id)` or `MAX(id)` moves: affected and actively writing.
- If row ids move but file sizes do not materially increase, say "actively writing/churning" rather than "actively growing on disk".
- Trigger absent, database large, high `TRACE`/`DEBUG`, but no sample movement: affected historically; recommend protection, cleanup optional.
- Main DB or WAL above hundreds of MB: recommend cleanup after installing protection if the active path is affected.
- WAL mtime or tiny WAL growth alone is not enough; use row/max-id samples.
- If `logs` is absent or schema differs, stop and report that the known workaround is not safely applicable.

## Safety Rules

- Run read-only diagnosis before write operations unless the user explicitly asks for a specific command.
- Do not claim the issue is fixed from file size alone; verify with `COUNT(*), MAX(id)` sampling.
- Treat `cleanup` as reversible only through its timestamped backup. Mention the backup path in the final answer.
- Do not delete backups automatically.
- If SQLite reports lock or corruption errors, stop and report the exact error. Do not kill Codex processes unless the user explicitly asks.
- This skill only manages Codex local SQLite diagnostic logs (`~/.codex/logs_2.sqlite*` and `~/.codex/sqlite/logs_2.sqlite*`); it does not manage conversation archives, repo files, credentials, or remote telemetry.

## Gotchas

- `COUNT(*)` can stay constant while `MIN(id)` and `MAX(id)` move; classify this as churn, not a quiet database.
- A WAL mtime change alone does not prove material disk growth.
- Two database candidates may exist. Mutate only the path proven active or explicitly selected; never mirror a write to both paths by assumption.
- Protection success does not authorize cleanup. Cleanup success requires a verified backup and fresh final sizes.
- An unknown schema, lock error, failed backup check, or post-write verification failure is a hard error. Do not continue to the next mutation.

## Answer Shape

Keep the user-facing answer short:

1. One-line conclusion.
2. Key evidence in 3-5 bullets.
3. Recommended action and whether it was already applied.
4. Backup path only if cleanup ran.
