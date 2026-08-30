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
        payload = dict(payload)
        if payload.get("run_phase") == "preflight" and "intent_contract" not in payload:
            payload["intent_contract"] = self.intent_contract()
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--path", str(log_path), *extra_args],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )

    def intent_contract(self):
        return {
            "goal": "Validate one bounded test tranche.",
            "done_when": "The preflight contract passes validation.",
            "authorized_actions": ["validate the test record"],
            "fresh_confirmation_required": [],
        }

    def queue_bounds(self):
        return {
            "max_items": 10,
            "max_model_calls": 2,
            "items_processed": 2,
            "model_calls_used": 2,
            "time_budget": "30m",
            "elapsed_seconds": 0,
            "checkpoint_every_items": 5,
            "queue_tranche": "bounded test tranche",
        }

    def preflight_bounds(self):
        bounds = self.queue_bounds()
        bounds.update(
            {
                "items_processed": 0,
                "model_calls_used": 0,
                "elapsed_seconds": 0,
                "planned_items": 1,
                "planned_model_calls": 1,
                "planned_seconds": 1,
            }
        )
        return bounds

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

    def test_rejects_duplicate_final_planned_lane_ids(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "duplicate-final-plan.jsonl"
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
                            {"id": "same", "role": "reviewer"},
                            {"id": "same", "role": "reviewer"},
                        ],
                        "native_thread_evidence": {
                            "spawned_agents": [
                                {
                                    "lane_id": "same",
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
            self.assertIn("planned_native_threads ids must be unique", result.stderr)
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
                    "queue_bounds": self.preflight_bounds(),
                },
                log_path,
                "--validate-only",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_preflight_usage_above_declared_ceilings(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "exhausted-preflight.jsonl"
            bounds = self.preflight_bounds()
            bounds.update(
                {
                    "max_items": 1,
                    "max_model_calls": 1,
                    "checkpoint_every_items": 1,
                    "items_processed": 99,
                    "model_calls_used": 99,
                    "time_budget": "1s",
                    "elapsed_seconds": 99,
                }
            )
            result = self.run_script(
                {
                    "run_phase": "preflight",
                    "skill": "threads",
                    "mode": "execute_direct",
                    "thread_dispatch_gate": {
                        "planned_native_threads": [{"id": "calibration"}],
                    },
                    "queue_bounds": bounds,
                },
                log_path,
                "--validate-only",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("items_processed exceeds max_items", result.stderr)

    def test_rejects_preflight_at_any_exhausted_ceiling(self):
        cases = [
            ({"max_items": 2, "checkpoint_every_items": 2, "items_processed": 2}, "item"),
            ({"max_model_calls": 2, "model_calls_used": 2}, "model-call"),
            ({"time_budget": "2s", "elapsed_seconds": 2}, "time"),
        ]
        for updates, ceiling_name in cases:
            with self.subTest(ceiling=ceiling_name), TemporaryDirectory() as temp_dir:
                bounds = self.preflight_bounds()
                bounds.update(updates)
                result = self.run_script(
                    {
                        "run_phase": "preflight",
                        "skill": "threads",
                        "thread_dispatch_gate": {
                            "planned_native_threads": [{"id": "calibration"}],
                        },
                        "queue_bounds": bounds,
                    },
                    Path(temp_dir) / "exhausted-preflight.jsonl",
                    "--validate-only",
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("preflight budget is exhausted", result.stderr)

    def test_rejects_preflight_lanes_above_remaining_model_calls(self):
        with TemporaryDirectory() as temp_dir:
            bounds = self.preflight_bounds()
            bounds["model_calls_used"] = 1
            bounds["planned_model_calls"] = 2
            result = self.run_script(
                {
                    "run_phase": "preflight",
                    "skill": "threads",
                    "thread_dispatch_gate": {
                        "planned_native_threads": [
                            {"id": "research"},
                            {"id": "review"},
                        ],
                    },
                    "queue_bounds": bounds,
                },
                Path(temp_dir) / "insufficient-calls.jsonl",
                "--validate-only",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("planned tranche exceeds remaining model calls", result.stderr)

    def test_rejects_preflight_tranche_above_each_remaining_allowance(self):
        cases = [
            ({"max_items": 100, "items_processed": 99, "planned_items": 2}, "items"),
            (
                {
                    "max_model_calls": 2,
                    "model_calls_used": 1,
                    "planned_model_calls": 2,
                },
                "model calls",
            ),
            (
                {"time_budget": "2s", "elapsed_seconds": 1, "planned_seconds": 2},
                "time",
            ),
        ]
        for updates, allowance in cases:
            with self.subTest(allowance=allowance), TemporaryDirectory() as temp_dir:
                bounds = self.preflight_bounds()
                bounds.update(updates)
                result = self.run_script(
                    {
                        "run_phase": "preflight",
                        "skill": "threads",
                        "thread_dispatch_gate": {
                            "planned_native_threads": [{"id": "calibration"}],
                        },
                        "queue_bounds": bounds,
                    },
                    Path(temp_dir) / "oversized-tranche.jsonl",
                    "--validate-only",
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    f"planned tranche exceeds remaining {allowance}", result.stderr
                )

    def test_rejects_appending_a_preflight_record(self):
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
                        "planned_native_threads": [{"id": "calibration"}],
                    },
                    "queue_bounds": self.preflight_bounds(),
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("preflight records require --validate-only", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_final_spawn_count_above_model_call_ceiling(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "too-many-model-calls.jsonl"
            bounds = self.queue_bounds()
            bounds["max_model_calls"] = 1
            bounds["model_calls_used"] = 3
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
                                "lane_id": f"lane-{index}",
                                "spawn_tool": "multi_agent_v1.spawn_agent",
                                "agent_id_or_thread_id": f"agent-{index}",
                                "wait_evidence": "wait_agent completed",
                                "close_evidence": "close_agent completed",
                                "result_collected": True,
                            }
                            for index in range(3)
                        ]
                    },
                    "lanes_total": 3,
                    "queue_bounds": bounds,
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("model_calls_used exceeds max_model_calls", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_final_items_closed_above_item_ceiling(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "too-many-items.jsonl"
            bounds = self.queue_bounds()
            bounds["max_items"] = 1
            bounds["checkpoint_every_items"] = 1
            bounds["items_processed"] = 500
            result = self.run_script(
                {
                    "skill": "threads",
                    "lanes_total": 2,
                    "queue_bounds": bounds,
                    "queue_ledger": {
                        "items_total": 500,
                        "items_closed": 500,
                        "items_deferred": 0,
                    },
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("max_items cannot be lower than processed queue_ledger items", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_final_deferred_items_above_item_ceiling(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "too-many-deferred-items.jsonl"
            bounds = self.queue_bounds()
            bounds["max_items"] = 1
            bounds["checkpoint_every_items"] = 1
            bounds["items_processed"] = 100
            result = self.run_script(
                {
                    "skill": "threads",
                    "lanes_total": 2,
                    "queue_bounds": bounds,
                    "queue_ledger": {
                        "items_total": 100,
                        "items_closed": 1,
                        "items_deferred": 99,
                    },
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("max_items cannot be lower than processed queue_ledger items", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_final_elapsed_time_above_time_budget(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "elapsed-budget.jsonl"
            bounds = self.queue_bounds()
            bounds["time_budget"] = "1s"
            bounds["elapsed_seconds"] = 1.5
            result = self.run_script(
                {
                    "skill": "threads",
                    "lanes_total": 2,
                    "queue_bounds": bounds,
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("elapsed_seconds exceeds time_budget", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_list_queue_ledger_above_item_ceiling(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "list-ledger-budget.jsonl"
            bounds = self.queue_bounds()
            bounds["max_items"] = 1
            bounds["checkpoint_every_items"] = 1
            bounds["items_processed"] = 2
            result = self.run_script(
                {
                    "skill": "threads",
                    "lanes_total": 2,
                    "queue_bounds": bounds,
                    "queue_ledger": [{"id": index} for index in range(100)],
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("max_items cannot be lower than processed queue_ledger items", result.stderr)
            self.assertFalse(log_path.exists())

    def test_accepts_open_list_ledger_larger_than_bounded_tranche(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "open-list-ledger.jsonl"
            bounds = self.queue_bounds()
            bounds["max_items"] = 1
            bounds["checkpoint_every_items"] = 1
            bounds["items_processed"] = 1
            result = self.run_script(
                {
                    "skill": "threads",
                    "queue_bounds": bounds,
                    "queue_ledger": [
                        {"item": f"#{index}", "remote_state": "open"}
                        for index in range(100)
                    ],
                },
                log_path,
            )

            self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_actual_model_calls_above_ceiling(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "model-call-overrun.jsonl"
            bounds = self.queue_bounds()
            bounds["max_model_calls"] = 1
            bounds["model_calls_used"] = 2
            result = self.run_script(
                {"skill": "threads", "lanes_total": 1, "queue_bounds": bounds},
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("model_calls_used exceeds max_model_calls", result.stderr)

    def test_rejects_superseded_items_missing_from_usage(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "superseded-usage.jsonl"
            bounds = self.queue_bounds()
            bounds["max_items"] = 100
            bounds["items_processed"] = 1
            result = self.run_script(
                {
                    "skill": "threads",
                    "queue_bounds": bounds,
                    "queue_ledger": {
                        "items_total": 50,
                        "items_closed": 0,
                        "items_deferred": 0,
                        "stale_base": False,
                        "superseded_items": list(range(50)),
                    },
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("items_processed cannot be lower than queue ledger usage", result.stderr)

    def test_rejects_nested_queue_ledger_items_above_item_ceiling(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "nested-ledger-budget.jsonl"
            bounds = self.queue_bounds()
            bounds["max_items"] = 1
            bounds["checkpoint_every_items"] = 1
            bounds["items_processed"] = 2
            result = self.run_script(
                {
                    "skill": "threads",
                    "queue_bounds": bounds,
                    "queue_ledger": {
                        "items_total": 2,
                        "items_closed": 0,
                        "items_deferred": 0,
                        "stale_base": False,
                        "items": [{"id": 1}, {"id": 2}],
                    },
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("max_items cannot be lower than processed queue_ledger items", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_queue_ledger_without_queue_bounds(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "ledger-no-budget.jsonl"
            result = self.run_script(
                {
                    "skill": "threads",
                    "queue_ledger": {
                        "items_total": 500,
                        "items_closed": 500,
                        "items_deferred": 0,
                        "stale_base": False,
                    },
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("queue_bounds is required", result.stderr)
            self.assertFalse(log_path.exists())

    def test_accepts_null_queue_ledger_without_queue_bounds(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "null-ledger.jsonl"
            result = self.run_script(
                {
                    "skill": "threads",
                    "queue_ledger": None,
                },
                log_path,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(log_path.exists())

    def test_accepts_final_elapsed_evidence_with_nested_ceiling_contract(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "nested-contract-final.jsonl"
            approved_bounds = self.preflight_bounds()
            for field in ("elapsed_seconds", "items_processed", "model_calls_used"):
                del approved_bounds[field]
            final_bounds = {
                field: value
                for field, value in approved_bounds.items()
                if field not in {"planned_items", "planned_model_calls", "planned_seconds"}
            }
            final_bounds["elapsed_seconds"] = 12
            final_bounds["items_processed"] = 2
            final_bounds["model_calls_used"] = 2
            result = self.run_script(
                {
                    "skill": "threads",
                    "intent_contract": {"queue_bounds": approved_bounds},
                    "queue_bounds": final_bounds,
                },
                log_path,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(record["queue_bounds"]["elapsed_seconds"], 12)

    def test_rejects_conflicting_preflight_planning_fields(self):
        with TemporaryDirectory() as temp_dir:
            top_level_bounds = self.preflight_bounds()
            nested_bounds = self.preflight_bounds()
            for field in ("elapsed_seconds", "items_processed", "model_calls_used"):
                del nested_bounds[field]
            nested_bounds["planned_items"] = 2
            intent = self.intent_contract()
            intent["queue_bounds"] = nested_bounds
            result = self.run_script(
                {
                    "run_phase": "preflight",
                    "skill": "threads",
                    "intent_contract": intent,
                    "thread_dispatch_gate": {
                        "planned_native_threads": [{"id": "calibration"}],
                    },
                    "queue_bounds": top_level_bounds,
                },
                Path(temp_dir) / "conflicting-plan.jsonl",
                "--validate-only",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("conflicting queue_bounds", result.stderr)

    def test_rejects_missing_planning_field_before_comparing_duplicate_bounds(self):
        with TemporaryDirectory() as temp_dir:
            top_level_bounds = self.preflight_bounds()
            del top_level_bounds["planned_items"]
            nested_bounds = self.preflight_bounds()
            for field in ("elapsed_seconds", "items_processed", "model_calls_used"):
                del nested_bounds[field]
            intent = self.intent_contract()
            intent["queue_bounds"] = nested_bounds
            result = self.run_script(
                {
                    "run_phase": "preflight",
                    "skill": "threads",
                    "intent_contract": intent,
                    "thread_dispatch_gate": {
                        "planned_native_threads": [{"id": "calibration"}],
                    },
                    "queue_bounds": top_level_bounds,
                },
                Path(temp_dir) / "missing-plan-field.jsonl",
                "--validate-only",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("queue_bounds.planned_items is required", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_rejects_action_in_both_authorization_lists(self):
        with TemporaryDirectory() as temp_dir:
            intent = self.intent_contract()
            intent["authorized_actions"] = ["merge PR #1"]
            intent["fresh_confirmation_required"] = ["merge PR #1"]
            result = self.run_script(
                {
                    "run_phase": "preflight",
                    "skill": "threads",
                    "intent_contract": intent,
                    "thread_dispatch_gate": {
                        "planned_native_threads": [{"id": "calibration"}],
                    },
                    "queue_bounds": self.preflight_bounds(),
                },
                Path(temp_dir) / "ambiguous-authorization.jsonl",
                "--validate-only",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("authorization lists must be disjoint", result.stderr)

    def test_rejects_malformed_thread_dispatch_gate_container(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "malformed-dispatch-gate.jsonl"
            result = self.run_script(
                {
                    "skill": "threads",
                    "thread_dispatch_gate": "planned work",
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("thread_dispatch_gate must be an object", result.stderr)

    def test_rejects_usage_evidence_inside_intent_bounds(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "nested-usage-conflict.jsonl"
            nested_bounds = self.queue_bounds()
            nested_bounds["model_calls_used"] = 99
            result = self.run_script(
                {
                    "skill": "threads",
                    "intent_contract": {"queue_bounds": nested_bounds},
                    "queue_bounds": self.queue_bounds(),
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "intent_contract.queue_bounds must not contain final usage fields",
                result.stderr,
            )

    def test_accepts_final_usage_in_sole_intent_bounds_container(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "sole-nested-final.jsonl"
            result = self.run_script(
                {
                    "skill": "threads",
                    "intent_contract": {"queue_bounds": self.queue_bounds()},
                },
                log_path,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(
                record["intent_contract"]["queue_bounds"]["model_calls_used"], 2
            )

    def test_rejects_non_array_spawned_agent_evidence(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "malformed-spawned-agents.jsonl"
            result = self.run_script(
                {
                    "skill": "threads",
                    "native_thread_evidence": {"spawned_agents": {"lane_id": "review"}},
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("native_thread_evidence.spawned_agents must be a list", result.stderr)

    def test_validates_nested_spawned_evidence_when_top_level_is_empty(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "nested-spawned-overflow.jsonl"
            result = self.run_script(
                {
                    "skill": "threads",
                    "native_thread_evidence": {},
                    "thread_dispatch_gate": {
                        "native_thread_evidence": {
                            "spawned_agents": [
                                {"lane_id": f"lane-{index}"} for index in range(101)
                            ]
                        }
                    },
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("spawned_agents exceeds 100 items", result.stderr)

    def test_rejects_conflicting_spawned_evidence_containers(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "conflicting-spawned-evidence.jsonl"
            result = self.run_script(
                {
                    "skill": "threads",
                    "native_thread_evidence": {"spawned_agents": []},
                    "thread_dispatch_gate": {
                        "native_thread_evidence": {
                            "spawned_agents": [{"lane_id": "review"}]
                        }
                    },
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("conflicting spawned_agents evidence", result.stderr)

    def test_rejects_non_array_final_dispatch_plan(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "malformed-final-plan.jsonl"
            result = self.run_script(
                {
                    "skill": "threads",
                    "thread_dispatch_gate": {
                        "planned_native_threads": {"id": "review"},
                    },
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("planned_native_threads must be a list", result.stderr)

    def test_preflight_requires_intent_contract(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "missing-intent-preflight.jsonl"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--path", str(log_path), "--validate-only"],
                input=json.dumps(
                    {
                        "run_phase": "preflight",
                        "skill": "threads",
                        "thread_dispatch_gate": {
                            "planned_native_threads": [{"id": "review"}],
                        },
                        "queue_bounds": self.queue_bounds(),
                    }
                ),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("intent_contract is required for preflight", result.stderr)

    def test_rejects_non_finite_elapsed_seconds(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "non-finite-elapsed.jsonl"
            bounds = self.queue_bounds()
            bounds["elapsed_seconds"] = float("nan")
            result = self.run_script(
                {
                    "skill": "threads",
                    "lanes_total": 2,
                    "queue_bounds": bounds,
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("elapsed_seconds must be a finite non-negative number", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_spawned_agents_truncated_before_budget_validation(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "too-many-spawned-agents.jsonl"
            bounds = self.queue_bounds()
            bounds["max_items"] = 101
            bounds["max_model_calls"] = 100
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
                                "lane_id": f"lane-{index}",
                                "spawn_tool": "multi_agent_v1.spawn_agent",
                                "agent_id_or_thread_id": f"agent-{index}",
                                "wait_evidence": "wait_agent completed",
                                "close_evidence": "close_agent completed",
                                "result_collected": True,
                            }
                            for index in range(101)
                        ]
                    },
                    "lanes_total": 101,
                    "queue_bounds": bounds,
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("spawned_agents exceeds 100 items", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_unbounded_queue_tranche_sentinels(self):
        for queue_tranche in ("unbounded", "as needed", "not pre-budgeted"):
            with self.subTest(queue_tranche=queue_tranche), TemporaryDirectory() as temp_dir:
                log_path = Path(temp_dir) / "unbounded-tranche.jsonl"
                bounds = self.queue_bounds()
                bounds["queue_tranche"] = queue_tranche
                result = self.run_script(
                    {
                        "run_phase": "preflight",
                        "skill": "threads",
                        "mode": "execute_direct",
                        "thread_dispatch_gate": {
                            "planned_native_threads": [{"id": "calibration"}],
                        },
                        "queue_bounds": bounds,
                    },
                    log_path,
                    "--validate-only",
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("queue_tranche must describe a bounded tranche", result.stderr)

    def test_rejects_invalid_preflight_fallback_semantics(self):
        cases = [
            ({}, "fallback_mode is required"),
            ({"fallback_mode": "single_agent"}, "single_agent fallback"),
            ({"fallback_mode": "prompt_pack_only"}, "prompt_pack_only fallback is invalid"),
        ]
        for gate_fields, expected_error in cases:
            with self.subTest(gate_fields=gate_fields), TemporaryDirectory() as temp_dir:
                log_path = Path(temp_dir) / "invalid-fallback.jsonl"
                result = self.run_script(
                    {
                        "run_phase": "preflight",
                        "skill": "threads",
                        "mode": "execute_direct",
                        "thread_dispatch_gate": {
                            "native_subagents": "available",
                            "explicit_thread_request": True,
                            "spawn_requirement": "required",
                            "planned_native_threads": [{"id": "calibration"}],
                            **gate_fields,
                        },
                        "queue_bounds": self.queue_bounds(),
                    },
                    log_path,
                    "--validate-only",
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)
                self.assertFalse(log_path.exists())

    def test_rejects_planned_threads_truncated_before_budget_validation(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "too-many-planned-threads.jsonl"
            bounds = self.queue_bounds()
            bounds["max_items"] = 101
            bounds["max_model_calls"] = 100
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
                            {"id": f"lane-{index}"} for index in range(101)
                        ],
                    },
                    "queue_bounds": bounds,
                },
                log_path,
                "--validate-only",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("planned_native_threads exceeds 100 items", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_nested_ledger_items_truncated_before_budget_validation(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "too-many-nested-ledger-items.jsonl"
            bounds = self.queue_bounds()
            bounds["max_items"] = 101
            bounds["checkpoint_every_items"] = 1
            result = self.run_script(
                {
                    "skill": "threads",
                    "queue_bounds": bounds,
                    "queue_ledger": {
                        "items_total": 101,
                        "items_closed": 0,
                        "items_deferred": 0,
                        "stale_base": False,
                        "items": [{"id": index} for index in range(101)],
                    },
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("queue_ledger.items exceeds 100 items", result.stderr)
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

    def test_rejects_non_string_preflight_lane_id(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "numeric-lane-id.jsonl"
            result = self.run_script(
                {
                    "run_phase": "preflight",
                    "skill": "threads",
                    "thread_dispatch_gate": {
                        "planned_native_threads": [{"id": 123}],
                    },
                    "queue_bounds": self.preflight_bounds(),
                },
                log_path,
                "--validate-only",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("planned_native_threads entries require string id", result.stderr)

    def test_rejects_malformed_lanes_total(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "malformed-lanes-total.jsonl"
            result = self.run_script(
                {"skill": "threads", "lanes_total": "20"},
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("lanes_total must be a non-negative integer", result.stderr)

    def test_accepts_zero_lane_final(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "zero-lane-final.jsonl"
            result = self.run_script(
                {"skill": "threads", "lanes_total": 0},
                log_path,
            )

            self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_duplicate_preflight_lane_ids(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "duplicate-lane-ids.jsonl"
            result = self.run_script(
                {
                    "run_phase": "preflight",
                    "skill": "threads",
                    "thread_dispatch_gate": {
                        "planned_native_threads": [
                            {"id": "review"},
                            {"id": "review"},
                        ],
                    },
                    "queue_bounds": self.preflight_bounds(),
                },
                log_path,
                "--validate-only",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("planned_native_threads ids must be unique", result.stderr)

    def test_rejects_non_string_run_phase_without_traceback(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "invalid-run-phase.jsonl"
            result = self.run_script(
                {"run_phase": {}, "skill": "threads"},
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("run_phase must be preflight or final", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

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

    def test_rejects_single_lane_final_without_queue_bounds(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "single-lane-no-budget.jsonl"
            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "execute_direct",
                    "native_subagents": "available",
                    "explicit_thread_request": True,
                    "spawn_requirement": "required",
                    "fallback_mode": "none",
                    "thread_dispatch_gate": {
                        "planned_native_threads": [{"id": "calibration"}],
                    },
                    "native_thread_evidence": {
                        "spawned_agents": [
                            {
                                "lane_id": "calibration",
                                "spawn_tool": "multi_agent_v1.spawn_agent",
                                "agent_id_or_thread_id": "agent-123",
                                "wait_evidence": "wait_agent completed",
                                "close_evidence": "close_agent completed",
                                "result_collected": True,
                            }
                        ]
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
