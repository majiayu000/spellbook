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

if [ $# -eq 2 ]; then
  OUT=$2
  if [ -e "$OUT" ] || [ -L "$OUT" ]; then
    echo "output directory already exists: $OUT" >&2
    exit 73
  fi
  mkdir "$OUT"
else
  OUT=$(mktemp -d "${TMPDIR:-/tmp}/xray-render.XXXXXX")
fi
OUT=$(cd "$OUT" && pwd)

if ! command -v npx >/dev/null 2>&1 || ! npx --no-install playwright --version >/dev/null 2>&1; then
  echo "Playwright CLI is unavailable; install Playwright before rendering" >&2
  exit 69
fi

PAGE_URL=$(python3 - "$PAGE" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).as_uri())
PY
)

npx --no-install playwright screenshot --browser chromium --full-page \
  --viewport-size "1280, 720" "$PAGE_URL" "$OUT/render-wide.png"
npx --no-install playwright screenshot --browser chromium --full-page \
  --viewport-size "390, 844" "$PAGE_URL" "$OUT/render-narrow.png"

echo "wrote $OUT"
