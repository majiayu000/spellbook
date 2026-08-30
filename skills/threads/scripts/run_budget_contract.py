"""Pre-dispatch budget validation for threads run records."""

from __future__ import annotations

import math
import re


ALLOWED_RUN_PHASES = {"preflight", "final"}
CONCRETE_DURATION = re.compile(r"^([1-9][0-9]*)(s|m|h)$")
FINAL_USAGE_FIELDS = {"elapsed_seconds", "items_processed", "model_calls_used"}


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _duration_seconds(value: object, field: str) -> int:
    match = CONCRETE_DURATION.fullmatch(value.strip()) if isinstance(value, str) else None
    if match is None:
        raise ValueError(f"{field} must be a concrete duration such as 30m or 2h")
    multiplier = {"s": 1, "m": 60, "h": 3600}[match.group(2)]
    return int(match.group(1)) * multiplier


def _planned_threads(record: dict[str, object]) -> list[object]:
    gate = record.get("thread_dispatch_gate")
    if not isinstance(gate, dict):
        return []
    planned = gate.get("planned_native_threads")
    return planned if isinstance(planned, list) else []


def _spawned_threads(record: dict[str, object]) -> list[object]:
    evidence = record.get("native_thread_evidence")
    if not isinstance(evidence, dict):
        gate = record.get("thread_dispatch_gate")
        evidence = gate.get("native_thread_evidence") if isinstance(gate, dict) else None
    if not isinstance(evidence, dict):
        return []
    if "spawned_agents" not in evidence:
        return []
    spawned = evidence["spawned_agents"]
    if not isinstance(spawned, list):
        raise ValueError("native_thread_evidence.spawned_agents must be a list")
    return spawned


def _multi_lane(record: dict[str, object]) -> bool:
    lanes_total = record.get("lanes_total")
    lanes = record.get("lanes")
    lane_map = record.get("lane_map")
    mapped_lanes = lane_map.get("lanes") if isinstance(lane_map, dict) else None
    return (
        isinstance(lanes_total, int)
        and not isinstance(lanes_total, bool)
        and lanes_total > 1
    ) or (
        isinstance(lanes, list) and len(lanes) > 1
    ) or (
        isinstance(mapped_lanes, list) and len(mapped_lanes) > 1
    ) or len(_planned_threads(record)) > 1


def validate_semantic_array_limits(record: dict[str, object], limit: int) -> None:
    if len(_planned_threads(record)) > limit:
        raise ValueError(
            f"thread_dispatch_gate.planned_native_threads exceeds {limit} items"
        )
    if len(_spawned_threads(record)) > limit:
        raise ValueError(f"native_thread_evidence.spawned_agents exceeds {limit} items")
    queue_ledger = record.get("queue_ledger")
    if isinstance(queue_ledger, list) and len(queue_ledger) > limit:
        raise ValueError(f"queue_ledger exceeds {limit} items")
    if isinstance(queue_ledger, dict):
        ledger_items = queue_ledger.get("items")
        if isinstance(ledger_items, list) and len(ledger_items) > limit:
            raise ValueError(f"queue_ledger.items exceeds {limit} items")
        superseded = queue_ledger.get("superseded_items")
        if isinstance(superseded, list) and len(superseded) > limit:
            raise ValueError(f"queue_ledger.superseded_items exceeds {limit} items")
    intent = record.get("intent_contract")
    if isinstance(intent, dict):
        for field in ("authorized_actions", "fresh_confirmation_required"):
            actions = intent.get(field)
            if isinstance(actions, list) and len(actions) > limit:
                raise ValueError(f"intent_contract.{field} exceeds {limit} items")


def _validate_bounds(bounds: object, field: str) -> None:
    if not isinstance(bounds, dict):
        raise ValueError(f"{field} must be an object")
    for name in (
        "max_items",
        "max_model_calls",
        "time_budget",
        "checkpoint_every_items",
        "queue_tranche",
    ):
        if name not in bounds:
            raise ValueError(f"{field}.{name} is required")

    max_items = _positive_int(bounds["max_items"], f"{field}.max_items")
    _positive_int(bounds["max_model_calls"], f"{field}.max_model_calls")
    checkpoint = _positive_int(
        bounds["checkpoint_every_items"], f"{field}.checkpoint_every_items"
    )
    if checkpoint > max_items:
        raise ValueError(f"{field}.checkpoint_every_items must not exceed {field}.max_items")
    _duration_seconds(bounds["time_budget"], f"{field}.time_budget")
    elapsed_seconds = bounds.get("elapsed_seconds")
    if elapsed_seconds is not None and (
        isinstance(elapsed_seconds, bool)
        or not isinstance(elapsed_seconds, (int, float))
        or elapsed_seconds < 0
        or (isinstance(elapsed_seconds, float) and not math.isfinite(elapsed_seconds))
    ):
        raise ValueError(f"{field}.elapsed_seconds must be a finite non-negative number")
    for name in ("items_processed", "model_calls_used"):
        value = bounds.get(name)
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            raise ValueError(f"{field}.{name} must be a non-negative integer")
    if not isinstance(bounds["queue_tranche"], str) or not bounds["queue_tranche"].strip():
        raise ValueError(f"{field}.queue_tranche must be a non-empty string")
    if bounds["queue_tranche"].strip().lower() in {
        "unbounded",
        "as needed",
        "not pre-budgeted",
    }:
        raise ValueError(f"{field}.queue_tranche must describe a bounded tranche")


def validate_run_budget(record: dict[str, object]) -> None:
    phase = record.get("run_phase")
    if not isinstance(phase, str) or phase not in ALLOWED_RUN_PHASES:
        raise ValueError("run_phase must be preflight or final")
    lanes_total = record.get("lanes_total")
    if lanes_total is not None and (
        isinstance(lanes_total, bool)
        or not isinstance(lanes_total, int)
        or lanes_total < 0
    ):
        raise ValueError("lanes_total must be a non-negative integer")

    top_level = record.get("queue_bounds")
    intent = record.get("intent_contract")
    if phase == "preflight":
        if not isinstance(intent, dict):
            raise ValueError("intent_contract is required for preflight")
        for field in ("goal", "done_when"):
            if not isinstance(intent.get(field), str) or not intent[field].strip():
                raise ValueError(f"intent_contract.{field} is required for preflight")
        for field in ("authorized_actions", "fresh_confirmation_required"):
            if field not in intent:
                raise ValueError(f"intent_contract.{field} is required for preflight")
    nested = intent.get("queue_bounds") if isinstance(intent, dict) else None
    if top_level is not None:
        _validate_bounds(top_level, "queue_bounds")
    if nested is not None:
        _validate_bounds(nested, "intent_contract.queue_bounds")
        if FINAL_USAGE_FIELDS.intersection(nested):
            raise ValueError(
                "intent_contract.queue_bounds must not contain final usage fields"
            )
    if top_level is not None and nested is not None:
        top_contract = {
            name: value for name, value in top_level.items()
            if name not in FINAL_USAGE_FIELDS
        }
        nested_contract = {
            name: value for name, value in nested.items()
            if name not in FINAL_USAGE_FIELDS
        }
        if top_contract != nested_contract:
            raise ValueError("conflicting queue_bounds across top-level and intent_contract")

    dispatched_work = bool(_planned_threads(record) or _spawned_threads(record))
    if (
        phase == "preflight"
        or _multi_lane(record)
        or dispatched_work
        or "queue_ledger" in record
    ) and top_level is None and nested is None:
        raise ValueError(
            "queue_bounds is required for preflight, multi-lane, queue-ledger, "
            "and dispatched runs"
        )
    bounds = top_level if top_level is not None else nested
    if phase == "preflight":
        planned = _planned_threads(record)
        if not planned:
            raise ValueError(
                "thread_dispatch_gate.planned_native_threads must contain at least one lane "
                "for a threads preflight"
            )
        planned_lane_ids: set[str] = set()
        for lane in planned:
            lane_id = lane.get("id") or lane.get("lane_id") if isinstance(lane, dict) else None
            if not isinstance(lane_id, str) or not lane_id.strip():
                raise ValueError(
                    "preflight planned_native_threads entries require string id"
                )
            if lane_id in planned_lane_ids:
                raise ValueError("preflight planned_native_threads ids must be unique")
            planned_lane_ids.add(lane_id)
        if _positive_int(bounds["max_model_calls"], "queue_bounds.max_model_calls") < len(planned):
            raise ValueError("queue_bounds.max_model_calls cannot be lower than planned lanes")
    elif bounds is not None:
        spawned = _spawned_threads(record)
        items_processed = bounds.get("items_processed")
        model_calls_used = bounds.get("model_calls_used")
        if items_processed is None:
            raise ValueError("queue_bounds.items_processed is required for final bounded runs")
        if model_calls_used is None:
            raise ValueError("queue_bounds.model_calls_used is required for final bounded runs")
        if model_calls_used < len(spawned):
            raise ValueError(
                "queue_bounds.model_calls_used cannot be lower than spawned agents"
            )
        if model_calls_used > _positive_int(
            bounds["max_model_calls"], "queue_bounds.max_model_calls"
        ):
            raise ValueError("queue_bounds.model_calls_used exceeds max_model_calls")
        queue_ledger = record.get("queue_ledger")
        known_ledger_usage = 0
        if isinstance(queue_ledger, dict):
            items_closed = queue_ledger.get("items_closed", 0) if isinstance(queue_ledger, dict) else 0
            items_deferred = queue_ledger.get("items_deferred", 0) if isinstance(queue_ledger, dict) else 0
            superseded = queue_ledger.get("superseded_items", [])
            superseded_count = len(superseded) if isinstance(superseded, list) else 0
            known_ledger_usage = items_closed + items_deferred + superseded_count
        if items_processed < known_ledger_usage:
            raise ValueError(
                "queue_bounds.items_processed cannot be lower than queue ledger usage"
            )
        if items_processed > _positive_int(bounds["max_items"], "queue_bounds.max_items"):
            raise ValueError(
                "queue_bounds.max_items cannot be lower than processed queue_ledger items"
            )
        elapsed_seconds = bounds.get("elapsed_seconds")
        if elapsed_seconds is None:
            raise ValueError("queue_bounds.elapsed_seconds is required for final bounded runs")
        if elapsed_seconds > _duration_seconds(
            bounds["time_budget"], "queue_bounds.time_budget"
        ):
            raise ValueError("queue_bounds.elapsed_seconds exceeds time_budget")
