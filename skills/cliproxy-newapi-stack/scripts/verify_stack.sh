#!/usr/bin/env bash
# Verify CLIProxyAPI through loopback, NewAPI through HTTPS, and exact billing.
#
# Usage:
#   SSH_TARGET=root@1.2.3.4 SSH_KEY=~/.ssh/id_ed25519 \
#   CLIPROXY_URL=http://127.0.0.1:8317 NEWAPI_URL=https://api.example.com \
#   CLIPROXY_KEY=cpa_xxx NEWAPI_TOKEN=sk-xxx MODEL=gpt-5.4 \
#   INPUT_USD_PER_M=2.5 OUTPUT_USD_PER_M=15 QUOTA_PER_UNIT=500000 \
#   ./verify_stack.sh

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=skills/cliproxy-newapi-stack/scripts/lib/validation.sh
. "$SCRIPT_DIR/lib/validation.sh"

: "${SSH_TARGET:?SSH_TARGET required}"
: "${SSH_KEY:=$HOME/.ssh/id_ed25519}"
: "${CLIPROXY_URL:=http://127.0.0.1:8317}"
: "${NEWAPI_URL:?NEWAPI_URL required and must use HTTPS}"
: "${CLIPROXY_KEY:?CLIPROXY_KEY required}"
: "${NEWAPI_TOKEN:?NEWAPI_TOKEN required}"
: "${MODEL:?MODEL required}"
: "${INPUT_USD_PER_M:?INPUT_USD_PER_M required}"
: "${OUTPUT_USD_PER_M:?OUTPUT_USD_PER_M required}"
: "${QUOTA_PER_UNIT:=500000}"
: "${MAX_QUOTA_ERROR_RATIO:=0.05}"
: "${DB:=/root/newapi/data/one-api.db}"

require_safe_ssh_target SSH_TARGET "$SSH_TARGET"
require_loopback_http_origin CLIPROXY_URL "$CLIPROXY_URL"
require_https_origin NEWAPI_URL "$NEWAPI_URL"
require_safe_token CLIPROXY_KEY "$CLIPROXY_KEY"
require_safe_token NEWAPI_TOKEN "$NEWAPI_TOKEN"
require_safe_model_name MODEL "$MODEL"
require_positive_decimal INPUT_USD_PER_M "$INPUT_USD_PER_M"
require_positive_decimal OUTPUT_USD_PER_M "$OUTPUT_USD_PER_M"
require_positive_uint QUOTA_PER_UNIT "$QUOTA_PER_UNIT"
require_positive_decimal MAX_QUOTA_ERROR_RATIO "$MAX_QUOTA_ERROR_RATIO"
require_absolute_safe_path DB "$DB"

tmp_dir="$(mktemp -d)"
chmod 700 "$tmp_dir"
trap 'rm -rf "$tmp_dir"' EXIT

nonce="$(date +%s)-$$"
payload='{"model":"'"$MODEL"'","messages":[{"role":"user","content":"billing probe '"$nonce"'; reply OK"}],"stream":false,"max_tokens":4}'

probe() {
  local base_url=$1 token=$2 output=$3 config=$4
  umask 077
  {
    printf 'silent\nshow-error\n'
    printf 'output = "%s"\n' "$output"
    printf 'write-out = "%%{http_code}"\n'
    printf 'request = "POST"\n'
    printf 'url = "%s/v1/chat/completions"\n' "$base_url"
    printf 'header = "Authorization: Bearer %s"\n' "$token"
    printf 'header = "Content-Type: application/json"\n'
  } > "$config"
  curl --config "$config" --data-binary @- <<< "$payload"
  rm -f "$config"
}

echo "[1/3] Direct CLIProxyAPI through loopback tunnel"
http_a="$(probe "$CLIPROXY_URL" "$CLIPROXY_KEY" "$tmp_dir/cpa.json" "$tmp_dir/cpa.curl")"
echo "  HTTP $http_a"
[ "$http_a" = "200" ] || {
  echo "FAIL direct CLIProxyAPI"
  cat "$tmp_dir/cpa.json"
  exit 1
}

echo "[2/3] Via NewAPI HTTPS"
http_b="$(probe "$NEWAPI_URL" "$NEWAPI_TOKEN" "$tmp_dir/newapi.json" "$tmp_dir/newapi.curl")"
echo "  HTTP $http_b"
[ "$http_b" = "200" ] || {
  echo "FAIL via NewAPI"
  cat "$tmp_dir/newapi.json"
  exit 1
}

request_id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("id", ""))' "$tmp_dir/newapi.json")"
require_safe_token request_id "$request_id"

echo "[3/3] Verify matching NewAPI billing log"
ssh -i "$SSH_KEY" -- "$SSH_TARGET" python3 - \
  "$DB" "$request_id" "$MODEL" "$INPUT_USD_PER_M" "$OUTPUT_USD_PER_M" \
  "$QUOTA_PER_UNIT" "$MAX_QUOTA_ERROR_RATIO" <<'PY'
from decimal import Decimal
import sqlite3
import sys


(
    db_path,
    request_id,
    expected_model,
    input_usd_per_m,
    output_usd_per_m,
    quota_per_unit,
    max_error_ratio,
) = sys.argv[1:]
connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
try:
    row = connection.execute(
        "SELECT model_name, prompt_tokens, completion_tokens, quota "
        "FROM logs WHERE request_id = ? ORDER BY id DESC LIMIT 1",
        (request_id,),
    ).fetchone()
finally:
    connection.close()

if row is None:
    raise RuntimeError("matching billing log not found")
model_name, prompt_tokens, completion_tokens, quota = row
if model_name != expected_model:
    raise RuntimeError(
        f"billing log model mismatch: expected {expected_model!r}, got {model_name!r}"
    )
if prompt_tokens is None or completion_tokens is None or quota is None:
    raise RuntimeError(f"billing log has null accounting fields: {row!r}")
error_ratio = Decimal(max_error_ratio)
if error_ratio > Decimal(1):
    raise RuntimeError("MAX_QUOTA_ERROR_RATIO must not exceed 1")
expected_quota = (
    Decimal(prompt_tokens) * Decimal(input_usd_per_m)
    + Decimal(completion_tokens) * Decimal(output_usd_per_m)
) * Decimal(quota_per_unit) / Decimal(1_000_000)
actual_quota = Decimal(quota)
allowed_error = max(Decimal(1), expected_quota * error_ratio)
if abs(actual_quota - expected_quota) > allowed_error:
    raise RuntimeError(
        "billing quota mismatch: "
        f"expected {expected_quota}, got {actual_quota}, tolerance {allowed_error}"
    )
print("model_name\tprompt_tokens\tcompletion_tokens\tquota")
print("\t".join(map(str, row)))
PY

echo "OK both paths returned 200 and the matching billing quota is within tolerance"
