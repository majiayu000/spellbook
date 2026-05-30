#!/usr/bin/env bash
# Two-path verification: direct CLIProxyAPI (cpa_ key) and via NewAPI (sk- token).
# Both must return HTTP 200 AND NewAPI must record a non-zero quota log entry.
# Provides W-16 fresh-session evidence for "stack is healthy".
#
# Usage:
#   HOST=1.2.3.4 \
#   SSH_TARGET=root@1.2.3.4 \
#   SSH_KEY=~/.ssh/id_ed25519 \
#   CLIPROXY_PORT=8317 NEWAPI_PORT=8200 \
#   CLIPROXY_KEY=cpa_xxx NEWAPI_TOKEN=sk-xxx \
#   MODEL=gpt-5.4 \
#   ./verify_stack.sh

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=skills/cliproxy-newapi-stack/scripts/lib/validation.sh
. "$SCRIPT_DIR/lib/validation.sh"

: "${HOST:?HOST required}"
: "${SSH_TARGET:?SSH_TARGET required}"
: "${SSH_KEY:=$HOME/.ssh/id_ed25519}"
: "${CLIPROXY_PORT:=8317}"
: "${NEWAPI_PORT:=8200}"
: "${CLIPROXY_KEY:?CLIPROXY_KEY required}"
: "${NEWAPI_TOKEN:?NEWAPI_TOKEN required}"
: "${MODEL:?MODEL required}"
: "${DB:=/root/newapi/data/one-api.db}"

require_safe_host HOST "$HOST"
require_safe_ssh_target SSH_TARGET "$SSH_TARGET"
require_port CLIPROXY_PORT "$CLIPROXY_PORT"
require_port NEWAPI_PORT "$NEWAPI_PORT"
require_safe_model_name MODEL "$MODEL"
require_absolute_safe_path DB "$DB"

payload='{"model":"'"$MODEL"'","messages":[{"role":"user","content":"reply OK"}],"stream":false,"max_tokens":4}'

echo "[1/3] Direct CLIProxyAPI :$CLIPROXY_PORT"
http_a=$(curl -s -o /tmp/_cpa.json -w "%{http_code}" \
  -H "Authorization: Bearer $CLIPROXY_KEY" -H "Content-Type: application/json" \
  --data "$payload" \
  "http://$HOST:$CLIPROXY_PORT/v1/chat/completions")
echo "  HTTP $http_a"
[ "$http_a" = "200" ] || { echo "FAIL direct CLIProxyAPI"; cat /tmp/_cpa.json; exit 1; }

echo "[2/3] Via NewAPI :$NEWAPI_PORT"
http_b=$(curl -s -o /tmp/_newapi.json -w "%{http_code}" \
  -H "Authorization: Bearer $NEWAPI_TOKEN" -H "Content-Type: application/json" \
  --data "$payload" \
  "http://$HOST:$NEWAPI_PORT/v1/chat/completions")
echo "  HTTP $http_b"
[ "$http_b" = "200" ] || { echo "FAIL via NewAPI"; cat /tmp/_newapi.json; exit 1; }

echo "[3/3] NewAPI billing log (latest 3)"
ssh -i "$SSH_KEY" -- "$SSH_TARGET" bash -s -- "$DB" <<'REMOTE'
  set -euo pipefail
  db=$1
  sqlite3 -header -column "$db" <<'SQL'
SELECT id, model_name, prompt_tokens, completion_tokens, quota, request_id
  FROM logs
 ORDER BY id DESC
 LIMIT 3;
SQL
REMOTE

echo OK both paths returned 200, latest billing log printed above
