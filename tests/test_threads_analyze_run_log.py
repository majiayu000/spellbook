import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "threads" / "scripts" / "analyze_run_log.py"


class ThreadsAnalyzeRunLogTests(unittest.TestCase):
    def run_script(self, log_path, *extra_args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--path", str(log_path), *extra_args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_missing_log_file_returns_clear_empty_report(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "missing.jsonl"

            result = self.run_script(log_path)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("status: missing", result.stdout)
            self.assertIn("records: 0", result.stdout)
            self.assertIn("no durable threads run log found", result.stdout)

            json_result = self.run_script(log_path, "--format", "json")
            self.assertEqual(json_result.returncode, 0, json_result.stderr)
            payload = json.loads(json_result.stdout)
            self.assertEqual(payload["status"], "missing")
            self.assertEqual(payload["missing_files"], [str(log_path)])
            self.assertEqual(payload["records_total"], 0)

    def test_summarizes_failure_codes_stale_base_and_native_spawn(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "run-log.jsonl"
            records = [
                {
                    "skill": "threads",
                    "mode": "execute_direct",
                    "truth_level": "A",
                    "failure_codes": ["review_thread_missed", "stale_base"],
                    "queue_gate": {"remote_refresh": {"stale_base": True}},
                    "explicit_thread_request": True,
                    "fallback_mode": "none",
                    "native_thread_evidence": {
                        "spawned_agents": [
                            {
                                "lane_id": "review-pr",
                                "spawn_tool": "multi_agent_v1.spawn_agent",
                                "agent_id_or_thread_id": "agent-123",
                                "result_collected": True,
                                "wait_evidence": "wait_agent completed",
                                "close_evidence": "close_agent completed",
                            }
                        ]
                    },
                    "run_log": {"write_status": "written"},
                    "outcome": "partial",
                    "repo": "/repo",
                },
                {
                    "skill": "threads",
                    "mode": "review_only",
                    "truth_level": "B",
                    "failure_codes": ["durable_log_skipped"],
                    "thread_dispatch_gate": {
                        "explicit_thread_request": True,
                        "fallback_mode": "single_agent",
                    },
                    "run_log": {"write_status": "not_written", "no_log_reason": "user opt out"},
                    "outcome": "blocked",
                    "repo": "/repo",
                },
            ]
            log_path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")

            result = self.run_script(log_path)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("records: 2", result.stdout)
            self.assertIn("invalid_lines: 0", result.stdout)
            self.assertIn("review_thread_missed: 1", result.stdout)
            self.assertIn("durable_log_skipped: 1", result.stdout)
            self.assertIn("stale_base_events: 1", result.stdout)
            self.assertIn("durable_log_gaps: 1", result.stdout)
            self.assertIn("runs_with_spawned_agents: 1", result.stdout)
            self.assertIn("spawned_agents_total: 1", result.stdout)
            self.assertIn("single_agent_fallbacks: 1", result.stdout)

    def test_matches_writer_spawn_and_gate_semantics(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "run-log.jsonl"
            records = [
                {
                    "skill": "threads",
                    "mode": "review_only",
                    "capability_gate": {"explicit_thread_request": True},
                    "native_thread_evidence": {
                        "spawned_agents": [
                            {
                                "lane_id": "placeholder",
                                "spawn_tool": "manual",
                                "agent_id_or_thread_id": "none",
                                "result_collected": False,
                            }
                        ]
                    },
                },
                {
                    "skill": "threads",
                    "mode": "execute_direct",
                    "queue_ledger": {"stale_base": True},
                    "run_log": {"write_status": "not_applicable"},
                },
            ]
            log_path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")

            result = self.run_script(log_path)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("explicit_thread_requests: 1", result.stdout)
            self.assertIn("runs_with_spawned_agents: 0", result.stdout)
            self.assertIn("spawned_agents_total: 0", result.stdout)
            self.assertIn("stale_base_events: 1", result.stdout)
            self.assertIn("durable_log_gaps: 0", result.stdout)

    def test_json_output_is_structured_and_private(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "run-log.jsonl"
            log_path.write_text(json.dumps({
                "skill": "threads",
                "mode": "plan_only",
                "truth_level": "C",
                "trigger_summary": "raw prompt should not appear",
                "notes": "private details should not appear",
            }) + "\n", encoding="utf-8")

            result = self.run_script(log_path, "--format", "json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["records_total"], 1)
            self.assertEqual(payload["truth_levels"], {"C": 1})
            self.assertEqual(payload["missing_files"], [])
            self.assertNotIn("raw prompt", result.stdout)
            self.assertNotIn("private details", result.stdout)

    def test_corrupt_jsonl_fails_clearly(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "run-log.jsonl"
            log_path.write_text(json.dumps({"skill": "threads"}) + "\nnot-json\n", encoding="utf-8")

            result = self.run_script(log_path)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid JSONL record", result.stderr)
            self.assertIn("run-log.jsonl:2", result.stderr)


if __name__ == "__main__":
    unittest.main()
