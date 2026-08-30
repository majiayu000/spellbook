import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "threads" / "scripts" / "append_run_log.py"


class ThreadsRunLogDispatchTests(unittest.TestCase):
    def run_script(self, payload, log_path, *extra_args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--path", str(log_path), *extra_args],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )

    def queue_bounds(self):
        return {
            "max_items": 10,
            "max_model_calls": 2,
            "time_budget": "30m",
            "checkpoint_every_items": 5,
            "queue_tranche": "bounded test tranche",
        }

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
                        "queue_bounds": self.queue_bounds(),
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
                    "queue_bounds": self.queue_bounds(),
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
                    "queue_bounds": self.queue_bounds(),
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
                    "queue_bounds": self.queue_bounds(),
                },
                log_path,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(log_path.exists())

    def test_accepts_preflight_without_completed_agent_evidence(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "preflight.jsonl"
            result = self.run_script(
                {
                    "run_phase": "preflight",
                    "skill": "threads",
                    "mode": "execute_direct",
                    "thread_dispatch_gate": {
                        "native_subagents": "available",
                        "explicit_thread_request": True,
                        "spawn_requirement": "required",
                        "fallback_mode": "none",
                        "planned_native_threads": [
                            {"id": "calibration", "role": "researcher"}
                        ],
                    },
                    "queue_bounds": self.queue_bounds(),
                },
                log_path,
                "--validate-only",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_preflight_without_queue_bounds(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "preflight-no-budget.jsonl"
            result = self.run_script(
                {
                    "run_phase": "preflight",
                    "skill": "threads",
                    "mode": "execute_direct",
                    "thread_dispatch_gate": {
                        "planned_native_threads": [{"id": "calibration"}],
                    },
                },
                log_path,
                "--validate-only",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("queue_bounds is required", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_multi_lane_list_without_queue_bounds(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "multi-lane-list-no-budget.jsonl"
            result = self.run_script(
                {
                    "skill": "threads",
                    "lanes": [{"role": "worker"}, {"role": "reviewer"}],
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("queue_bounds is required", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_multi_lane_map_without_queue_bounds(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "multi-lane-map-no-budget.jsonl"
            result = self.run_script(
                {
                    "skill": "threads",
                    "lane_map": {
                        "lanes": [{"role": "worker"}, {"role": "reviewer"}],
                    },
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("queue_bounds is required", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_free_text_time_budget(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "preflight-free-text.jsonl"
            bounds = self.queue_bounds()
            bounds["time_budget"] = "not pre-budgeted"
            result = self.run_script(
                {
                    "run_phase": "preflight",
                    "skill": "threads",
                    "mode": "research_spec",
                    "thread_dispatch_gate": {
                        "planned_native_threads": [{"id": "calibration"}],
                    },
                    "queue_bounds": bounds,
                },
                log_path,
                "--validate-only",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("concrete duration", result.stderr)

    def test_rejects_missing_model_call_ceiling(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "preflight-no-calls.jsonl"
            bounds = self.queue_bounds()
            del bounds["max_model_calls"]
            result = self.run_script(
                {
                    "run_phase": "preflight",
                    "skill": "threads",
                    "mode": "research_spec",
                    "thread_dispatch_gate": {
                        "planned_native_threads": [{"id": "calibration"}],
                    },
                    "queue_bounds": bounds,
                },
                log_path,
                "--validate-only",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("queue_bounds.max_model_calls is required", result.stderr)

    def test_rejects_checkpoint_larger_than_item_ceiling(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "preflight-bad-checkpoint.jsonl"
            bounds = self.queue_bounds()
            bounds["checkpoint_every_items"] = 11
            result = self.run_script(
                {
                    "run_phase": "preflight",
                    "skill": "threads",
                    "mode": "research_spec",
                    "thread_dispatch_gate": {
                        "planned_native_threads": [{"id": "calibration"}],
                    },
                    "queue_bounds": bounds,
                },
                log_path,
                "--validate-only",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must not exceed", result.stderr)

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

    def test_rejects_explicit_single_agent_mode_without_fallback_reason(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "single-agent-mode-missing.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "single_agent",
                    "native_subagents": "available",
                    "explicit_thread_request": "yes",
                    "spawn_requirement": "required",
                    "fallback_mode": "none",
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("native_thread_evidence.spawned_agents", result.stderr)
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


if __name__ == "__main__":
    unittest.main()
