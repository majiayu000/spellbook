#!/usr/bin/env python3
"""Tests for run_luna_worker.py using a fake Codex executable."""

from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("run_luna_worker.py")

SPEC = importlib.util.spec_from_file_location("run_luna_worker", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load {SCRIPT}")
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


class Invocation:
    def __init__(self, returncode: int, stdout: str, stderr: str) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


FAKE_CODEX = r'''#!/usr/bin/env python3
import json
import os
import sys
import time

mode = os.environ.get("FAKE_CODEX_MODE", "success")
capture = os.environ.get("FAKE_CODEX_ARGS_FILE")
if capture:
    with open(capture, "w", encoding="utf-8") as handle:
        json.dump(sys.argv[1:], handle)
environment_capture = os.environ.get("FAKE_CODEX_ENV_FILE")
if environment_capture:
    keys = ("PYTHONDONTWRITEBYTECODE", "XDG_CACHE_HOME", "CARGO_TARGET_DIR", "GOCACHE", "npm_config_cache")
    with open(environment_capture, "w", encoding="utf-8") as handle:
        json.dump({key: os.environ.get(key) for key in keys}, handle)
if mode == "malformed":
    print("not-json")
    raise SystemExit(0)
if mode == "failure":
    print(json.dumps({"type": "error", "message": "simulated failure"}))
    raise SystemExit(7)
if mode == "failure-with-usage":
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 40, "cached_input_tokens": 10, "output_tokens": 8}}))
    raise SystemExit(7)
if mode == "config-incompatible":
    print("Error loading config.toml: unknown configuration field `disable_response_storage`", file=sys.stderr)
    raise SystemExit(7)
if mode == "capacity":
    print(json.dumps({"type": "error", "message": "usage limit reached"}))
    raise SystemExit(7)
print(json.dumps({"type": "thread.started", "thread_id": "thread-123"}), flush=True)
if mode == "post-start-unknown-field":
    print(json.dumps({"type": "error", "message": "tool returned unknown field `status`"}))
    raise SystemExit(7)
if mode == "sleep":
    time.sleep(10)
if mode == "recovered":
    print(json.dumps({"type": "error", "message": "Reconnecting after request timed out"}))
    print(json.dumps({"type": "item.completed", "item": {"type": "error", "message": "Falling back to HTTPS transport"}}))
if mode == "turn-failed":
    print(json.dumps({"type": "turn.failed", "error": {"message": "terminal failure"}}))
if mode == "turn-failed-with-usage":
    print(json.dumps({"type": "turn.failed", "usage": {"input_tokens": 30, "cached_input_tokens": 5, "output_tokens": 7}, "error": {"message": "terminal failure with usage"}}))
    raise SystemExit(0)
if mode == "missing-final-after-error":
    print(json.dumps({"type": "error", "message": "retry before empty completion"}))
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 0}}))
    raise SystemExit(0)
print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "done"}}))
if mode == "incomplete-after-error":
    print(json.dumps({"type": "error", "message": "retry was never recovered"}))
    raise SystemExit(0)
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 4, "output_tokens": 2}}))
'''


class RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sol-luna-router-test-")
        self.root = Path(self.temp_dir.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.prompt = self.root / "task.md"
        self.prompt.write_text("Implement the bounded task.", encoding="utf-8")
        self.fake_codex = self.root / "fake-codex"
        self.fake_codex.write_text(textwrap.dedent(FAKE_CODEX), encoding="utf-8")
        self.fake_codex.chmod(0o755)
        self.args_file = self.root / "args.json"
        self.env_file = self.root / "environment.json"
        self.run_log = self.root / "state" / "runs.jsonl"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def invoke(self, *arguments: str, mode: str = "success") -> Invocation:
        argv = [
            str(SCRIPT),
            *arguments,
            "--codex-bin",
            str(self.fake_codex),
        ]
        stdout = io.StringIO()
        stderr = io.StringIO()
        environment = {
            "FAKE_CODEX_MODE": mode,
            "FAKE_CODEX_ARGS_FILE": str(self.args_file),
            "FAKE_CODEX_ENV_FILE": str(self.env_file),
            "SOL_LUNA_RUN_LOG": str(self.run_log),
            "SOL_LUNA_PARENT_SESSION_ID": "parent-session-456",
            "CODEX_THREAD_ID": "ignored-parent-session",
        }
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.dict(os.environ, environment),
            mock.patch.object(sys, "stdout", stdout),
            mock.patch.object(sys, "stderr", stderr),
        ):
            returncode = RUNNER.main()
        return Invocation(returncode, stdout.getvalue(), stderr.getvalue())

    def read_records(self) -> list[dict[str, object]]:
        return [
            json.loads(line)
            for line in self.run_log.read_text(encoding="utf-8").splitlines()
        ]

    def annotate(
        self,
        run_id: str,
        outcome: str,
        *,
        checks_passed: int = 0,
        checks_failed: int = 0,
    ) -> Invocation:
        argv = [
            str(SCRIPT),
            "annotate",
            "--run-id",
            run_id,
            "--outcome",
            outcome,
            "--checks-passed",
            str(checks_passed),
            "--checks-failed",
            str(checks_failed),
            "--run-log",
            str(self.run_log),
        ]
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.dict(
                os.environ,
                {"SOL_LUNA_PARENT_SESSION_ID": "parent-session-456"},
            ),
            mock.patch.object(sys, "stdout", stdout),
            mock.patch.object(sys, "stderr", stderr),
        ):
            returncode = RUNNER.main()
        return Invocation(returncode, stdout.getvalue(), stderr.getvalue())

    def test_run_uses_luna_max_and_writes_privacy_safe_telemetry(self) -> None:
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["thread_id"], "thread-123")
        self.assertEqual(payload["model"], "gpt-5.6-luna")
        self.assertEqual(payload["reasoning_effort"], "max")
        self.assertEqual(payload["profile"], "implementation")
        self.assertEqual(payload["sandbox"], "workspace-write")
        self.assertEqual(payload["timeout_seconds"], 1800)
        self.assertEqual(payload["final_response"], "done")
        self.assertEqual(payload["telemetry"]["status"], "written")

        command = json.loads(self.args_file.read_text(encoding="utf-8"))
        self.assertIn("gpt-5.6-luna", command)
        self.assertIn('model_reasoning_effort="max"', command)
        self.assertNotIn("--skip-git-repo-check", command)

        records = self.read_records()
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["status"], "success")
        self.assertEqual(record["parent_session_id"], "parent-session-456")
        self.assertEqual(record["worker_thread_id"], "thread-123")
        self.assertEqual(record["usage"]["input_tokens"], 10)
        self.assertEqual(record["usage"]["cached_input_tokens"], 4)
        self.assertEqual(record["usage"]["output_tokens"], 2)
        self.assertEqual(record["reasoning_effort"], "max")
        self.assertEqual(len(record["prompt_sha256"]), 64)
        serialized = json.dumps(record, ensure_ascii=False)
        self.assertNotIn("Implement the bounded task.", serialized)
        self.assertNotIn("done", serialized)
        self.assertEqual(stat.S_IMODE(self.run_log.stat().st_mode), 0o600)

    def test_bounded_review_is_read_only_and_injects_budget_policy(self) -> None:
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            "--profile",
            "bounded-review",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["profile"], "bounded-review")
        self.assertEqual(payload["sandbox"], "read-only")
        self.assertEqual(payload["timeout_seconds"], 900)
        self.assertTrue(payload["isolated_caches"])
        command = json.loads(self.args_file.read_text(encoding="utf-8"))
        sandbox_index = command.index("--sandbox")
        self.assertEqual(command[sandbox_index + 1], "read-only")
        self.assertIn("Use at most 8 repository commands", command[-1])
        self.assertIn("Implement the bounded task.", command[-1])
        environment = json.loads(self.env_file.read_text(encoding="utf-8"))
        self.assertEqual(environment["PYTHONDONTWRITEBYTECODE"], "1")
        for key in ("XDG_CACHE_HOME", "CARGO_TARGET_DIR", "GOCACHE", "npm_config_cache"):
            self.assertIn("sol-luna-router-cache-", environment[key])

    def test_bounded_review_rejects_write_sandbox_and_logs_failure(self) -> None:
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            "--profile",
            "bounded-review",
            "--sandbox",
            "workspace-write",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("requires the read-only sandbox", result.stderr)
        self.assertFalse(self.args_file.exists())
        record = self.read_records()[0]
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["failure_code"], "invalid_profile")

    def test_resume_reasserts_luna_max_and_records_both_thread_ids(self) -> None:
        result = self.invoke(
            "resume",
            "--cwd",
            str(self.repo),
            "--thread-id",
            "thread-previous",
            "--prompt-file",
            str(self.prompt),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        command = json.loads(self.args_file.read_text(encoding="utf-8"))
        self.assertEqual(command[:4], ["exec", "--json", "--strict-config", "resume"])
        self.assertIn("-m", command)
        self.assertIn("gpt-5.6-luna", command)
        self.assertIn('model_reasoning_effort="max"', command)
        self.assertIn('sandbox_mode="workspace-write"', command)
        record = self.read_records()[0]
        self.assertEqual(record["resumed_thread_id"], "thread-previous")
        self.assertEqual(record["worker_thread_id"], "thread-123")

    def test_no_run_log_is_explicit_opt_out(self) -> None:
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            "--no-run-log",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["telemetry"]["status"], "disabled")
        self.assertFalse(self.run_log.exists())

    def test_run_log_write_failure_is_visible_without_losing_worker_result(self) -> None:
        blocked_path = self.root / "blocked-log"
        blocked_path.mkdir()
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            "--run-log",
            str(blocked_path),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["final_response"], "done")
        self.assertEqual(payload["telemetry"]["status"], "write_failed")
        self.assertIn("telemetry write failed", result.stderr)

    def test_custom_run_log_does_not_change_existing_directory_permissions(self) -> None:
        custom_directory = self.root / "shared-state"
        custom_directory.mkdir(mode=0o755)
        custom_log = custom_directory / "runs.jsonl"
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            "--run-log",
            str(custom_log),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stat.S_IMODE(custom_directory.stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE(custom_log.stat().st_mode), 0o600)

    def test_annotation_closes_the_verification_feedback_loop(self) -> None:
        run_result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
        )
        self.assertEqual(run_result.returncode, 0, run_result.stderr)
        run_id = json.loads(run_result.stdout)["telemetry"]["run_id"]
        annotation = self.annotate(run_id, "verified", checks_passed=2)
        self.assertEqual(annotation.returncode, 0, annotation.stderr)
        payload = json.loads(annotation.stdout)
        self.assertEqual(payload["record_type"], "evaluation")
        self.assertEqual(payload["run_id"], run_id)
        self.assertEqual(payload["outcome"], "verified")
        self.assertEqual(payload["checks_passed"], 2)
        self.assertEqual(payload["checks_failed"], 0)
        records = self.read_records()
        self.assertEqual([record["record_type"] for record in records], ["run", "evaluation"])

    def test_annotation_rejects_an_unknown_run_id(self) -> None:
        self.run_log.parent.mkdir(parents=True)
        self.run_log.write_text("", encoding="utf-8")
        annotation = self.annotate(
            "00000000-0000-4000-8000-000000000000",
            "verified",
            checks_passed=1,
        )
        self.assertEqual(annotation.returncode, 1)
        self.assertIn("was not found", annotation.stderr)
        self.assertEqual(self.run_log.read_text(encoding="utf-8"), "")

    def test_verified_annotation_requires_fresh_passing_checks(self) -> None:
        run_result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
        )
        run_id = json.loads(run_result.stdout)["telemetry"]["run_id"]

        annotation = self.annotate(run_id, "verified")

        self.assertEqual(annotation.returncode, 1)
        self.assertIn("at least one passed check", annotation.stderr)
        self.assertEqual(len(self.read_records()), 1)

    def test_non_git_target_requires_explicit_override(self) -> None:
        non_git = self.root / "plain"
        non_git.mkdir()
        result = self.invoke(
            "run",
            "--cwd",
            str(non_git),
            "--prompt-file",
            str(self.prompt),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("not inside a Git repository", result.stderr)
        self.assertFalse(self.args_file.exists())

    def test_invalid_jsonl_fails_closed_and_logs_failure(self) -> None:
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            mode="malformed",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid JSONL", result.stderr)
        self.assertEqual(self.read_records()[0]["failure_code"], "invalid_jsonl")

    def test_codex_failure_propagates_exact_error_and_capacity_classification(self) -> None:
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            mode="capacity",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("usage limit reached", result.stderr)
        self.assertEqual(self.read_records()[0]["failure_code"], "capacity_exhausted")
        self.assertNotIn("usage", self.read_records()[0])

    def test_nonzero_exit_preserves_exact_usage_in_failure_telemetry(self) -> None:
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            mode="failure-with-usage",
        )
        self.assertEqual(result.returncode, 1)
        record = self.read_records()[0]
        self.assertEqual(record["failure_code"], "codex_exit")
        self.assertEqual(
            record["usage"],
            {"input_tokens": 40, "cached_input_tokens": 10, "output_tokens": 8},
        )

    def test_strict_config_unknown_field_is_classified_as_incompatible(self) -> None:
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            mode="config-incompatible",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("unknown configuration field `disable_response_storage`", result.stderr)
        command = json.loads(self.args_file.read_text(encoding="utf-8"))
        self.assertIn("--strict-config", command)
        record = self.read_records()[0]
        self.assertEqual(record["failure_code"], "config_incompatible")
        self.assertNotIn("disable_response_storage", json.dumps(record))

    def test_unknown_field_after_worker_start_is_not_a_config_failure(self) -> None:
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            mode="post-start-unknown-field",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("unknown field `status`", result.stderr)
        self.assertEqual(self.read_records()[0]["failure_code"], "codex_exit")

    def test_recovered_transport_errors_are_warnings_not_failures(self) -> None:
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            mode="recovered",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["warnings"],
            ["Reconnecting after request timed out", "Falling back to HTTPS transport"],
        )
        self.assertEqual(self.read_records()[0]["warning_count"], 2)

    def test_turn_failed_remains_fatal_even_with_completion_evidence(self) -> None:
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            mode="turn-failed",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("terminal failure", result.stderr)
        self.assertNotIn("usage", self.read_records()[0])

    def test_turn_failed_preserves_exact_usage_and_absent_usage_is_not_zero(self) -> None:
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            mode="turn-failed-with-usage",
        )
        self.assertEqual(result.returncode, 1)
        record = self.read_records()[0]
        self.assertEqual(record["failure_code"], "turn_failed")
        self.assertEqual(
            record["usage"],
            {"input_tokens": 30, "cached_input_tokens": 5, "output_tokens": 7},
        )

        absent_result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            mode="failure",
        )
        self.assertEqual(absent_result.returncode, 1)
        self.assertNotIn("usage", self.read_records()[-1])

    def test_recovered_error_without_turn_completed_fails_closed(self) -> None:
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            mode="incomplete-after-error",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("did not emit turn.completed", result.stderr)

    def test_recovered_error_without_final_message_fails_closed(self) -> None:
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            mode="missing-final-after-error",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("did not emit a final agent message", result.stderr)

    def test_events_file_preserves_jsonl_with_private_permissions(self) -> None:
        events_file = self.root / "events" / "worker.jsonl"
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            "--events-file",
            str(events_file),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = events_file.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(json.loads(lines[0])["type"], "thread.started")
        self.assertEqual(stat.S_IMODE(events_file.stat().st_mode), 0o600)
        self.assertTrue(self.read_records()[0]["raw_events_retained"])

    def test_timeout_preserves_partial_events_thread_and_failure_record(self) -> None:
        events_file = self.root / "events" / "partial.jsonl"
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            "--events-file",
            str(events_file),
            "--timeout-seconds",
            "1",
            "--heartbeat-seconds",
            "0",
            mode="sleep",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("timed out after 1 seconds", result.stderr)
        self.assertIn("resume with --thread-id thread-123", result.stderr)
        lines = events_file.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        record = self.read_records()[0]
        self.assertEqual(record["failure_code"], "timeout")
        self.assertEqual(record["worker_thread_id"], "thread-123")

    def test_existing_events_file_is_not_overwritten(self) -> None:
        events_file = self.root / "events.jsonl"
        events_file.write_text("preserve\n", encoding="utf-8")
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            "--events-file",
            str(events_file),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("already exists", result.stderr)
        self.assertEqual(events_file.read_text(encoding="utf-8"), "preserve\n")


if __name__ == "__main__":
    unittest.main()
