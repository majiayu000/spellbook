#!/usr/bin/env bash
set -euo pipefail

readonly claude_versions_dir="${CLAUDE_CODE_VERSIONS_DIR:-$HOME/.local/share/claude/versions}"
readonly cache_root="${XDG_CACHE_HOME:-$HOME/.cache}/claude-code-reverse"

usage() {
  cat <<'EOF'
Read-only string extraction for local files.

Usage:
  extract.sh dump [--target TARGET]
  extract.sh info [--target TARGET]
  extract.sh search [--target TARGET] LITERAL
  extract.sh diff --target-a TARGET_A --target-b TARGET_B LITERAL

Claude Code compatibility:
  extract.sh                         # dump current Claude Code
  extract.sh LITERAL                 # search current Claude Code cache
  extract.sh dump [VERSION]
  extract.sh diff VERSION_A VERSION_B LITERAL

TARGET may be an absolute/relative file path or a command name resolved with
command -v. The target is read but never executed.
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

canonical_file() {
  local candidate="$1"
  local parent base

  [[ -f "$candidate" ]] || die "target is not a regular file: $candidate"
  parent=$(cd "$(dirname "$candidate")" && pwd -P)
  base=$(basename "$candidate")
  printf '%s/%s\n' "$parent" "$base"
}

resolve_claude() {
  local candidate=""

  if [[ -e "$HOME/.local/bin/claude" ]]; then
    candidate="$HOME/.local/bin/claude"
  elif command -v claude >/dev/null 2>&1; then
    candidate=$(command -v claude)
  else
    die "Claude Code not found; pass --target PATH for another local file"
  fi

  canonical_file "$candidate"
}

resolve_target() {
  local requested="${1-}"
  local candidate=""

  [[ -n "$requested" ]] || die "target must not be empty"

  if [[ "$requested" == "claude" ]]; then
    resolve_claude
    return
  fi

  if [[ "$requested" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] && [[ -f "$claude_versions_dir/$requested" ]]; then
    canonical_file "$claude_versions_dir/$requested"
    return
  fi

  if [[ -f "$requested" ]]; then
    canonical_file "$requested"
    return
  fi

  if [[ "$requested" != */* ]] && command -v "$requested" >/dev/null 2>&1; then
    candidate=$(command -v "$requested")
    canonical_file "$candidate"
    return
  fi

  die "target not found: $requested"
}

sha256_file() {
  local target="$1"

  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$target" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$target" | awk '{print $1}'
  else
    die "required SHA-256 tool not found: shasum or sha256sum"
  fi
}

cache_file_for() {
  local target="$1"
  local digest

  digest=$(sha256_file "$target")
  printf '%s/target-%s.strings\n' "$cache_root" "$digest"
}

ensure_cache_dir() {
  umask 077
  mkdir -p "$cache_root"
  chmod 700 "$cache_root"
}

print_info() {
  local target digest bytes

  target=$(resolve_target "${1-}")
  digest=$(sha256_file "$target")
  bytes=$(wc -c < "$target" | tr -d '[:space:]')

  printf 'path: %s\n' "$target"
  printf 'bytes: %s\n' "$bytes"
  printf 'sha256: %s\n' "$digest"
  if command -v file >/dev/null 2>&1; then
    file "$target"
  else
    printf 'file_type: unavailable (command not found: file)\n'
  fi
}

dump_target() {
  local requested="${1-}"
  local target output tmp_file lines

  require_command strings
  target=$(resolve_target "$requested")
  ensure_cache_dir
  output=$(cache_file_for "$target")
  tmp_file=$(mktemp "$cache_root/.strings.XXXXXX")
  trap 'rm -f "$tmp_file"' EXIT

  strings "$target" > "$tmp_file"
  chmod 600 "$tmp_file"
  mv -f "$tmp_file" "$output"
  trap - EXIT
  lines=$(wc -l < "$output" | tr -d '[:space:]')

  printf 'dumped_lines: %s\n' "$lines"
  printf 'target: %s\n' "$target"
  printf 'cache: %s\n' "$output"
}

search_cache() {
  local requested="$1"
  local anchor="$2"
  local target cache_file

  [[ -n "$anchor" ]] || die "search literal must not be empty"
  target=$(resolve_target "$requested")
  cache_file=$(cache_file_for "$target")
  [[ -f "$cache_file" ]] || die "cache not found; run: $0 dump --target '$target'"

  printf '### %s ###\n' "$anchor"
  awk -v anchor="$anchor" '
    index($0, anchor) {
      start = index($0, anchor) - 400
      if (start < 1) start = 1
      print substr($0, start, 1400)
      matches++
      if (matches == 8) exit
    }
  ' "$cache_file"
}

diff_targets() {
  local requested_a="$1"
  local requested_b="$2"
  local anchor="$3"
  local target_a target_b tmp_dir file_a file_b diff_status

  [[ -n "$anchor" ]] || die "diff literal must not be empty"
  require_command strings
  target_a=$(resolve_target "$requested_a")
  target_b=$(resolve_target "$requested_b")
  ensure_cache_dir
  tmp_dir=$(mktemp -d "$cache_root/.diff.XXXXXX")
  trap 'rm -rf "$tmp_dir"' EXIT
  file_a="$tmp_dir/a.txt"
  file_b="$tmp_dir/b.txt"

  strings "$target_a" | awk -v anchor="$anchor" '
    BEGIN { anchor = tolower(anchor) }
    index(tolower($0), anchor) { print }
  ' | LC_ALL=C sort -u > "$file_a"
  strings "$target_b" | awk -v anchor="$anchor" '
    BEGIN { anchor = tolower(anchor) }
    index(tolower($0), anchor) { print }
  ' | LC_ALL=C sort -u > "$file_b"

  printf '%s\n' "--- target_a: $target_a"
  printf '%s\n' "+++ target_b: $target_b"
  set +e
  diff "$file_a" "$file_b"
  diff_status=$?
  set -e
  if [[ "$diff_status" -gt 1 ]]; then
    die "diff command failed with status $diff_status"
  fi

  rm -rf "$tmp_dir"
  trap - EXIT
}

parse_optional_target() {
  if [[ "${1:-}" == "--target" ]]; then
    [[ $# -ge 2 ]] || die "--target requires a value"
    printf '%s\n' "$2"
  elif [[ $# -ge 1 ]]; then
    printf '%s\n' "$1"
  else
    printf 'claude\n'
  fi
}

main() {
  local command="${1:-}"
  local target="claude"

  case "$command" in
    "")
      dump_target claude
      ;;
    -h|--help)
      usage
      ;;
    info|dump)
      shift
      if [[ "${1:-}" == "--target" ]]; then
        [[ $# -eq 2 ]] || die "usage: $command --target TARGET"
        target="$2"
      else
        [[ $# -le 1 ]] || die "usage: $command [--target TARGET]"
        target=$(parse_optional_target "$@")
      fi
      if [[ "$command" == "info" ]]; then
        print_info "$target"
      else
        dump_target "$target"
      fi
      ;;
    search)
      shift
      if [[ "${1:-}" == "--target" ]]; then
        [[ $# -eq 3 ]] || die "usage: search --target TARGET LITERAL"
        search_cache "$2" "$3"
      else
        [[ $# -eq 1 ]] || die "usage: search [--target TARGET] LITERAL"
        search_cache claude "$1"
      fi
      ;;
    diff)
      shift
      if [[ "${1:-}" == "--target-a" ]]; then
        [[ $# -eq 5 ]] || die "usage: diff --target-a TARGET_A --target-b TARGET_B LITERAL"
        [[ "$3" == "--target-b" ]] || die "expected --target-b after TARGET_A"
        diff_targets "$2" "$4" "$5"
      else
        [[ $# -eq 3 ]] || die "usage: diff VERSION_A VERSION_B LITERAL"
        diff_targets "$1" "$2" "$3"
      fi
      ;;
    *)
      [[ $# -eq 1 ]] || die "unknown command: $command"
      search_cache claude "$command"
      ;;
  esac
}

main "$@"
