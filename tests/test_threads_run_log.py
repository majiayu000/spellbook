import json
import os
import subprocess
import stat
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "threads" / "scripts" / "append_run_log.py"


class ThreadsRunLogTests(unittest.TestCase):
    def run_script(self, payload, log_path, *extra_args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--path", str(log_path), *extra_args],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_appends_sanitized_jsonl_record(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "threads.jsonl"
            payload = {
                "skill": "threads",
                "mode": "execute_direct",
                "notes": "contains ghp_1234567890abcdefghijklmnopqrst and sk-1234567890abcdefghijklmnopqrst",
                "verification": {
                    "api_key": "secret-value",
                    "commands": ["pytest"],
                },
            }

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--path", str(log_path)],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(log_path))
            lines = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertNotIn("ghp_1234567890abcdefghijklmnopqrst", record["notes"])
            self.assertNotIn("sk-1234567890abcdefghijklmnopqrst", record["notes"])
            self.assertEqual(record["verification"]["api_key"], "[REDACTED]")
            self.assertEqual(record["verification"]["commands"], ["pytest"])
            self.assertEqual(record["schema_version"], 1)
            self.assertIn("recorded_at_utc", record)

    def test_uses_env_path_by_default(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "env.jsonl"
            env = {**os.environ, "CODEX_THREADS_RUN_LOG": str(log_path)}

            result = subprocess.run(
                [sys.executable, str(SCRIPT)],
                input=json.dumps({"skill": "threads", "mode": "plan_only"}),
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(log_path.exists())

    def test_defaults_to_git_metadata_log_path(self):
        with TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            (project_root / ".git").mkdir()
            expected_log = (
                project_root.resolve()
                / ".git"
                / "codex"
                / "threads"
                / "run-log.jsonl"
            )
            env = os.environ.copy()
            env.pop("CODEX_THREADS_RUN_LOG", None)

            result = subprocess.run(
                [sys.executable, str(SCRIPT)],
                input=json.dumps({"skill": "threads", "mode": "plan_only"}),
                text=True,
                capture_output=True,
                check=False,
                cwd=project_root,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(expected_log))
            self.assertTrue(expected_log.exists())

    def test_defaults_to_worktree_git_metadata_log_path(self):
        with TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "worktree"
            project_root.mkdir()
            git_metadata = Path(temp_dir) / "git" / "worktrees" / "worktree"
            git_metadata.mkdir(parents=True)
            (project_root / ".git").write_text(
                f"gitdir: {git_metadata}\n",
                encoding="utf-8",
            )
            expected_log = git_metadata / "codex" / "threads" / "run-log.jsonl"
            env = os.environ.copy()
            env.pop("CODEX_THREADS_RUN_LOG", None)

            result = subprocess.run(
                [sys.executable, str(SCRIPT)],
                input=json.dumps({"skill": "threads", "mode": "plan_only"}),
                text=True,
                capture_output=True,
                check=False,
                cwd=project_root,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(expected_log))
            self.assertTrue(expected_log.exists())

    def test_allows_documented_cleanup_run_log_fields(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "closure.jsonl"

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--path", str(log_path)],
                input=json.dumps(
                    {
                        "skill": "threads",
                        "mode": "execute_direct",
                        "remote_truth": {"origin_main_sha": "abc123"},
                        "local_state": {"dirty_worktree": False},
                    }
                ),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(record["remote_truth"]["origin_main_sha"], "abc123")
            self.assertFalse(record["local_state"]["dirty_worktree"])

    def test_accepts_clarify_first_mode(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "clarify.jsonl"

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--path", str(log_path)],
                input=json.dumps({"skill": "threads", "mode": "clarify_first"}),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(record["mode"], "clarify_first")

    def test_rejects_required_native_threads_without_spawned_agent(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "native-missing.jsonl"

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--path", str(log_path)],
                input=json.dumps(
                    {
                        "skill": "threads",
                        "mode": "execute_direct",
                        "native_subagents": "available",
                        "explicit_thread_request": True,
                        "spawn_requirement": "required",
                        "fallback_mode": "none",
                        "lanes_total": 2,
                    }
                ),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("native_thread_evidence.spawned_agents", result.stderr)
            self.assertFalse(log_path.exists())

    def test_accepts_required_native_threads_with_spawned_agent(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "native-present.jsonl"

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--path", str(log_path)],
                input=json.dumps(
                    {
                        "skill": "threads",
                        "mode": "execute_direct",
                        "native_subagents": "available",
                        "explicit_thread_request": True,
                        "spawn_requirement": "required",
                        "fallback_mode": "none",
                        "native_thread_evidence": {
                            "spawned_agents": [
                                {
                                    "lane_id": "review-pr",
                                    "spawn_tool": "multi_agent_v1.spawn_agent",
                                    "agent_id_or_thread_id": "agent-123",
                                    "wait_evidence": "wait_agent completed",
                                    "close_evidence": "close_agent completed",
                                    "result_collected": True,
                                }
                            ]
                        },
                        "lanes_total": 2,
                    }
                ),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(
                record["native_thread_evidence"]["spawned_agents"][0]["agent_id_or_thread_id"],
                "agent-123",
            )

    def test_rejects_required_native_threads_without_fallback_mode(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "fallback-omitted.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "execute_direct",
                    "native_subagents": "available",
                    "explicit_thread_request": True,
                    "spawn_requirement": "required",
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("fallback_mode is required", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_prompt_pack_fallback_when_native_threads_available(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "prompt-pack.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "review_only",
                    "native_subagents": "available",
                    "explicit_thread_request": True,
                    "spawn_requirement": "required",
                    "fallback_mode": "prompt_pack_only",
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("prompt_pack_only fallback is invalid", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_invalid_fallback_mode_for_required_native_threads(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "invalid-fallback.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "execute_direct",
                    "native_subagents": "available",
                    "explicit_thread_request": True,
                    "spawn_requirement": "required",
                    "fallback_mode": "serial",
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown fallback_mode", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_fake_native_thread_evidence(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "fake-native.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "execute_direct",
                    "native_subagents": "available",
                    "explicit_thread_request": True,
                    "spawn_requirement": "required",
                    "fallback_mode": "none",
                    "native_thread_evidence": {
                        "spawned_agents": [
                            {
                                "lane_id": "review-pr",
                                "spawn_tool": "manual",
                                "agent_id_or_thread_id": "none",
                                "result_collected": False,
                            }
                        ]
                    },
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("native_thread_evidence.spawned_agents", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_conflicting_capability_gate(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "conflict.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "execute_direct",
                    "native_subagents": "available",
                    "explicit_thread_request": True,
                    "spawn_requirement": "required",
                    "fallback_mode": "none",
                    "capability_gate": {
                        "native_subagents": "unavailable",
                    },
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("conflicting native_subagents", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_explicit_plan_only_without_spawned_agent(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "plan-only-missing.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "plan_only",
                    "native_subagents": "available",
                    "explicit_thread_request": True,
                    "spawn_requirement": "required",
                    "fallback_mode": "none",
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("native_thread_evidence.spawned_agents", result.stderr)
            self.assertFalse(log_path.exists())

    def test_accepts_thread_dispatch_gate_spawned_agent(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "dispatch-gate.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "review_only",
                    "thread_dispatch_gate": {
                        "native_subagents": "available",
                        "explicit_thread_request": True,
                        "spawn_requirement": "required",
                        "fallback_mode": "none",
                        "native_thread_evidence": {
                            "spawned_agents": [
                                {
                                    "lane_id": "review-pr",
                                    "spawn_tool": "multi_agent_v1.spawn_agent",
                                    "agent_id_or_thread_id": "agent-123",
                                    "wait_evidence": "wait_agent completed",
                                    "close_evidence": "close_agent completed",
                                    "result_collected": True,
                                }
                            ]
                        },
                    },
                },
                log_path,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(
                record["thread_dispatch_gate"]["native_thread_evidence"]["spawned_agents"][0][
                    "agent_id_or_thread_id"
                ],
                "agent-123",
            )

    def test_rejects_planned_native_thread_without_spawn_or_reason(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "planned-missing.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "review_only",
                    "thread_dispatch_gate": {
                        "native_subagents": "available",
                        "explicit_thread_request": True,
                        "spawn_requirement": "required",
                        "fallback_mode": "none",
                        "planned_native_threads": [
                            {"id": "review-docs", "role": "reviewer"},
                            {"id": "review-tests", "role": "reviewer"},
                        ],
                        "native_thread_evidence": {
                            "spawned_agents": [
                                {
                                    "lane_id": "review-docs",
                                    "spawn_tool": "multi_agent_v1.spawn_agent",
                                    "agent_id_or_thread_id": "agent-123",
                                    "wait_evidence": "wait_agent completed",
                                    "close_evidence": "close_agent completed",
                                    "result_collected": True,
                                }
                            ]
                        },
                    },
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("planned_native_threads missing spawned evidence", result.stderr)
            self.assertFalse(log_path.exists())

    def test_accepts_planned_native_thread_with_lane_no_spawn_reason(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "planned-reason.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "review_only",
                    "thread_dispatch_gate": {
                        "native_subagents": "available",
                        "explicit_thread_request": True,
                        "spawn_requirement": "required",
                        "fallback_mode": "none",
                        "planned_native_threads": [
                            {"id": "review-docs", "role": "reviewer"},
                            {
                                "id": "review-tests",
                                "role": "reviewer",
                                "no_spawn_reason": "sequential_dependency",
                            },
                        ],
                        "native_thread_evidence": {
                            "spawned_agents": [
                                {
                                    "lane_id": "review-docs",
                                    "spawn_tool": "multi_agent_v1.spawn_agent",
                                    "agent_id_or_thread_id": "agent-123",
                                    "wait_evidence": "wait_agent completed",
                                    "close_evidence": "close_agent completed",
                                    "result_collected": True,
                                }
                            ]
                        },
                    },
                },
                log_path,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(log_path.exists())

    def test_requires_reason_for_explicit_single_agent_fallback(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "fallback-missing.jsonl"

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--path", str(log_path)],
                input=json.dumps(
                    {
                        "skill": "threads",
                        "mode": "review_only",
                        "native_subagents": "available",
                        "explicit_thread_request": "yes",
                        "spawn_requirement": "required",
                        "fallback_mode": "single_agent",
                    }
                ),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("single_agent fallback", result.stderr)
            self.assertFalse(log_path.exists())

    def test_accepts_reasoned_explicit_single_agent_fallback(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "fallback-reason.jsonl"

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--path", str(log_path)],
                input=json.dumps(
                    {
                        "skill": "threads",
                        "mode": "review_only",
                        "native_subagents": "available",
                        "explicit_thread_request": "yes",
                        "spawn_requirement": "required",
                        "fallback_mode": "single_agent",
                        "single_agent_justification": {
                            "reason": "sequential_dependency",
                            "evidence": "next step depends on one immediate result",
                        },
                    }
                ),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(
                record["single_agent_justification"]["reason"],
                "sequential_dependency",
            )

    def test_accepts_thread_dispatch_gate_single_agent_reason(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "dispatch-fallback-reason.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "review_only",
                    "thread_dispatch_gate": {
                        "native_subagents": "available",
                        "explicit_thread_request": True,
                        "spawn_requirement": "required",
                        "fallback_mode": "single_agent",
                        "no_spawn_reason": "sequential_dependency",
                    },
                },
                log_path,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(log_path.exists())

    def test_rejects_invalid_explicit_single_agent_fallback_reason(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "fallback-invalid-reason.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "review_only",
                    "native_subagents": "available",
                    "explicit_thread_request": "yes",
                    "spawn_requirement": "required",
                    "fallback_mode": "single_agent",
                    "single_agent_justification": {
                        "reason": "too_hard",
                        "evidence": "vague",
                    },
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("single_agent fallback", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_non_object_input(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "bad.jsonl"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--path", str(log_path)],
                input="[]",
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("JSON object", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_unknown_top_level_fields_by_default(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "unknown.jsonl"

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--path", str(log_path)],
                input=json.dumps({"skill": "threads", "mode": "plan_only", "unexpected": "value"}),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown top-level field", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_unknown_truth_level(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "truth.jsonl"

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--path", str(log_path)],
                input=json.dumps({"skill": "threads", "mode": "plan_only", "truth_level": "Z"}),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown truth_level", result.stderr)
            self.assertFalse(log_path.exists())

    def test_allow_extra_preserves_redacted_unknown_top_level_fields(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "extra.jsonl"

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--path", str(log_path), "--allow-extra"],
                input=json.dumps(
                    {
                        "skill": "threads",
                        "mode": "plan_only",
                        "extra": {"token": "should-not-leak"},
                    }
                ),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(record["extra"]["token"], "[REDACTED]")

    def test_new_log_file_is_private(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "private.jsonl"

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--path", str(log_path)],
                input=json.dumps({"skill": "threads", "mode": "plan_only"}),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            mode = stat.S_IMODE(log_path.stat().st_mode)
            self.assertEqual(mode, 0o600)


if __name__ == "__main__":
    unittest.main()
