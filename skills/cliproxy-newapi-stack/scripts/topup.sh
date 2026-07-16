#!/usr/bin/env bash
# Set one NewAPI user's quota with a parameterized SQLite update.
#
# Usage:
#   SSH_TARGET=root@host SSH_KEY=~/.ssh/id_ed25519 ./topup.sh <user_id> <quota>

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

ssh -i "$SSH_KEY" -- "$SSH_TARGET" python3 - \
  "$DB" "$CONTAINER" "$USER_ID" "$QUOTA" <<'PY'
import sqlite3
import subprocess
import sys


db_path, container, user_id_raw, quota_raw = sys.argv[1:]
user_id = int(user_id_raw)
quota = int(quota_raw)

connection = sqlite3.connect(f"file:{db_path}?mode=rw", uri=True)
try:
    cursor = connection.execute(
        "UPDATE users SET quota = ? WHERE id = ?",
        (quota, user_id),
    )
    if cursor.rowcount != 1:
        connection.rollback()
        raise RuntimeError(f"expected one user row, updated {cursor.rowcount}")
    row = connection.execute(
        "SELECT id, username, quota, used_quota FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    connection.commit()
finally:
    connection.close()

if row is None:
    raise RuntimeError("updated user could not be read back")

print("id\tusername\tquota\tused_quota")
print("\t".join(map(str, row)))
subprocess.run(
    ["docker", "restart", container],
    check=True,
    stdout=subprocess.DEVNULL,
)
print(f"restarted {container}")
PY
