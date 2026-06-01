#!/usr/bin/env bash
set -u

workspace="${1:-}"

section() {
  printf '\n## %s\n' "$1"
}

print_path_list() {
  value="${1:-}"
  if [ -z "$value" ]; then
    return 0
  fi
  printf '%s' "$value" | tr ':' '\n' | sed '/^$/d'
}

maybe_limit() {
  limit="${1:-}"
  if [ -n "$limit" ]; then
    head -n "$limit"
  else
    cat
  fi
}

section "System Baseline"
uptime || true
sysctl -n hw.ncpu hw.memsize 2>/dev/null || true
sysctl vm.swapusage 2>/dev/null || true
memory_pressure 2>/dev/null || vm_stat 2>/dev/null || true

section "Top CPU"
ps aux | sort -nrk 3 | maybe_limit "${PROCESS_SAMPLE_LIMIT:-}" || true

section "Top RSS"
ps aux | sort -nrk 6 | maybe_limit "${PROCESS_SAMPLE_LIMIT:-}" || true

section "Editor CLI Status"
if [ -n "${EDITOR_COMMANDS:-}" ]; then
  for cmd in $EDITOR_COMMANDS; do
    if command -v "$cmd" >/dev/null 2>&1; then
      echo "=== $cmd ==="
      command -v "$cmd"
      "$cmd" --version </dev/null 2>/dev/null || true
      "$cmd" --status </dev/null 2>/dev/null || true
    else
      echo "missing_command=$cmd"
    fi
  done
else
  echo "EDITOR_COMMANDS not set; CLI status skipped"
fi

section "Focused Processes"
if [ -n "${EDITOR_PROCESS_QUERY:-}" ]; then
  ps aux | awk 'NR==1 {print; next} $0 ~ pattern {print}' pattern="$EDITOR_PROCESS_QUERY" || true
else
  echo "EDITOR_PROCESS_QUERY not set; focused process filter skipped"
fi

section "Rendering and Input Context"
uname -a 2>/dev/null || true
sw_vers 2>/dev/null || true
if [ -n "${RENDER_PROCESS_QUERY:-}" ]; then
  ps aux | awk 'NR==1 {print; next} $0 ~ pattern {print}' pattern="$RENDER_PROCESS_QUERY" || true
else
  echo "RENDER_PROCESS_QUERY not set; rendering/input process filter skipped"
fi

section "Language Service Processes"
if [ -n "${LANGUAGE_PROCESS_QUERY:-}" ]; then
  ps aux | awk 'NR==1 {print; next} $0 ~ pattern {print}' pattern="$LANGUAGE_PROCESS_QUERY" || true
else
  echo "LANGUAGE_PROCESS_QUERY not set; language-service process filter skipped"
fi

section "Editor Data Sizes"
if [ -n "${EDITOR_DATA_DIRS:-}" ]; then
  while IFS= read -r data_dir; do
    [ -e "$data_dir" ] && du -sh "$data_dir" 2>/dev/null || true
  done <<EOF
$(print_path_list "${EDITOR_DATA_DIRS:-}")
EOF
else
  echo "EDITOR_DATA_DIRS not set; data-size probe skipped"
fi

section "Editor Settings Signals"
if [ -n "${EDITOR_SETTINGS_FILES:-}" ] && [ -n "${SETTINGS_QUERY:-}" ]; then
  while IFS= read -r settings_file; do
    [ -e "$settings_file" ] && rg -n "$SETTINGS_QUERY" "$settings_file" 2>/dev/null || true
  done <<EOF
$(print_path_list "${EDITOR_SETTINGS_FILES:-}")
EOF
else
  echo "EDITOR_SETTINGS_FILES or SETTINGS_QUERY not set; settings probe skipped"
fi

section "Editor Log Signals"
if [ -n "${EDITOR_LOG_DIRS:-}" ] && [ -n "${LOG_SIGNAL_QUERY:-}" ] && [ -n "${LOG_FILE_GLOB:-}" ]; then
  while IFS= read -r logs_dir; do
    if [ -d "$logs_dir" ]; then
      echo "logs_dir=$logs_dir"
      find_args=("$logs_dir" -type f -name "$LOG_FILE_GLOB")
      if [ -n "${LOG_MTIME_DAYS:-}" ]; then
        find_args+=(-mtime "$LOG_MTIME_DAYS")
      fi
      find "${find_args[@]}" \
        -exec rg -n "$LOG_SIGNAL_QUERY" {} + 2>/dev/null |
        maybe_limit "${LOG_SAMPLE_LIMIT:-}" || true
    fi
  done <<EOF
$(print_path_list "${EDITOR_LOG_DIRS:-}")
EOF
else
  echo "EDITOR_LOG_DIRS, LOG_FILE_GLOB, or LOG_SIGNAL_QUERY not set; log probe skipped"
fi

section "Remote Workspace Signals"
if [ -n "${REMOTE_MARKER_PATHS:-}" ]; then
  while IFS= read -r marker_path; do
    [ -e "$marker_path" ] && printf 'marker_exists=%s\n' "$marker_path"
  done <<EOF
$(print_path_list "${REMOTE_MARKER_PATHS:-}")
EOF
else
  echo "REMOTE_MARKER_PATHS not set; remote/container marker probe skipped"
fi

section "Workspace Surface"
if [ -n "$workspace" ] && [ -d "$workspace" ]; then
  scan_root="$workspace"
else
  scan_root="$PWD"
fi
echo "scan_root=$scan_root"

section "Workspace Disk Context"
df -h "$scan_root" 2>/dev/null || true
if [ -n "${WORKSPACE_SIZE_PATHS:-}" ]; then
  while IFS= read -r size_path; do
    [ -e "$size_path" ] && du -sh "$size_path" 2>/dev/null || true
  done <<EOF
$(print_path_list "${WORKSPACE_SIZE_PATHS:-}")
EOF
else
  echo "WORKSPACE_SIZE_PATHS not set; workspace size probe skipped"
fi

if git -C "$scan_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "git_root=$(git -C "$scan_root" rev-parse --show-toplevel 2>/dev/null || true)"
  echo "tracked_files=$(git -C "$scan_root" ls-files 2>/dev/null | wc -l | tr -d ' ')"
  echo "ignored_entries_sample="
  git -C "$scan_root" status --ignored --short -uall 2>/dev/null | maybe_limit "${IGNORED_SAMPLE_LIMIT:-}" || true
else
  echo "not_inside_git_worktree"
fi

if [ -n "${GENERATED_DIR_PATTERNS:-}" ]; then
  {
    while IFS= read -r pattern; do
      [ -n "$pattern" ] || continue
      find_args=("$scan_root")
      if [ -n "${GENERATED_DIR_MAX_DEPTH:-}" ]; then
        find_args+=(-maxdepth "$GENERATED_DIR_MAX_DEPTH")
      fi
      find "${find_args[@]}" -type d -name "$pattern" -prune -print 2>/dev/null || true
    done <<EOF
$(print_path_list "${GENERATED_DIR_PATTERNS:-}")
EOF
  } | awk -v limit="${GENERATED_DIR_SAMPLE_LIMIT:-}" '
    BEGIN { print "generated_dirs_sample=" }
    { count += 1; if (limit == "" || count <= limit) print }
    END { print "generated_dir_count=" count }
  '
else
  echo "GENERATED_DIR_PATTERNS not set; generated directory name scan skipped"
fi
