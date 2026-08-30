#!/bin/sh
# Render an X-Ray explainer at desktop and mobile widths with Playwright.
# Usage: scripts/render-check.sh <page.html> [new-output-directory]
set -eu

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
  echo "usage: render-check.sh <page.html> [new-output-directory]" >&2
  exit 64
fi

PAGE=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
if [ ! -f "$PAGE" ]; then
  echo "not a file: $PAGE" >&2
  exit 66
fi

if [ $# -eq 2 ] && { [ -e "$2" ] || [ -L "$2" ]; }; then
  echo "output directory already exists: $2" >&2
  exit 73
fi

PLAYWRIGHT_MODE=
if command -v playwright >/dev/null 2>&1 && playwright --version >/dev/null 2>&1; then
  PLAYWRIGHT_MODE=direct
elif command -v npx >/dev/null 2>&1 && npx --no-install playwright --version >/dev/null 2>&1; then
  PLAYWRIGHT_MODE=npx
else
  echo "Playwright CLI is unavailable; install Playwright before rendering" >&2
  exit 69
fi

run_playwright() {
  if [ "$PLAYWRIGHT_MODE" = direct ]; then
    playwright "$@"
  else
    npx --no-install playwright "$@"
  fi
}

CREATED_OUT=
cleanup_failed_render() {
  status=$?
  trap - 0
  if [ "$status" -ne 0 ] && [ -n "$CREATED_OUT" ] && [ -d "$CREATED_OUT" ]; then
    if ! rm -r -- "$CREATED_OUT"; then
      echo "failed to remove incomplete output directory: $CREATED_OUT" >&2
    fi
  fi
  exit "$status"
}
trap cleanup_failed_render 0

if [ $# -eq 2 ]; then
  OUT=$2
  mkdir "$OUT"
else
  OUT=$(mktemp -d "${TMPDIR:-/tmp}/xray-render.XXXXXX")
fi
CREATED_OUT=$OUT
OUT=$(cd "$OUT" && pwd)
CREATED_OUT=$OUT

PAGE_URL=$(python3 - "$PAGE" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).as_uri())
PY
)

run_playwright screenshot --browser chromium --full-page \
  --viewport-size "1280, 720" "$PAGE_URL" "$OUT/render-wide.png"
run_playwright screenshot --browser chromium --full-page \
  --viewport-size "390, 844" "$PAGE_URL" "$OUT/render-narrow.png"

CREATED_OUT=
echo "wrote $OUT"
