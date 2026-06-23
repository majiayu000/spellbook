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
ALLOWED_FALLBACK_MODES = {"none", "single_agent", "prompt_pack_only"}
ALLOWED_NATIVE_SPAWN_TOOLS = {"multi_agent_v1.spawn_agent"}
INVALID_AGENT_IDS = {"", "none", "n/a", "na", "null", "main", "main_thread", "coordinator"}
ALLOWED_SINGLE_AGENT_REASONS = {
    "no_independent_lanes",
    "sequential_dependency",
    "shared_writable_files",
    "tool_unavailable",
    "user_requested_single_agent",
}
ALLOWED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "recorded_at_utc",
    "skill",
    "skill_source",
    "active_skill_source",
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
    "thread_dispatch_gate",
    "queue_bounds",
    "remote_refresh",
    "queue_ledger",
    "lane_map",
    "lanes_total",
    "lanes",
    "failure_codes",
    "remote_truth",
    "remote_closure",
    "connector_review",
    "closure_audit",
    "local_state",
    "ci_wait",
    "review_loop",
    "run_log",
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


def canonical_gate_value(field: str, value: Any) -> Any:
    if field == "explicit_thread_request":
        return truthy(value)
    return value


def nested_get(mapping: dict[str, Any], field: str) -> Any:
    values: list[tuple[str, Any]] = []
    if field in mapping:
        values.append(("top-level", mapping.get(field)))
    for container in ("capability_gate", "thread_dispatch_gate"):
        nested = mapping.get(container)
        if isinstance(nested, dict) and field in nested:
            values.append((container, nested.get(field)))

    present = [(source, value) for source, value in values if value is not None]
    if not present:
        return None
    canonical_values = {
        canonical_gate_value(field, value)
        for _, value in present
    }
    if len(canonical_values) > 1:
        sources = ", ".join(source for source, _ in present)
        raise ValueError(f"conflicting {field} values across {sources}")
    return present[0][1]


def native_thread_evidence(record: dict[str, Any]) -> dict[str, Any] | None:
    evidence = record.get("native_thread_evidence")
    if isinstance(evidence, dict):
        return evidence
    dispatch_gate = record.get("thread_dispatch_gate")
    if isinstance(dispatch_gate, dict):
        nested = dispatch_gate.get("native_thread_evidence")
        if isinstance(nested, dict):
            return nested
    return None


def thread_dispatch_gate(record: dict[str, Any]) -> dict[str, Any] | None:
    gate = record.get("thread_dispatch_gate")
    return gate if isinstance(gate, dict) else None


def valid_agent_id(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return value.strip().lower() not in INVALID_AGENT_IDS


def valid_spawned_agents(record: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = native_thread_evidence(record)
    if evidence is None:
        return []
    spawned_agents = evidence.get("spawned_agents")
    if not isinstance(spawned_agents, list):
        return []
    valid_agents = []
    for agent in spawned_agents:
        if not isinstance(agent, dict):
            continue
        agent_id = agent.get("agent_id_or_thread_id") or agent.get("tool_agent_id")
        if (
            agent.get("spawn_tool") in ALLOWED_NATIVE_SPAWN_TOOLS
            and valid_agent_id(agent_id)
            and agent.get("result_collected") is True
            and bool(agent.get("wait_evidence"))
            and bool(agent.get("close_evidence"))
        ):
            valid_agents.append(agent)
    return valid_agents


def has_spawned_agent(record: dict[str, Any]) -> bool:
    return bool(valid_spawned_agents(record))


def normalize_reason(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized or None


def allowed_reason(reason: Any, evidence: Any = None) -> bool:
    normalized = normalize_reason(reason)
    if normalized not in ALLOWED_SINGLE_AGENT_REASONS:
        return False
    return evidence is None or bool(evidence)


def has_single_agent_reason(record: dict[str, Any]) -> bool:
    no_spawn_reason = record.get("no_spawn_reason")
    if isinstance(no_spawn_reason, dict):
        if allowed_reason(no_spawn_reason.get("reason"), no_spawn_reason.get("evidence")):
            return True
    elif allowed_reason(no_spawn_reason):
        return True

    gate = thread_dispatch_gate(record)
    if gate is not None:
        gate_reason = gate.get("no_spawn_reason")
        if isinstance(gate_reason, dict):
            if allowed_reason(gate_reason.get("reason"), gate_reason.get("evidence")):
                return True
        elif allowed_reason(gate_reason):
            return True

    justification = record.get("single_agent_justification")
    if (
        isinstance(justification, dict)
        and allowed_reason(justification.get("reason"), justification.get("evidence"))
    ):
        return True

    evidence = native_thread_evidence(record)
    if not isinstance(evidence, dict):
        return False
    return allowed_reason(evidence.get("fallback_reason"))


def lane_has_no_spawn_reason(lane: dict[str, Any]) -> bool:
    reason = lane.get("no_spawn_reason")
    if isinstance(reason, dict):
        return allowed_reason(reason.get("reason"), reason.get("evidence"))
    return allowed_reason(reason)


def validate_planned_native_threads(record: dict[str, Any]) -> None:
    gate = thread_dispatch_gate(record)
    if gate is None:
        return
    planned_threads = gate.get("planned_native_threads")
    if planned_threads is None:
        return
    if not isinstance(planned_threads, list):
        raise ValueError("thread_dispatch_gate.planned_native_threads must be a list")

    spawned_lane_ids = {
        agent.get("lane_id")
        for agent in valid_spawned_agents(record)
        if isinstance(agent.get("lane_id"), str) and agent.get("lane_id")
    }
    missing_reasons = []
    for lane in planned_threads:
        if not isinstance(lane, dict):
            raise ValueError("thread_dispatch_gate.planned_native_threads entries must be objects")
        lane_id = lane.get("id") or lane.get("lane_id")
        if not lane_id:
            raise ValueError("thread_dispatch_gate.planned_native_threads entries require id")
        if lane_id in spawned_lane_ids:
            continue
        if lane_has_no_spawn_reason(lane):
            continue
        missing_reasons.append(str(lane_id))

    if missing_reasons:
        raise ValueError(
            "thread_dispatch_gate.planned_native_threads missing spawned evidence "
            "or no_spawn_reason for lane(s): " + ", ".join(missing_reasons)
        )


def validate_native_thread_evidence(record: dict[str, Any]) -> None:
    mode = record.get("mode")
    native_subagents = nested_get(record, "native_subagents")
    fallback_mode = nested_get(record, "fallback_mode")
    explicit_request = nested_get(record, "explicit_thread_request")
    spawn_requirement = nested_get(record, "spawn_requirement")
    dispatch_mode = mode in {
        "single_agent",
        "plan_only",
        "execute_direct",
        "review_only",
        "research_spec",
    }
    required = truthy(explicit_request) or spawn_requirement == "required"

    if fallback_mode is not None and fallback_mode not in ALLOWED_FALLBACK_MODES:
        raise ValueError(f"unknown fallback_mode: {fallback_mode}")

    explicit_native_required = dispatch_mode and native_subagents == "available" and required

    if explicit_native_required and fallback_mode is None:
        raise ValueError(
            "fallback_mode is required when native subagents are available "
            "for an explicit threads run"
        )

    if (
        explicit_native_required
        and fallback_mode == "none"
        and not has_spawned_agent(record)
    ):
        raise ValueError(
            "native_thread_evidence.spawned_agents is required when native "
            "subagents are available for an explicit threads run"
        )

    if (
        explicit_native_required
        and fallback_mode == "single_agent"
        and not has_single_agent_reason(record)
    ):
        raise ValueError(
            "single_agent fallback for an explicit threads run requires "
            "an allowed no_spawn_reason or single_agent_justification.reason"
        )

    if explicit_native_required and fallback_mode == "prompt_pack_only":
        raise ValueError(
            "prompt_pack_only fallback is invalid when native subagents are "
            "available for an explicit threads run"
        )

    if explicit_native_required and fallback_mode == "none":
        validate_planned_native_threads(record)


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
