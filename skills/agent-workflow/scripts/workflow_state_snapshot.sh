#!/usr/bin/env bash
set -u

target="${1:-.}"

if ! cd "$target" 2>/dev/null; then
  printf 'error: cannot cd to target path: %s\n' "$target" >&2
  exit 2
fi

printf '# Agent Workflow State Snapshot\n\n'
printf 'snapshot_time: %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')"
printf 'cwd: %s\n' "$(pwd -P)"
printf '\n'

printf '## Applicable Parent AGENTS.md\n'
dir="$(pwd -P)"
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
  branch="$(git branch --show-current 2>/dev/null || true)"
  head="$(git rev-parse --short HEAD 2>/dev/null || printf 'unknown')"
  upstream=""
  if upstream_candidate="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)"; then
    upstream="$upstream_candidate"
  fi

  printf 'repo_root: %s\n' "$repo_root"
  printf 'branch: %s\n' "${branch:-detached}"
  printf 'head: %s\n' "$head"
  printf 'upstream: %s\n' "${upstream:-none}"

  printf '\n### Status Short\n'
  if ! git status --short; then
    printf 'error: git status failed\n' >&2
  fi

  printf '\n### Changed Files\n'
  changed_files="$(git diff --name-only 2>/dev/null || true)"
  staged_files="$(git diff --cached --name-only 2>/dev/null || true)"
  untracked_files="$(git ls-files --others --exclude-standard 2>/dev/null || true)"
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
  if ! git diff --stat; then
    printf 'error: git diff --stat failed\n' >&2
  fi
else
  printf 'inside_work_tree: no\n'
fi

printf '\n## Verification Hints\n'
[ -f Cargo.toml ] && printf -- '- Rust: cargo check; cargo test\n'
[ -f package.json ] && printf -- '- TypeScript/JS: inspect package.json scripts; likely npx tsc --noEmit and project test command\n'
[ -f go.mod ] && printf -- '- Go: go build ./...; go test ./...\n'
[ -f pyproject.toml ] && printf -- '- Python: inspect pyproject.toml; likely pytest\n'
[ -f pytest.ini ] && printf -- '- Python: pytest\n'

printf '\n## Handoff Reminder\n'
printf 'Preserve modified files, constraint set or SPEC, verification commands, key decisions, current priority, and L1-L7 summary when VibeGuard applies.\n'
