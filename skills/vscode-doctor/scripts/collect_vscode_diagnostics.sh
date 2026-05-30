#!/usr/bin/env bash
set -u

workspace="${1:-}"

section() {
  printf '\n## %s\n' "$1"
}

section "System"
uptime || true
sysctl -n hw.ncpu hw.memsize 2>/dev/null || true
sysctl vm.swapusage 2>/dev/null || true
memory_pressure 2>/dev/null || vm_stat 2>/dev/null || true

section "Top CPU"
ps aux | sort -nrk 3 | head -21 || true

section "Top RSS"
ps aux | sort -nrk 6 | head -21 || true

section "Editor CLI (VS Code + Cursor)"
for cmd in code cursor; do
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "=== $cmd ==="
    command -v "$cmd"
    "$cmd" --version || true
    "$cmd" --status 2>/dev/null || true
  fi
done

section "Editor Processes (VS Code + Cursor)"
ps aux | awk 'NR==1 || /Visual Studio Code|Code Helper|Cursor Helper|tsserver|jedi|ruff server|pet server|extension-host|languageServer/ {print}' || true

section "Focused Resource Indicators"
echo "=== WindowServer ==="
ps aux | awk 'NR==1 || /WindowServer/ {print}' || true
echo "=== Renderer CPU Top ==="
ps aux | awk '/Code Helper \(Renderer\)|Cursor Helper \(Renderer\)/ {print}' | sort -k3 -rn | head -10 || true
echo "=== Extension Host / Language Server CPU Top ==="
ps aux | awk '/Code Helper \(Plugin\)|Cursor Helper \(Plugin\)|tsserver|jedi|ruff server|pet server|languageServer/ {print}' | sort -k3 -rn | head -15 || true

section "Hardware Acceleration & argv.json"
for app in Code Cursor; do
  for base in "$HOME/Library/Application Support/$app" "$HOME/.vscode"; do
    if [ -f "$base/argv.json" ]; then
      echo "=== $app argv.json ($base) ==="
      cat "$base/argv.json"
    fi
  done
done

section "Installed Extensions"
if command -v code >/dev/null 2>&1; then
  code --list-extensions --show-versions || true
fi

section "Editor Data Sizes (VS Code + Cursor)"
du -sh \
  "$HOME/Library/Application Support/Code" \
  "$HOME/Library/Application Support/Cursor" \
  "$HOME/Library/Caches/com.microsoft.VSCode" \
  "$HOME/Library/Caches/dev.cursor.Cursor" \
  "$HOME/Library/Caches/com.microsoft.VSCode.ShipIt" \
  "$HOME/.vscode/extensions" \
  "$HOME/Library/Application Support/Code/User/workspaceStorage" \
  2>/dev/null || true

section "Performance Settings (User + Profiles)"
for app in Code Cursor; do
  rg -n \
    'files\.(watcherExclude|exclude)|search\.exclude|git\.(autoRepositoryDetection|autorefresh)|typescript\.|js/ts\.|python\.analysis|jupyter\.|extensions\.auto|editor\.(minimap|codeLens|occurrencesHighlight)|workbench\.(reduceMotion|animation)' \
    "$HOME/Library/Application Support/$app/User/settings.json" \
    "$HOME/Library/Application Support/$app/User/profiles" \
    2>/dev/null || true
done

section "macOS Tahoe Electron Bug Status (2025-2026 Critical)"
echo "NSAutoFillHeuristicControllerEnabled=$(defaults read -g NSAutoFillHeuristicControllerEnabled 2>/dev/null || echo 'not-set')"
echo "CHROME_HEADLESS=$(launchctl getenv CHROME_HEADLESS 2>/dev/null || echo 'not-set')"
sw_vers 2>/dev/null || true

section "Recent VS Code Log Signals"
for app in Code Cursor; do
  logs_dir="$HOME/Library/Application Support/$app/logs"
  if [ -d "$logs_dir" ]; then
    echo "logs_dir=$logs_dir"
    find "$logs_dir" -type f -name '*.log' -mtime -3 \
      -exec rg -o 'Events were dropped|Extension host .*unresponsive|File Watcher|heap out|OOM|crash|unresponsive' {} + 2>/dev/null |
      awk -F: '{counts[$NF]++} END {for (signal in counts) print counts[signal], signal}' |
      sort -nr || true
    find "$logs_dir" -type f -name '*.log' -mtime -3 \
      -exec rg -n --glob '!**/product.json' --glob '!**/sharedprocess.log' \
        'Extension host .*unresponsive|Events were dropped|File Watcher|Failed to create database|Shell execution timed out|heap out|OOM|crash|unresponsive' \
        {} + 2>/dev/null |
      tail -80 || true
  fi
done

section "Workspace Generated Directories"
if [ -n "$workspace" ] && [ -d "$workspace" ]; then
  scan_root="$workspace"
else
  scan_root="$PWD"
fi
echo "scan_root=$scan_root"
generated_dirs_file="$(mktemp "${TMPDIR:-/tmp}/vscode-doctor-generated-dirs.XXXXXX")"
find "$scan_root" -maxdepth 5 -type d \( \
  -name node_modules -o \
  -name target -o \
  -name dist -o \
  -name build -o \
  -name .next -o \
  -name .turbo -o \
  -name .venv -o \
  -name __pycache__ \
\) -prune -print > "$generated_dirs_file" 2>/dev/null || true
echo "generated_dir_counts="
for name in node_modules target dist build .next .turbo .venv __pycache__; do
  count="$(awk -v n="$name" 'BEGIN { c = 0 } { base = $0; sub(/^.*\//, "", base); if (base == n) c++ } END { print c }' "$generated_dirs_file")"
  printf '%s=%s\n' "$name" "$count"
done
echo "total_generated_dirs_depth5=$(wc -l < "$generated_dirs_file" | tr -d ' ')"
entries_depth4=0
sampled_dirs=0
while IFS= read -r generated_dir; do
  sampled_dirs=$((sampled_dirs + 1))
  entry_count="$(find "$generated_dir" -maxdepth 4 -print 2>/dev/null | wc -l | tr -d ' ')"
  entries_depth4=$((entries_depth4 + entry_count))
done < "$generated_dirs_file"
echo "generated_subtree_entries_depth4=$entries_depth4"
echo "generated_subtree_dirs_sampled=$sampled_dirs"
head -120 "$generated_dirs_file" || true
rm -f "$generated_dirs_file"
