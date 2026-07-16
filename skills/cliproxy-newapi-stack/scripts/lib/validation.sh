#!/usr/bin/env bash

die() {
  printf 'error: %s\n' "$*" >&2
  exit 2
}

require_uint() {
  local name=$1
  local value=$2

  if [[ ! "$value" =~ ^[0-9]+$ ]]; then
    die "$name must be an unsigned integer"
  fi
}

require_positive_uint() {
  local name=$1
  local value=$2

  require_uint "$name" "$value"
  if [[ "$value" =~ ^0+$ ]]; then
    die "$name must be greater than zero"
  fi
}

require_port() {
  local name=$1
  local value=$2

  require_uint "$name" "$value"
  if (( ${#value} > 5 )); then
    die "$name must be between 1 and 65535"
  fi
  if (( 10#$value < 1 || 10#$value > 65535 )); then
    die "$name must be between 1 and 65535"
  fi
}

require_positive_decimal() {
  local name=$1
  local value=$2
  local nonzero=${value//[.0]/}

  if [[ ! "$value" =~ ^[0-9]+([.][0-9]+)?$ || -z "$nonzero" ]]; then
    die "$name must be a positive decimal"
  fi
}

require_absolute_safe_path() {
  local name=$1
  local value=$2

  if [[ -z "$value" || "$value" != /* ]]; then
    die "$name must be an absolute path"
  fi
  if [[ ! "$value" =~ ^/[A-Za-z0-9._/:+-]+$ ]]; then
    die "$name contains unsupported characters"
  fi
  if [[ "$value" == *"/../"* || "$value" == *"/.." || "$value" == *"//"* ]]; then
    die "$name must not contain path traversal or duplicate slashes"
  fi
}

require_safe_container_name() {
  local name=$1
  local value=$2

  if [[ "$value" == -* || ! "$value" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]]; then
    die "$name must be a Docker container name"
  fi
}

require_safe_docker_image() {
  local name=$1
  local value=$2

  if [[ "$value" == -* || ! "$value" =~ ^[A-Za-z0-9][A-Za-z0-9._/:@-]*$ ]]; then
    die "$name must be a Docker image reference"
  fi
}

require_pinned_docker_image() {
  local name=$1
  local value=$2

  require_safe_docker_image "$name" "$value"
  if [[ ! "$value" =~ @sha256:[0-9a-fA-F]{64}$ ]]; then
    die "$name must use an immutable sha256 digest"
  fi
}

require_safe_host() {
  local name=$1
  local value=$2

  if [[ "$value" == -* || ! "$value" =~ ^[A-Za-z0-9._:-]+$ ]]; then
    die "$name must be a host name or IP address"
  fi
}

require_safe_model_name() {
  local name=$1
  local value=$2

  if [[ "$value" == -* || ! "$value" =~ ^[A-Za-z0-9][A-Za-z0-9._:+/@-]*$ ]]; then
    die "$name must be a model name"
  fi
}

require_loopback_http_origin() {
  local name=$1
  local value=$2

  if [[ ! "$value" =~ ^http://127\.0\.0\.1:([0-9]+)$ ]]; then
    die "$name must be an HTTP loopback origin with an explicit port"
  fi
  require_port "$name port" "${BASH_REMATCH[1]}"
}

require_https_origin() {
  local name=$1
  local value=$2

  if [[ ! "$value" =~ ^https://[A-Za-z0-9][A-Za-z0-9.-]*(:[0-9]+)?$ ]]; then
    die "$name must be an HTTPS origin without a path"
  fi
  if [[ "$value" =~ :([0-9]+)$ ]]; then
    require_port "$name port" "${BASH_REMATCH[1]}"
  fi
}

require_safe_token() {
  local name=$1
  local value=$2

  if [[ -z "$value" || ! "$value" =~ ^[A-Za-z0-9._-]+$ ]]; then
    die "$name contains unsupported characters"
  fi
}

require_safe_ssh_target() {
  local name=$1
  local value=$2

  if [[ "$value" == -* || ! "$value" =~ ^([A-Za-z0-9._~-]+@)?[A-Za-z0-9._:-]+$ ]]; then
    die "$name must be an SSH host or user@host target"
  fi
}

require_safe_timezone() {
  local name=$1
  local value=$2

  if [[ "$value" == -* || ! "$value" =~ ^[A-Za-z0-9_+./-]+$ ]]; then
    die "$name must be an IANA-style timezone"
  fi
}
