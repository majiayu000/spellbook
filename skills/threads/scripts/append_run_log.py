#!/usr/bin/env python3
"""Append a sanitized threads run record to a local JSONL file."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def default_log_path() -> Path:
    override = os.environ.get("CODEX_THREADS_RUN_LOG")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".codex" / "threads-run-log.jsonl"


def redact(value: Any, key_hint: str = "") -> Any:
    lower_key = key_hint.lower()
    if any(part in lower_key for part in SENSITIVE_KEY_PARTS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(key): redact(item, str(key)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item, key_hint) for item in value]
    if isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            return value[:MAX_STRING_LENGTH] + "...[TRUNCATED]"
        return value
    return value


def normalize_record(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("run log input must be a JSON object")
    record = redact(raw)
    record.setdefault("schema_version", 1)
    record["recorded_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return record


def append_record(record: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        type=Path,
        default=default_log_path(),
        help="JSONL path. Defaults to CODEX_THREADS_RUN_LOG or ~/.codex/threads-run-log.jsonl.",
    )
    args = parser.parse_args()

    try:
        raw = json.load(sys.stdin)
        record = normalize_record(raw)
        append_record(record, args.path.expanduser())
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"append_run_log.py: {exc}", file=sys.stderr)
        return 1

    print(str(args.path.expanduser()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
