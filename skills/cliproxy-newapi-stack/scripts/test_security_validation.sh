#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=skills/cliproxy-newapi-stack/scripts/lib/validation.sh
. "$SCRIPT_DIR/lib/validation.sh"

failures=0

assert_pass() {
  local name=$1
  shift
  if ! ("$@"); then
    printf 'FAIL expected pass: %s\n' "$name" >&2
    failures=$((failures + 1))
  fi
}

assert_fail() {
  local name=$1
  shift
  if ("$@") >/dev/null 2>&1; then
    printf 'FAIL expected rejection: %s\n' "$name" >&2
    failures=$((failures + 1))
  fi
}

assert_pass port_valid require_port PORT 8200
assert_fail port_shell_meta require_port PORT '8200;id'
assert_fail port_out_of_range require_port PORT 70000

assert_pass path_valid require_absolute_safe_path DB /root/newapi/data/one-api.db
assert_fail path_quote require_absolute_safe_path DB "/root/newapi/data/one-api.db';id'"
assert_fail path_space require_absolute_safe_path DB '/root/newapi/data/one api.db'
assert_fail path_traversal require_absolute_safe_path DB /root/newapi/../etc/passwd

assert_pass ssh_target_valid require_safe_ssh_target SSH_TARGET root@1.2.3.4
assert_fail ssh_target_option require_safe_ssh_target SSH_TARGET '-oProxyCommand=id'
assert_fail ssh_target_shell_meta require_safe_ssh_target SSH_TARGET 'root@host;id'

assert_pass docker_image_valid require_safe_docker_image IMAGE calciumion/new-api:latest
assert_fail docker_image_option require_safe_docker_image IMAGE '-bad'
assert_fail docker_image_shell_meta require_safe_docker_image IMAGE 'calciumion/new-api:latest;id'

assert_pass container_valid require_safe_container_name CONTAINER new-api
assert_fail container_shell_meta require_safe_container_name CONTAINER 'new-api;id'

assert_pass model_valid require_safe_model_name MODEL gpt-5.4
assert_fail model_json_breakout require_safe_model_name MODEL 'gpt";id'

if ((failures > 0)); then
  exit 1
fi

echo "security validation tests passed"
