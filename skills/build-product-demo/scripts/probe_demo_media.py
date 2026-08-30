#!/usr/bin/env python3
"""Probe a demo video with ffprobe and assert delivery constraints."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media", type=Path)
    parser.add_argument("--expect-width", type=int)
    parser.add_argument("--expect-height", type=int)
    parser.add_argument("--expect-fps", type=float)
    parser.add_argument("--fps-tolerance", type=float, default=0.1)
    parser.add_argument("--expect-duration", type=float)
    parser.add_argument("--duration-tolerance", type=float, default=0.25)
    parser.add_argument("--min-duration", type=float)
    parser.add_argument("--max-duration", type=float)
    parser.add_argument("--expect-container")
    parser.add_argument("--expect-video-codec")
    parser.add_argument("--expect-audio-codec")
    parser.add_argument("--require-audio", action="store_true")
    parser.add_argument("--json-out", type=Path)
    return parser.parse_args()


def frame_rate(value: object) -> float | None:
    if not isinstance(value, str) or not value or value == "0/0":
        return None
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        return None


def main() -> int:
    args = parse_cli_args()
    if not args.media.is_file():
        print(f"error: media not found: {args.media}", file=sys.stderr)
        return 2
    if args.json_out is not None and args.json_out.resolve() == args.media.resolve():
        print("error: json output must not overwrite media input", file=sys.stderr)
        return 2
    if shutil.which("ffprobe") is None:
        print("error: ffprobe is not available on PATH", file=sys.stderr)
        return 2

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration,format_name:stream=index,codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels",
        "-of",
        "json",
        str(args.media),
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        payload = json.loads(result.stdout)
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or f"ffprobe exited {exc.returncode}"
        print(f"error: {detail}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"error: invalid ffprobe JSON: {exc}", file=sys.stderr)
        return 2

    streams = payload.get("streams", [])
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    format_data = payload.get("format", {})
    format_name = format_data.get("format_name")
    try:
        duration = float(format_data.get("duration"))
    except (TypeError, ValueError):
        duration = None

    errors: list[str] = []
    if video_stream is None:
        errors.append("no video stream")
    if args.require_audio and audio_stream is None:
        errors.append("no audio stream")
    actual_containers = format_name.split(",") if isinstance(format_name, str) else []
    if args.expect_container and args.expect_container not in actual_containers:
        errors.append(f"container is {format_name}, expected {args.expect_container}")

    fps = frame_rate(video_stream.get("avg_frame_rate")) if video_stream else None
    if video_stream:
        if args.expect_width is not None and video_stream.get("width") != args.expect_width:
            errors.append(f"width is {video_stream.get('width')}, expected {args.expect_width}")
        if args.expect_height is not None and video_stream.get("height") != args.expect_height:
            errors.append(f"height is {video_stream.get('height')}, expected {args.expect_height}")
        if args.expect_video_codec and video_stream.get("codec_name") != args.expect_video_codec:
            errors.append(f"video codec is {video_stream.get('codec_name')}, expected {args.expect_video_codec}")
        if args.expect_fps is not None:
            if fps is None or abs(fps - args.expect_fps) > args.fps_tolerance:
                errors.append(f"frame rate is {fps}, expected {args.expect_fps} +/- {args.fps_tolerance}")

    if args.expect_audio_codec:
        actual_audio_codec = audio_stream.get("codec_name") if audio_stream else None
        if actual_audio_codec != args.expect_audio_codec:
            errors.append(f"audio codec is {actual_audio_codec}, expected {args.expect_audio_codec}")

    if duration is None:
        errors.append("duration is unavailable")
    else:
        if (
            args.expect_duration is not None
            and abs(duration - args.expect_duration) > args.duration_tolerance
        ):
            errors.append(
                f"duration is {duration:.3f}s, expected {args.expect_duration:.3f}s "
                f"+/- {args.duration_tolerance:.3f}s"
            )
        if args.min_duration is not None and duration < args.min_duration:
            errors.append(f"duration is {duration:.3f}s, below minimum {args.min_duration:.3f}s")
        if args.max_duration is not None and duration > args.max_duration:
            errors.append(f"duration is {duration:.3f}s, above maximum {args.max_duration:.3f}s")

    report = {
        "valid": not errors,
        "media": args.media.name,
        "size_bytes": args.media.stat().st_size,
        "format": format_name,
        "duration_seconds": duration,
        "video": None if video_stream is None else {
            "codec": video_stream.get("codec_name"),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "fps": fps,
        },
        "audio": None if audio_stream is None else {
            "codec": audio_stream.get("codec_name"),
            "sample_rate": audio_stream.get("sample_rate"),
            "channels": audio_stream.get("channels"),
        },
        "errors": errors,
    }
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(f"{rendered}\n", encoding="utf-8")

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
