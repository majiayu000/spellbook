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

TERMINATION_SIGNALS = (signal.SIGHUP, signal.SIGINT, signal.SIGQUIT, signal.SIGTERM)


def positive_seconds(value: str) -> float:
    seconds = float(value)
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("timeout must be finite and positive")
    return seconds


def ps_reports_live_members(group_id: int) -> bool:
    try:
        result = subprocess.run(
            ["ps", "-axo", "pgid=,stat="],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return True
    if result.returncode != 0:
        return True
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0] == str(group_id) and not fields[1].startswith("Z"):
            return True
    return False


def process_group_has_live_members(group_id: int) -> bool:
    try:
        os.killpg(group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return ps_reports_live_members(group_id)
    return ps_reports_live_members(group_id)


def stop_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 5
    while process_group_has_live_members(process.pid) and time.monotonic() < deadline:
        process.poll()
        time.sleep(0.05)
    if process_group_has_live_members(process.pid):
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

    def handle_termination(signum: int, frame: object) -> None:
        for termination_signal in TERMINATION_SIGNALS:
            signal.signal(termination_signal, signal.SIG_IGN)
        stop_process_group(process)
        raise SystemExit(128 + signum)

    for termination_signal in TERMINATION_SIGNALS:
        signal.signal(termination_signal, handle_termination)
    deadline = time.monotonic() + args.timeout_seconds
    try:
        return_code = process.wait(timeout=args.timeout_seconds)
        while process_group_has_live_members(process.pid):
            remaining_seconds = deadline - time.monotonic()
            if remaining_seconds <= 0:
                raise subprocess.TimeoutExpired(args.command, args.timeout_seconds)
            time.sleep(min(0.05, remaining_seconds))
        return 128 - return_code if return_code < 0 else return_code
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
