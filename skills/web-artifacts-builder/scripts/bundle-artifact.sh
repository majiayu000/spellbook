#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f "index.html" ]]; then
  echo "error: run this script from the artifact project root containing index.html" >&2
  exit 1
fi

if [[ ! -d "node_modules" ]]; then
  echo "error: node_modules not found. Run npm install before bundling." >&2
  exit 1
fi

dist_dir="dist-artifact"
rm -rf "$dist_dir"

npx parcel build index.html --dist-dir "$dist_dir" --no-source-maps

node <<'NODE'
import fs from "node:fs";
import path from "node:path";

const distDir = "dist-artifact";
const htmlPath = path.join(distDir, "index.html");
let html = fs.readFileSync(htmlPath, "utf8");

html = html.replace(/<script([^>]*)src="([^"]+)"([^>]*)><\/script>/g, (_match, before, src, after) => {
  const filePath = path.join(distDir, src.replace(/^\//, ""));
  const code = fs.readFileSync(filePath, "utf8");
  return `<script${before}${after}>${code}</script>`;
});

html = html.replace(/<link([^>]*?)rel="stylesheet"([^>]*?)href="([^"]+)"([^>]*)>/g, (_match, before, middle, href, after) => {
  const filePath = path.join(distDir, href.replace(/^\//, ""));
  const css = fs.readFileSync(filePath, "utf8");
  return `<style${before}${middle}${after}>${css}</style>`;
});

fs.writeFileSync("bundle.html", html);
NODE

echo "Created bundle.html"
