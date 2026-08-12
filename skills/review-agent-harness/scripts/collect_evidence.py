#!/usr/bin/env python3
"""Collect bounded static and explicitly authorized session evidence."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from harness_common import (
    privacy_rule_matches,
    relative_path,
    run_command,
    sanitize_text,
    target_binding,
    write_json_atomic,
)
from session_adapters import (
    MAX_SESSION_BYTES,
    MAX_SESSION_LINE_BYTES,
    MAX_SESSION_LINES,
    MAX_SESSION_WARNINGS,
    SUPPORTED_PROVIDERS,
    discover_jsonl_files,
    parse_sessions,
)


SKIP_DIRS = {
    ".git",
    ".agent-harness-review",
    ".venv",
    "build",
    "dist",
    "node_modules",
    "target",
    "vendor",
}
SKIP_RELATIVE_PREFIXES = {
    ".agent-harness-review",
    ".claude/worktrees",
    ".qoder/better-harness",
}
INSTRUCTION_NAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "WARP.md",
    "CONTRIBUTING.md",
    "copilot-instructions.md",
}
MANIFEST_NAMES = {
    "Cargo.toml",
    "go.mod",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Makefile",
}
HOOK_NAMES = {
    "hooks.json",
    "settings.json",
    "settings.local.json",
    "config.toml",
}
TEST_DIRECTORY_NAMES = {"test", "tests", "spec", "specs", "__tests__"}
DOCUMENTATION_DIRECTORY_NAMES = {"doc", "docs", "documentation"}
TEST_FILE_RE = re.compile(
    r"(?:^test(?:[._-].+)?|.+[._-](?:test|tests|spec))\."
    r"(?:py|js|jsx|ts|tsx|mjs|cjs|rs|go|rb|java|kt|kts|cs|php|swift|sh|bash|zsh|bats|feature)$",
    re.IGNORECASE,
)
NESTED_GIT_SEARCH_MAX_DEPTH = 6
NESTED_GIT_SEARCH_MAX_DIRECTORIES = 3000
NESTED_GIT_ROOT_OUTPUT_LIMIT = 20


def _raise_walk_error(error: OSError) -> None:
    raise error


def _bounded_files(
    root: Path,
    *,
    max_depth: int = 6,
    limit: int = 3000,
    blocked_roots: set[Path] | None = None,
) -> tuple[list[Path], int, list[str]]:
    files: list[Path] = []
    omitted = 0
    depth_limited: list[str] = []
    blocked = {path.resolve() for path in (blocked_roots or set())}
    for current, directories, names in os.walk(root, onerror=_raise_walk_error):
        current_path = Path(current)
        depth = len(current_path.relative_to(root).parts)
        kept_directories: list[str] = []
        for directory in sorted(directories):
            candidate = current_path / directory
            relative = candidate.relative_to(root).as_posix()
            if directory in SKIP_DIRS or candidate.resolve() in blocked:
                continue
            if any(relative == prefix or relative.startswith(f"{prefix}/") for prefix in SKIP_RELATIVE_PREFIXES):
                continue
            kept_directories.append(directory)
        directories[:] = kept_directories
        if depth >= max_depth:
            depth_limited.extend(
                (current_path / directory).relative_to(root).as_posix()
                for directory in directories
            )
            directories[:] = []
        for name in sorted(names):
            path = current_path / name
            if len(files) < limit:
                files.append(path)
            else:
                omitted += 1
    return files, omitted, sorted(depth_limited)


def _find_nested_git_roots(
    target: Path,
    *,
    max_depth: int = NESTED_GIT_SEARCH_MAX_DEPTH,
    max_directories: int = NESTED_GIT_SEARCH_MAX_DIRECTORIES,
) -> tuple[list[Path], list[str], bool]:
    """Find nested Git roots without following links or leaving the target."""

    nested_roots: list[Path] = []
    depth_limited: list[str] = []
    pending: deque[tuple[Path, int]] = deque([(target, 0)])
    directories_observed = 0
    directory_limit_reached = False
    while pending:
        current, depth = pending.popleft()
        try:
            with os.scandir(current) as iterator:
                entries = sorted(iterator, key=lambda entry: entry.name)
        except OSError:
            raise
        for entry in entries:
            if entry.name == ".git":
                continue
            if not entry.is_dir(follow_symlinks=False):
                continue
            if directories_observed >= max_directories:
                directory_limit_reached = True
                pending.clear()
                break
            directories_observed += 1
            candidate = Path(entry.path)
            relative = candidate.relative_to(target).as_posix()
            candidate_depth = depth + 1
            if candidate_depth > max_depth:
                depth_limited.append(relative)
                continue
            git_marker = candidate / ".git"
            if not git_marker.is_symlink() and (git_marker.is_dir() or git_marker.is_file()):
                nested_roots.append(candidate)
                continue
            pending.append((candidate, candidate_depth))
    return nested_roots, sorted(depth_limited), directory_limit_reached


def _target_resolution(target: Path) -> tuple[dict[str, object], Path | None, set[Path]]:
    root_result = run_command(["git", "rev-parse", "--show-toplevel"], cwd=target)
    if root_result["status"] == "available" and root_result["exit_code"] == 0:
        git_root = Path(str(root_result["stdout"]).strip()).resolve()
        relation = "exact_git_root" if git_root == target else "inside_git_worktree"
        return {
            "status": "available",
            "relation": relation,
            "git_root_name": git_root.name,
            "nested_git_roots": [],
            "nested_git_root_count": 0,
            "nested_git_search_max_depth": NESTED_GIT_SEARCH_MAX_DEPTH,
            "nested_git_search_complete": True,
        }, git_root, set()

    try:
        nested_roots, depth_limited, directory_limit_reached = _find_nested_git_roots(target)
    except OSError as error:
        return {
            "status": "unavailable",
            "relation": "unknown",
            "reason": sanitize_text(error, limit=180),
            "nested_git_roots": [],
            "nested_git_root_count": 0,
            "nested_git_search_max_depth": NESTED_GIT_SEARCH_MAX_DEPTH,
            "nested_git_search_complete": False,
        }, None, set()
    names = [path.relative_to(target).as_posix() for path in nested_roots]
    search_complete = not depth_limited and not directory_limit_reached
    if nested_roots:
        multiple_roots = len(nested_roots) > 1
        return {
            "status": "constrained",
            "relation": "contains_nested_git_root",
            "reason": (
                "multiple-nested-git-roots-require-explicit-target"
                if multiple_roots
                else "target-is-not-the-nested-git-root"
            ),
            "nested_git_roots": names[:NESTED_GIT_ROOT_OUTPUT_LIMIT],
            "nested_git_root_count": len(names),
            "nested_git_roots_omitted": max(0, len(names) - NESTED_GIT_ROOT_OUTPUT_LIMIT),
            "nested_git_search_max_depth": NESTED_GIT_SEARCH_MAX_DEPTH,
            "nested_git_search_complete": search_complete,
            "nested_git_search_depth_limited_count": len(depth_limited),
            "nested_git_search_directory_limit_reached": directory_limit_reached,
        }, None, set(nested_roots)
    return {
        "status": "available" if search_complete else "constrained",
        "relation": "non_git_directory",
        "reason": None if search_complete else "nested-git-root-search-bounded",
        "nested_git_roots": [],
        "nested_git_root_count": 0,
        "nested_git_search_max_depth": NESTED_GIT_SEARCH_MAX_DEPTH,
        "nested_git_search_complete": search_complete,
        "nested_git_search_depth_limited_count": len(depth_limited),
        "nested_git_search_directory_limit_reached": directory_limit_reached,
    }, None, set()


def _git_inventory(target: Path, git_root: Path, *, limit: int = 3000) -> tuple[list[Path], int]:
    relative_target = target.relative_to(git_root).as_posix() or "."
    result = run_command(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", relative_target],
        cwd=git_root,
    )
    if result["status"] != "available" or result["exit_code"] != 0:
        raise RuntimeError(str(result.get("stderr") or "git inventory failed"))
    candidates: list[Path] = []
    for line in str(result["stdout"]).splitlines():
        path = git_root / line
        relative = relative_path(path, target)
        if relative is None:
            continue
        if any(relative == prefix or relative.startswith(f"{prefix}/") for prefix in SKIP_RELATIVE_PREFIXES):
            continue
        if path.is_file() or path.is_symlink():
            candidates.append(path)
    candidates.sort(key=lambda path: relative_path(path, target) or "")
    return candidates[:limit], max(0, len(candidates) - limit)


def _relative_list(paths: list[Path], root: Path, *, limit: int = 80) -> dict[str, object]:
    relative = sorted(filter(None, (relative_path(path, root) for path in paths)))
    return {
        "items": relative[:limit],
        "total": len(relative),
        "omitted": max(0, len(relative) - limit),
    }


def _is_test_path(path: Path, target: Path) -> bool:
    relative = relative_path(path, target)
    if relative is None:
        return False
    parts = tuple(part.lower() for part in Path(relative).parts)
    directories = parts[:-1]
    if any(part in DOCUMENTATION_DIRECTORY_NAMES for part in directories):
        return False
    return any(part in TEST_DIRECTORY_NAMES for part in directories) or bool(TEST_FILE_RE.search(parts[-1]))


def _package_scripts(target: Path) -> dict[str, object]:
    package_path = target / "package.json"
    if not package_path.is_file():
        return {"status": "not_applicable", "items": []}
    if package_path.is_symlink() or relative_path(package_path, target) is None:
        return {"status": "unavailable", "reason": "manifest-resolves-outside-target", "items": []}
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {"status": "unavailable", "error": sanitize_text(error, limit=180), "items": []}
    scripts = package.get("scripts") if isinstance(package, dict) else None
    names = sorted(str(name) for name in scripts) if isinstance(scripts, dict) else []
    return {"status": "available", "items": names, "total": len(names)}


def _make_targets(target: Path) -> dict[str, object]:
    makefile = target / "Makefile"
    if not makefile.is_file():
        return {"status": "not_applicable", "items": []}
    if makefile.is_symlink() or relative_path(makefile, target) is None:
        return {"status": "unavailable", "reason": "manifest-resolves-outside-target", "items": []}
    try:
        text = makefile.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return {"status": "unavailable", "error": sanitize_text(error, limit=180), "items": []}
    names = sorted(set(re.findall(r"^([A-Za-z0-9_.-]+):(?:\s|$)", text, re.MULTILINE)))
    return {"status": "available", "items": names[:80], "total": len(names), "omitted": max(0, len(names) - 80)}


def _git_evidence(target: Path) -> dict[str, object]:
    root_result = run_command(["git", "rev-parse", "--show-toplevel"], cwd=target)
    if root_result["status"] != "available" or root_result["exit_code"] != 0:
        return {"status": "not_applicable", "reason": "target-is-not-a-git-worktree"}
    branch = run_command(["git", "branch", "--show-current"], cwd=target)
    head = run_command(["git", "rev-parse", "--short=12", "HEAD"], cwd=target)
    status = run_command(
        ["git", "status", "--porcelain=v1", "--untracked-files=normal", "--", "."],
        cwd=target,
    )
    changed: list[str] = []
    if status["status"] == "available" and status["exit_code"] == 0:
        for line in str(status["stdout"]).splitlines():
            candidate = line[3:] if len(line) >= 4 else ""
            if " -> " in candidate:
                candidate = candidate.split(" -> ", 1)[1]
            if candidate:
                changed.append(candidate)
    return {
        "status": "available",
        "branch": str(branch.get("stdout", "")).strip() or None,
        "head": str(head.get("stdout", "")).strip() or None,
        "changed_files": sorted(changed)[:100],
        "changed_file_count": len(changed),
        "changed_files_omitted": max(0, len(changed) - 100),
        "dirty": bool(changed),
    }


def collect_static_evidence(
    target: Path,
    root_resolution: dict[str, object],
    git_root: Path | None,
    nested_git_roots: set[Path],
) -> dict[str, object]:
    scan_source = "filesystem"
    if git_root is not None:
        files, omitted_files = _git_inventory(target, git_root)
        depth_limited: list[str] = []
        scan_source = "git-index"
    else:
        files, omitted_files, depth_limited = _bounded_files(
            target,
            blocked_roots=nested_git_roots,
        )
    instructions = [
        path for path in files
        if path.name in INSTRUCTION_NAMES or path.as_posix().endswith(".github/copilot-instructions.md")
    ]
    manifests = [path for path in files if path.name in MANIFEST_NAMES]
    skills = [path for path in files if path.name == "SKILL.md" and any(part in {"skills", ".skills"} for part in path.parts)]
    hooks = [
        path for path in files
        if path.name in HOOK_NAMES and any(part in {".claude", ".codex", ".qoder"} for part in path.parts)
    ]
    ci = [path for path in files if ".github" in path.parts and "workflows" in path.parts]
    tests = [path for path in files if _is_test_path(path, target)]
    return {
        "status": (
            "constrained"
            if omitted_files or depth_limited or root_resolution.get("status") == "constrained"
            else "available"
        ),
        "root_resolution": root_resolution,
        "scan": {
            "source": scan_source,
            "files_observed": len(files),
            "files_omitted": omitted_files,
            "depth_limited_directories": depth_limited[:80],
            "depth_limited_directory_count": len(depth_limited),
            "depth_limited_directories_omitted": max(0, len(depth_limited) - 80),
            "max_depth": 6,
            "skipped_directories": sorted(SKIP_DIRS),
        },
        "git": _git_evidence(target),
        "agent_assets": {
            "instructions": _relative_list(instructions, target),
            "skills": _relative_list(skills, target),
            "hooks_and_settings": _relative_list(hooks, target),
        },
        "project": {
            "manifests": _relative_list(manifests, target),
            "ci": _relative_list(ci, target),
            "tests": _relative_list(tests, target),
            "package_scripts": _package_scripts(target),
            "make_targets": _make_targets(target),
        },
    }


def build_evidence(args: argparse.Namespace) -> dict[str, object]:
    if args.mode == "static" and (
        args.session_file
        or args.session_root
        or args.provider
        or args.mechanism_category
        or args.episode_role
        or args.comparison_basis
        or args.include_request_summaries
        or args.max_session_bytes != MAX_SESSION_BYTES
        or args.max_session_lines != MAX_SESSION_LINES
        or args.max_session_line_bytes != MAX_SESSION_LINE_BYTES
        or args.max_session_warnings != MAX_SESSION_WARNINGS
    ):
        raise ValueError("static mode does not accept session sources")
    target = Path(args.target).expanduser().resolve()
    if not target.is_dir():
        raise ValueError(f"target is not a directory: {args.target}")
    root_resolution, git_root, nested_git_roots = _target_resolution(target)
    binding = target_binding(target)
    session_files = [Path(value) for value in args.session_file]
    discovered_omitted = 0
    if args.session_root:
        discovered, discovered_omitted = discover_jsonl_files(
            [Path(value) for value in args.session_root],
            limit=args.max_session_files,
        )
        session_files.extend(discovered)
    unique_session_files = list(dict.fromkeys(path.expanduser().resolve() for path in session_files))
    session_files_omitted = discovered_omitted + max(0, len(unique_session_files) - args.max_session_files)
    session_files = unique_session_files[: args.max_session_files]

    session_evidence: dict[str, object]
    if args.mode == "static":
        session_evidence = {
            "status": "not_authorized",
            "reason": "static-mode-excludes-session-evidence",
        }
    elif not args.provider:
        session_evidence = {
            "status": "unobserved",
            "reason": "provider-not-specified",
        }
    elif not session_files:
        session_evidence = {
            "status": "unobserved",
            "provider": args.provider,
            "reason": "explicit-session-source-not-provided",
        }
    else:
        session_evidence = parse_sessions(
            args.provider,
            session_files,
            include_request_summaries=args.include_request_summaries,
            max_bytes=args.max_session_bytes,
            max_lines=args.max_session_lines,
            max_line_bytes=args.max_session_line_bytes,
            max_warnings=args.max_session_warnings,
        )
        session_evidence["session_files_omitted"] = session_files_omitted

    unavailable: list[str] = []
    if session_evidence.get("status") != "available":
        unavailable.append(f"session-evidence:{session_evidence.get('status')}")

    return {
        "schema_version": 1,
        "kind": "agent-harness-evidence",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "scope": {
            "target": target.name,
            "target_id": binding["target_id"],
            "snapshot": {
                "baseline": "current_checkout" if git_root is not None else "filesystem_state",
                "target_relation": root_resolution["relation"],
                "id": binding["snapshot_id"],
            },
            "mode": args.mode,
            "provider": args.provider,
            "locale": args.locale,
            "decision": sanitize_text(args.decision, limit=240),
            "acceptance_boundary": sanitize_text(args.acceptance_boundary, limit=240),
            "output_mode": args.output_mode,
            "mechanism_category": args.mechanism_category,
            "episode_role": args.episode_role,
            "comparison_basis": (
                sanitize_text(args.comparison_basis, limit=240) if args.comparison_basis else None
            ),
        },
        "evidence_boundary": {
            "included": ["repository-static-evidence"] + (["explicit-session-sources"] if session_files else []),
            "excluded": [
                "user-home-discovery",
                "memory-bodies",
                "raw-transcripts",
                "secret-values",
                "stable-session-identifiers",
            ],
            "session_source_policy": "explicit-files-or-roots-only",
            "unavailable": unavailable,
        },
        "static": collect_static_evidence(
            target,
            root_resolution,
            git_root,
            nested_git_roots,
        ),
        "sessions": session_evidence,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default=".")
    parser.add_argument("--mode", choices=("static", "episode", "longitudinal"), default="static")
    parser.add_argument("--locale", choices=("en", "zh-CN"), required=True)
    parser.add_argument("--decision", required=True)
    parser.add_argument("--acceptance-boundary", required=True)
    parser.add_argument("--output-mode", choices=("inline", "durable"), required=True)
    parser.add_argument("--provider", choices=SUPPORTED_PROVIDERS)
    parser.add_argument("--mechanism-category", choices=("edit", "validation"))
    parser.add_argument("--episode-role", choices=("baseline", "later"))
    parser.add_argument("--comparison-basis")
    parser.add_argument("--session-file", action="append", default=[])
    parser.add_argument("--session-root", action="append", default=[])
    parser.add_argument("--max-session-files", type=int, default=20)
    parser.add_argument("--max-session-bytes", type=int, default=MAX_SESSION_BYTES)
    parser.add_argument("--max-session-lines", type=int, default=MAX_SESSION_LINES)
    parser.add_argument("--max-session-line-bytes", type=int, default=MAX_SESSION_LINE_BYTES)
    parser.add_argument("--max-session-warnings", type=int, default=MAX_SESSION_WARNINGS)
    parser.add_argument("--include-request-summaries", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--replace", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_session_files < 1 or args.max_session_files > 100:
        raise ValueError("--max-session-files must be between 1 and 100")
    if args.max_session_bytes < 1 or args.max_session_bytes > 64 * 1024 * 1024:
        raise ValueError("--max-session-bytes must be between 1 and 67108864")
    if args.max_session_lines < 1 or args.max_session_lines > 500_000:
        raise ValueError("--max-session-lines must be between 1 and 500000")
    if args.max_session_line_bytes < 1 or args.max_session_line_bytes > 4 * 1024 * 1024:
        raise ValueError("--max-session-line-bytes must be between 1 and 4194304")
    if args.max_session_warnings < 1 or args.max_session_warnings > 1000:
        raise ValueError("--max-session-warnings must be between 1 and 1000")
    if bool(args.episode_role) != bool(args.comparison_basis):
        raise ValueError("--episode-role and --comparison-basis must be supplied together")
    evidence = build_evidence(args)
    privacy_hits = privacy_rule_matches(evidence)
    if privacy_hits:
        raise ValueError(f"collected evidence violates privacy: {', '.join(privacy_hits)}")
    if args.output:
        write_json_atomic(Path(args.output), evidence, replace=args.replace)
    else:
        print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
