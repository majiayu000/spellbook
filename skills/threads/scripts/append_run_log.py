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
    "explicit_thread_request",
    "spawn_requirement",
    "native_thread_evidence",
    "fallback_mode",
    "no_spawn_reason",
    "single_agent_justification",
    "capability_gate",
    "queue_bounds",
    "remote_refresh",
    "queue_ledger",
    "lane_map",
    "lanes_total",
    "lanes",
    "failure_codes",
    "remote_truth",
    "remote_closure",
    "closure_audit",
    "local_state",
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
    validate_native_thread_evidence(record)

    record.setdefault("schema_version", 1)
    record["recorded_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return record


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"yes", "true", "1", "required"}
    return False


def nested_get(mapping: dict[str, Any], field: str) -> Any:
    nested = mapping.get("capability_gate")
    if isinstance(nested, dict) and field in nested:
        return nested.get(field)
    return mapping.get(field)


def has_spawned_agent(record: dict[str, Any]) -> bool:
    evidence = record.get("native_thread_evidence")
    if not isinstance(evidence, dict):
        return False
    spawned_agents = evidence.get("spawned_agents")
    if not isinstance(spawned_agents, list):
        return False
    for agent in spawned_agents:
        if not isinstance(agent, dict):
            continue
        if agent.get("agent_id_or_thread_id") or agent.get("tool_agent_id"):
            return True
    return False


def has_single_agent_reason(record: dict[str, Any]) -> bool:
    if record.get("no_spawn_reason"):
        return True
    justification = record.get("single_agent_justification")
    if isinstance(justification, dict) and justification.get("reason"):
        return True
    evidence = record.get("native_thread_evidence")
    return isinstance(evidence, dict) and bool(evidence.get("fallback_reason"))


def validate_native_thread_evidence(record: dict[str, Any]) -> None:
    mode = record.get("mode")
    native_subagents = nested_get(record, "native_subagents")
    fallback_mode = nested_get(record, "fallback_mode")
    explicit_request = nested_get(record, "explicit_thread_request")
    spawn_requirement = nested_get(record, "spawn_requirement")
    dispatch_mode = mode in {"execute_direct", "review_only", "research_spec"}
    required = truthy(explicit_request) or spawn_requirement == "required"

    if (
        dispatch_mode
        and native_subagents == "available"
        and fallback_mode == "none"
        and required
        and not has_spawned_agent(record)
    ):
        raise ValueError(
            "native_thread_evidence.spawned_agents is required when native "
            "subagents are available for an explicit threads run"
        )

    if (
        dispatch_mode
        and native_subagents == "available"
        and fallback_mode == "single_agent"
        and required
        and not has_single_agent_reason(record)
    ):
        raise ValueError(
            "single_agent fallback for an explicit threads run requires "
            "no_spawn_reason or single_agent_justification.reason"
        )


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
            "<git-dir>/codex/threads/run-log.jsonl inside a Git project."
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
