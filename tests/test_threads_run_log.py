import json
import os
import shutil
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

    def nested_payload(self):
        return {
            "skill": "threads",
            "mode": "execute_direct",
            "truth_level": "A",
            "queue_gate": {
                "fetched_remote": True,
                "truth_level": "A",
                "open_prs": [],
                "open_issues": [117, 118],
                "pr_classification": [],
                "issue_to_pr_map": [
                    {
                        "issue": 117,
                        "covering_pr": None,
                        "status": "uncovered",
                        "reason": "no covering PR",
                    }
                ],
            },
            "remote_refresh": {
                "owner_lane": "coordinator",
                "origin_main_sha": "abc123",
                "local_base_sha": "abc123",
                "stale_base": False,
                "policy": "continue",
            },
            "queue_ledger": {
                "items_total": 2,
                "items_closed": 0,
                "items_deferred": 2,
                "superseded_items": [],
                "items": [
                    {
                        "item": "#117",
                        "type": "issue",
                        "remote_state": "open",
                    }
                ],
            },
            "lane_map": {
                "lanes": [
                    {
                        "id": "planner",
                        "role": "planner",
                        "verification_scope": "inspection_only",
                    }
                ]
            },
            "lanes": [
                {
                    "id": "planner",
                    "role": "planner",
                    "verification_scope": "inspection_only",
                }
            ],
            "remote_closure": {
                "checked": True,
                "open_prs": 0,
                "open_issues": 2,
                "unresolved_review_threads": 0,
            },
            "connector_review": {
                "expected": False,
                "status": "no_connector_expected",
                "head_sha": "abc123",
            },
            "ci_wait": {
                "duration_seconds": 0,
                "budget_exhausted": False,
                "pending_checks": [],
            },
            "review_loop": {
                "cycles": 0,
                "outcome": "not_applicable",
            },
        }

    def assert_rejects_payload(self, payload, expected_error):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "bad-nested.jsonl"

            result = self.run_script(payload, log_path)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(expected_error, result.stderr)
            self.assertFalse(log_path.exists())

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

    def test_allows_queue_gate_from_skill_contract(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "queue-gate.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "plan_only",
                    "queue_gate": {
                        "fetched_remote": True,
                        "truth_level": "A",
                        "open_prs": [],
                        "open_issues": [],
                    },
                    "remote_refresh": {
                        "owner_lane": "coordinator",
                        "origin_main_sha": "abc123",
                        "local_base_sha": "abc123",
                        "stale_base": False,
                        "policy": "continue",
                    },
                },
                log_path,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertTrue(record["queue_gate"]["fetched_remote"])

    def test_allows_documented_nested_queue_record(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "nested-valid.jsonl"

            result = self.run_script(self.nested_payload(), log_path)

            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(record["queue_gate"]["issue_to_pr_map"][0]["status"], "uncovered")
            self.assertEqual(record["connector_review"]["status"], "no_connector_expected")

    def test_allows_context_budget_and_output_firewall_fields(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "context-firewall.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "execute_direct",
                    "context_budget": {
                        "window_tokens": 258400,
                        "soft_stop_ratio": 0.5,
                        "hard_stop_ratio": 0.65,
                        "critical_stop_ratio": 0.75,
                        "current_usage_signal": "below_soft_stop",
                    },
                    "output_firewall": {
                        "raw_log_policy": "file_only",
                        "max_parent_stdout_lines": 150,
                        "max_subagent_final_lines": 150,
                        "artifact_root": "artifacts/logs/t01",
                        "evidence_paths": ["artifacts/logs/t01/cargo-test.log"],
                    },
                    "failure_codes": ["raw_output_blocked", "parent_context_hard_stop"],
                },
                log_path,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(record["output_firewall"]["raw_log_policy"], "file_only")
            self.assertEqual(record["context_budget"]["hard_stop_ratio"], 0.65)

    def test_rejects_context_budget_ratios_out_of_order(self):
        payload = self.nested_payload()
        payload["context_budget"] = {
            "window_tokens": 258400,
            "soft_stop_ratio": 0.7,
            "hard_stop_ratio": 0.65,
            "critical_stop_ratio": 0.75,
        }

        self.assert_rejects_payload(payload, "context_budget ratios")

    def test_rejects_partial_context_budget(self):
        payload = self.nested_payload()
        payload["context_budget"] = {
            "soft_stop_ratio": 0.5,
            "hard_stop_ratio": 0.65,
            "critical_stop_ratio": 0.75,
        }

        self.assert_rejects_payload(payload, "context_budget.window_tokens")

    def test_rejects_unknown_output_firewall_policy(self):
        payload = self.nested_payload()
        payload["output_firewall"] = {"raw_log_policy": "paste_raw_logs"}

        self.assert_rejects_payload(payload, "output_firewall.raw_log_policy")

    def test_rejects_file_only_output_firewall_without_artifact_root(self):
        payload = self.nested_payload()
        payload["output_firewall"] = {
            "raw_log_policy": "file_only",
        }

        self.assert_rejects_payload(payload, "output_firewall.artifact_root")

    def test_rejects_non_string_output_firewall_evidence_path(self):
        payload = self.nested_payload()
        payload["output_firewall"] = {
            "raw_log_policy": "file_only",
            "artifact_root": "artifacts/logs/t01",
            "evidence_paths": ["artifacts/logs/t01/cargo-test.log", 123],
        }

        self.assert_rejects_payload(payload, "output_firewall.evidence_paths")

    def test_rejects_intent_contract_context_budget_ratios_out_of_order(self):
        payload = self.nested_payload()
        payload["intent_contract"] = {
            "context_budget": {
                "window_tokens": 258400,
                "soft_stop_ratio": 0.7,
                "hard_stop_ratio": 0.65,
                "critical_stop_ratio": 0.75,
            }
        }

        self.assert_rejects_payload(payload, "intent_contract.context_budget ratios")

    def test_rejects_intent_contract_output_firewall_policy(self):
        payload = self.nested_payload()
        payload["intent_contract"] = {
            "output_firewall": {
                "raw_log_policy": "paste_raw_logs",
            }
        }

        self.assert_rejects_payload(payload, "intent_contract.output_firewall.raw_log_policy")

    def test_allows_legacy_queue_ledger_stale_base_record(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "legacy-ledger.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "execute_direct",
                    "queue_ledger": {"stale_base": True},
                },
                log_path,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(log_path.exists())

    def test_allows_documented_queue_ledger_list_record(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "ledger-list.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "execute_direct",
                    "queue_ledger": [
                        {
                            "item": "#117",
                            "type": "issue",
                            "remote_state": "open",
                        }
                    ],
                },
                log_path,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(record["queue_ledger"][0]["item"], "#117")

    def test_rejects_invalid_issue_to_pr_map_shape(self):
        payload = self.nested_payload()
        payload["queue_gate"]["issue_to_pr_map"] = [
            {"issue": 117, "status": "maybe_covered"},
        ]

        self.assert_rejects_payload(payload, "queue_gate.issue_to_pr_map.status")

    def test_rejects_invalid_queue_ledger_shape(self):
        payload = self.nested_payload()
        payload["queue_ledger"]["items_total"] = -1

        self.assert_rejects_payload(payload, "queue_ledger.items_total")

    def test_rejects_invalid_queue_ledger_list_entry_shape(self):
        payload = self.nested_payload()
        payload["queue_ledger"] = ["#117"]

        self.assert_rejects_payload(payload, "queue_ledger entries")

    def test_rejects_invalid_remote_closure_shape(self):
        payload = self.nested_payload()
        payload["remote_closure"]["open_prs"] = "none"

        self.assert_rejects_payload(payload, "remote_closure.open_prs")

    def test_rejects_invalid_connector_review_shape(self):
        payload = self.nested_payload()
        payload["connector_review"]["status"] = "skipped"

        self.assert_rejects_payload(payload, "connector_review.status")

    def test_rejects_invalid_lane_map_shape(self):
        payload = self.nested_payload()
        payload["lane_map"]["lanes"][0]["role"] = "owner"

        self.assert_rejects_payload(payload, "lane_map.lanes.role")

    def test_rejects_invalid_ci_wait_shape(self):
        payload = self.nested_payload()
        payload["ci_wait"]["pending_checks"] = "none"

        self.assert_rejects_payload(payload, "ci_wait.pending_checks")

    def test_rejects_invalid_review_loop_shape(self):
        payload = self.nested_payload()
        payload["review_loop"]["cycles"] = -1

        self.assert_rejects_payload(payload, "review_loop.cycles")

    def test_allow_extra_does_not_bypass_known_nested_validation(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "bad-extra-nested.jsonl"
            payload = self.nested_payload()
            payload["extra"] = {"debug": True}
            payload["connector_review"]["status"] = "skipped"

            result = self.run_script(payload, log_path, "--allow-extra")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("connector_review.status", result.stderr)
            self.assertFalse(log_path.exists())

    def test_runs_from_copied_installed_skill_path(self):
        with TemporaryDirectory() as temp_dir:
            installed_skill = Path(temp_dir) / "threads"
            shutil.copytree(ROOT / "skills" / "threads", installed_skill)
            copied_script = installed_skill / "scripts" / "append_run_log.py"
            log_path = Path(temp_dir) / "installed.jsonl"

            result = subprocess.run(
                [sys.executable, str(copied_script), "--path", str(log_path)],
                input=json.dumps({"skill": "threads", "mode": "plan_only"}),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(log_path.exists())

    def test_rejects_queue_gate_without_remote_refresh_owner(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "queue-missing-owner.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "plan_only",
                    "queue_gate": {"truth_level": "A"},
                    "remote_refresh": {
                        "origin_main_sha": "abc123",
                        "local_base_sha": "abc123",
                        "stale_base": False,
                        "policy": "continue",
                    },
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("remote_refresh.owner_lane", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_queue_gate_unknown_pr_classification(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "queue-pr-classification.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "plan_only",
                    "queue_gate": {
                        "truth_level": "A",
                        "pr_classification": [
                            {"PR": 1, "classification": "looks_good"},
                        ],
                    },
                    "remote_refresh": {
                        "owner_lane": "coordinator",
                        "origin_main_sha": "abc123",
                        "local_base_sha": "abc123",
                        "stale_base": False,
                        "policy": "continue",
                    },
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("queue_gate.pr_classification.classification", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_conflicting_top_level_and_queue_gate_truth_level(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "queue-truth-conflict.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "plan_only",
                    "truth_level": "A",
                    "queue_gate": {"truth_level": "B"},
                    "remote_refresh": {
                        "owner_lane": "coordinator",
                        "origin_main_sha": "abc123",
                        "local_base_sha": "abc123",
                        "stale_base": False,
                        "policy": "continue",
                    },
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("conflicting truth_level", result.stderr)
            self.assertFalse(log_path.exists())

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

    def test_rejects_unknown_native_subagents_value(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "native-enum.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "plan_only",
                    "native_subagents": "maybe",
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown native_subagents", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_unknown_spawn_requirement_value(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "spawn-enum.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "plan_only",
                    "spawn_requirement": "mandatory",
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown spawn_requirement", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_unknown_failure_code(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "failure-code.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "plan_only",
                    "failure_codes": ["made_up_failure"],
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown failure_codes", result.stderr)
            self.assertFalse(log_path.exists())

    def test_rejects_unknown_lane_role(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "lane-role.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "plan_only",
                    "lanes": [{"id": "x", "role": "boss"}],
                },
                log_path,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown lanes.role", result.stderr)
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

    def test_redacts_env_assignment_tokens_in_strings(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "env-token.jsonl"

            result = self.run_script(
                {
                    "skill": "threads",
                    "mode": "plan_only",
                    "notes": "ran API_TOKEN=super-secret-token command",
                },
                log_path,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertNotIn("super-secret-token", record["notes"])
            self.assertIn("API_TOKEN=[REDACTED]", record["notes"])

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

    def test_existing_log_file_permissions_are_tightened(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "existing.jsonl"
            log_path.write_text("", encoding="utf-8")
            log_path.chmod(0o644)

            result = self.run_script({"skill": "threads", "mode": "plan_only"}, log_path)

            self.assertEqual(result.returncode, 0, result.stderr)
            mode = stat.S_IMODE(log_path.stat().st_mode)
            self.assertEqual(mode, 0o600)

    def test_print_path_does_not_require_stdin(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "print-path.jsonl"

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--path", str(log_path), "--print-path"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(log_path))
            self.assertFalse(log_path.exists())

    def test_validate_only_does_not_append(self):
        with TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "validate-only.jsonl"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--path",
                    str(log_path),
                    "--validate-only",
                ],
                input=json.dumps({"skill": "threads", "mode": "plan_only"}),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertFalse(log_path.exists())


if __name__ == "__main__":
    unittest.main()
