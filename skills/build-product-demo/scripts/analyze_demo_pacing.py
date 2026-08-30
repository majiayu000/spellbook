#!/usr/bin/env python3
"""Measure audio silence and low-motion spans in a product demo with ffmpeg."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


SILENCE_START_RE = re.compile(r"silence_start:\s*([0-9.]+)")
SILENCE_END_RE = re.compile(r"silence_end:\s*([0-9.]+)")
SILENCE_DURATION_RE = re.compile(r"silence_duration:\s*([0-9.]+)")
FREEZE_START_RE = re.compile(r"freeze_start:\s*([0-9.]+)")
FREEZE_END_RE = re.compile(r"freeze_end:\s*([0-9.]+)")
FREEZE_DURATION_RE = re.compile(r"freeze_duration:\s*([0-9.]+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media", type=Path)
    parser.add_argument("--plan", type=Path, help="Validated beat plan containing hold intervals.")
    parser.add_argument("--silence-noise", default="-35dB")
    parser.add_argument("--silence-min-duration", type=float, default=0.45)
    # Terminal and code demos often change only a small text region. A more
    # sensitive default keeps those real interactions from being mistaken for
    # a frozen full-screen slide while still catching long static holds.
    parser.add_argument("--freeze-noise", default="-50dB")
    parser.add_argument("--freeze-min-duration", type=float, default=1.0)
    parser.add_argument("--max-silence-ratio", type=float, default=0.18)
    parser.add_argument("--max-silence-segment", type=float, default=1.75)
    parser.add_argument("--max-low-motion-ratio", type=float, default=0.40)
    parser.add_argument("--max-low-motion-segment", type=float, default=4.0)
    parser.add_argument("--json-out", type=Path)
    return parser.parse_args()


def run(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"command exited {result.returncode}")
    return result.stdout + result.stderr


def timed_segments(
    start_pattern: re.Pattern[str],
    end_pattern: re.Pattern[str],
    duration_pattern: re.Pattern[str],
    output: str,
    media_duration: float,
) -> list[tuple[float, float, float]]:
    starts = [float(match.group(1)) for match in start_pattern.finditer(output)]
    ends = [float(match.group(1)) for match in end_pattern.finditer(output)]
    durations = [float(match.group(1)) for match in duration_pattern.finditer(output)]
    if not starts and not ends and not durations:
        return []
    if len(starts) == len(ends) + 1 and len(durations) == len(ends):
        ends.append(media_duration)
        durations.append(media_duration - starts[-1])
    if not (len(starts) == len(ends) == len(durations)):
        raise RuntimeError("ffmpeg emitted incomplete interval metadata")
    segments = list(zip(starts, ends, durations))
    if any(end <= start or abs((end - start) - duration) > 0.1 for start, end, duration in segments):
        raise RuntimeError("ffmpeg emitted inconsistent interval metadata")
    return segments


def load_hold_intervals(path: Path | None) -> list[tuple[float, float]]:
    if path is None:
        return []
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read beat plan: {exc}") from exc
    if not isinstance(plan, dict) or not isinstance(plan.get("beats"), list):
        raise RuntimeError("beat plan must contain a beats array")
    intervals: list[tuple[float, float]] = []
    for index, beat in enumerate(plan["beats"]):
        if not isinstance(beat, dict) or beat.get("type") != "hold":
            continue
        start = beat.get("start_seconds")
        end = beat.get("end_seconds")
        reason = beat.get("hold_reason")
        if (
            isinstance(start, bool)
            or not isinstance(start, (int, float))
            or isinstance(end, bool)
            or not isinstance(end, (int, float))
            or start < 0
            or end <= start
            or not isinstance(reason, str)
            or not reason.strip()
        ):
            raise RuntimeError(f"beats[{index}] has an invalid hold interval")
        intervals.append((float(start), float(end)))
    return intervals


def split_exempt_segments(
    segments: list[tuple[float, float, float]],
    holds: list[tuple[float, float]],
) -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]]]:
    checked: list[tuple[float, float, float]] = []
    exempt: list[tuple[float, float, float]] = []
    for segment in segments:
        start, end, _ = segment
        target = exempt if any(start >= left - 0.05 and end <= right + 0.05 for left, right in holds) else checked
        target.append(segment)
    return checked, exempt


def main() -> int:
    args = parse_args()
    if not args.media.is_file():
        print(f"error: media not found: {args.media}", file=sys.stderr)
        return 2
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        print("error: ffmpeg and ffprobe are required", file=sys.stderr)
        return 2
    try:
        hold_intervals = load_hold_intervals(args.plan)
        probe = json.loads(run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration:stream=index,codec_type,duration",
            "-of", "json", str(args.media)
        ]))
        duration = float(probe["format"]["duration"])
        streams = probe.get("streams", [])
        stream_details: list[tuple[str, object, float | None]] = []
        for position, stream in enumerate(streams):
            if not isinstance(stream, dict):
                continue
            stream_type = stream.get("codec_type")
            if stream_type not in {"audio", "video"}:
                continue
            stream_index = stream.get("index", position)
            raw_duration = stream.get("duration")
            try:
                stream_duration = float(raw_duration) if raw_duration is not None else None
            except (TypeError, ValueError):
                stream_duration = None
            stream_details.append((stream_type, stream_index, stream_duration))
        stream_types = {stream_type for stream_type, _, _ in stream_details}
        silence_output = run([
            "ffmpeg", "-hide_banner", "-nostats", "-i", str(args.media),
            "-af", f"silencedetect=noise={args.silence_noise}:d={args.silence_min_duration}",
            "-f", "null", "-",
        ])
        freeze_output = run([
            "ffmpeg", "-hide_banner", "-nostats", "-i", str(args.media),
            "-vf", f"freezedetect=n={args.freeze_noise}:d={args.freeze_min_duration}",
            "-an", "-f", "null", "-",
        ])
        silence_segments = timed_segments(
            SILENCE_START_RE, SILENCE_END_RE, SILENCE_DURATION_RE, silence_output, duration
        )
        low_motion_segments = timed_segments(
            FREEZE_START_RE, FREEZE_END_RE, FREEZE_DURATION_RE, freeze_output, duration
        )
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    checked_silence, exempt_silence = split_exempt_segments(silence_segments, hold_intervals)
    checked_low_motion, exempt_low_motion = split_exempt_segments(
        low_motion_segments, hold_intervals
    )
    silence_total = sum(segment[2] for segment in silence_segments)
    low_motion_total = sum(segment[2] for segment in low_motion_segments)
    checked_silence_total = sum(segment[2] for segment in checked_silence)
    checked_low_motion_total = sum(segment[2] for segment in checked_low_motion)
    checked_duration = max(0.0, duration - sum(end - start for start, end in hold_intervals))
    silence_ratio = checked_silence_total / checked_duration if checked_duration else 0.0
    low_motion_ratio = checked_low_motion_total / checked_duration if checked_duration else 0.0
    silence_durations = [segment[2] for segment in checked_silence]
    low_motion_durations = [segment[2] for segment in checked_low_motion]
    errors: list[str] = []
    if "video" not in stream_types:
        errors.append("media has no video stream")
    if "audio" not in stream_types:
        errors.append("media has no audio stream")
    for stream_type, stream_index, stream_duration in stream_details:
        stream_label = f"{stream_type} stream {stream_index}"
        if stream_duration is None:
            errors.append(f"{stream_label} duration is unavailable")
        elif stream_duration is not None and abs(stream_duration - duration) > 0.2:
            errors.append(
                f"{stream_label} duration {stream_duration:.3f}s differs from "
                f"container duration {duration:.3f}s"
            )
    if silence_ratio > args.max_silence_ratio:
        errors.append(f"silence ratio {silence_ratio:.3f} exceeds {args.max_silence_ratio:.3f}")
    if silence_durations and max(silence_durations) > args.max_silence_segment:
        errors.append(f"longest silence {max(silence_durations):.3f}s exceeds {args.max_silence_segment:.3f}s")
    if low_motion_ratio > args.max_low_motion_ratio:
        errors.append(f"low-motion ratio {low_motion_ratio:.3f} exceeds {args.max_low_motion_ratio:.3f}")
    if low_motion_durations and max(low_motion_durations) > args.max_low_motion_segment:
        errors.append(f"longest low-motion span {max(low_motion_durations):.3f}s exceeds {args.max_low_motion_segment:.3f}s")

    report = {
        "valid": not errors,
        "media": args.media.name,
        "duration_seconds": duration,
        "checked_duration_seconds": round(checked_duration, 3),
        "stream_durations_seconds": [
            {
                "index": stream_index,
                "type": stream_type,
                "duration_seconds": None if stream_duration is None else round(stream_duration, 3),
            }
            for stream_type, stream_index, stream_duration in stream_details
        ],
        "silence": {
            "total_seconds": round(silence_total, 3),
            "checked_seconds": round(checked_silence_total, 3),
            "exempt_seconds": round(sum(segment[2] for segment in exempt_silence), 3),
            "ratio": round(silence_ratio, 4),
            "longest_segment_seconds": round(max(silence_durations, default=0.0), 3),
            "segments": len(silence_segments),
            "exempt_segments": len(exempt_silence),
        },
        "low_motion": {
            "total_seconds": round(low_motion_total, 3),
            "checked_seconds": round(checked_low_motion_total, 3),
            "exempt_seconds": round(sum(segment[2] for segment in exempt_low_motion), 3),
            "ratio": round(low_motion_ratio, 4),
            "longest_segment_seconds": round(max(low_motion_durations, default=0.0), 3),
            "segments": len(low_motion_segments),
            "exempt_segments": len(exempt_low_motion),
        },
        "thresholds": {
            "max_silence_ratio": args.max_silence_ratio,
            "max_silence_segment": args.max_silence_segment,
            "max_low_motion_ratio": args.max_low_motion_ratio,
            "max_low_motion_segment": args.max_low_motion_segment,
        },
        "errors": errors,
    }
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered + "\n", encoding="utf-8")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
