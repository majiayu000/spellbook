#!/usr/bin/env python3
"""Run or resume a fixed GPT-5.6 Luna Max Codex worker and summarize JSONL output."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import TextIO


MODEL = "gpt-5.6-luna"
REASONING_EFFORT = "max"
DEFAULT_TIMEOUT_SECONDS = 1800
STDERR_TAIL_CHARS = 4000


class WorkerRunError(RuntimeError):
    """Raised when the Luna worker does not complete with valid evidence."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run or resume a gpt-5.6-luna Codex worker at max reasoning."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Start a new Luna Max worker thread.")
    add_shared_arguments(run_parser)
    run_parser.add_argument(
        "--sandbox",
        choices=("read-only", "workspace-write"),
        default="workspace-write",
        help="Worker sandbox for the new thread.",
    )
    run_parser.add_argument(
        "--allow-non-git",
        action="store_true",
        help="Allow a target that is not inside a Git repository.",
    )

    resume_parser = subparsers.add_parser("resume", help="Resume an existing Luna worker thread.")
    add_shared_arguments(resume_parser)
    resume_parser.add_argument("--thread-id", required=True, help="Codex worker thread UUID or name.")

    return parser


def add_shared_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cwd", required=True, help="Absolute target working directory.")
    parser.add_argument("--prompt-file", required=True, help="UTF-8 worker prompt file.")
    parser.add_argument(
        "--events-file",
        help="Optional path for the unmodified Codex JSONL event stream.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Maximum worker runtime before termination.",
    )
    parser.add_argument(
        "--codex-bin",
        help="Codex executable path. Defaults to SOL_LUNA_CODEX_BIN or PATH lookup.",
    )


def resolve_codex_bin(explicit: str | None) -> str:
    candidate = explicit or os.environ.get("SOL_LUNA_CODEX_BIN") or shutil.which("codex")
    if not candidate:
        raise WorkerRunError("Codex executable was not found")
    resolved = Path(candidate).expanduser()
    if resolved.is_absolute():
        if not resolved.is_file() or not os.access(resolved, os.X_OK):
            raise WorkerRunError(f"Codex executable is not runnable: {resolved}")
        return str(resolved)
    return candidate


def resolve_inputs(args: argparse.Namespace) -> tuple[Path, Path, str, str | None]:
    cwd = Path(args.cwd).expanduser()
    if not cwd.is_absolute() or not cwd.is_dir():
        raise WorkerRunError(f"--cwd must be an existing absolute directory: {cwd}")

    prompt_file = Path(args.prompt_file).expanduser()
    if not prompt_file.is_absolute() or not prompt_file.is_file():
        raise WorkerRunError(
            f"--prompt-file must be an existing absolute file: {prompt_file}"
        )
    prompt = prompt_file.read_text(encoding="utf-8")
    if not prompt.strip():
        raise WorkerRunError("Worker prompt must not be empty")

    git_root = find_git_root(cwd)
    if args.command == "run" and git_root is None and not args.allow_non_git:
        raise WorkerRunError(
            "Target is not inside a Git repository; pass --allow-non-git only when intentional"
        )
    return cwd.resolve(), prompt_file.resolve(), prompt, git_root


def find_git_root(cwd: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    root = result.stdout.strip()
    return root or None


def build_codex_args(
    args: argparse.Namespace,
    codex_bin: str,
    cwd: Path,
    prompt: str,
) -> list[str]:
    command = [codex_bin, "exec", "--json", "--strict-config"]
    if args.command == "resume":
        return [*command, "resume", args.thread_id, prompt]

    command.extend(
        [
            "-m",
            MODEL,
            "-c",
            f'model_reasoning_effort="{REASONING_EFFORT}"',
            "-c",
            "features.multi_agent_v2.enabled=false",
            "-c",
            "agents.enabled=false",
            "--sandbox",
            args.sandbox,
            "-C",
            str(cwd),
        ]
    )
    if args.allow_non_git:
        command.append("--skip-git-repo-check")
    command.append(prompt)
    return command


def execute_worker(
    command: list[str], cwd: Path, timeout_seconds: int
) -> tuple[str, str, int]:
    if timeout_seconds <= 0:
        raise WorkerRunError("--timeout-seconds must be greater than zero")
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as error:
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
        raise WorkerRunError(
            f"Luna worker timed out after {timeout_seconds} seconds; "
            f"stderr tail: {stderr[-STDERR_TAIL_CHARS:]}"
        ) from error
    return stdout, stderr, process.returncode


def parse_events(stdout: str, stderr: str, returncode: int) -> dict[str, object]:
    events: list[dict[str, object]] = []
    thread_id: str | None = None
    final_response: str | None = None
    usage: object = None
    completed = False
    fatal_error: str | None = None
    warnings: list[str] = []

    for line_number, raw_line in enumerate(stdout.splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError as error:
            raise WorkerRunError(
                f"Codex emitted invalid JSONL on line {line_number}: {error.msg}"
            ) from error
        if not isinstance(event, dict):
            raise WorkerRunError(f"Codex JSONL line {line_number} is not an object")
        events.append(event)

        event_type = event.get("type")
        if event_type == "thread.started":
            candidate = event.get("thread_id")
            if isinstance(candidate, str) and candidate:
                thread_id = candidate
        elif event_type == "item.completed":
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message":
                text = item.get("text")
                if isinstance(text, str):
                    final_response = text
            elif isinstance(item, dict) and item.get("type") == "error":
                warnings.append(extract_error(item))
        elif event_type == "turn.completed":
            completed = True
            usage = event.get("usage")
        elif event_type == "turn.failed":
            fatal_error = extract_error(event)
        elif event_type == "error":
            warnings.append(extract_error(event))

    if returncode != 0:
        detail = fatal_error or (warnings[-1] if warnings else None)
        detail = detail or stderr[-STDERR_TAIL_CHARS:] or "no error details"
        raise WorkerRunError(f"Codex exited with status {returncode}: {detail}")
    if fatal_error:
        raise WorkerRunError(f"Codex reported a failed turn: {fatal_error}")
    if not completed:
        raise WorkerRunError("Codex did not emit turn.completed")
    if not thread_id:
        raise WorkerRunError("Codex did not emit thread.started with a thread ID")
    if final_response is None:
        raise WorkerRunError("Codex did not emit a final agent message")

    return {
        "thread_id": thread_id,
        "final_response": final_response,
        "usage": usage,
        "event_count": len(events),
        "warnings": warnings,
    }


def extract_error(event: dict[str, object]) -> str:
    error = event.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str):
            return message
        return json.dumps(error, ensure_ascii=False, sort_keys=True)
    if isinstance(error, str):
        return error
    message = event.get("message")
    if isinstance(message, str):
        return message
    return json.dumps(event, ensure_ascii=False, sort_keys=True)


def write_events(path_text: str | None, stdout: str) -> str | None:
    if path_text is None:
        return None
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        raise WorkerRunError(f"--events-file must be absolute: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stdout, encoding="utf-8")
    return str(path.resolve())


def run(args: argparse.Namespace, output: TextIO) -> None:
    cwd, prompt_file, prompt, git_root = resolve_inputs(args)
    codex_bin = resolve_codex_bin(args.codex_bin)
    command = build_codex_args(args, codex_bin, cwd, prompt)
    stdout, stderr, returncode = execute_worker(command, cwd, args.timeout_seconds)
    result = parse_events(stdout, stderr, returncode)
    result.update(
        {
            "model": MODEL,
            "reasoning_effort": REASONING_EFFORT,
            "cwd": str(cwd),
            "git_root": git_root,
            "prompt_file": str(prompt_file),
            "events_file": write_events(args.events_file, stdout),
        }
    )
    json.dump(result, output, ensure_ascii=False, sort_keys=True)
    output.write("\n")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        run(args, sys.stdout)
    except (OSError, WorkerRunError) as error:
        print(f"sol-luna-router: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
