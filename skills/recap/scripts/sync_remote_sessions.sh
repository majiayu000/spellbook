#!/usr/bin/env bash
# Sync remote ~/.claude/projects session transcripts into
# ~/.claude/remote-sessions/<host>/projects so recap can scan them.
#
# Usage: sync_remote_sessions.sh <ssh-host> [<ssh-host>...]
#        RECAP_SYNC_HOSTS="starlight agentos" sync_remote_sessions.sh
set -uo pipefail

hosts=("$@")
if [ ${#hosts[@]} -eq 0 ] && [ -n "${RECAP_SYNC_HOSTS:-}" ]; then
  read -r -a hosts <<<"$RECAP_SYNC_HOSTS"
fi
if [ ${#hosts[@]} -eq 0 ]; then
  echo "usage: $0 <ssh-host>... (or set RECAP_SYNC_HOSTS)" >&2
  exit 1
fi

dest_base="$HOME/.claude/remote-sessions"
failed=0
for h in "${hosts[@]}"; do
  dest="$dest_base/$h/projects"
  mkdir -p "$dest"
  if rsync -az --timeout=30 \
      --exclude='subagents/' \
      --include='*/' --include='*.jsonl' --exclude='*' \
      --prune-empty-dirs \
      "$h:.claude/projects/" "$dest/"; then
    n=$(find "$dest" -name '*.jsonl' | wc -l | tr -d ' ')
    echo "[recap-sync] $h ok: $n transcripts"
  else
    echo "[recap-sync] $h FAILED (ssh/rsync error)" >&2
    failed=1
  fi
done
exit $failed
