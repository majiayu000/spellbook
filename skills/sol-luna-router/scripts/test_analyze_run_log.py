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

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_records(self, *records: dict[str, object]) -> None:
        self.path.write_text(
            "".join(json.dumps(record) + "\n" for record in records),
            encoding="utf-8",
        )

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


if __name__ == "__main__":
    unittest.main()
