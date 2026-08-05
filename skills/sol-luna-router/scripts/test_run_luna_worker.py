#!/usr/bin/env python3
"""Tests for run_luna_worker.py using a fake Codex executable."""

from __future__ import annotations

import json
import os
from pathlib import Path
import importlib.util
import io
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

mode = os.environ.get("FAKE_CODEX_MODE", "success")
capture = os.environ.get("FAKE_CODEX_ARGS_FILE")
if capture:
    with open(capture, "w", encoding="utf-8") as handle:
        json.dump(sys.argv[1:], handle)
if mode == "malformed":
    print("not-json")
    raise SystemExit(0)
if mode == "failure":
    print(json.dumps({"type": "error", "message": "simulated failure"}))
    raise SystemExit(7)
print(json.dumps({"type": "thread.started", "thread_id": "thread-123"}))
if mode == "recovered":
    print(json.dumps({"type": "error", "message": "Reconnecting after request timed out"}))
    print(json.dumps({"type": "item.completed", "item": {"type": "error", "message": "Falling back to HTTPS transport"}}))
if mode == "turn-failed":
    print(json.dumps({"type": "turn.failed", "error": {"message": "terminal failure"}}))
if mode == "missing-final-after-error":
    print(json.dumps({"type": "error", "message": "retry before empty completion"}))
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 0}}))
    raise SystemExit(0)
print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "done"}}))
if mode == "incomplete-after-error":
    print(json.dumps({"type": "error", "message": "retry was never recovered"}))
    raise SystemExit(0)
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 2}}))
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

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def invoke(
        self,
        *arguments: str,
        mode: str = "success",
        reasoning_effort_env: str = "",
    ) -> Invocation:
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
            "SOL_LUNA_REASONING_EFFORT": reasoning_effort_env,
        }
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.dict(os.environ, environment),
            mock.patch.object(sys, "stdout", stdout),
            mock.patch.object(sys, "stderr", stderr),
        ):
            returncode = RUNNER.main()
        return Invocation(returncode, stdout.getvalue(), stderr.getvalue())

    def test_run_defaults_to_luna_high_and_disables_native_agents(self) -> None:
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
        self.assertEqual(payload["reasoning_effort"], "high")
        self.assertEqual(payload["final_response"], "done")

        command = json.loads(self.args_file.read_text(encoding="utf-8"))
        self.assertIn("gpt-5.6-luna", command)
        self.assertIn('model_reasoning_effort="high"', command)
        self.assertIn("features.multi_agent_v2.enabled=false", command)
        self.assertIn("agents.enabled=false", command)
        self.assertNotIn("--skip-git-repo-check", command)

    def test_resume_reuses_thread_without_model_override(self) -> None:
        result = self.invoke(
            "resume",
            "--cwd",
            str(self.repo),
            "--thread-id",
            "thread-previous",
            "--prompt-file",
            str(self.prompt),
            reasoning_effort_env="extreme",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["reasoning_effort"], "inherited")
        command = json.loads(self.args_file.read_text(encoding="utf-8"))
        self.assertEqual(command[:3], ["exec", "--json", "--strict-config"])
        self.assertEqual(command[3:5], ["resume", "thread-previous"])
        self.assertNotIn("-m", command)
        self.assertNotIn("-c", command)

    def test_explicit_reasoning_effort_overrides_environment(self) -> None:
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            "--reasoning-effort",
            "max",
            reasoning_effort_env="low",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["reasoning_effort"], "max")
        command = json.loads(self.args_file.read_text(encoding="utf-8"))
        self.assertIn('model_reasoning_effort="max"', command)

    def test_environment_sets_reasoning_effort(self) -> None:
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            reasoning_effort_env="xhigh",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["reasoning_effort"], "xhigh")
        command = json.loads(self.args_file.read_text(encoding="utf-8"))
        self.assertIn('model_reasoning_effort="xhigh"', command)

    def test_invalid_environment_reasoning_effort_fails_closed(self) -> None:
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            reasoning_effort_env="extreme",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("SOL_LUNA_REASONING_EFFORT must be one of", result.stderr)
        self.assertFalse(self.args_file.exists())

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

    def test_invalid_jsonl_fails_closed(self) -> None:
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

    def test_codex_failure_propagates_exact_error(self) -> None:
        result = self.invoke(
            "run",
            "--cwd",
            str(self.repo),
            "--prompt-file",
            str(self.prompt),
            mode="failure",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("simulated failure", result.stderr)

    def test_recovered_transport_errors_are_returned_as_warnings(self) -> None:
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
        self.assertEqual(payload["final_response"], "done")
        self.assertEqual(
            payload["warnings"],
            [
                "Reconnecting after request timed out",
                "Falling back to HTTPS transport",
            ],
        )

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

    def test_events_file_preserves_jsonl(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
