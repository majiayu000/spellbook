#!/usr/bin/env bash
# Top up a NewAPI user's quota directly in SQLite (admin API does not always persist).
#
# Usage:
#   SSH_TARGET=root@host SSH_KEY=~/.ssh/id_ed25519 ./topup.sh <user_id> <quota>
# Example: ./topup.sh 1 1000000000   # 1B quota = USD 2000 at QuotaPerUnit=500000

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=skills/cliproxy-newapi-stack/scripts/lib/validation.sh
. "$SCRIPT_DIR/lib/validation.sh"

: "${SSH_TARGET:?SSH_TARGET required}"
: "${SSH_KEY:=$HOME/.ssh/id_ed25519}"
: "${DB:=/root/newapi/data/one-api.db}"
: "${CONTAINER:=new-api}"

USER_ID="${1:?user_id required}"
QUOTA="${2:?quota integer required}"

require_safe_ssh_target SSH_TARGET "$SSH_TARGET"
require_positive_uint USER_ID "$USER_ID"
require_uint QUOTA "$QUOTA"
require_absolute_safe_path DB "$DB"
require_safe_container_name CONTAINER "$CONTAINER"

ssh -i "$SSH_KEY" -- "$SSH_TARGET" bash -s -- "$USER_ID" "$QUOTA" "$DB" "$CONTAINER" <<'REMOTE'
  set -euo pipefail
  user_id=$1
  quota=$2
  db=$3
  container=$4

  sqlite3 "$db" "UPDATE users SET quota=$quota WHERE id=$user_id;"
  sqlite3 -header -column "$db" "SELECT id, username, quota, used_quota FROM users WHERE id=$user_id;"
  docker restart "$container" >/dev/null
  echo "restarted ${container}"
REMOTE
