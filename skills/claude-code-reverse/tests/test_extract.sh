#!/usr/bin/env bash
set -euo pipefail

skill_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
readonly skill_dir
readonly script="$skill_dir/extract.sh"
test_root=$(mktemp -d)
test_root=$(cd "$test_root" && pwd -P)
readonly test_root
trap 'rm -rf "$test_root"' EXIT

export XDG_CACHE_HOME="$test_root/cache root"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_contains() {
  local output="$1"
  local expected="$2"
  [[ "$output" == *"$expected"* ]] || fail "expected output to contain: $expected"
}

assert_fails() {
  if "$@" >"$test_root/unexpected.stdout" 2>"$test_root/unexpected.stderr"; then
    fail "command unexpectedly succeeded: $*"
  fi
}

file_mode() {
  if stat -f '%Lp' "$1" >/dev/null 2>&1; then
    stat -f '%Lp' "$1"
  else
    stat -c '%a' "$1"
  fi
}

fixture_a="$test_root/fixture a.bin"
fixture_b="$test_root/fixture b.bin"
printf 'prefix\0shared anchor\0only version one\0' > "$fixture_a"
printf 'prefix\0shared anchor\0only version two\0' > "$fixture_b"

info_output=$(bash "$script" info --target "$fixture_a")
assert_contains "$info_output" "path: $fixture_a"
assert_contains "$info_output" "bytes:"
assert_contains "$info_output" "sha256:"

dump_output=$(bash "$script" dump --target "$fixture_a")
assert_contains "$dump_output" "target: $fixture_a"
cache_file=$(printf '%s\n' "$dump_output" | awk -F': ' '$1 == "cache" { print $2 }')
[[ -f "$cache_file" ]] || fail "cache file was not created"
[[ "$cache_file" == "$XDG_CACHE_HOME/claude-code-reverse/"* ]] || fail "cache escaped private cache root"
[[ "$(file_mode "$cache_file")" == "600" ]] || fail "cache file is not mode 600"

search_output=$(bash "$script" search --target "$fixture_a" "shared anchor")
assert_contains "$search_output" "shared anchor"

diff_output=$(bash "$script" diff --target-a "$fixture_a" --target-b "$fixture_b" "only version")
assert_contains "$diff_output" "only version one"
assert_contains "$diff_output" "only version two"

command_output=$(bash "$script" info --target sh)
assert_contains "$command_output" "sha256:"

help_output=$(bash "$script" --help)
assert_contains "$help_output" "--target-a"

fake_home="$test_root/fake home"
fake_versions="$fake_home/versions"
mkdir -p "$fake_home/.local/bin" "$fake_versions"
ln -s "$fixture_a" "$fake_home/.local/bin/claude"
cp "$fixture_a" "$fake_versions/1.2.3"
cp "$fixture_b" "$fake_versions/1.2.4"

legacy_dump=$(HOME="$fake_home" bash "$script")
assert_contains "$legacy_dump" "target: $fake_home/.local/bin/claude"
legacy_search=$(HOME="$fake_home" bash "$script" "shared anchor")
assert_contains "$legacy_search" "shared anchor"
legacy_diff=$(HOME="$fake_home" CLAUDE_CODE_VERSIONS_DIR="$fake_versions" bash "$script" diff 1.2.3 1.2.4 "only version")
assert_contains "$legacy_diff" "only version two"

assert_fails bash "$script" info --target "$test_root/missing.bin"
assert_fails bash "$script" search --target "$fixture_b" "shared anchor"
assert_fails bash "$script" diff --target-a "$fixture_a" --target-b "$fixture_b" ""
assert_fails bash "$script" diff --target-a "$fixture_a" wrong-flag "$fixture_b" "anchor"
assert_fails bash "$script" dump --target
assert_fails bash "$script" info --target ""

printf 'claude-code-reverse extract tests passed\n'
