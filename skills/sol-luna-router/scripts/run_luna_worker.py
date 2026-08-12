#!/usr/bin/env python3
"""Run or resume a fixed GPT-5.6 Luna Max worker with privacy-safe telemetry."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from typing import TextIO
import uuid


MODEL = "gpt-5.6-luna"
REASONING_EFFORT = "max"
DEFAULT_TIMEOUT_SECONDS = 1800
BOUNDED_REVIEW_TIMEOUT_SECONDS = 900
DEFAULT_HEARTBEAT_SECONDS = 30
STDERR_TAIL_CHARS = 4000
PROFILES = ("implementation", "bounded-review")
OUTCOMES = ("verified", "needs_correction", "blocked", "rejected")
RUN_LOG_ENV = "SOL_LUNA_RUN_LOG"
PARENT_SESSION_ENV = "SOL_LUNA_PARENT_SESSION_ID"
TELEMETRY_SCHEMA_VERSION = 1
RUNNER_VERSION = "2.0.0"
BOUNDED_REVIEW_POLICY = """Worker execution policy for bounded review:
- Keep the target repository read-only. Use environment-owned temporary scratch only when required.
- Use at most 8 repository commands and do not start a command expected to exceed 120 seconds.
- Do not run full integration, end-to-end, setup, installer, release, or all-workspace test suites.
- Prefer static inspection and the smallest focused reproduction that can decide the claim.
- If broader verification is needed, return it as requires_commander_verification instead of running it.
- Preserve enough time to return partial findings and verification evidence before the worker timeout."""


class WorkerRunError(RuntimeError):
    """Raised when the Luna worker does not complete with valid evidence."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "worker_error",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
        default=None,
        help="Worker sandbox. Defaults from --profile.",
    )
    run_parser.add_argument(
        "--allow-non-git",
        action="store_true",
        help="Allow a target that is not inside a Git repository.",
    )

    resume_parser = subparsers.add_parser("resume", help="Resume a Luna Max worker thread.")
    add_shared_arguments(resume_parser)
    resume_parser.add_argument("--thread-id", required=True, help="Codex worker thread UUID or name.")

    annotate_parser = subparsers.add_parser(
        "annotate", help="Append a commander verification outcome for an existing run."
    )
    annotate_parser.add_argument("--run-id", required=True, help="Run UUID returned by the worker.")
    annotate_parser.add_argument("--outcome", required=True, choices=OUTCOMES)
    annotate_parser.add_argument(
        "--checks-passed",
        type=int,
        default=0,
        help="Number of fresh verification checks that passed.",
    )
    annotate_parser.add_argument(
        "--checks-failed",
        type=int,
        default=0,
        help="Number of fresh verification checks that failed.",
    )
    annotate_parser.add_argument(
        "--run-log",
        help=(
            f"Absolute JSONL ledger path. Defaults to {RUN_LOG_ENV} or "
            "$CODEX_HOME/state/sol-luna-router/runs.jsonl."
        ),
    )
    annotate_parser.add_argument(
        "--parent-session-id",
        help=(
            f"Commander session ID. Defaults to {PARENT_SESSION_ENV}, then CODEX_THREAD_ID."
        ),
    )

    return parser


def add_shared_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cwd", required=True, help="Absolute target working directory.")
    parser.add_argument("--prompt-file", required=True, help="UTF-8 worker prompt file.")
    parser.add_argument(
        "--profile",
        choices=PROFILES,
        default="implementation",
        help="Implementation is write-capable; bounded-review is read-only and budgeted.",
    )
    parser.add_argument(
        "--events-file",
        help="Optional new absolute file receiving the raw Codex JSONL stream while the worker runs.",
    )
    parser.add_argument(
        "--run-log",
        help=(
            f"Absolute privacy-safe JSONL ledger path. Defaults to {RUN_LOG_ENV} or "
            "$CODEX_HOME/state/sol-luna-router/runs.jsonl."
        ),
    )
    parser.add_argument(
        "--no-run-log",
        action="store_true",
        help="Disable the default privacy-safe run ledger for this invocation.",
    )
    parser.add_argument(
        "--parent-session-id",
        help=(
            f"Commander session ID. Defaults to {PARENT_SESSION_ENV}, then CODEX_THREAD_ID."
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=None,
        help="Maximum runtime. Defaults to 1800 for implementation and 900 for bounded-review.",
    )
    parser.add_argument(
        "--heartbeat-seconds",
        type=int,
        default=DEFAULT_HEARTBEAT_SECONDS,
        help="Progress heartbeat interval on stderr; use 0 to disable.",
    )
    parser.add_argument(
        "--codex-bin",
        help="Codex executable path. Defaults to SOL_LUNA_CODEX_BIN or PATH lookup.",
    )


def resolve_codex_bin(explicit: str | None) -> str:
    candidate = explicit or os.environ.get("SOL_LUNA_CODEX_BIN") or shutil.which("codex")
    if not candidate:
        raise WorkerRunError("Codex executable was not found", code="codex_not_found")
    resolved = Path(candidate).expanduser()
    if resolved.is_absolute():
        if not resolved.is_file() or not os.access(resolved, os.X_OK):
            raise WorkerRunError(
                f"Codex executable is not runnable: {resolved}", code="codex_not_runnable"
            )
        return str(resolved)
    return candidate


def resolve_inputs(args: argparse.Namespace) -> tuple[Path, Path, str, str | None]:
    cwd = Path(args.cwd).expanduser()
    if not cwd.is_absolute() or not cwd.is_dir():
        raise WorkerRunError(
            f"--cwd must be an existing absolute directory: {cwd}", code="invalid_input"
        )

    prompt_file = Path(args.prompt_file).expanduser()
    if not prompt_file.is_absolute() or not prompt_file.is_file():
        raise WorkerRunError(
            f"--prompt-file must be an existing absolute file: {prompt_file}",
            code="invalid_input",
        )
    prompt = prompt_file.read_text(encoding="utf-8")
    if not prompt.strip():
        raise WorkerRunError("Worker prompt must not be empty", code="invalid_input")

    git_root = find_git_root(cwd)
    if args.command == "run" and git_root is None and not args.allow_non_git:
        raise WorkerRunError(
            "Target is not inside a Git repository; pass --allow-non-git only when intentional",
            code="non_git_target",
        )
    return cwd.resolve(), prompt_file.resolve(), prompt, git_root


def resolve_runtime_options(args: argparse.Namespace) -> tuple[str, int, int]:
    if args.heartbeat_seconds < 0:
        raise WorkerRunError(
            "--heartbeat-seconds must be zero or greater", code="invalid_input"
        )
    default_timeout = (
        BOUNDED_REVIEW_TIMEOUT_SECONDS
        if args.profile == "bounded-review"
        else DEFAULT_TIMEOUT_SECONDS
    )
    timeout_seconds = default_timeout if args.timeout_seconds is None else args.timeout_seconds
    if timeout_seconds <= 0:
        raise WorkerRunError(
            "--timeout-seconds must be greater than zero", code="invalid_input"
        )
    sandbox = getattr(args, "sandbox", None) or (
        "read-only" if args.profile == "bounded-review" else "workspace-write"
    )
    if args.profile == "bounded-review" and sandbox != "read-only":
        raise WorkerRunError(
            "bounded-review requires the read-only sandbox", code="invalid_profile"
        )
    return sandbox, timeout_seconds, args.heartbeat_seconds


def apply_profile_policy(profile: str, prompt: str) -> str:
    if profile == "bounded-review":
        return f"{BOUNDED_REVIEW_POLICY}\n\nTask:\n{prompt}"
    return prompt


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
    sandbox: str,
) -> list[str]:
    command = [codex_bin, "exec", "--json", "--strict-config"]
    fixed_worker_options = [
        "-m",
        MODEL,
        "-c",
        f'model_reasoning_effort="{REASONING_EFFORT}"',
        "-c",
        "features.multi_agent_v2.enabled=false",
        "-c",
        "agents.enabled=false",
    ]
    if args.command == "resume":
        return [
            *command,
            "resume",
            *fixed_worker_options,
            "-c",
            f'sandbox_mode="{sandbox}"',
            args.thread_id,
            prompt,
        ]

    command.extend(
        [
            *fixed_worker_options,
            "--sandbox",
            sandbox,
            "-C",
            str(cwd),
        ]
    )
    if args.allow_non_git:
        command.append("--skip-git-repo-check")
    command.append(prompt)
    return command


def resolve_events_path(path_text: str | None) -> Path | None:
    if path_text is None:
        return None
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        raise WorkerRunError(f"--events-file must be absolute: {path}", code="invalid_input")
    if path.exists():
        raise WorkerRunError(f"--events-file already exists: {path}", code="artifact_exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def default_run_log_path() -> Path:
    codex_home = Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()
    return codex_home / "state" / "sol-luna-router" / "runs.jsonl"


def resolve_run_log_path(args: argparse.Namespace) -> Path | None:
    if getattr(args, "no_run_log", False):
        if getattr(args, "run_log", None):
            raise WorkerRunError(
                "--run-log and --no-run-log cannot be used together", code="invalid_input"
            )
        return None
    path = Path(
        getattr(args, "run_log", None)
        or os.environ.get(RUN_LOG_ENV)
        or default_run_log_path()
    ).expanduser()
    if not path.is_absolute():
        raise WorkerRunError(f"--run-log must be absolute: {path}", code="invalid_input")
    return path.resolve()


def resolve_parent_session_id(args: argparse.Namespace) -> str | None:
    return (
        getattr(args, "parent_session_id", None)
        or os.environ.get(PARENT_SESSION_ENV)
        or os.environ.get("CODEX_THREAD_ID")
        or None
    )


def _read_stream(stream: TextIO) -> str:
    stream.flush()
    stream.seek(0)
    return stream.read()


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait()
    except ProcessLookupError:
        process.wait()


def partial_event_summary(stdout: str) -> tuple[str | None, int]:
    thread_id: str | None = None
    event_count = 0
    for raw_line in stdout.splitlines():
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        event_count += 1
        candidate = event.get("thread_id") if event.get("type") == "thread.started" else None
        if isinstance(candidate, str) and candidate:
            thread_id = candidate
    return thread_id, event_count


def build_worker_environment(profile: str, cache_root: Path | None) -> dict[str, str] | None:
    if profile != "bounded-review":
        return None
    if cache_root is None:
        raise WorkerRunError(
            "bounded-review requires an isolated cache root", code="invalid_profile"
        )
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "XDG_CACHE_HOME": str(cache_root / "xdg"),
            "CARGO_TARGET_DIR": str(cache_root / "cargo-target"),
            "GOCACHE": str(cache_root / "go-cache"),
            "npm_config_cache": str(cache_root / "npm-cache"),
            "RUFF_CACHE_DIR": str(cache_root / "ruff-cache"),
            "MYPY_CACHE_DIR": str(cache_root / "mypy-cache"),
        }
    )
    return environment


def execute_worker(
    command: list[str],
    cwd: Path,
    timeout_seconds: int,
    heartbeat_seconds: int,
    events_path: Path | None,
    progress: TextIO,
    environment: dict[str, str] | None,
) -> tuple[str, str, int, float]:
    stdout_context: TextIO
    if events_path is None:
        stdout_context = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
    else:
        descriptor = os.open(events_path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        stdout_context = os.fdopen(descriptor, mode="w+", encoding="utf-8")
    with stdout_context as stdout_stream, tempfile.TemporaryFile(
        mode="w+", encoding="utf-8"
    ) as stderr_stream:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=stdout_stream,
            stderr=stderr_stream,
            text=True,
            start_new_session=True,
            env=environment,
        )
        started_at = time.monotonic()
        next_heartbeat = started_at + heartbeat_seconds if heartbeat_seconds else None
        while process.poll() is None:
            now = time.monotonic()
            elapsed = now - started_at
            if elapsed >= timeout_seconds:
                _terminate_process(process)
                stdout = _read_stream(stdout_stream)
                stderr = _read_stream(stderr_stream)
                thread_id, event_count = partial_event_summary(stdout)
                recovery = (
                    f"resume with --thread-id {thread_id}"
                    if thread_id
                    else "no thread ID was observed"
                )
                artifact = str(events_path) if events_path else "not retained"
                raise WorkerRunError(
                    f"Luna worker timed out after {timeout_seconds} seconds; {recovery}; "
                    f"partial events={event_count}; events_file={artifact}; "
                    f"stderr tail: {stderr[-STDERR_TAIL_CHARS:]}",
                    code="timeout",
                    details={
                        "worker_thread_id": thread_id,
                        "event_count": event_count,
                        "duration_seconds": round(time.monotonic() - started_at, 3),
                    },
                )
            if next_heartbeat is not None and now >= next_heartbeat:
                print(
                    f"sol-luna-router: worker running elapsed={int(elapsed)}s pid={process.pid}",
                    file=progress,
                    flush=True,
                )
                next_heartbeat = now + heartbeat_seconds
            time.sleep(0.2)
        duration_seconds = time.monotonic() - started_at
        return (
            _read_stream(stdout_stream),
            _read_stream(stderr_stream),
            process.returncode,
            duration_seconds,
        )


def parse_events(stdout: str, stderr: str, returncode: int) -> dict[str, object]:
    events: list[dict[str, object]] = []
    thread_id: str | None = None
    final_response: str | None = None
    usage: object = None
    failure_usage: object = None
    completed = False
    fatal_error: str | None = None
    warnings: list[str] = []

    for line_number, raw_line in enumerate(stdout.splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError as error:
            partial_thread_id, event_count = partial_event_summary(stdout)
            raise WorkerRunError(
                f"Codex emitted invalid JSONL on line {line_number}: {error.msg}",
                code="invalid_jsonl",
                details={
                    "worker_thread_id": partial_thread_id,
                    "event_count": event_count,
                },
            ) from error
        if not isinstance(event, dict):
            raise WorkerRunError(
                f"Codex JSONL line {line_number} is not an object", code="invalid_jsonl"
            )
        events.append(event)

        candidate_usage = event.get("usage")
        if isinstance(candidate_usage, dict):
            usage = candidate_usage

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
            failure_usage = usage
        elif event_type == "error":
            warnings.append(extract_error(event))

    details = {"worker_thread_id": thread_id, "event_count": len(events)}
    usage_for_failure = failure_usage if fatal_error is not None else usage
    normalized_usage = normalize_usage(usage_for_failure)
    if normalized_usage:
        details["usage"] = normalized_usage
    if returncode != 0:
        detail = fatal_error or (warnings[-1] if warnings else None)
        detail = detail or stderr[-STDERR_TAIL_CHARS:] or "no error details"
        raise WorkerRunError(
            f"Codex exited with status {returncode}: {detail}",
            code="codex_exit",
            details=details,
        )
    if fatal_error:
        raise WorkerRunError(
            f"Codex reported a failed turn: {fatal_error}",
            code="turn_failed",
            details=details,
        )
    if not completed:
        raise WorkerRunError(
            "Codex did not emit turn.completed", code="incomplete_turn", details=details
        )
    if not thread_id:
        raise WorkerRunError(
            "Codex did not emit thread.started with a thread ID",
            code="missing_thread_id",
            details=details,
        )
    if final_response is None:
        raise WorkerRunError(
            "Codex did not emit a final agent message",
            code="missing_final_response",
            details=details,
        )

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


def normalize_usage(usage: object) -> dict[str, int]:
    if not isinstance(usage, dict):
        return {}
    return {
        str(key): value
        for key, value in usage.items()
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0
    }


def classify_failure(error: BaseException) -> str:
    message = str(error).lower()
    capacity_markers = (
        "rate limit",
        "rate_limit",
        "usage limit",
        "quota",
        "insufficient credits",
        "spend limit",
        "capacity exhausted",
    )
    if any(marker in message for marker in capacity_markers):
        return "capacity_exhausted"
    if isinstance(error, WorkerRunError):
        return error.code
    return "os_error"


def prompt_fingerprint(prompt: str) -> tuple[str, int]:
    encoded = prompt.encode("utf-8")
    return hashlib.sha256(encoded).hexdigest(), len(encoded)


def append_run_log(path: Path, record: dict[str, object]) -> None:
    parent_existed = path.parent.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not parent_existed:
        try:
            path.parent.chmod(0o700)
        except OSError:
            pass
    descriptor = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    try:
        os.chmod(path, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            descriptor = -1
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def base_telemetry_record(
    args: argparse.Namespace,
    *,
    run_id: str,
    started_at: str,
    completed_at: str,
    duration_seconds: float,
    parent_session_id: str | None,
) -> dict[str, object]:
    return {
        "schema_version": TELEMETRY_SCHEMA_VERSION,
        "runner_version": RUNNER_VERSION,
        "record_type": "run",
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_seconds": round(duration_seconds, 3),
        "command": args.command,
        "parent_session_id": parent_session_id,
        "resumed_thread_id": getattr(args, "thread_id", None),
        "model": MODEL,
        "reasoning_effort": REASONING_EFFORT,
        "profile": args.profile,
        "cwd": str(Path(args.cwd).expanduser()),
        "raw_events_retained": bool(args.events_file),
    }


def build_success_record(
    args: argparse.Namespace,
    result: dict[str, object],
    *,
    run_id: str,
    started_at: str,
    completed_at: str,
    duration_seconds: float,
    parent_session_id: str | None,
    prompt_sha256: str,
    prompt_bytes: int,
) -> dict[str, object]:
    record = base_telemetry_record(
        args,
        run_id=run_id,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=duration_seconds,
        parent_session_id=parent_session_id,
    )
    record.update(
        {
            "status": "success",
            "worker_thread_id": result["thread_id"],
            "git_root": result["git_root"],
            "sandbox": result["sandbox"],
            "timeout_seconds": result["timeout_seconds"],
            "prompt_sha256": prompt_sha256,
            "prompt_bytes": prompt_bytes,
            "event_count": result["event_count"],
            "warning_count": len(result["warnings"]),
            "usage": normalize_usage(result["usage"]),
        }
    )
    return record


def normalize_run_id(run_id: str) -> str:
    try:
        parsed = uuid.UUID(run_id)
    except ValueError as error:
        raise WorkerRunError(f"--run-id must be a UUID: {run_id}", code="invalid_input") from error
    return str(parsed)


def ledger_contains_run(path: Path, run_id: str) -> bool:
    if not path.is_file():
        return False
    with path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as error:
                raise WorkerRunError(
                    f"Run ledger contains invalid JSONL on line {line_number}: {error.msg}",
                    code="invalid_run_log",
                ) from error
            if isinstance(record, dict) and record.get("run_id") == run_id:
                if record.get("record_type", "run") == "run":
                    return True
    return False


def annotate_run(args: argparse.Namespace, output: TextIO) -> int:
    run_log_path = resolve_run_log_path(args)
    if run_log_path is None:
        raise WorkerRunError("annotate requires a run log", code="invalid_input")
    run_id = normalize_run_id(args.run_id)
    if args.checks_passed < 0 or args.checks_failed < 0:
        raise WorkerRunError(
            "--checks-passed and --checks-failed must be zero or greater",
            code="invalid_input",
        )
    if args.outcome == "verified" and (
        args.checks_passed < 1 or args.checks_failed != 0
    ):
        raise WorkerRunError(
            "verified requires at least one passed check and zero failed checks",
            code="invalid_evaluation",
        )
    if not ledger_contains_run(run_log_path, run_id):
        raise WorkerRunError(
            f"Run ID was not found in ledger: {run_id}", code="run_not_found"
        )
    evaluation_id = str(uuid.uuid4())
    record = {
        "schema_version": TELEMETRY_SCHEMA_VERSION,
        "runner_version": RUNNER_VERSION,
        "record_type": "evaluation",
        "evaluation_id": evaluation_id,
        "run_id": run_id,
        "recorded_at": utc_now(),
        "parent_session_id": resolve_parent_session_id(args),
        "outcome": args.outcome,
        "checks_passed": args.checks_passed,
        "checks_failed": args.checks_failed,
    }
    append_run_log(run_log_path, record)
    json.dump(record, output, ensure_ascii=False, sort_keys=True)
    output.write("\n")
    return 0


def build_failure_record(
    args: argparse.Namespace,
    error: BaseException,
    *,
    run_id: str,
    started_at: str,
    completed_at: str,
    duration_seconds: float,
    parent_session_id: str | None,
) -> dict[str, object]:
    record = base_telemetry_record(
        args,
        run_id=run_id,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=duration_seconds,
        parent_session_id=parent_session_id,
    )
    details = error.details if isinstance(error, WorkerRunError) else {}
    record.update(
        {
            "status": "failed",
            "failure_code": classify_failure(error),
            "worker_thread_id": details.get("worker_thread_id"),
            "event_count": details.get("event_count", 0),
        }
    )
    if isinstance(details.get("duration_seconds"), (int, float)):
        record["worker_duration_seconds"] = details["duration_seconds"]
    usage = details.get("usage")
    if isinstance(usage, dict) and usage:
        record["usage"] = usage
    return record


def run(args: argparse.Namespace, progress: TextIO) -> tuple[dict[str, object], str, int]:
    cwd, prompt_file, raw_prompt, git_root = resolve_inputs(args)
    sandbox, timeout_seconds, heartbeat_seconds = resolve_runtime_options(args)
    prompt_sha256, prompt_bytes = prompt_fingerprint(raw_prompt)
    worker_prompt = apply_profile_policy(args.profile, raw_prompt)
    events_path = resolve_events_path(args.events_file)
    codex_bin = resolve_codex_bin(args.codex_bin)
    command = build_codex_args(args, codex_bin, cwd, worker_prompt, sandbox)
    cache_context = (
        tempfile.TemporaryDirectory(prefix="sol-luna-router-cache-")
        if args.profile == "bounded-review"
        else None
    )
    try:
        cache_root = Path(cache_context.name) if cache_context is not None else None
        environment = build_worker_environment(args.profile, cache_root)
        stdout, stderr, returncode, duration_seconds = execute_worker(
            command,
            cwd,
            timeout_seconds,
            heartbeat_seconds,
            events_path,
            progress,
            environment,
        )
    finally:
        if cache_context is not None:
            cache_context.cleanup()
    result = parse_events(stdout, stderr, returncode)
    result.update(
        {
            "model": MODEL,
            "reasoning_effort": REASONING_EFFORT,
            "profile": args.profile,
            "sandbox": sandbox,
            "timeout_seconds": timeout_seconds,
            "duration_seconds": round(duration_seconds, 3),
            "isolated_caches": args.profile == "bounded-review",
            "cwd": str(cwd),
            "git_root": git_root,
            "prompt_file": str(prompt_file),
            "events_file": str(events_path) if events_path else None,
        }
    )
    return result, prompt_sha256, prompt_bytes


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "annotate":
        try:
            return annotate_run(args, sys.stdout)
        except (OSError, WorkerRunError) as error:
            print(f"sol-luna-router: {error}", file=sys.stderr)
            return 1
    run_id = str(uuid.uuid4())
    started_at = utc_now()
    started_monotonic = time.monotonic()
    parent_session_id = resolve_parent_session_id(args)
    try:
        run_log_path = resolve_run_log_path(args)
    except WorkerRunError as error:
        print(f"sol-luna-router: {error}", file=sys.stderr)
        return 1

    try:
        result, prompt_sha256, prompt_bytes = run(args, sys.stderr)
        completed_at = utc_now()
        duration_seconds = time.monotonic() - started_monotonic
        record = build_success_record(
            args,
            result,
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            parent_session_id=parent_session_id,
            prompt_sha256=prompt_sha256,
            prompt_bytes=prompt_bytes,
        )
        telemetry_status = "disabled"
        if run_log_path is not None:
            try:
                append_run_log(run_log_path, record)
                telemetry_status = "written"
            except OSError as log_error:
                telemetry_status = "write_failed"
                print(
                    f"sol-luna-router: telemetry write failed for run_id={run_id}: {log_error}",
                    file=sys.stderr,
                )
        result["telemetry"] = {
            "run_id": run_id,
            "run_log": str(run_log_path) if run_log_path else None,
            "status": telemetry_status,
        }
        json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    except (OSError, WorkerRunError) as error:
        completed_at = utc_now()
        duration_seconds = time.monotonic() - started_monotonic
        record = build_failure_record(
            args,
            error,
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            parent_session_id=parent_session_id,
        )
        log_status = "disabled"
        if run_log_path is not None:
            try:
                append_run_log(run_log_path, record)
                log_status = f"written run_id={run_id} run_log={run_log_path}"
            except OSError as log_error:
                log_status = f"write_failed run_id={run_id} error={log_error}"
        print(f"sol-luna-router: {error}; telemetry={log_status}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
