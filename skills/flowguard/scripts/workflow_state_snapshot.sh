#!/usr/bin/env bash
set -u

target="${1:-.}"

if ! cd "$target" 2>/dev/null; then
  printf 'error: cannot cd to target path: %s\n' "$target" >&2
  exit 2
fi

snapshot_cwd="$(pwd -P)"
manifest_root="$snapshot_cwd"

printf '# Flowguard State Snapshot\n\n'
printf 'snapshot_time: %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')"
printf 'cwd: %s\n' "$snapshot_cwd"
printf '\n'

printf '## Applicable Parent AGENTS.md\n'
dir="$snapshot_cwd"
found_agents=0
while :; do
  if [ -f "$dir/AGENTS.md" ]; then
    printf -- '- %s\n' "$dir/AGENTS.md"
    found_agents=1
  fi
  [ "$dir" = "/" ] && break
  next_dir="$(dirname "$dir")"
  [ "$next_dir" = "$dir" ] && break
  dir="$next_dir"
done
if [ "$found_agents" -eq 0 ]; then
  printf -- '- none found in parent path\n'
fi
printf -- '- check nested AGENTS.md before editing files in child directories\n'
printf '\n'

if ! command -v git >/dev/null 2>&1; then
  printf '## Git\n'
  printf 'git_available: no\n'
  exit 0
fi

printf '## Git\n'
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  repo_root="$(git rev-parse --show-toplevel 2>/dev/null || printf 'unknown')"
  if [ "$repo_root" != "unknown" ]; then
    manifest_root="$repo_root"
  fi
  branch="$(git -C "$repo_root" branch --show-current 2>/dev/null || true)"
  head="$(git -C "$repo_root" rev-parse --short HEAD 2>/dev/null || printf 'unknown')"
  upstream=""
  if upstream_candidate="$(git -C "$repo_root" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)"; then
    upstream="$upstream_candidate"
  fi

  printf 'repo_root: %s\n' "$repo_root"
  printf 'branch: %s\n' "${branch:-detached}"
  printf 'head: %s\n' "$head"
  printf 'upstream: %s\n' "${upstream:-none}"

  printf '\n### Status Short\n'
  if ! git -C "$repo_root" status --short; then
    printf 'error: git status failed\n' >&2
  fi

  printf '\n### Changed Files\n'
  changed_files="$(git -C "$repo_root" diff --name-only 2>/dev/null || true)"
  staged_files="$(git -C "$repo_root" diff --cached --name-only 2>/dev/null || true)"
  untracked_files="$(git -C "$repo_root" ls-files --others --exclude-standard 2>/dev/null || true)"
  if [ -n "$changed_files" ] || [ -n "$staged_files" ] || [ -n "$untracked_files" ]; then
    {
      printf '%s\n' "$changed_files"
      printf '%s\n' "$staged_files"
      printf '%s\n' "$untracked_files"
    } | sed '/^$/d' | sort -u
  else
    printf 'none\n'
  fi

  printf '\n### Diff Stat\n'
  if ! git -C "$repo_root" diff --stat; then
    printf 'error: git diff --stat failed\n' >&2
  fi
else
  printf 'inside_work_tree: no\n'
fi

printf '\n## Verification Hints\n'
[ -f "$manifest_root/Cargo.toml" ] && printf -- '- Rust: cargo check; cargo test\n'
[ -f "$manifest_root/package.json" ] && printf -- '- TypeScript/JS: inspect package.json scripts; likely npx tsc --noEmit and project test command\n'
[ -f "$manifest_root/go.mod" ] && printf -- '- Go: go build ./...; go test ./...\n'
[ -f "$manifest_root/pyproject.toml" ] && printf -- '- Python: inspect pyproject.toml; likely pytest\n'
[ -f "$manifest_root/pytest.ini" ] && printf -- '- Python: pytest\n'

printf '\n## Handoff Reminder\n'
printf 'Preserve modified files, constraint set or SPEC, verification commands, key decisions, current priority, and L1-L7 summary when VibeGuard applies.\n'
