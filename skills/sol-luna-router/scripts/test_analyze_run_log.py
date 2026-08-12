#!/usr/bin/env python3
"""Tests for analyze_run_log.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("analyze_run_log.py")
SPEC = importlib.util.spec_from_file_location("analyze_run_log", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load {SCRIPT}")
ANALYZER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ANALYZER
SPEC.loader.exec_module(ANALYZER)


class AnalyzeRunLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sol-luna-analysis-test-")
        self.path = Path(self.temp_dir.name) / "runs.jsonl"
        self.sessions_root = Path(self.temp_dir.name) / "sessions"
        self.rate_card = SCRIPT.parent.parent / "references" / "rate-card-2026-08-05.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_records(self, *records: dict[str, object]) -> None:
        self.path.write_text(
            "".join(json.dumps(record) + "\n" for record in records),
            encoding="utf-8",
        )

    def write_session(
        self,
        session_id: str,
        *snapshots: dict[str, int] | tuple[str, dict[str, int]],
        filename: str | None = None,
    ) -> Path:
        session_path = self.sessions_root / "2026" / "08" / "12" / (
            filename or f"rollout-{session_id}.jsonl"
        )
        session_path.parent.mkdir(parents=True, exist_ok=True)
        records: list[dict[str, object]] = [
            {
                "type": "session_meta",
                "payload": {
                    "id": session_id,
                    "cwd": "/private/project",
                    "instructions": "private prompt text must not appear in reports",
                },
            }
        ]
        for index, snapshot in enumerate(snapshots):
            if isinstance(snapshot, tuple):
                timestamp, usage = snapshot
            else:
                timestamp = f"2026-08-12T00:0{index}:00Z"
                usage = snapshot
            records.append(
                {
                    "timestamp": timestamp,
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {"total_token_usage": usage},
                    },
                }
            )
        session_path.write_text(
            "".join(json.dumps(record) + "\n" for record in records),
            encoding="utf-8",
        )
        return session_path

    def test_summary_joins_latest_evaluation_and_reports_quality_cost(self) -> None:
        self.write_records(
            {
                "record_type": "run",
                "run_id": "run-1",
                "command": "run",
                "status": "success",
                "duration_seconds": 8,
                "warning_count": 0,
                "usage": {"input_tokens": 100, "cached_input_tokens": 40, "output_tokens": 20},
            },
            {
                "record_type": "run",
                "run_id": "run-2",
                "command": "resume",
                "status": "success",
                "duration_seconds": 12,
                "warning_count": 1,
                "usage": {"input_tokens": 60, "cached_input_tokens": 30, "output_tokens": 10},
            },
            {
                "record_type": "run",
                "run_id": "run-3",
                "command": "run",
                "status": "failed",
                "duration_seconds": 30,
                "failure_code": "timeout",
            },
            {"record_type": "evaluation", "run_id": "run-1", "outcome": "needs_correction"},
            {
                "record_type": "evaluation",
                "run_id": "run-1",
                "outcome": "verified",
                "checks_passed": 2,
                "checks_failed": 0,
            },
            {
                "record_type": "evaluation",
                "run_id": "run-2",
                "outcome": "verified",
                "checks_passed": 1,
                "checks_failed": 0,
            },
        )

        summary = ANALYZER.summarize(self.path)

        self.assertEqual(summary["runs_total"], 3)
        self.assertEqual(summary["reliability"]["success_rate"], 0.6667)
        self.assertEqual(summary["reliability"]["failure_codes"], {"timeout": 1})
        self.assertEqual(summary["quality"]["evaluated_runs"], 2)
        self.assertEqual(summary["quality"]["verified_rate_among_evaluated_successes"], 1.0)
        self.assertEqual(summary["quality"]["first_pass_verified_rate"], 1.0)
        self.assertEqual(summary["quality"]["verified_check_evidence_coverage"], 1.0)
        self.assertEqual(summary["quality"]["checks_passed"], 3)
        self.assertEqual(summary["efficiency"]["resume_runs"], 1)
        self.assertEqual(summary["efficiency"]["token_scope"], "luna_worker_only")
        self.assertEqual(summary["efficiency"]["token_totals"]["input_tokens"], 160)
        self.assertEqual(summary["efficiency"]["median_duration_seconds"], 12.0)
        self.assertEqual(summary["integrity"]["evaluation_overwrites"], 1)

    def test_missing_log_reports_zero_sample_without_inventing_rates(self) -> None:
        summary = ANALYZER.summarize(self.path)

        self.assertFalse(summary["source_exists"])
        self.assertEqual(summary["runs_total"], 0)
        self.assertIsNone(summary["reliability"]["success_rate"])
        self.assertIsNone(summary["quality"]["verified_rate_among_evaluated_successes"])

    def test_invalid_jsonl_fails_closed(self) -> None:
        self.path.write_text("not-json\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "invalid JSONL"):
            ANALYZER.summarize(self.path)

    def test_worker_only_cost_uses_uncached_and_cached_input_separately(self) -> None:
        self.write_records(
            {
                "record_type": "run",
                "run_id": "run-cost",
                "command": "run",
                "status": "success",
                "usage": {
                    "input_tokens": 1_000_000,
                    "cached_input_tokens": 200_000,
                    "output_tokens": 100_000,
                },
            }
        )

        summary = ANALYZER.summarize(self.path, rate_card_path=self.rate_card)

        cost = summary["cost"]
        self.assertEqual(cost["worker_credits"], 7.1)
        self.assertIsNone(cost["commander_credits"])
        self.assertIsNone(cost["total_credits"])
        self.assertEqual(cost["estimate_scope"], "worker_only")
        self.assertTrue(cost["rate_card"]["historical_estimate"])
        self.assertEqual(cost["rate_card"]["as_of"], "2026-08-05")

    def test_failed_run_with_exact_usage_is_costed(self) -> None:
        self.write_records(
            {
                "record_type": "run",
                "run_id": "run-failed-with-usage",
                "command": "run",
                "status": "failed",
                "failure_code": "codex_exit",
                "usage": {
                    "input_tokens": 1_000_000,
                    "cached_input_tokens": 200_000,
                    "output_tokens": 100_000,
                },
            }
        )

        summary = ANALYZER.summarize(self.path, rate_card_path=self.rate_card)

        cost = summary["cost"]
        self.assertEqual(cost["worker_runs_total"], 1)
        self.assertEqual(cost["worker_runs_costed"], 1)
        self.assertEqual(cost["worker_runs_unresolved"], 0)
        self.assertEqual(cost["worker_cost_coverage"], 1.0)
        self.assertTrue(cost["worker_estimate_complete"])
        self.assertEqual(cost["worker_credits"], 7.1)

    def test_failed_run_without_usage_makes_totals_and_normalized_metrics_incomplete(self) -> None:
        usage = {
            "input_tokens": 1_000_000,
            "cached_input_tokens": 200_000,
            "output_tokens": 100_000,
        }
        self.write_records(
            {
                "record_type": "run",
                "run_id": "run-complete-worker",
                "command": "run",
                "status": "success",
                "parent_session_id": "parent-worker-gap",
                "started_at": "2026-08-12T10:00:00Z",
                "completed_at": "2026-08-12T10:10:00Z",
                "usage": usage,
            },
            {
                "record_type": "run",
                "run_id": "run-missing-worker",
                "command": "run",
                "status": "failed",
                "failure_code": "codex_exit",
                "parent_session_id": "parent-worker-gap",
                "started_at": "2026-08-12T10:11:00Z",
                "completed_at": "2026-08-12T10:20:00Z",
            },
            {
                "record_type": "evaluation",
                "run_id": "run-complete-worker",
                "outcome": "verified",
                "checks_passed": 1,
                "checks_failed": 0,
            },
        )
        self.write_session(
            "parent-worker-gap",
            (
                "2026-08-12T09:59:00Z",
                {"input_tokens": 100, "cached_input_tokens": 10, "output_tokens": 20},
            ),
            (
                "2026-08-12T10:10:30Z",
                {"input_tokens": 500, "cached_input_tokens": 50, "output_tokens": 60},
            ),
            (
                "2026-08-12T10:21:00Z",
                {
                    "input_tokens": 1_000_100,
                    "cached_input_tokens": 100_010,
                    "output_tokens": 100_020,
                },
            ),
        )

        summary = ANALYZER.summarize(
            self.path,
            rate_card_path=self.rate_card,
            codex_sessions_root=self.sessions_root,
        )

        cost = summary["cost"]
        quality = summary["quality"]
        self.assertEqual(cost["worker_runs_total"], 2)
        self.assertEqual(cost["worker_runs_costed"], 1)
        self.assertEqual(cost["worker_runs_unresolved"], 1)
        self.assertEqual(cost["worker_cost_coverage"], 0.5)
        self.assertFalse(cost["worker_estimate_complete"])
        self.assertEqual(cost["worker_unresolved_usage_reasons"], {"missing_usage": 1})
        self.assertEqual(cost["commander_window_credits"], 188.75)
        self.assertIsNone(cost["total_credits"])
        self.assertFalse(cost["total_estimate_complete"])
        self.assertEqual(
            quality["normalized_credit_scope"],
            "incomplete_worker_usage_coverage",
        )
        self.assertIsNone(quality["worker_credits_per_verified_run"])
        self.assertIsNone(quality["credits_per_verified_run"])
        self.assertIsNone(quality["commander_credit_share"])

    def test_parent_join_uses_bounded_window_delta_and_reports_separate_costs(self) -> None:
        self.write_records(
            {
                "record_type": "run",
                "run_id": "run-parent",
                "command": "run",
                "status": "success",
                "parent_session_id": "parent-1",
                "started_at": "2026-08-12T10:00:00Z",
                "completed_at": "2026-08-12T10:10:00Z",
                "usage": {
                    "input_tokens": 1_000_000,
                    "cached_input_tokens": 200_000,
                    "output_tokens": 100_000,
                },
            }
        )
        self.write_session(
            "parent-1",
            (
                "2026-08-12T09:59:00Z",
                {"input_tokens": 100, "cached_input_tokens": 10, "output_tokens": 20},
            ),
            (
                "2026-08-12T10:11:00Z",
                {
                    "input_tokens": 1_000_100,
                    "cached_input_tokens": 100_010,
                    "output_tokens": 100_020,
                },
            ),
        )

        summary = ANALYZER.summarize(
            self.path,
            rate_card_path=self.rate_card,
            codex_sessions_root=self.sessions_root,
        )

        join = summary["parent_session_join"]
        cost = summary["cost"]
        self.assertEqual(join["matched_parent_sessions"], 1)
        self.assertEqual(join["attribution_scope"], "union_of_merged_run_windows")
        self.assertEqual(join["parent_session_coverage"], 1.0)
        self.assertEqual(join["commander_window_token_totals"]["input_tokens"], 1_000_000)
        self.assertEqual(cost["worker_credits"], 7.1)
        self.assertEqual(cost["commander_credits"], 188.75)
        self.assertEqual(cost["commander_window_credits"], 188.75)
        self.assertEqual(cost["total_credits"], 195.85)
        self.assertTrue(cost["total_estimate_complete"])
        self.assertAlmostEqual(summary["quality"]["commander_credit_share"], 188.75 / 195.85)

    def test_shared_parent_is_counted_once_and_duplicate_references_are_visible(self) -> None:
        usage = {
            "input_tokens": 1_000_000,
            "cached_input_tokens": 200_000,
            "output_tokens": 100_000,
        }
        self.write_records(
            {
                "record_type": "run",
                "run_id": "run-shared-1",
                "command": "run",
                "status": "success",
                "parent_session_id": "parent-shared",
                "started_at": "2026-08-12T10:00:00Z",
                "completed_at": "2026-08-12T10:10:00Z",
                "usage": usage,
            },
            {
                "record_type": "run",
                "run_id": "run-shared-2",
                "command": "resume",
                "status": "success",
                "parent_session_id": "parent-shared",
                "started_at": "2026-08-12T10:05:00Z",
                "completed_at": "2026-08-12T10:15:00Z",
                "usage": usage,
            },
        )
        self.write_session(
            "parent-shared",
            (
                "2026-08-12T09:59:00Z",
                {"input_tokens": 100, "cached_input_tokens": 10, "output_tokens": 20},
            ),
            (
                "2026-08-12T10:16:00Z",
                {
                    "input_tokens": 1_000_100,
                    "cached_input_tokens": 100_010,
                    "output_tokens": 100_020,
                },
            ),
        )

        summary = ANALYZER.summarize(
            self.path,
            rate_card_path=self.rate_card,
            codex_sessions_root=self.sessions_root,
        )

        join = summary["parent_session_join"]
        cost = summary["cost"]
        self.assertEqual(join["shared_parent_sessions"], 1)
        self.assertEqual(join["duplicate_parent_references"], 1)
        self.assertEqual(cost["worker_credits"], 14.2)
        self.assertEqual(cost["commander_credits"], 188.75)
        self.assertEqual(cost["total_credits"], 202.95)

    def test_missing_parent_is_visible_and_total_is_marked_incomplete(self) -> None:
        self.write_records(
            {
                "record_type": "run",
                "run_id": "run-missing-parent",
                "command": "run",
                "status": "success",
                "parent_session_id": "parent-missing",
                "started_at": "2026-08-12T10:00:00Z",
                "completed_at": "2026-08-12T10:10:00Z",
                "usage": {
                    "input_tokens": 1_000_000,
                    "cached_input_tokens": 0,
                    "output_tokens": 0,
                },
            }
        )
        self.sessions_root.mkdir(parents=True)

        summary = ANALYZER.summarize(
            self.path,
            rate_card_path=self.rate_card,
            codex_sessions_root=self.sessions_root,
        )

        join = summary["parent_session_join"]
        cost = summary["cost"]
        self.assertEqual(join["missing_parent_sessions"], 1)
        self.assertEqual(join["unresolved_parent_sessions"], 1)
        self.assertEqual(join["parent_session_coverage"], 0.0)
        self.assertEqual(cost["commander_credits"], 0)
        self.assertIsNone(cost["total_credits"])
        self.assertFalse(cost["total_estimate_complete"])
        self.assertEqual(
            summary["quality"]["normalized_credit_scope"],
            "incomplete_commander_window_coverage",
        )
        self.assertEqual(summary["quality"]["worker_credits_per_verified_run"], None)
        self.assertIsNone(summary["quality"]["credits_per_verified_run"])

    def test_ambiguous_parent_is_visible_and_not_costed(self) -> None:
        self.write_records(
            {
                "record_type": "run",
                "run_id": "run-ambiguous-parent",
                "command": "run",
                "status": "success",
                "parent_session_id": "parent-ambiguous",
                "started_at": "2026-08-12T10:00:00Z",
                "completed_at": "2026-08-12T10:10:00Z",
                "usage": {
                    "input_tokens": 1_000_000,
                    "cached_input_tokens": 0,
                    "output_tokens": 0,
                },
            }
        )
        usage = {
            "input_tokens": 1_000_100,
            "cached_input_tokens": 100_010,
            "output_tokens": 100_020,
        }
        baseline = {
            "input_tokens": 100,
            "cached_input_tokens": 10,
            "output_tokens": 20,
        }
        self.write_session(
            "parent-ambiguous",
            ("2026-08-12T09:59:00Z", baseline),
            ("2026-08-12T10:11:00Z", usage),
            filename="one.jsonl",
        )
        self.write_session(
            "parent-ambiguous",
            ("2026-08-12T09:59:00Z", baseline),
            ("2026-08-12T10:11:00Z", usage),
            filename="two.jsonl",
        )

        summary = ANALYZER.summarize(
            self.path,
            rate_card_path=self.rate_card,
            codex_sessions_root=self.sessions_root,
        )

        join = summary["parent_session_join"]
        self.assertEqual(join["ambiguous_parent_sessions"], 1)
        self.assertEqual(join["unresolved_by_reason"], {"ambiguous_session_file": 1})
        self.assertEqual(summary["cost"]["commander_credits"], 0)

    def test_pre_and_post_unrelated_parent_usage_is_excluded(self) -> None:
        self.write_records(
            {
                "record_type": "run",
                "run_id": "run-window-boundary",
                "command": "run",
                "status": "success",
                "parent_session_id": "parent-boundary",
                "started_at": "2026-08-12T10:00:00Z",
                "completed_at": "2026-08-12T10:10:00Z",
                "usage": {
                    "input_tokens": 1_000_000,
                    "cached_input_tokens": 200_000,
                    "output_tokens": 100_000,
                },
            }
        )
        self.write_session(
            "parent-boundary",
            (
                "2026-08-12T08:00:00Z",
                {"input_tokens": 10, "cached_input_tokens": 1, "output_tokens": 2},
            ),
            (
                "2026-08-12T09:59:00Z",
                {"input_tokens": 100, "cached_input_tokens": 10, "output_tokens": 20},
            ),
            (
                "2026-08-12T10:11:00Z",
                {
                    "input_tokens": 1_000_100,
                    "cached_input_tokens": 100_010,
                    "output_tokens": 100_020,
                },
            ),
            (
                "2026-08-12T10:20:00Z",
                {
                    "input_tokens": 9_000_000,
                    "cached_input_tokens": 900_000,
                    "output_tokens": 900_000,
                },
            ),
        )

        summary = ANALYZER.summarize(
            self.path,
            rate_card_path=self.rate_card,
            codex_sessions_root=self.sessions_root,
        )

        self.assertEqual(summary["cost"]["commander_window_credits"], 188.75)
        self.assertEqual(
            summary["parent_session_join"]["commander_window_token_totals"]["input_tokens"],
            1_000_000,
        )

    def test_missing_baseline_makes_parent_window_unresolved(self) -> None:
        self.write_records(
            {
                "record_type": "run",
                "run_id": "run-no-baseline",
                "command": "run",
                "status": "success",
                "parent_session_id": "parent-no-baseline",
                "started_at": "2026-08-12T10:00:00Z",
                "completed_at": "2026-08-12T10:10:00Z",
                "usage": {
                    "input_tokens": 10,
                    "cached_input_tokens": 1,
                    "output_tokens": 2,
                },
            }
        )
        self.write_session(
            "parent-no-baseline",
            (
                "2026-08-12T10:01:00Z",
                {"input_tokens": 100, "cached_input_tokens": 10, "output_tokens": 20},
            ),
            (
                "2026-08-12T10:11:00Z",
                {"input_tokens": 200, "cached_input_tokens": 20, "output_tokens": 30},
            ),
        )

        summary = ANALYZER.summarize(
            self.path,
            rate_card_path=self.rate_card,
            codex_sessions_root=self.sessions_root,
        )

        join = summary["parent_session_join"]
        self.assertEqual(join["unresolved_by_reason"]["missing_baseline"], 1)
        self.assertEqual(join["parent_window_coverage"], 0.0)
        self.assertIsNone(summary["cost"]["total_credits"])

    def test_missing_endpoint_makes_parent_window_unresolved(self) -> None:
        self.write_records(
            {
                "record_type": "run",
                "run_id": "run-no-endpoint",
                "command": "run",
                "status": "success",
                "parent_session_id": "parent-no-endpoint",
                "started_at": "2026-08-12T10:00:00Z",
                "completed_at": "2026-08-12T10:10:00Z",
                "usage": {
                    "input_tokens": 10,
                    "cached_input_tokens": 1,
                    "output_tokens": 2,
                },
            }
        )
        self.write_session(
            "parent-no-endpoint",
            (
                "2026-08-12T09:59:00Z",
                {"input_tokens": 100, "cached_input_tokens": 10, "output_tokens": 20},
            ),
        )

        summary = ANALYZER.summarize(
            self.path,
            rate_card_path=self.rate_card,
            codex_sessions_root=self.sessions_root,
        )

        join = summary["parent_session_join"]
        self.assertEqual(join["unresolved_by_reason"]["missing_endpoint"], 1)
        self.assertEqual(join["parent_window_coverage"], 0.0)
        self.assertIsNone(summary["cost"]["total_credits"])

    def test_counter_decrease_or_reset_makes_parent_window_unresolved(self) -> None:
        self.write_records(
            {
                "record_type": "run",
                "run_id": "run-counter-reset",
                "command": "run",
                "status": "success",
                "parent_session_id": "parent-counter-reset",
                "started_at": "2026-08-12T10:00:00Z",
                "completed_at": "2026-08-12T10:10:00Z",
                "usage": {
                    "input_tokens": 10,
                    "cached_input_tokens": 1,
                    "output_tokens": 2,
                },
            }
        )
        self.write_session(
            "parent-counter-reset",
            (
                "2026-08-12T09:59:00Z",
                {"input_tokens": 100, "cached_input_tokens": 10, "output_tokens": 20},
            ),
            (
                "2026-08-12T10:05:00Z",
                {"input_tokens": 90, "cached_input_tokens": 9, "output_tokens": 19},
            ),
            (
                "2026-08-12T10:11:00Z",
                {"input_tokens": 120, "cached_input_tokens": 12, "output_tokens": 24},
            ),
        )

        summary = ANALYZER.summarize(
            self.path,
            rate_card_path=self.rate_card,
            codex_sessions_root=self.sessions_root,
        )

        join = summary["parent_session_join"]
        self.assertEqual(join["unresolved_by_reason"]["counter_decrease_or_reset"], 1)
        self.assertEqual(summary["cost"]["commander_window_credits"], 0)
        self.assertIsNone(summary["cost"]["total_credits"])

    def test_partial_parent_windows_expose_partial_components_but_no_total_scope_metrics(self) -> None:
        run_usage = {
            "input_tokens": 1_000_000,
            "cached_input_tokens": 200_000,
            "output_tokens": 100_000,
        }
        self.write_records(
            {
                "record_type": "run",
                "run_id": "run-partial-resolved",
                "command": "run",
                "status": "success",
                "parent_session_id": "parent-resolved",
                "started_at": "2026-08-12T10:00:00Z",
                "completed_at": "2026-08-12T10:10:00Z",
                "usage": run_usage,
            },
            {
                "record_type": "run",
                "run_id": "run-partial-missing",
                "command": "run",
                "status": "success",
                "parent_session_id": "parent-missing-partial",
                "started_at": "2026-08-12T11:00:00Z",
                "completed_at": "2026-08-12T11:10:00Z",
                "usage": run_usage,
            },
            {
                "record_type": "evaluation",
                "run_id": "run-partial-resolved",
                "outcome": "verified",
                "checks_passed": 1,
                "checks_failed": 0,
            },
        )
        self.write_session(
            "parent-resolved",
            (
                "2026-08-12T09:59:00Z",
                {"input_tokens": 100, "cached_input_tokens": 10, "output_tokens": 20},
            ),
            (
                "2026-08-12T10:11:00Z",
                {
                    "input_tokens": 1_000_100,
                    "cached_input_tokens": 100_010,
                    "output_tokens": 100_020,
                },
            ),
        )

        summary = ANALYZER.summarize(
            self.path,
            rate_card_path=self.rate_card,
            codex_sessions_root=self.sessions_root,
        )

        self.assertEqual(summary["cost"]["commander_window_credits"], 188.75)
        self.assertIsNone(summary["cost"]["total_credits"])
        self.assertIsNone(summary["quality"]["credits_per_verified_run"])
        self.assertEqual(
            summary["quality"]["worker_credits_per_verified_run"],
            14.2,
        )
        self.assertEqual(summary["parent_session_join"]["parent_window_coverage"], 0.5)

    def test_both_worker_and_commander_coverage_are_named_in_normalized_scope(self) -> None:
        self.write_records(
            {
                "record_type": "run",
                "run_id": "run-both-incomplete",
                "command": "run",
                "status": "failed",
                "failure_code": "codex_exit",
                "parent_session_id": "parent-both-incomplete",
                "started_at": "2026-08-12T10:00:00Z",
                "completed_at": "2026-08-12T10:10:00Z",
            }
        )
        self.sessions_root.mkdir(parents=True)

        summary = ANALYZER.summarize(
            self.path,
            rate_card_path=self.rate_card,
            codex_sessions_root=self.sessions_root,
        )

        self.assertEqual(
            summary["quality"]["normalized_credit_scope"],
            "incomplete_worker_usage_and_commander_window_coverage",
        )

    def test_rate_card_rejects_malformed_or_negative_usage(self) -> None:
        invalid_usages = (
            {"input_tokens": "100", "cached_input_tokens": 0, "output_tokens": 1},
            {"input_tokens": 100, "cached_input_tokens": -1, "output_tokens": 1},
            {"input_tokens": 100, "cached_input_tokens": 101, "output_tokens": 1},
        )
        for index, usage in enumerate(invalid_usages):
            with self.subTest(index=index):
                self.write_records(
                    {
                        "record_type": "run",
                        "run_id": f"run-invalid-{index}",
                        "status": "success",
                        "usage": usage,
                    }
                )
                summary = ANALYZER.summarize(self.path, rate_card_path=self.rate_card)
                self.assertEqual(summary["cost"]["worker_runs_costed"], 0)
                self.assertEqual(summary["cost"]["worker_runs_unresolved"], 1)
                self.assertFalse(summary["cost"]["worker_estimate_complete"])

    def test_no_rate_card_preserves_non_estimating_backward_compatibility(self) -> None:
        self.write_records(
            {
                "record_type": "run",
                "run_id": "run-legacy",
                "status": "success",
                "usage": {
                    "input_tokens": -10,
                    "cached_input_tokens": "bad",
                    "output_tokens": 4,
                },
            }
        )

        summary = ANALYZER.summarize(self.path)

        self.assertNotIn("cost", summary)
        self.assertNotIn("parent_session_join", summary)
        self.assertEqual(summary["efficiency"]["token_totals"]["input_tokens"], 0)
        json.dumps(summary, ensure_ascii=False, sort_keys=True)

    def test_quality_normalized_metrics_use_available_credit_scope(self) -> None:
        self.write_records(
            {
                "record_type": "run",
                "run_id": "run-quality-1",
                "command": "run",
                "status": "success",
                "usage": {
                    "input_tokens": 1_000_000,
                    "cached_input_tokens": 200_000,
                    "output_tokens": 100_000,
                },
            },
            {
                "record_type": "run",
                "run_id": "run-quality-2",
                "command": "resume",
                "status": "success",
                "usage": {
                    "input_tokens": 500_000,
                    "cached_input_tokens": 0,
                    "output_tokens": 0,
                },
            },
            {
                "record_type": "evaluation",
                "run_id": "run-quality-1",
                "outcome": "verified",
                "checks_passed": 1,
                "checks_failed": 0,
            },
            {
                "record_type": "evaluation",
                "run_id": "run-quality-2",
                "outcome": "verified",
                "checks_passed": 1,
                "checks_failed": 0,
            },
        )

        summary = ANALYZER.summarize(self.path, rate_card_path=self.rate_card)

        quality = summary["quality"]
        self.assertEqual(summary["cost"]["worker_credits"], 9.6)
        self.assertEqual(quality["credits_per_verified_run"], 4.8)
        self.assertEqual(quality["credits_per_first_pass_verified_run"], 9.6)
        self.assertIsNone(quality["commander_credit_share"])


if __name__ == "__main__":
    unittest.main()
