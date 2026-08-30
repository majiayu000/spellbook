#!/usr/bin/env python3
"""Run a command with a hard timeout and terminate its whole process group."""

from __future__ import annotations

import argparse
import math
import os
import signal
import subprocess
import sys
import time


def positive_seconds(value: str) -> float:
    seconds = float(value)
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("timeout must be finite and positive")
    return seconds


def process_group_exists(group_id: int) -> bool:
    try:
        os.killpg(group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def stop_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 5
    while process_group_exists(process.pid) and time.monotonic() < deadline:
        process.poll()
        time.sleep(0.05)
    if process_group_exists(process.pid):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            process.wait()
            return
    process.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timeout_seconds", type=positive_seconds)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.command:
        parser.error("command is required")

    try:
        process = subprocess.Popen(args.command, start_new_session=True)
    except OSError as exc:
        print(f"run_with_timeout.py: cannot start command: {exc}", file=sys.stderr)
        return 127

    def handle_sigterm(signum: int, frame: object) -> None:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        stop_process_group(process)
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, handle_sigterm)
    try:
        return process.wait(timeout=args.timeout_seconds)
    except subprocess.TimeoutExpired:
        stop_process_group(process)
        print(
            f"run_with_timeout.py: command exceeded {args.timeout_seconds:g}s timeout",
            file=sys.stderr,
        )
        return 124
    except KeyboardInterrupt:
        stop_process_group(process)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
