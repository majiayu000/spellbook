#!/usr/bin/env python3
"""Validate the structural and pacing contract of a product demo beat plan."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


TOLERANCE_SECONDS = 0.05
BEAT_TYPES = {"normal", "title", "hold"}
TRUTH_MODES = {"live", "deterministic", "composite", "title"}
REQUIRED_TEXT_FIELDS = (
    "claim",
    "visible_action",
    "audience_before",
    "audience_after",
    "entry_state",
    "exit_state",
    "audio_intent",
    "cut_reason",
)


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path, help="Path to beat-plan.json")
    return parser.parse_args()


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def require_text(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} must be a non-empty string")


def require_positive_number(value: Any, path: str, errors: list[str]) -> None:
    if not is_number(value) or value <= 0:
        errors.append(f"{path} must be a positive number")


def require_string_list(value: Any, path: str, errors: list[str], *, allow_empty: bool = True) -> None:
    if not isinstance(value, list):
        errors.append(f"{path} must be an array")
        return
    if not allow_empty and not value:
        errors.append(f"{path} must not be empty")
    for index, item in enumerate(value):
        require_text(item, f"{path}[{index}]", errors)


def validate_plan(plan: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["plan root must be an object"]

    if plan.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    product = plan.get("product")
    if not isinstance(product, dict):
        errors.append("product must be an object")
    else:
        for field in ("name", "repository", "revision"):
            require_text(product.get(field), f"product.{field}", errors)

    require_text(plan.get("audience"), "audience", errors)
    require_text(plan.get("proof_proposition"), "proof_proposition", errors)
    require_positive_number(plan.get("duration_seconds"), "duration_seconds", errors)
    require_positive_number(plan.get("max_information_gap_seconds"), "max_information_gap_seconds", errors)

    delivery = plan.get("delivery")
    if not isinstance(delivery, dict):
        errors.append("delivery must be an object")
    else:
        for field in ("width", "height", "fps"):
            require_positive_number(delivery.get(field), f"delivery.{field}", errors)
        require_text(delivery.get("container"), "delivery.container", errors)

    truth_boundary = plan.get("truth_boundary")
    if not isinstance(truth_boundary, dict):
        errors.append("truth_boundary must be an object")
    else:
        for field in ("live", "deterministic", "composite", "excluded"):
            require_string_list(truth_boundary.get(field), f"truth_boundary.{field}", errors)

    duration = plan.get("duration_seconds")
    max_gap = plan.get("max_information_gap_seconds")
    beats = plan.get("beats")
    if not isinstance(beats, list) or not beats:
        errors.append("beats must be a non-empty array")
        return errors

    seen_ids: set[str] = set()
    previous_end = 0.0

    for index, beat in enumerate(beats):
        prefix = f"beats[{index}]"
        if not isinstance(beat, dict):
            errors.append(f"{prefix} must be an object")
            continue

        beat_id = beat.get("id")
        require_text(beat_id, f"{prefix}.id", errors)
        if isinstance(beat_id, str) and beat_id.strip():
            if beat_id in seen_ids:
                errors.append(f"{prefix}.id duplicates {beat_id!r}")
            seen_ids.add(beat_id)

        beat_type = beat.get("type")
        if beat_type not in BEAT_TYPES:
            errors.append(f"{prefix}.type must be one of {sorted(BEAT_TYPES)}")

        truth_mode = beat.get("truth_mode")
        if truth_mode not in TRUTH_MODES:
            errors.append(f"{prefix}.truth_mode must be one of {sorted(TRUTH_MODES)}")

        start = beat.get("start_seconds")
        end = beat.get("end_seconds")
        if not is_number(start) or start < 0:
            errors.append(f"{prefix}.start_seconds must be a non-negative number")
        if not is_number(end) or end <= 0:
            errors.append(f"{prefix}.end_seconds must be a positive number")

        if is_number(start) and is_number(end):
            if end <= start:
                errors.append(f"{prefix} must end after it starts")
            if abs(start - previous_end) > TOLERANCE_SECONDS:
                relation = "gap" if start > previous_end else "overlap"
                errors.append(f"{prefix} has a {relation}: expected start {previous_end:.3f}, got {start:.3f}")
            beat_duration = end - start
            if beat_type == "normal" and is_number(max_gap) and max_gap > 0 and beat_duration > max_gap + TOLERANCE_SECONDS:
                errors.append(f"{prefix} lasts {beat_duration:.3f}s, above max_information_gap_seconds {max_gap}")
            previous_end = end

        for field in REQUIRED_TEXT_FIELDS:
            require_text(beat.get(field), f"{prefix}.{field}", errors)
        if not isinstance(beat.get("narration"), str):
            errors.append(f"{prefix}.narration must be a string")

        require_string_list(beat.get("evidence"), f"{prefix}.evidence", errors, allow_empty=truth_mode == "title")

        if beat_type == "hold":
            require_text(beat.get("hold_reason"), f"{prefix}.hold_reason", errors)

        audience_changed = beat.get("audience_before") != beat.get("audience_after")
        product_changed = beat.get("entry_state") != beat.get("exit_state")
        if not audience_changed and not product_changed:
            errors.append(f"{prefix} changes neither audience knowledge nor product state")

    if is_number(duration) and abs(previous_end - duration) > TOLERANCE_SECONDS:
        errors.append(f"beats end at {previous_end:.3f}s but duration_seconds is {duration:.3f}s")

    return errors


def main() -> int:
    args = parse_cli_args()
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"error: plan not found: {args.plan}", file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read plan: {exc}", file=sys.stderr)
        return 2

    errors = validate_plan(plan)
    if errors:
        print(f"invalid demo plan: {len(errors)} error(s)", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(json.dumps({
        "valid": True,
        "plan": str(args.plan),
        "beats": len(plan["beats"]),
        "duration_seconds": plan["duration_seconds"],
        "max_information_gap_seconds": plan["max_information_gap_seconds"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
