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

const mimeTypes = {
  ".avif": "image/avif",
  ".gif": "image/gif",
  ".ico": "image/x-icon",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".mp3": "audio/mpeg",
  ".mp4": "video/mp4",
  ".otf": "font/otf",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".ttf": "font/ttf",
  ".webm": "video/webm",
  ".webp": "image/webp",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

const localAssetPattern = /\.(?:avif|gif|ico|jpe?g|mp3|mp4|otf|png|svg|ttf|webm|webp|woff2?)(?:[?#][^"')\s]+)?$/i;

function isExternalReference(ref) {
  return /^(?:data:|https?:|mailto:|tel:|#|javascript:)/i.test(ref);
}

function resolveAsset(ref, baseDir) {
  if (!ref || isExternalReference(ref) || !localAssetPattern.test(ref)) {
    return null;
  }
  const cleanRef = ref.split(/[?#]/, 1)[0];
  const candidates = [
    path.join(baseDir, cleanRef),
    path.join(distDir, cleanRef.replace(/^\//, "")),
  ];
  return candidates.find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile()) ?? null;
}

function toDataUri(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const mime = mimeTypes[ext] ?? "application/octet-stream";
  const data = fs.readFileSync(filePath).toString("base64");
  return `data:${mime};base64,${data}`;
}

function inlineAssetReferences(text, baseDir) {
  let output = text.replace(/url\((["']?)([^"')]+)\1\)/g, (match, quote, ref) => {
    const filePath = resolveAsset(ref.trim(), baseDir);
    if (!filePath) {
      return match;
    }
    return `url(${quote}${toDataUri(filePath)}${quote})`;
  });
  output = output.replace(
    /(["'])(\/?[^"']+\.(?:avif|gif|ico|jpe?g|mp3|mp4|otf|png|svg|ttf|webm|webp|woff2?)(?:[?#][^"']*)?)\1/gi,
    (match, quote, ref) => {
      const filePath = resolveAsset(ref, baseDir);
      if (!filePath) {
        return match;
      }
      return `${quote}${toDataUri(filePath)}${quote}`;
    }
  );
  return output;
}

function inlineHtmlAssetAttributes(text) {
  return text.replace(
    /\b(src|href)=(")([^"]+\.(?:avif|gif|ico|jpe?g|mp3|mp4|otf|png|svg|ttf|webm|webp|woff2?)(?:[?#][^"]*)?)(")/gi,
    (match, attribute, openQuote, ref, closeQuote) => {
      const filePath = resolveAsset(ref, distDir);
      if (!filePath) {
        return match;
      }
      return `${attribute}=${openQuote}${toDataUri(filePath)}${closeQuote}`;
    }
  );
}

html = html.replace(/<script([^>]*)src="([^"]+)"([^>]*)><\/script>/g, (_match, before, src, after) => {
  const filePath = path.join(distDir, src.replace(/^\//, ""));
  const code = inlineAssetReferences(fs.readFileSync(filePath, "utf8"), path.dirname(filePath)).replace(
    /<\/script/gi,
    "<\\/script"
  );
  return `<script${before}${after}>${code}</script>`;
});

html = html.replace(/<link([^>]*?)rel="stylesheet"([^>]*?)href="([^"]+)"([^>]*)>/g, (_match, before, middle, href, after) => {
  const filePath = path.join(distDir, href.replace(/^\//, ""));
  const css = inlineAssetReferences(fs.readFileSync(filePath, "utf8"), path.dirname(filePath));
  return `<style${before}${middle}${after}>${css}</style>`;
});

html = inlineHtmlAssetAttributes(html);

fs.writeFileSync("bundle.html", html);
NODE

echo "Created bundle.html"
