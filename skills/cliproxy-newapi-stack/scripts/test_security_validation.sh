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
assert_fail port_overflow require_port PORT 18446744073709559816

assert_pass decimal_integer require_positive_decimal PRICE 15
assert_pass decimal_fraction require_positive_decimal PRICE 0.25
assert_fail decimal_zero require_positive_decimal PRICE 0.0
assert_fail decimal_exponent require_positive_decimal PRICE 1e3

assert_pass path_valid require_absolute_safe_path DB /root/newapi/data/one-api.db
assert_fail path_quote require_absolute_safe_path DB "/root/newapi/data/one-api.db';id'"
assert_fail path_space require_absolute_safe_path DB '/root/newapi/data/one api.db'
assert_fail path_traversal require_absolute_safe_path DB /root/newapi/../etc/passwd

assert_pass ssh_target_valid require_safe_ssh_target SSH_TARGET root@1.2.3.4
assert_fail ssh_target_option require_safe_ssh_target SSH_TARGET '-oProxyCommand=id'
assert_fail ssh_target_shell_meta require_safe_ssh_target SSH_TARGET 'root@host;id'

digest='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
assert_pass docker_image_pinned require_pinned_docker_image IMAGE "calciumion/new-api@sha256:$digest"
assert_fail docker_image_tag require_pinned_docker_image IMAGE calciumion/new-api:latest
assert_fail docker_image_option require_pinned_docker_image IMAGE '-bad'
assert_fail docker_image_short_digest require_pinned_docker_image IMAGE calciumion/new-api@sha256:abcd

assert_pass container_valid require_safe_container_name CONTAINER new-api
assert_fail container_shell_meta require_safe_container_name CONTAINER 'new-api;id'

assert_pass model_valid require_safe_model_name MODEL gpt-5.4
assert_fail model_json_breakout require_safe_model_name MODEL 'gpt";id'

assert_pass loopback_url_valid require_loopback_http_origin URL http://127.0.0.1:8317
assert_fail loopback_url_public require_loopback_http_origin URL http://example.com:8317
assert_fail loopback_url_bad_port require_loopback_http_origin URL http://127.0.0.1:70000

assert_pass https_origin_valid require_https_origin URL https://api.example.com
assert_pass https_origin_port require_https_origin URL https://api.example.com:8443
assert_fail https_origin_http require_https_origin URL http://api.example.com
assert_fail https_origin_path require_https_origin URL https://api.example.com/v1

assert_pass token_valid require_safe_token TOKEN sk_example.test-1
assert_fail token_newline require_safe_token TOKEN $'bad\ntoken'

if ((failures > 0)); then
  exit 1
fi

echo "security validation tests passed"
