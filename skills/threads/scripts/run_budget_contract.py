"""Pre-dispatch budget validation for threads run records."""

from __future__ import annotations

import re


ALLOWED_RUN_PHASES = {"preflight", "final"}
CONCRETE_DURATION = re.compile(r"^[1-9][0-9]*(?:s|m|h)$")


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _planned_threads(record: dict[str, object]) -> list[object]:
    gate = record.get("thread_dispatch_gate")
    if not isinstance(gate, dict):
        return []
    planned = gate.get("planned_native_threads")
    return planned if isinstance(planned, list) else []


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
    if not isinstance(bounds["time_budget"], str) or not CONCRETE_DURATION.fullmatch(
        bounds["time_budget"].strip()
    ):
        raise ValueError(f"{field}.time_budget must be a concrete duration such as 30m or 2h")
    if not isinstance(bounds["queue_tranche"], str) or not bounds["queue_tranche"].strip():
        raise ValueError(f"{field}.queue_tranche must be a non-empty string")


def validate_run_budget(record: dict[str, object]) -> None:
    phase = record.get("run_phase")
    if phase not in ALLOWED_RUN_PHASES:
        raise ValueError(f"unknown run_phase: {phase}")

    top_level = record.get("queue_bounds")
    intent = record.get("intent_contract")
    nested = intent.get("queue_bounds") if isinstance(intent, dict) else None
    if top_level is not None:
        _validate_bounds(top_level, "queue_bounds")
    if nested is not None:
        _validate_bounds(nested, "intent_contract.queue_bounds")
    if top_level is not None and nested is not None and top_level != nested:
        raise ValueError("conflicting queue_bounds across top-level and intent_contract")

    if (phase == "preflight" or _multi_lane(record)) and top_level is None and nested is None:
        raise ValueError("queue_bounds is required for preflight and multi-lane runs")
    if phase == "preflight":
        planned = _planned_threads(record)
        if not planned:
            raise ValueError(
                "thread_dispatch_gate.planned_native_threads must contain at least one lane "
                "for a threads preflight"
            )
        for lane in planned:
            if not isinstance(lane, dict) or not (lane.get("id") or lane.get("lane_id")):
                raise ValueError("preflight planned_native_threads entries require id")
        bounds = top_level if top_level is not None else nested
        if _positive_int(bounds["max_model_calls"], "queue_bounds.max_model_calls") < len(planned):
            raise ValueError("queue_bounds.max_model_calls cannot be lower than planned lanes")
