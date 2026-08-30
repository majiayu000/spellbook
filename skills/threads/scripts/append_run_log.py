#!/usr/bin/env python3
"""Append a sanitized threads run record to a local JSONL file."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from run_log_schema import MAX_INPUT_BYTES, normalize_record

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback.
    fcntl = None

def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return current


def find_git_metadata_dir(project_root: Path) -> Path | None:
    dot_git = project_root / ".git"
    if dot_git.is_dir():
        return dot_git
    if not dot_git.is_file():
        return None

    try:
        marker = dot_git.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    prefix = "gitdir:"
    if not marker.lower().startswith(prefix):
        return None

    git_dir = Path(marker[len(prefix) :].strip()).expanduser()
    if not git_dir.is_absolute():
        git_dir = (project_root / git_dir).resolve()
    return git_dir


def default_log_path() -> Path:
    override = os.environ.get("CODEX_THREADS_RUN_LOG")
    if override:
        return Path(override).expanduser()
    project_root = find_project_root()
    git_metadata_dir = find_git_metadata_dir(project_root)
    if git_metadata_dir is not None:
        return git_metadata_dir / "codex" / "threads" / "run-log.jsonl"
    return project_root / ".codex" / "threads" / "run-log.jsonl"


def append_record(record: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    os.chmod(path, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def load_input() -> Any:
    raw_bytes = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw_bytes) > MAX_INPUT_BYTES:
        raise ValueError(f"run log input exceeds {MAX_INPUT_BYTES} bytes")
    return json.loads(raw_bytes.decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help=(
            "JSONL path. Defaults to CODEX_THREADS_RUN_LOG or "
            "<git-dir>/codex/threads/run-log.jsonl inside a Git project."
        ),
    )
    parser.add_argument(
        "--allow-extra",
        action="store_true",
        help="Allow unknown top-level fields after redaction. Defaults to rejecting them.",
    )
    parser.add_argument(
        "--print-path",
        action="store_true",
        help="Print the resolved JSONL path and exit without reading stdin.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate and redact stdin JSON without appending a log record.",
    )
    args = parser.parse_args()

    try:
        path = args.path.expanduser() if args.path is not None else default_log_path()
        if args.print_path:
            output_path = path
        else:
            raw = load_input()
            record = normalize_record(raw, allow_extra=args.allow_extra)
            if args.validate_only:
                return 0
            if record.get("run_phase") == "preflight":
                raise ValueError("preflight records require --validate-only")
            append_record(record, path)
            output_path = path
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"append_run_log.py: {exc}", file=sys.stderr)
        return 1

    sys.stdout.write(str(output_path) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
