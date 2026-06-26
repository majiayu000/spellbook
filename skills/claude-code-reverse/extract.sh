#!/usr/bin/env bash
# claude-code-reverse 辅助脚本
# 用法:
#   ./extract.sh              # dump 当前版本的 strings 到 /tmp/cc_strings.txt
#   ./extract.sh dump [ver]   # dump 指定版本
#   ./extract.sh <锚点>        # 在已 dump 的 strings 里截取锚点周围上下文
#   ./extract.sh diff A B 锚点 # 两版本某关键词 sort -u 后 diff
set -euo pipefail

VERSIONS_DIR="$HOME/.local/share/claude/versions"
OUT="/tmp/cc_strings.txt"

resolve_bin() {
  local ver="${1:-}"
  if [[ -z "$ver" ]]; then
    local link
    link=$(readlink "$HOME/.local/bin/claude" 2>/dev/null || true)
    ver=$(printf '%s' "$link" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+$' || true)
  fi
  local bin="$VERSIONS_DIR/$ver"
  [[ -f "$bin" ]] || { echo "binary not found: $bin" >&2; exit 1; }
  printf '%s' "$bin"
}

dump() {
  local bin; bin=$(resolve_bin "${1:-}")
  strings "$bin" > "$OUT"
  echo "dumped $(wc -l < "$OUT" | tr -d ' ') lines -> $OUT  (from $bin)"
}

around() {
  local anchor="$1"
  [[ -f "$OUT" ]] || { echo "run '$0 dump' first" >&2; exit 1; }
  echo "### $anchor ###"
  awk -v a="$anchor" 'index($0,a){i=index($0,a);print substr($0,i>400?i-400:1,1400)}' "$OUT" | head -8
}

diff_versions() {
  local a="$1" b="$2" anchor="$3"
  local fa="/tmp/ccv_$a.txt" fb="/tmp/ccv_$b.txt"
  strings "$VERSIONS_DIR/$a" | grep -iF "$anchor" | sort -u > "$fa"
  strings "$VERSIONS_DIR/$b" | grep -iF "$anchor" | sort -u > "$fb"
  echo "--- $a vs $b  (anchor: $anchor)  [+ = $b 新增] ---"
  diff "$fa" "$fb" || true
}

case "${1:-}" in
  "") dump ;;
  dump) shift; dump "${1:-}" ;;
  diff) shift; diff_versions "$1" "$2" "$3" ;;
  -h|--help) sed -n '1,8p' "$0" ;;
  *) around "$1" ;;
esac
