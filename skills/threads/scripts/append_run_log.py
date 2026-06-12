#!/usr/bin/env python3
"""Append a sanitized threads run record to a local JSONL file."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback.
    fcntl = None


SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
)
MAX_STRING_LENGTH = 4000
MAX_INPUT_BYTES = 64 * 1024
MAX_DEPTH = 8
MAX_ARRAY_ITEMS = 100
ALLOWED_MODES = {
    "single_agent",
    "plan_only",
    "execute_direct",
    "review_only",
    "research_spec",
    "clarify_first",
}
ALLOWED_TRUTH_LEVELS = {"A", "B", "C", "D"}
ALLOWED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "recorded_at_utc",
    "skill",
    "skill_source",
    "mode",
    "repo",
    "base_ref",
    "trigger_summary",
    "goal",
    "non_goals",
    "intent_contract",
    "merge_policy",
    "data_collection",
    "truth_level",
    "native_subagents",
    "fallback_mode",
    "capability_gate",
    "queue_bounds",
    "remote_refresh",
    "queue_ledger",
    "lane_map",
    "lanes_total",
    "lanes",
    "failure_codes",
    "remote_closure",
    "closure_audit",
    "ci_wait",
    "review_loop",
    "exclusive_verification",
    "verification",
    "outcome",
    "notes",
}

SENSITIVE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
)


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return current


def default_log_path() -> Path:
    override = os.environ.get("CODEX_THREADS_RUN_LOG")
    if override:
        return Path(override).expanduser()
    return find_project_root() / ".codex" / "threads" / "run-log.jsonl"


def redact_string(value: str) -> str:
    redacted = value
    for pattern in SENSITIVE_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    if len(redacted) > MAX_STRING_LENGTH:
        return redacted[:MAX_STRING_LENGTH] + "...[TRUNCATED]"
    return redacted


def redact(value: Any, key_hint: str = "", depth: int = 0) -> Any:
    if depth > MAX_DEPTH:
        return "[TRUNCATED_DEPTH]"
    lower_key = key_hint.lower()
    if any(part in lower_key for part in SENSITIVE_KEY_PARTS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(key): redact(item, str(key), depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item, key_hint, depth + 1) for item in value[:MAX_ARRAY_ITEMS]]
    if isinstance(value, str):
        return redact_string(value)
    return value


def normalize_record(raw: Any, allow_extra: bool = False) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("run log input must be a JSON object")
    unknown_fields = sorted(set(raw) - ALLOWED_TOP_LEVEL_FIELDS)
    if unknown_fields and not allow_extra:
        raise ValueError("unknown top-level field(s): " + ", ".join(unknown_fields))

    record = redact(raw)
    mode = record.get("mode")
    if mode is not None and mode not in ALLOWED_MODES:
        raise ValueError(f"unknown mode: {mode}")
    truth_level = record.get("truth_level")
    if truth_level is not None and truth_level not in ALLOWED_TRUTH_LEVELS:
        raise ValueError(f"unknown truth_level: {truth_level}")

    record.setdefault("schema_version", 1)
    record["recorded_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return record


def append_record(record: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
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
            "<project>/.codex/threads/run-log.jsonl."
        ),
    )
    parser.add_argument(
        "--allow-extra",
        action="store_true",
        help="Allow unknown top-level fields after redaction. Defaults to rejecting them.",
    )
    args = parser.parse_args()

    try:
        raw = load_input()
        record = normalize_record(raw, allow_extra=args.allow_extra)
        path = args.path.expanduser() if args.path is not None else default_log_path()
        append_record(record, path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"append_run_log.py: {exc}", file=sys.stderr)
        return 1

    print(str(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
