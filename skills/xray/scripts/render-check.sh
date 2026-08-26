#!/bin/sh
# Render an X-Ray explainer at desktop and mobile widths with headless Chromium.
# Usage: scripts/render-check.sh <page.html> [chromium-binary]
set -eu

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
  echo "usage: render-check.sh <page.html> [chromium-binary]" >&2
  exit 64
fi

PAGE=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
if [ ! -f "$PAGE" ]; then
  echo "not a file: $PAGE" >&2
  exit 66
fi

if [ $# -eq 2 ]; then
  CHROME=$2
else
  CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  if [ ! -x "$CHROME" ]; then
    CHROME=$(command -v chromium || command -v chromium-browser || command -v google-chrome || true)
  fi
fi
if [ -z "$CHROME" ] || [ ! -x "$CHROME" ]; then
  echo "no Chromium binary found; pass one explicitly" >&2
  exit 69
fi

OUT=$(dirname "$PAGE")
"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --screenshot="$OUT/render-wide.png" --window-size=1280,3000 "file://$PAGE"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --screenshot="$OUT/render-narrow.png" --window-size=390,3000 "file://$PAGE"

echo "wrote $OUT/render-wide.png (1280px) and $OUT/render-narrow.png (390px)"
