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


SILENCE_RE = re.compile(r"silence_duration:\s*([0-9.]+)")
FREEZE_RE = re.compile(r"freeze_duration:\s*([0-9.]+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media", type=Path)
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


def durations(pattern: re.Pattern[str], output: str) -> list[float]:
    return [float(match.group(1)) for match in pattern.finditer(output)]


def main() -> int:
    args = parse_args()
    if not args.media.is_file():
        print(f"error: media not found: {args.media}", file=sys.stderr)
        return 2
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        print("error: ffmpeg and ffprobe are required", file=sys.stderr)
        return 2
    try:
        probe = json.loads(run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,duration",
            "-of", "json", str(args.media)
        ]))
        duration = float(probe["format"]["duration"])
        streams = probe.get("streams", [])
        stream_types = {stream.get("codec_type") for stream in streams}
        stream_durations = {
            stream.get("codec_type"): float(stream["duration"])
            for stream in streams
            if stream.get("codec_type") in {"audio", "video"} and stream.get("duration")
        }
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
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    silence = durations(SILENCE_RE, silence_output)
    low_motion = durations(FREEZE_RE, freeze_output)
    silence_total = sum(silence)
    low_motion_total = sum(low_motion)
    silence_ratio = silence_total / duration if duration else 0.0
    low_motion_ratio = low_motion_total / duration if duration else 0.0
    errors: list[str] = []
    if "video" not in stream_types:
        errors.append("media has no video stream")
    if "audio" not in stream_types:
        errors.append("media has no audio stream")
    for stream_type in ("video", "audio"):
        stream_duration = stream_durations.get(stream_type)
        if stream_type in stream_types and stream_duration is None:
            errors.append(f"{stream_type} stream duration is unavailable")
        elif stream_duration is not None and abs(stream_duration - duration) > 0.2:
            errors.append(
                f"{stream_type} stream duration {stream_duration:.3f}s differs from "
                f"container duration {duration:.3f}s"
            )
    if silence_ratio > args.max_silence_ratio:
        errors.append(f"silence ratio {silence_ratio:.3f} exceeds {args.max_silence_ratio:.3f}")
    if silence and max(silence) > args.max_silence_segment:
        errors.append(f"longest silence {max(silence):.3f}s exceeds {args.max_silence_segment:.3f}s")
    if low_motion_ratio > args.max_low_motion_ratio:
        errors.append(f"low-motion ratio {low_motion_ratio:.3f} exceeds {args.max_low_motion_ratio:.3f}")
    if low_motion and max(low_motion) > args.max_low_motion_segment:
        errors.append(f"longest low-motion span {max(low_motion):.3f}s exceeds {args.max_low_motion_segment:.3f}s")

    report = {
        "valid": not errors,
        "media": str(args.media.resolve()),
        "duration_seconds": duration,
        "stream_durations_seconds": {
            key: round(value, 3) for key, value in sorted(stream_durations.items())
        },
        "silence": {
            "total_seconds": round(silence_total, 3),
            "ratio": round(silence_ratio, 4),
            "longest_segment_seconds": round(max(silence, default=0.0), 3),
            "segments": len(silence),
        },
        "low_motion": {
            "total_seconds": round(low_motion_total, 3),
            "ratio": round(low_motion_ratio, 4),
            "longest_segment_seconds": round(max(low_motion, default=0.0), 3),
            "segments": len(low_motion),
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
