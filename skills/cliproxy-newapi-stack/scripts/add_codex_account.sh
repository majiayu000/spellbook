#!/usr/bin/env bash
# Add a new OAuth account (codex/claude/qwen/iflow/gemini) to an existing
# CLIProxyAPI deployment by running OAuth locally and syncing the credential
# JSON to the VPS auth-dir. CLIProxyAPI watcher hot-loads the new file —
# no restart needed.
#
# Usage:
#   PROVIDER=codex SSH_TARGET=root@host SSH_KEY=~/.ssh/id_ed25519 \
#     CLIPROXY_LOCAL=/path/to/CLIProxyAPI \
#     ./add_codex_account.sh

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=skills/cliproxy-newapi-stack/scripts/lib/validation.sh
. "$SCRIPT_DIR/lib/validation.sh"

: "${PROVIDER:=codex}"   # one of: codex|claude|qwen|iflow|antigravity|gemini
: "${SSH_TARGET:?SSH_TARGET required}"
: "${SSH_KEY:=$HOME/.ssh/id_ed25519}"
: "${CLIPROXY_LOCAL:=$PWD}"
: "${LOCAL_AUTH_DIR:=$HOME/.cli-proxy-api}"
: "${REMOTE_AUTH_DIR:=/root/.cli-proxy-api}"

case "$PROVIDER" in
  codex)        FLAG=-codex-login        ;;
  claude)       FLAG=-claude-login       ;;
  qwen)         FLAG=-qwen-login         ;;
  iflow)        FLAG=-iflow-login        ;;
  antigravity)  FLAG=-antigravity-login  ;;
  gemini)       FLAG=-login              ;;
  *) echo "unknown PROVIDER=$PROVIDER" >&2; exit 2 ;;
esac

require_safe_ssh_target SSH_TARGET "$SSH_TARGET"
require_absolute_safe_path REMOTE_AUTH_DIR "$REMOTE_AUTH_DIR"

mkdir -p "$LOCAL_AUTH_DIR"
echo ">> Capturing existing credentials before login"
before=$(find "$LOCAL_AUTH_DIR" -maxdepth 1 -type f -name "${PROVIDER}-*.json" -print | sort)

echo ">> Run OAuth in browser for the NEW account (logout/incognito as needed)"
( cd "$CLIPROXY_LOCAL" && go run ./cmd/server "$FLAG" -config config.yaml )

after=$(find "$LOCAL_AUTH_DIR" -maxdepth 1 -type f -name "${PROVIDER}-*.json" -print | sort)
new=$(comm -13 <(printf '%s\n' "$before" | sed '/^$/d') <(printf '%s\n' "$after" | sed '/^$/d') || true)

if [ -z "$new" ]; then
  echo "no new credential file detected; aborting"
  exit 1
fi

echo ">> New credential(s):"
echo "$new"

echo ">> Syncing to $SSH_TARGET:$REMOTE_AUTH_DIR"
ssh -i "$SSH_KEY" -- "$SSH_TARGET" bash -s -- "$REMOTE_AUTH_DIR" <<'REMOTE'
  set -euo pipefail
  remote_auth_dir=$1
  mkdir -p -- "$remote_auth_dir"
REMOTE
while IFS= read -r f; do
  [ -n "$f" ] && scp -i "$SSH_KEY" -- "$f" "$SSH_TARGET:$REMOTE_AUTH_DIR/"
done <<< "$new"

echo ">> Watcher should auto-load. Tailing log for confirmation..."
ssh -i "$SSH_KEY" -- "$SSH_TARGET" \
  "tail -n 100 /root/CLIProxyAPI/cli-proxy-api.log | grep -iE 'auth file changed|added' | tail -n 5"

echo ">> Listing remote credentials"
ssh -i "$SSH_KEY" -- "$SSH_TARGET" bash -s -- "$REMOTE_AUTH_DIR" "$PROVIDER" <<'REMOTE'
  set -euo pipefail
  remote_auth_dir=$1
  provider=$2
  shopt -s nullglob
  files=("${remote_auth_dir}/${provider}-"*.json)
  if ((${#files[@]} == 0)); then
    echo "no remote credentials found for provider ${provider}" >&2
    exit 1
  fi
  ls -l -- "${files[@]}"
REMOTE
