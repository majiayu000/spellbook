#!/usr/bin/env python3
"""Summarize Luna run telemetry into reliability, quality, and efficiency evidence."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import math
from pathlib import Path
import re
import statistics
import sys

from run_luna_worker import default_run_log_path


TOKEN_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens")
RATE_FIELDS = ("uncached_input", "cached_input", "output")
ONE_MILLION = Decimal(1_000_000)
ISO_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$"
)


@dataclass(frozen=True)
class TimeWindow:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class TokenSnapshot:
    timestamp: datetime
    usage: dict[str, int]


@dataclass
class ParentSessionFile:
    snapshots: list[TokenSnapshot]
    errors: Counter[str]


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _integer(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _number(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
        return float(value)
    return None


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * percentile + 0.5)))
    return round(ordered[index], 3)


def read_records(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    records: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"{path}:{line_number}: invalid JSONL: {error.msg}"
                ) from error
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: record must be an object")
            records.append(record)
    return records


def _required_string(value: object, field: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}: {field} must be a non-empty string")
    return value


def _rate_value(value: object, field: str, context: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{context}: {field} must be a non-negative number")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"{context}: {field} must be a non-negative number") from error
    if not parsed.is_finite() or parsed < 0:
        raise ValueError(f"{context}: {field} must be a non-negative number")
    return parsed


def load_rate_card(path: Path) -> dict[str, object]:
    context = f"rate card {path}"
    try:
        with path.open(encoding="utf-8") as handle:
            card = json.load(handle)
    except json.JSONDecodeError as error:
        raise ValueError(f"{context}: invalid JSON: {error.msg}") from error
    except UnicodeDecodeError as error:
        raise ValueError(f"{context}: invalid UTF-8") from error
    if not isinstance(card, dict):
        raise ValueError(f"{context}: top-level value must be an object")

    schema_version = card.get("schema_version")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool) or schema_version < 1:
        raise ValueError(f"{context}: schema_version must be a positive integer")
    card_id = _required_string(card.get("id"), "id", context)
    as_of = _required_string(card.get("as_of"), "as_of", context)
    label = _required_string(card.get("label"), "label", context)
    if "historical" not in label.lower() and "estimate" not in label.lower():
        raise ValueError(f"{context}: label must identify a historical estimate")
    if card.get("not_current_pricing") is not True:
        raise ValueError(f"{context}: not_current_pricing must be true")

    units = card.get("units")
    if not isinstance(units, dict):
        raise ValueError(f"{context}: units must be an object")
    if units.get("currency") != "credits" or units.get("token_basis") != "per_1m_tokens":
        raise ValueError(
            f"{context}: units must declare credits and per_1m_tokens"
        )

    model_mapping = card.get("model_mapping")
    if not isinstance(model_mapping, dict):
        raise ValueError(f"{context}: model_mapping must be an object")
    mapped_models: dict[str, str] = {}
    for role in ("sol", "luna"):
        mapped_models[role] = _required_string(model_mapping.get(role), role, context)

    rates = card.get("rates")
    if not isinstance(rates, dict):
        raise ValueError(f"{context}: rates must be an object")
    parsed_rates: dict[str, dict[str, Decimal]] = {}
    for role, model in mapped_models.items():
        model_rates = rates.get(model)
        if not isinstance(model_rates, dict):
            raise ValueError(f"{context}: missing rates for model {model}")
        parsed_rates[role] = {
            field: _rate_value(model_rates.get(field), field, f"{context} model {model}")
            for field in RATE_FIELDS
        }

    return {
        "schema_version": schema_version,
        "id": card_id,
        "as_of": as_of,
        "label": label,
        "not_current_pricing": True,
        "units": units,
        "model_mapping": mapped_models,
        "_rates": parsed_rates,
        "source": str(path.resolve()),
    }


def _strict_usage(usage: object, context: str) -> dict[str, int]:
    if not isinstance(usage, dict):
        raise ValueError(f"{context}: usage must be an object")

    parsed: dict[str, int] = {}
    for field in TOKEN_FIELDS:
        value = usage.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{context}: {field} must be a non-negative integer")
        parsed[field] = value

    if parsed["cached_input_tokens"] > parsed["input_tokens"]:
        raise ValueError(
            f"{context}: cached_input_tokens cannot exceed input_tokens"
        )

    for field, value in usage.items():
        if isinstance(field, str) and field.endswith("_tokens"):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{context}: {field} must be a non-negative integer")
            parsed[field] = value
    return parsed


def _json_number(value: Decimal) -> int | float:
    if not value.is_finite():
        raise ValueError("estimated credits must be finite")
    if value == value.to_integral_value():
        return int(value)
    as_float = float(value)
    if not math.isfinite(as_float):
        raise ValueError("estimated credits exceed JSON number range")
    return as_float


def _usage_credits(usage: object, rates: dict[str, Decimal], context: str) -> Decimal:
    parsed = _strict_usage(usage, context)
    uncached_input_tokens = parsed["input_tokens"] - parsed["cached_input_tokens"]
    return (
        Decimal(uncached_input_tokens) * rates["uncached_input"]
        + Decimal(parsed["cached_input_tokens"]) * rates["cached_input"]
        + Decimal(parsed["output_tokens"]) * rates["output"]
    ) / ONE_MILLION


def _parse_timestamp(value: object, field: str, context: str) -> datetime:
    if not isinstance(value, str) or not value or not ISO_TIMESTAMP_RE.fullmatch(value):
        raise ValueError(f"{context}: {field} must be an ISO-8601 timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError(f"{context}: {field} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{context}: {field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _session_id_from_record(record: dict[str, object]) -> str | None:
    payload = record.get("payload")
    if isinstance(payload, dict):
        for field in ("id", "session_id"):
            candidate = payload.get(field)
            if isinstance(candidate, str) and candidate:
                return candidate
    for field in ("session_id", "id"):
        candidate = record.get(field)
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def _token_count_payload(event: dict[str, object]) -> dict[str, object] | None:
    payload = event.get("payload")
    if isinstance(payload, dict) and payload.get("type") == "token_count":
        return payload
    if event.get("type") == "token_count":
        return event
    return None


def _parent_total_usage(event: dict[str, object], context: str) -> object | None:
    token_count = _token_count_payload(event)
    if token_count is None:
        return None
    info = token_count.get("info")
    if not isinstance(info, dict):
        raise ValueError(f"{context}: token_count info must be an object")
    if "total_token_usage" not in info:
        raise ValueError(f"{context}: token_count has no total_token_usage")
    return info["total_token_usage"]


def _find_parent_sessions(
    root: Path, target_ids: set[str]
) -> tuple[dict[str, list[ParentSessionFile]], int, int]:
    if not root.is_dir():
        raise ValueError(f"Codex sessions root is not a directory: {root}")

    candidates: dict[str, list[ParentSessionFile]] = {}
    files_scanned = 0
    malformed_files = 0
    for path in sorted(root.rglob("*.jsonl"), key=lambda item: str(item)):
        if not path.is_file():
            continue
        files_scanned += 1
        session_id: str | None = None
        session: ParentSessionFile | None = None
        try:
            with path.open(encoding="utf-8") as handle:
                first_line = handle.readline()
                if not first_line.strip():
                    continue
                try:
                    first_record = json.loads(first_line)
                except json.JSONDecodeError:
                    malformed_files += 1
                    continue
                if not isinstance(first_record, dict):
                    malformed_files += 1
                    continue
                session_id = _session_id_from_record(first_record)
                if session_id not in target_ids:
                    continue

                session = ParentSessionFile([], Counter())

                def consume_event(event: dict[str, object], line_number: int) -> None:
                    if _token_count_payload(event) is None:
                        return
                    context = f"{path}:{line_number}"
                    try:
                        timestamp = _parse_timestamp(
                            event.get("timestamp"), "timestamp", context
                        )
                    except ValueError:
                        session.errors["malformed_parent_timestamp"] += 1
                        return
                    try:
                        usage = _strict_usage(
                            _parent_total_usage(event, context), context
                        )
                    except ValueError:
                        session.errors["malformed_token_usage"] += 1
                        return
                    session.snapshots.append(TokenSnapshot(timestamp, usage))

                consume_event(first_record, 1)
                for line_number, raw_line in enumerate(handle, start=2):
                    if not raw_line.strip():
                        continue
                    try:
                        event = json.loads(raw_line)
                    except json.JSONDecodeError:
                        session.errors["malformed_session_jsonl"] += 1
                        malformed_files += 1
                        continue
                    if not isinstance(event, dict):
                        session.errors["malformed_session_jsonl"] += 1
                        malformed_files += 1
                        continue
                    consume_event(event, line_number)
        except UnicodeDecodeError:
            malformed_files += 1
            if session is not None:
                session.errors["malformed_session_encoding"] += 1
        if session_id in target_ids and session is not None:
            candidates.setdefault(session_id, []).append(session)
    return candidates, files_scanned, malformed_files


def _parent_references(
    run_values: list[dict[str, object]],
) -> Counter[str]:
    references: Counter[str] = Counter()
    for record in run_values:
        parent_session_id = record.get("parent_session_id")
        if isinstance(parent_session_id, str) and parent_session_id:
            references[parent_session_id] += 1
    return references


def _merge_windows(windows: list[TimeWindow]) -> list[TimeWindow]:
    if not windows:
        return []
    ordered = sorted(windows, key=lambda window: (window.start, window.end))
    merged: list[TimeWindow] = [ordered[0]]
    for window in ordered[1:]:
        current = merged[-1]
        if window.start <= current.end:
            merged[-1] = TimeWindow(current.start, max(current.end, window.end))
        else:
            merged.append(window)
    return merged


def _build_parent_windows(
    run_values: list[dict[str, object]],
) -> tuple[Counter[str], dict[str, list[TimeWindow]], dict[str, Counter[str]]]:
    references = _parent_references(run_values)
    raw_windows: dict[str, list[TimeWindow]] = {
        session_id: [] for session_id in references
    }
    invalid_windows: Counter[str] = Counter()
    invalid_reasons: dict[str, Counter[str]] = {
        session_id: Counter() for session_id in references
    }
    for record in run_values:
        session_id = record.get("parent_session_id")
        if not isinstance(session_id, str) or not session_id:
            continue
        context = f"run {record.get('run_id', '<unknown>')}"
        try:
            start = _parse_timestamp(record.get("started_at"), "started_at", context)
            end = _parse_timestamp(record.get("completed_at"), "completed_at", context)
        except ValueError:
            invalid_windows[session_id] += 1
            if record.get("started_at") is None or record.get("completed_at") is None:
                invalid_reasons[session_id]["missing_ledger_timestamp"] += 1
            else:
                invalid_reasons[session_id]["malformed_ledger_timestamp"] += 1
            continue
        if end < start:
            invalid_windows[session_id] += 1
            invalid_reasons[session_id]["invalid_ledger_window"] += 1
            continue
        raw_windows[session_id].append(TimeWindow(start, end))
    return (
        invalid_windows,
        {
            session_id: _merge_windows(windows)
            for session_id, windows in raw_windows.items()
        },
        invalid_reasons,
    )


def _usage_delta(
    baseline: TokenSnapshot, endpoint: TokenSnapshot, context: str
) -> dict[str, int]:
    delta: dict[str, int] = {}
    for field in TOKEN_FIELDS:
        difference = endpoint.usage[field] - baseline.usage[field]
        if difference < 0:
            raise ValueError(f"{context}: cumulative token counter decreased or reset")
        delta[field] = difference
    if delta["cached_input_tokens"] > delta["input_tokens"]:
        raise ValueError(f"{context}: cumulative input counter is inconsistent")
    return delta


def _session_has_counter_reset(snapshots: list[TokenSnapshot]) -> bool:
    ordered = sorted(snapshots, key=lambda snapshot: snapshot.timestamp)
    return any(
        current.usage[field] < previous.usage[field]
        for previous, current in zip(ordered, ordered[1:])
        for field in TOKEN_FIELDS
    )


def _disabled_parent_join(run_values: list[dict[str, object]]) -> dict[str, object]:
    references = _parent_references(run_values)
    shared = sum(count > 1 for count in references.values())
    duplicates = sum(count - 1 for count in references.values() if count > 1)
    return {
        "schema_version": 1,
        "enabled": False,
        "reason": "codex_sessions_root_not_supplied",
        "ledger_parent_sessions": len(references),
        "ledger_run_references": sum(references.values()),
        "shared_parent_sessions": shared,
        "duplicate_parent_references": duplicates,
    }


def _join_parent_sessions(
    run_values: list[dict[str, object]], root: Path
) -> tuple[dict[str, object], list[dict[str, int]]]:
    references = _parent_references(run_values)
    target_ids = set(references)
    candidates, files_scanned, malformed_files = _find_parent_sessions(root, target_ids)
    invalid_windows, windows_by_parent, invalid_reasons = _build_parent_windows(run_values)
    unresolved: Counter[str] = Counter()
    resolved_window_usage: list[dict[str, int]] = []
    required_windows = sum(
        invalid_windows[session_id] + len(windows_by_parent[session_id])
        for session_id in target_ids
    )
    resolved_windows = 0
    matched_session_ids: set[str] = set()
    resolved_parents: set[str] = set()
    unresolved_parents: set[str] = set()
    missing_parent_sessions = 0
    ambiguous_parent_sessions = 0
    missing_usage_parent_sessions = 0

    for session_id in sorted(target_ids):
        session_windows = windows_by_parent[session_id]
        parent_unresolved = invalid_windows[session_id] > 0
        for reason, count in invalid_reasons[session_id].items():
            unresolved[reason] += count
        session_candidates = candidates.get(session_id, [])
        session: ParentSessionFile | None = None
        if not session_candidates:
            missing_parent_sessions += 1
            unresolved["missing_parent_session"] += len(session_windows)
            parent_unresolved = True
        elif len(session_candidates) > 1:
            ambiguous_parent_sessions += 1
            unresolved["ambiguous_session_file"] += len(session_windows)
            parent_unresolved = True
        else:
            matched_session_ids.add(session_id)
            session = session_candidates[0]

        if session is not None:
            for reason, count in session.errors.items():
                unresolved[reason] += count
            if session.errors:
                parent_unresolved = True
            elif not session.snapshots:
                missing_usage_parent_sessions += 1
                unresolved["missing_baseline"] += len(session_windows)
                unresolved["missing_endpoint"] += len(session_windows)
                parent_unresolved = True
            elif _session_has_counter_reset(session.snapshots):
                unresolved["counter_decrease_or_reset"] += len(session_windows)
                parent_unresolved = True
            else:
                snapshots = sorted(session.snapshots, key=lambda snapshot: snapshot.timestamp)
                for window in session_windows:
                    baseline_candidates = [
                        snapshot
                        for snapshot in snapshots
                        if snapshot.timestamp <= window.start
                    ]
                    endpoint_candidates = [
                        snapshot
                        for snapshot in snapshots
                        if snapshot.timestamp >= window.end
                    ]
                    if not baseline_candidates:
                        unresolved["missing_baseline"] += 1
                        parent_unresolved = True
                        continue
                    if not endpoint_candidates:
                        unresolved["missing_endpoint"] += 1
                        parent_unresolved = True
                        continue
                    try:
                        resolved_window_usage.append(
                            _usage_delta(
                                baseline_candidates[-1],
                                endpoint_candidates[0],
                                f"parent session {session_id}",
                            )
                        )
                    except ValueError:
                        unresolved["counter_decrease_or_reset"] += 1
                        parent_unresolved = True
                        continue
                    resolved_windows += 1

        if parent_unresolved:
            unresolved_parents.add(session_id)
        else:
            resolved_parents.add(session_id)

    matched_references = sum(references[session_id] for session_id in resolved_parents)
    token_totals: Counter[str] = Counter()
    for usage in resolved_window_usage:
        for field, value in usage.items():
            if field.endswith("_tokens"):
                token_totals[field] += value

    total_parent_sessions = len(target_ids)
    total_references = sum(references.values())
    shared = sum(count > 1 for count in references.values())
    duplicates = sum(count - 1 for count in references.values() if count > 1)
    join = {
        "schema_version": 1,
        "enabled": True,
        "ledger_parent_sessions": total_parent_sessions,
        "ledger_run_references": total_references,
        "shared_parent_sessions": shared,
        "duplicate_parent_references": duplicates,
        "session_files_scanned": files_scanned,
        "malformed_session_files": malformed_files,
        "matched_parent_sessions": len(matched_session_ids),
        "resolved_parent_sessions": len(resolved_parents),
        "missing_parent_sessions": missing_parent_sessions,
        "ambiguous_parent_sessions": ambiguous_parent_sessions,
        "missing_usage_parent_sessions": missing_usage_parent_sessions,
        "required_parent_windows": required_windows,
        "resolved_parent_windows": resolved_windows,
        "unresolved_parent_windows": required_windows - resolved_windows,
        "unresolved_parent_sessions": len(unresolved_parents),
        "all_parent_windows_resolved": required_windows == resolved_windows,
        "parent_session_coverage": _ratio(len(resolved_parents), total_parent_sessions),
        "parent_window_coverage": _ratio(resolved_windows, required_windows),
        "run_reference_coverage": _ratio(matched_references, total_references),
        "attribution_scope": "union_of_merged_run_windows",
        "preflight_before_run_start_excluded": True,
        "post_completion_after_run_end_excluded": True,
        "unresolved_by_reason": dict(sorted(unresolved.items())),
        "commander_window_token_totals": dict(sorted(token_totals.items())),
    }
    return join, resolved_window_usage


def _rate_values(rate_card: dict[str, object], role: str) -> dict[str, Decimal]:
    rates = rate_card.get("_rates")
    if not isinstance(rates, dict):
        raise ValueError("rate card internal rates are missing")
    role_rates = rates.get(role)
    if not isinstance(role_rates, dict):
        raise ValueError(f"rate card rates are missing for {role}")
    return role_rates


def _rate_card_metadata(rate_card: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": rate_card["schema_version"],
        "id": rate_card["id"],
        "as_of": rate_card["as_of"],
        "label": rate_card["label"],
        "historical_estimate": True,
        "not_current_pricing": True,
        "units": rate_card["units"],
        "model_mapping": rate_card["model_mapping"],
        "source": rate_card["source"],
    }


def _worker_usage_reason(usage: object) -> str:
    if not isinstance(usage, dict):
        return "missing_usage"
    values = {field: usage.get(field) for field in TOKEN_FIELDS}
    if any(isinstance(value, int) and not isinstance(value, bool) and value < 0 for value in values.values()):
        return "negative_usage"
    input_tokens = values["input_tokens"]
    cached_input_tokens = values["cached_input_tokens"]
    if (
        isinstance(input_tokens, int)
        and not isinstance(input_tokens, bool)
        and isinstance(cached_input_tokens, int)
        and not isinstance(cached_input_tokens, bool)
        and cached_input_tokens > input_tokens
    ):
        return "inconsistent_usage"
    return "malformed_usage"


def _estimate_cost(
    path: Path,
    runs: list[dict[str, object]],
    rate_card: dict[str, object],
    join: dict[str, object] | None,
    commander_window_usage: list[dict[str, int]],
) -> tuple[dict[str, object], Decimal, Decimal | None, Decimal | None, bool]:
    worker_model = rate_card["model_mapping"]["luna"]
    worker_rates = _rate_values(rate_card, "luna")
    worker_credits = Decimal(0)
    worker_runs_costed = 0
    worker_unresolved_reasons: Counter[str] = Counter()
    for index, record in enumerate(runs, start=1):
        model = record.get("model")
        if model is not None and model != worker_model:
            raise ValueError(
                f"{path}: worker run {index} has model {model!r}, "
                f"expected {worker_model!r} for the Luna rate card"
            )
        usage = record.get("usage")
        try:
            worker_credits += _usage_credits(
                usage,
                worker_rates,
                f"{path}: worker run {index}",
            )
        except ValueError:
            worker_unresolved_reasons[_worker_usage_reason(usage)] += 1
            continue
        worker_runs_costed += 1

    worker_runs_total = len(runs)
    worker_runs_unresolved = worker_runs_total - worker_runs_costed
    worker_estimate_complete = worker_runs_unresolved == 0

    commander_window_credits: Decimal | None = None
    total_credits: Decimal | None = None
    total_estimate_complete = False
    commander_window_estimate_complete = False
    if join is not None and join.get("enabled") is True:
        commander_rates = _rate_values(rate_card, "sol")
        commander_window_credits = Decimal(0)
        for usage in commander_window_usage:
            commander_window_credits += _usage_credits(
                usage,
                commander_rates,
                f"{path}: joined commander window",
            )
        commander_window_estimate_complete = (
            join.get("all_parent_windows_resolved") is True
        )
        total_estimate_complete = (
            worker_estimate_complete and commander_window_estimate_complete
        )
        if total_estimate_complete:
            total_credits = worker_credits + commander_window_credits
            estimate_scope = "worker_plus_commander_window"
        else:
            estimate_scope = "worker_plus_resolved_commander_window_partial"
    else:
        estimate_scope = "worker_only"

    cost = {
        "schema_version": 1,
        "estimate": True,
        "estimate_scope": estimate_scope,
        "total_estimate_complete": total_estimate_complete,
        "rate_card": _rate_card_metadata(rate_card),
        "worker_model": worker_model,
        "commander_model": rate_card["model_mapping"]["sol"],
        "commander_attribution": "merged_run_window_delta",
        "worker_runs_total": worker_runs_total,
        "worker_runs_costed": worker_runs_costed,
        "worker_runs_unresolved": worker_runs_unresolved,
        "worker_cost_coverage": _ratio(worker_runs_costed, worker_runs_total),
        "worker_estimate_complete": worker_estimate_complete,
        "worker_unresolved_usage_reasons": dict(sorted(worker_unresolved_reasons.items())),
        "worker_credits": _json_number(worker_credits),
        "worker_only_credits": _json_number(worker_credits),
        "commander_sessions_costed": (
            join.get("resolved_parent_sessions")
            if commander_window_credits is not None and isinstance(join, dict)
            else None
        ),
        "commander_windows_costed": (
            len(commander_window_usage) if commander_window_credits is not None else None
        ),
        "commander_window_credits": (
            _json_number(commander_window_credits)
            if commander_window_credits is not None
            else None
        ),
        "commander_credits": (
            _json_number(commander_window_credits)
            if commander_window_credits is not None
            else None
        ),
        "total_credits": (
            _json_number(total_credits) if total_credits is not None else None
        ),
        "commander_window_estimate_complete": commander_window_estimate_complete,
    }
    return (
        cost,
        worker_credits,
        commander_window_credits,
        total_credits,
        total_estimate_complete,
    )


def summarize(
    path: Path,
    *,
    rate_card_path: Path | None = None,
    codex_sessions_root: Path | None = None,
) -> dict[str, object]:
    records = read_records(path)
    runs: dict[str, dict[str, object]] = {}
    latest_evaluations: dict[str, dict[str, object]] = {}
    evaluation_overwrites = 0
    orphan_evaluations = 0

    for record in records:
        record_type = record.get("record_type", "run")
        run_id = record.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            continue
        if record_type == "run":
            runs[run_id] = record
        elif record_type == "evaluation":
            if run_id in latest_evaluations:
                evaluation_overwrites += 1
            latest_evaluations[run_id] = record

    for run_id in latest_evaluations:
        if run_id not in runs:
            orphan_evaluations += 1

    run_values = list(runs.values())
    successful = [record for record in run_values if record.get("status") == "success"]
    failed = [record for record in run_values if record.get("status") == "failed"]
    evaluated = {
        run_id: evaluation
        for run_id, evaluation in latest_evaluations.items()
        if run_id in runs
    }
    evaluated_successes = {
        run_id: evaluation
        for run_id, evaluation in evaluated.items()
        if runs[run_id].get("status") == "success"
    }
    verified = {
        run_id: evaluation
        for run_id, evaluation in evaluated_successes.items()
        if evaluation.get("outcome") == "verified"
    }
    verified_with_checks = {
        run_id: evaluation
        for run_id, evaluation in verified.items()
        if _integer(evaluation.get("checks_passed")) > 0
        and _integer(evaluation.get("checks_failed")) == 0
    }
    initial_evaluated = {
        run_id: evaluation
        for run_id, evaluation in evaluated_successes.items()
        if runs[run_id].get("command") == "run"
    }
    first_pass_verified = {
        run_id: evaluation
        for run_id, evaluation in initial_evaluated.items()
        if evaluation.get("outcome") == "verified"
    }

    outcomes = Counter(
        str(evaluation.get("outcome"))
        for evaluation in evaluated.values()
        if isinstance(evaluation.get("outcome"), str)
    )
    failures = Counter(
        str(record.get("failure_code"))
        for record in failed
        if isinstance(record.get("failure_code"), str)
    )
    usage_totals: Counter[str] = Counter()
    for record in successful:
        usage = record.get("usage")
        if not isinstance(usage, dict):
            continue
        for name, value in usage.items():
            if isinstance(name, str):
                usage_totals[name] += _integer(value)

    durations = [
        duration
        for record in run_values
        if (duration := _number(record.get("duration_seconds"))) is not None
    ]
    checks_passed = sum(_integer(evaluation.get("checks_passed")) for evaluation in evaluated.values())
    checks_failed = sum(_integer(evaluation.get("checks_failed")) for evaluation in evaluated.values())
    warning_runs = sum(_integer(record.get("warning_count")) > 0 for record in successful)

    quality: dict[str, object] = {
        "evaluated_runs": len(evaluated),
        "evaluation_coverage": _ratio(len(evaluated), len(run_values)),
        "evaluated_successful_runs": len(evaluated_successes),
        "successful_evaluation_coverage": _ratio(
            len(evaluated_successes), len(successful)
        ),
        "verified_runs": len(verified),
        "verified_rate_among_evaluated_successes": _ratio(
            len(verified), len(evaluated_successes)
        ),
        "verified_with_check_evidence": len(verified_with_checks),
        "verified_check_evidence_coverage": _ratio(
            len(verified_with_checks), len(verified)
        ),
        "initial_runs_evaluated": len(initial_evaluated),
        "first_pass_verified_runs": len(first_pass_verified),
        "first_pass_verified_rate": _ratio(
            len(first_pass_verified), len(initial_evaluated)
        ),
        "outcomes": dict(sorted(outcomes.items())),
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
    }

    summary: dict[str, object] = {
        "schema_version": 1,
        "source": str(path),
        "source_exists": path.is_file(),
        "records_total": len(records),
        "runs_total": len(run_values),
        "reliability": {
            "successful_runs": len(successful),
            "failed_runs": len(failed),
            "success_rate": _ratio(len(successful), len(run_values)),
            "warning_runs": warning_runs,
            "failure_codes": dict(sorted(failures.items())),
        },
        "quality": quality,
        "efficiency": {
            "token_scope": "luna_worker_only",
            "resume_runs": sum(record.get("command") == "resume" for record in run_values),
            "token_totals": dict(sorted(usage_totals.items())),
            "average_input_tokens_per_success": (
                round(usage_totals.get("input_tokens", 0) / len(successful), 2)
                if successful
                else None
            ),
            "average_output_tokens_per_success": (
                round(usage_totals.get("output_tokens", 0) / len(successful), 2)
                if successful
                else None
            ),
            "median_duration_seconds": (
                round(statistics.median(durations), 3) if durations else None
            ),
            "p95_duration_seconds": _percentile(durations, 0.95),
        },
        "integrity": {
            "evaluation_overwrites": evaluation_overwrites,
            "orphan_evaluations": orphan_evaluations,
        },
        "claim_boundary": (
            "observational evidence only; compare similar task cohorts or controlled benchmarks "
            "before claiming causal improvement"
        ),
    }

    join: dict[str, object] | None = None
    commander_window_usage: list[dict[str, int]] = []
    if codex_sessions_root is not None:
        join, commander_window_usage = _join_parent_sessions(
            run_values, codex_sessions_root
        )

    if rate_card_path is not None:
        rate_card = load_rate_card(rate_card_path)
        if join is None:
            join = _disabled_parent_join(run_values)
        (
            cost,
            worker_credits,
            commander_window_credits,
            total_credits,
            total_estimate_complete,
        ) = _estimate_cost(
            path,
            run_values,
            rate_card,
            join,
            commander_window_usage,
        )
        summary["cost"] = cost
        quality["credit_scope"] = cost["estimate_scope"]
        worker_normalized_credits = (
            worker_credits if cost["worker_estimate_complete"] is True else None
        )
        quality["worker_credits_per_verified_run"] = (
            _json_number(worker_normalized_credits / Decimal(len(verified)))
            if worker_normalized_credits is not None and verified
            else None
        )
        quality["worker_credits_per_first_pass_verified_run"] = (
            _json_number(worker_normalized_credits / Decimal(len(first_pass_verified)))
            if worker_normalized_credits is not None and first_pass_verified
            else None
        )
        if join is None or join.get("enabled") is not True:
            normalized_credits = worker_normalized_credits
            normalized_scope = (
                "worker_only"
                if cost["worker_estimate_complete"] is True
                else "incomplete_worker_usage_coverage"
            )
        elif total_estimate_complete and total_credits is not None:
            normalized_credits = total_credits
            normalized_scope = "worker_plus_commander_window"
        else:
            normalized_credits = None
            worker_complete = cost["worker_estimate_complete"] is True
            commander_complete = cost["commander_window_estimate_complete"] is True
            if not worker_complete and not commander_complete:
                normalized_scope = (
                    "incomplete_worker_usage_and_commander_window_coverage"
                )
            elif not worker_complete:
                normalized_scope = "incomplete_worker_usage_coverage"
            else:
                normalized_scope = "incomplete_commander_window_coverage"
        quality["normalized_credit_scope"] = normalized_scope
        quality["credits_per_verified_run"] = (
            _json_number(normalized_credits / Decimal(len(verified)))
            if normalized_credits is not None and verified
            else None
        )
        quality["credits_per_first_pass_verified_run"] = (
            _json_number(normalized_credits / Decimal(len(first_pass_verified)))
            if normalized_credits is not None and first_pass_verified
            else None
        )
        quality["commander_credit_share"] = (
            _json_number(commander_window_credits / total_credits)
            if total_estimate_complete
            and commander_window_credits is not None
            and total_credits
            else None
        )

    if join is not None:
        summary["parent_session_join"] = join

    return summary


def to_text(summary: dict[str, object]) -> str:
    reliability = summary["reliability"]
    quality = summary["quality"]
    efficiency = summary["efficiency"]
    assert isinstance(reliability, dict)
    assert isinstance(quality, dict)
    assert isinstance(efficiency, dict)
    lines = [
        "Sol-Luna evidence summary",
        f"runs: {summary['runs_total']}",
        f"success_rate: {reliability['success_rate']}",
        f"evaluated_runs: {quality['evaluated_runs']}",
        f"evaluation_coverage: {quality['evaluation_coverage']}",
        f"verified_rate_among_evaluated_successes: {quality['verified_rate_among_evaluated_successes']}",
        f"first_pass_verified_rate: {quality['first_pass_verified_rate']}",
        f"verified_check_evidence_coverage: {quality['verified_check_evidence_coverage']}",
        f"resume_runs: {efficiency['resume_runs']}",
        f"median_duration_seconds: {efficiency['median_duration_seconds']}",
        f"p95_duration_seconds: {efficiency['p95_duration_seconds']}",
    ]
    cost = summary.get("cost")
    if isinstance(cost, dict):
        lines.extend(
            [
                f"estimate_scope: {cost['estimate_scope']}",
                f"commander_attribution: {cost['commander_attribution']}",
                f"worker_credits: {cost['worker_credits']}",
                f"commander_window_credits: {cost['commander_window_credits']}",
                f"total_credits: {cost['total_credits']}",
                f"worker_credits_per_verified_run: {quality['worker_credits_per_verified_run']}",
                f"worker_credits_per_first_pass_verified_run: {quality['worker_credits_per_first_pass_verified_run']}",
                f"credits_per_verified_run: {quality['credits_per_verified_run']}",
                f"credits_per_first_pass_verified_run: {quality['credits_per_first_pass_verified_run']}",
                f"commander_credit_share: {quality['commander_credit_share']}",
            ]
        )
    join = summary.get("parent_session_join")
    if isinstance(join, dict) and join.get("enabled") is True:
        lines.append(f"parent_session_coverage: {join['parent_session_coverage']}")
        lines.append(f"parent_window_coverage: {join['parent_window_coverage']}")
        lines.append(f"unresolved_parent_sessions: {join['unresolved_parent_sessions']}")
    lines.append(f"claim_boundary: {summary['claim_boundary']}")
    return "\n".join(lines) + "\n"


def _absolute_optional_path(value: Path | None, option: str) -> Path | None:
    if value is None:
        return None
    path = value.expanduser()
    if not path.is_absolute():
        raise ValueError(f"{option} must be absolute: {path}")
    return path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-log", type=Path, help="JSONL ledger; defaults to the Luna run log.")
    parser.add_argument(
        "--rate-card",
        type=Path,
        help="Absolute JSON rate card for an explicit historical credit estimate.",
    )
    parser.add_argument(
        "--codex-sessions-root",
        type=Path,
        help="Optional local Codex sessions root for an explicit parent-session join.",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    path = args.run_log.expanduser() if args.run_log else default_run_log_path()
    if not path.is_absolute():
        print(f"analyze_run_log.py: --run-log must be absolute: {path}", file=sys.stderr)
        return 1
    try:
        rate_card_path = _absolute_optional_path(args.rate_card, "--rate-card")
        sessions_root = _absolute_optional_path(
            args.codex_sessions_root, "--codex-sessions-root"
        )
        summary = summarize(
            path.resolve(),
            rate_card_path=rate_card_path,
            codex_sessions_root=sessions_root,
        )
    except (OSError, ValueError) as error:
        print(f"analyze_run_log.py: {error}", file=sys.stderr)
        return 1
    if args.format == "json":
        json.dump(summary, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(to_text(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
