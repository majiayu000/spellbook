#!/usr/bin/env bash
# Deploy a digest-pinned NewAPI container on loopback of a Linux VPS.
#
# Usage:
#   IMAGE=calciumion/new-api@sha256:<digest> \
#   SSH_TARGET=root@1.2.3.4 SSH_KEY=~/.ssh/id_ed25519 PORT=8200 \
#   ./deploy_newapi.sh

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=skills/cliproxy-newapi-stack/scripts/lib/validation.sh
. "$SCRIPT_DIR/lib/validation.sh"

: "${SSH_TARGET:?SSH_TARGET required (e.g. root@1.2.3.4)}"
: "${SSH_KEY:=$HOME/.ssh/id_ed25519}"
: "${PORT:=8200}"
: "${DATA_DIR:=/root/newapi/data}"
: "${LOGS_DIR:=/root/newapi/logs}"
: "${IMAGE:?IMAGE required; use an immutable image@sha256:digest reference}"
: "${TZ_VAL:=Asia/Shanghai}"

require_safe_ssh_target SSH_TARGET "$SSH_TARGET"
require_port PORT "$PORT"
require_absolute_safe_path DATA_DIR "$DATA_DIR"
require_absolute_safe_path LOGS_DIR "$LOGS_DIR"
require_pinned_docker_image IMAGE "$IMAGE"
require_safe_timezone TZ_VAL "$TZ_VAL"

ssh -i "$SSH_KEY" -- "$SSH_TARGET" bash -s -- \
  "$PORT" "$DATA_DIR" "$LOGS_DIR" "$IMAGE" "$TZ_VAL" <<'REMOTE'
  set -euo pipefail
  port=$1
  data_dir=$2
  logs_dir=$3
  image=$4
  tz_val=$5

  command -v docker >/dev/null || {
    apt-get update
    apt-get install -y docker.io
  }
  systemctl enable --now docker
  mkdir -p -- "$data_dir" "$logs_dir"
  docker pull "$image"
  if docker inspect new-api >/dev/null 2>&1; then
    docker rm -f new-api
  fi
  docker run -d --name new-api --restart unless-stopped \
    -p "127.0.0.1:${port}:3000" \
    -e "TZ=${tz_val}" \
    -v "${data_dir}:/data" \
    -v "${logs_dir}:/app/logs" \
    "$image"
  for _attempt in 1 2 3 4 5 6 7 8 9 10; do
    sleep 2
    if curl -fsS -o /dev/null "http://127.0.0.1:${port}/api/setup"; then
      echo "NewAPI ready on loopback port ${port}"
      exit 0
    fi
  done
  echo "NewAPI did not become ready; recent logs follow" >&2
  docker logs --tail 50 new-api >&2
  exit 1
REMOTE
