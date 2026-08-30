#!/usr/bin/env python3
"""Validate the structural and pacing contract of a product demo beat plan."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import TypeGuard


TOLERANCE_SECONDS = 0.05
BEAT_TYPES = {"normal", "title", "hold"}
TRUTH_MODES = {"live", "deterministic", "composite", "title"}
SURFACES = {"native", "composite", "title"}
EVENT_KINDS = {"product_action", "input", "result", "reveal", "cut", "sound", "hold"}
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


def is_number(value: object) -> TypeGuard[int | float]:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return abs(value) <= sys.float_info.max
    return isinstance(value, float) and math.isfinite(value)


def require_text(value: object, path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} must be a non-empty string")


def require_positive_number(value: object, path: str, errors: list[str]) -> None:
    if not is_number(value) or value <= 0:
        errors.append(f"{path} must be a positive number")


def require_positive_integer(value: object, path: str, errors: list[str]) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        errors.append(f"{path} must be a positive integer")


def require_enum(value: object, allowed: set[str], path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or value not in allowed:
        errors.append(f"{path} must be one of {sorted(allowed)}")


def require_string_list(value: object, path: str, errors: list[str], *, allow_empty: bool = True) -> None:
    if not isinstance(value, list):
        errors.append(f"{path} must be an array")
        return
    if not allow_empty and not value:
        errors.append(f"{path} must not be empty")
    for index, item in enumerate(value):
        require_text(item, f"{path}[{index}]", errors)


def validate_plan(plan: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["plan root must be an object"]

    schema_version = plan.get("schema_version")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != 2
    ):
        errors.append("schema_version must be integer 2")

    product = plan.get("product")
    if not isinstance(product, dict):
        errors.append("product must be an object")
    else:
        for field in ("name", "repository", "revision"):
            require_text(product.get(field), f"product.{field}", errors)

    require_text(plan.get("audience"), "audience", errors)
    require_text(plan.get("proof_proposition"), "proof_proposition", errors)
    require_text(plan.get("reference_benchmark"), "reference_benchmark", errors)
    require_positive_number(plan.get("duration_seconds"), "duration_seconds", errors)
    require_positive_number(plan.get("max_information_gap_seconds"), "max_information_gap_seconds", errors)
    require_positive_number(plan.get("max_attention_gap_seconds"), "max_attention_gap_seconds", errors)

    native_exception = plan.get("native_surface_exception")
    has_native_exception = isinstance(native_exception, str) and bool(native_exception.strip())
    if native_exception is not None:
        require_text(native_exception, "native_surface_exception", errors)
    native_target = plan.get("native_surface_target_ratio")
    minimum_native_target = 0 if has_native_exception else 0.6
    if not is_number(native_target) or not minimum_native_target <= native_target <= 1:
        errors.append(
            "native_surface_target_ratio must be between "
            f"{minimum_native_target:g} and 1"
        )
    uses_native_exception = (
        has_native_exception and is_number(native_target) and native_target < 0.6
    )
    if has_native_exception and not uses_native_exception:
        errors.append("native_surface_exception is only allowed for a target below 0.6")
    first_action_limit = plan.get("first_product_action_seconds")
    if not is_number(first_action_limit) or not 0 <= first_action_limit <= 5:
        errors.append("first_product_action_seconds must be between 0 and 5")

    delivery = plan.get("delivery")
    if not isinstance(delivery, dict):
        errors.append("delivery must be an object")
    else:
        for field in ("width", "height"):
            require_positive_integer(delivery.get(field), f"delivery.{field}", errors)
        require_positive_number(delivery.get("fps"), "delivery.fps", errors)
        for field in ("container", "video_codec", "audio_codec"):
            require_text(delivery.get(field), f"delivery.{field}", errors)
        duration_tolerance = delivery.get("duration_tolerance_seconds")
        require_positive_number(
            duration_tolerance, "delivery.duration_tolerance_seconds", errors
        )
        if is_number(duration_tolerance) and duration_tolerance > 0.25:
            require_text(
                delivery.get("duration_tolerance_reason"),
                "delivery.duration_tolerance_reason",
                errors,
            )

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
    native_duration = 0.0
    explanatory_duration = 0.0
    cumulative_gap = 0.0
    cumulative_overlap = 0.0
    event_times: list[tuple[float, str, str]] = []
    product_action_times: list[float] = []
    hold_intervals: list[tuple[float, float]] = []
    used_truth_modes: set[str] = set()

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
        require_enum(beat_type, BEAT_TYPES, f"{prefix}.type", errors)

        truth_mode = beat.get("truth_mode")
        require_enum(truth_mode, TRUTH_MODES, f"{prefix}.truth_mode", errors)
        if isinstance(truth_mode, str) and truth_mode in {
            "live",
            "deterministic",
            "composite",
        }:
            used_truth_modes.add(truth_mode)

        surface = beat.get("surface")
        require_enum(surface, SURFACES, f"{prefix}.surface", errors)
        if beat_type == "title" and surface != "title":
            errors.append(f"{prefix}.surface must be 'title' for a title beat")
        if beat_type == "title" and truth_mode != "title":
            errors.append(f"{prefix}.truth_mode must be 'title' for a title beat")
        if truth_mode == "title" and beat_type != "title":
            errors.append(f"{prefix}.type must be 'title' when truth_mode is 'title'")
        if truth_mode == "title" and beat_type != "title" and surface != "title":
            errors.append(f"{prefix}.surface must be 'title' when truth_mode is 'title'")
        if surface == "title" and beat_type != "title":
            errors.append(f"{prefix}.type must be 'title' for a title surface")
        if surface == "title" and truth_mode != "title":
            errors.append(f"{prefix}.truth_mode must be 'title' for a title surface")

        start = beat.get("start_seconds")
        end = beat.get("end_seconds")
        if not is_number(start) or start < 0:
            errors.append(f"{prefix}.start_seconds must be a non-negative number")
        if not is_number(end) or end <= 0:
            errors.append(f"{prefix}.end_seconds must be a positive number")

        if is_number(start) and is_number(end):
            if end <= start:
                errors.append(f"{prefix} must end after it starts")
            boundary_delta = start - previous_end
            if boundary_delta > 0:
                cumulative_gap += boundary_delta
            elif boundary_delta < 0:
                cumulative_overlap -= boundary_delta
            if abs(boundary_delta) > TOLERANCE_SECONDS:
                relation = "gap" if boundary_delta > 0 else "overlap"
                errors.append(f"{prefix} has a {relation}: expected start {previous_end:.3f}, got {start:.3f}")
            beat_duration = end - start
            if beat_type == "title":
                explanatory_duration += beat_duration
            elif surface == "native":
                native_duration += beat_duration
            elif surface == "title" or surface == "composite":
                explanatory_duration += beat_duration
            if beat_type == "hold":
                hold_intervals.append((float(start), float(end)))
            if beat_type == "normal" and is_number(max_gap) and max_gap > 0 and beat_duration > max_gap + TOLERANCE_SECONDS:
                errors.append(f"{prefix} lasts {beat_duration:.3f}s, above max_information_gap_seconds {max_gap}")
            previous_end = end

        for field in REQUIRED_TEXT_FIELDS:
            require_text(beat.get(field), f"{prefix}.{field}", errors)
        if not isinstance(beat.get("narration"), str):
            errors.append(f"{prefix}.narration must be a string")

        require_string_list(beat.get("evidence"), f"{prefix}.evidence", errors, allow_empty=truth_mode == "title")

        events = beat.get("events")
        if not isinstance(events, list) or (beat_type == "normal" and not events):
            errors.append(f"{prefix}.events must be a non-empty array for normal beats")
        elif isinstance(events, list):
            previous_event = None
            for event_index, event in enumerate(events):
                event_prefix = f"{prefix}.events[{event_index}]"
                if not isinstance(event, dict):
                    errors.append(f"{event_prefix} must be an object")
                    continue
                at_seconds = event.get("at_seconds")
                kind = event.get("kind")
                require_text(event.get("description"), f"{event_prefix}.description", errors)
                require_enum(kind, EVENT_KINDS, f"{event_prefix}.kind", errors)
                if not is_number(at_seconds):
                    errors.append(f"{event_prefix}.at_seconds must be a number")
                    continue
                if is_number(start) and is_number(end) and not start <= at_seconds < end:
                    errors.append(f"{event_prefix}.at_seconds must fall inside its beat")
                    continue
                if previous_event is not None and at_seconds <= previous_event:
                    errors.append(f"{event_prefix}.at_seconds must increase within the beat")
                previous_event = at_seconds
                event_times.append((float(at_seconds), str(kind), str(beat_type)))
                qualifying_product_surface = surface == "native" or (
                    uses_native_exception and surface == "composite"
                )
                if kind == "product_action" and beat_type == "normal" and qualifying_product_surface:
                    product_action_times.append(float(at_seconds))

        if beat_type == "hold":
            require_text(beat.get("hold_reason"), f"{prefix}.hold_reason", errors)

        audience_changed = beat.get("audience_before") != beat.get("audience_after")
        product_changed = beat.get("entry_state") != beat.get("exit_state")
        if not audience_changed and not product_changed:
            errors.append(f"{prefix} changes neither audience knowledge nor product state")

    if isinstance(truth_boundary, dict):
        for truth_mode in sorted(used_truth_modes):
            if not truth_boundary.get(truth_mode):
                errors.append(
                    f"truth_boundary.{truth_mode} must disclose the used truth mode"
                )

    if is_number(duration):
        terminal_delta = duration - previous_end
        if terminal_delta > 0:
            cumulative_gap += terminal_delta
        elif terminal_delta < 0:
            cumulative_overlap -= terminal_delta
    if cumulative_gap > TOLERANCE_SECONDS:
        errors.append(
            f"aggregate beat gaps total {cumulative_gap:.3f}s, "
            f"above tolerance {TOLERANCE_SECONDS:.3f}s"
        )
    if cumulative_overlap > TOLERANCE_SECONDS:
        errors.append(
            f"aggregate beat overlaps total {cumulative_overlap:.3f}s, "
            f"above tolerance {TOLERANCE_SECONDS:.3f}s"
        )
    if is_number(duration) and abs(previous_end - duration) > TOLERANCE_SECONDS:
        errors.append(f"beats end at {previous_end:.3f}s but duration_seconds is {duration:.3f}s")

    if is_number(duration) and duration > 0 and is_number(native_target):
        native_ratio = native_duration / duration
        if native_ratio + 1e-6 < native_target:
            errors.append(
                f"native surface ratio is {native_ratio:.3f}, below target {native_target:.3f}"
            )
        explanatory_ratio = explanatory_duration / duration
        if not uses_native_exception and explanatory_ratio >= 0.2 - 1e-6:
            errors.append(
                f"explanatory surface ratio is {explanatory_ratio:.3f}, "
                "but must stay below 0.200 without native_surface_exception"
            )

    if not product_action_times:
        errors.append("plan must contain at least one product_action event")
    elif is_number(first_action_limit) and min(product_action_times) > first_action_limit + TOLERANCE_SECONDS:
        errors.append(
            f"first product action occurs at {min(product_action_times):.3f}s, after limit {first_action_limit:.3f}s"
        )

    max_attention_gap = plan.get("max_attention_gap_seconds")
    if is_number(duration) and is_number(max_attention_gap) and max_attention_gap > 0:
        active_times = sorted(time for time, kind, beat_type in event_times if kind != "hold" and beat_type != "hold")
        boundaries = [0.0, *active_times, float(duration)]
        for left, right in zip(boundaries, boundaries[1:]):
            motivated_hold = sum(
                max(0.0, min(right, hold_end) - max(left, hold_start))
                for hold_start, hold_end in hold_intervals
            )
            gap = right - left - motivated_hold
            if gap > max_attention_gap + TOLERANCE_SECONDS:
                errors.append(
                    f"unmotivated attention gap from {left:.3f}s to {right:.3f}s is "
                    f"{gap:.3f}s after excluding holds, above {max_attention_gap:.3f}s"
                )

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
        "plan": args.plan.name,
        "beats": len(plan["beats"]),
        "duration_seconds": plan["duration_seconds"],
        "max_information_gap_seconds": plan["max_information_gap_seconds"],
        "max_attention_gap_seconds": plan["max_attention_gap_seconds"],
        "native_surface_target_ratio": plan["native_surface_target_ratio"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
