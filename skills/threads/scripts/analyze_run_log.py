#!/usr/bin/env python3
"""Summarize local threads run-log JSONL without exposing raw prompts."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from append_run_log import default_log_path, nested_get, valid_spawned_agents


JSONValue = None | bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"]
JSONObject = dict[str, JSONValue]


@dataclass
class RunLogSummary:
    path: str
    path_exists: bool
    records_total: int = 0
    invalid_lines: int = 0
    failure_codes: Counter[str] = field(default_factory=Counter)
    truth_levels: Counter[str] = field(default_factory=Counter)
    modes: Counter[str] = field(default_factory=Counter)
    outcomes: Counter[str] = field(default_factory=Counter)
    repos: Counter[str] = field(default_factory=Counter)
    explicit_thread_requests: int = 0
    runs_with_spawned_agents: int = 0
    spawned_agents_total: int = 0
    single_agent_fallbacks: int = 0
    stale_base_events: int = 0
    durable_log_gaps: int = 0
    missing_log_file: bool = False


def _as_object(value: JSONValue | None) -> JSONObject:
    return value if isinstance(value, dict) else {}


def _as_list(value: JSONValue | None) -> list[JSONValue]:
    return value if isinstance(value, list) else []


def _truthy(value: JSONValue | None) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"yes", "true", "1", "required"}
    return False


def _string(value: JSONValue | None) -> str | None:
    return value if isinstance(value, str) and value else None


def _native_evidence(record: JSONObject) -> JSONObject:
    evidence = _as_object(record.get("native_thread_evidence"))
    if evidence:
        return evidence
    gate = _as_object(record.get("thread_dispatch_gate"))
    return _as_object(gate.get("native_thread_evidence"))


def _spawned_agents(record: JSONObject) -> list[JSONObject]:
    return valid_spawned_agents(record)


def _explicit_thread_request(record: JSONObject) -> bool:
    return _truthy(nested_get(record, "explicit_thread_request"))


def _fallback_mode(record: JSONObject) -> str | None:
    return _string(nested_get(record, "fallback_mode"))


def _stale_base(record: JSONObject) -> bool:
    remote_refresh = _as_object(record.get("remote_refresh"))
    remote_truth = _as_object(record.get("remote_truth"))
    queue_gate = _as_object(record.get("queue_gate"))
    queue_remote_refresh = _as_object(queue_gate.get("remote_refresh"))
    queue_ledger = _as_object(record.get("queue_ledger"))
    failure_codes = [code for code in _as_list(record.get("failure_codes")) if isinstance(code, str)]
    return (
        _truthy(remote_refresh.get("stale_base"))
        or _truthy(remote_truth.get("stale_base"))
        or _truthy(queue_remote_refresh.get("stale_base"))
        or _truthy(queue_ledger.get("stale_base"))
        or "stale_base" in failure_codes
    )


def _durable_log_gap(record: JSONObject) -> bool:
    run_log = _as_object(record.get("run_log"))
    write_status = _string(run_log.get("write_status"))
    no_log_reason = _string(run_log.get("no_log_reason"))
    failure_codes = [code for code in _as_list(record.get("failure_codes")) if isinstance(code, str)]
    if "durable_log_skipped" in failure_codes:
        return True
    if write_status in {"failed", "error", "skipped"}:
        return True
    return write_status == "not_written" and no_log_reason is None


def _read_records(path: Path) -> tuple[list[JSONObject], int]:
    records: list[JSONObject] = []
    if not path.exists():
        return records, 0
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                raise ValueError(f"{path}:{line_number}: invalid JSONL record")
            if isinstance(parsed, dict):
                records.append(parsed)
            else:
                raise ValueError(f"{path}:{line_number}: JSONL record must be an object")
    return records, 0


def summarize(path: Path) -> RunLogSummary:
    records, invalid = _read_records(path)
    summary = RunLogSummary(
        path=str(path),
        path_exists=path.exists(),
        records_total=len(records),
        invalid_lines=invalid,
        missing_log_file=not path.exists(),
    )
    for record in records:
        for field_name, counter in (
            ("truth_level", summary.truth_levels),
            ("mode", summary.modes),
            ("outcome", summary.outcomes),
            ("repo", summary.repos),
        ):
            value = _string(record.get(field_name))
            if value:
                counter[value] += 1
        for code in _as_list(record.get("failure_codes")):
            if isinstance(code, str) and code:
                summary.failure_codes[code] += 1
        if _explicit_thread_request(record):
            summary.explicit_thread_requests += 1
        spawned = _spawned_agents(record)
        if spawned:
            summary.runs_with_spawned_agents += 1
            summary.spawned_agents_total += len(spawned)
        if _fallback_mode(record) == "single_agent":
            summary.single_agent_fallbacks += 1
        if _stale_base(record):
            summary.stale_base_events += 1
        if _durable_log_gap(record):
            summary.durable_log_gaps += 1
    return summary


def _top(counter: Counter[str], limit: int) -> list[dict[str, int | str]]:
    return [{"name": name, "count": count} for name, count in counter.most_common(limit)]


def to_json(summary: RunLogSummary, limit: int) -> str:
    payload = {
        "path": summary.path,
        "status": "missing" if summary.missing_log_file else "ok",
        "missing_files": [summary.path] if summary.missing_log_file else [],
        "records_total": summary.records_total,
        "invalid_lines": summary.invalid_lines,
        "failure_codes": _top(summary.failure_codes, limit),
        "truth_levels": dict(summary.truth_levels),
        "modes": dict(summary.modes),
        "outcomes": dict(summary.outcomes),
        "repos": _top(summary.repos, limit),
        "stale_base_events": summary.stale_base_events,
        "durable_log_gaps": summary.durable_log_gaps,
        "native_spawn_evidence": {
            "explicit_thread_requests": summary.explicit_thread_requests,
            "runs_with_spawned_agents": summary.runs_with_spawned_agents,
            "spawned_agents_total": summary.spawned_agents_total,
            "single_agent_fallbacks": summary.single_agent_fallbacks,
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _format_counter(counter: Counter[str], limit: int) -> list[str]:
    if not counter:
        return ["  none"]
    return [f"  {name}: {count}" for name, count in counter.most_common(limit)]


def to_text(summary: RunLogSummary, limit: int) -> str:
    status = "missing" if summary.missing_log_file else "ok"
    lines = [
        "Threads run log summary",
        f"path: {summary.path}",
        f"status: {status}",
        f"records: {summary.records_total}",
        f"invalid_lines: {summary.invalid_lines}",
    ]
    if summary.missing_log_file:
        lines.append("note: no durable threads run log found; pass --path or set CODEX_THREADS_RUN_LOG")
    lines.extend([
        "truth_levels:",
        *_format_counter(summary.truth_levels, limit),
        "failure_codes:",
        *_format_counter(summary.failure_codes, limit),
        f"stale_base_events: {summary.stale_base_events}",
        f"durable_log_gaps: {summary.durable_log_gaps}",
        "native_spawn_evidence:",
        f"  explicit_thread_requests: {summary.explicit_thread_requests}",
        f"  runs_with_spawned_agents: {summary.runs_with_spawned_agents}",
        f"  spawned_agents_total: {summary.spawned_agents_total}",
        f"  single_agent_fallbacks: {summary.single_agent_fallbacks}",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=None, help="JSONL path; defaults to the threads run-log path")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--limit", type=int, default=20, help="Maximum rows per counted section")
    args = parser.parse_args()

    path = args.path.expanduser() if args.path is not None else default_log_path()
    try:
        summary = summarize(path)
    except ValueError as exc:
        sys.stderr.write(f"analyze_run_log.py: {exc}\n")
        return 1
    limit = max(1, args.limit)
    if args.format == "json":
        sys.stdout.write(to_json(summary, limit))
    else:
        sys.stdout.write(to_text(summary, limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
