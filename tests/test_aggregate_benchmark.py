"""Synthetic file fixtures only; these tests do not run any model or skill."""

import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/skill-creator/scripts/aggregate_benchmark.py"
VIEWER = ROOT / "skills/skill-creator/eval-viewer/viewer.html"
spec = importlib.util.spec_from_file_location("aggregate_benchmark", SCRIPT)
aggregate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aggregate)


class BenchmarkTokenTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write_run(self, config="with_skill", number=1, timing=None,
                  grading_timing=None, legacy=False):
        root = self.root / "runs" if legacy else self.root
        run = root / "eval-1" / config / f"run-{number}"
        run.mkdir(parents=True)
        grading = {
            "summary": {"passed": 1, "failed": 0, "total": 1, "pass_rate": 1.0},
            "timing": grading_timing if grading_timing is not None else {},
            "execution_metrics": {"output_chars": 9000, "total_tool_calls": 2},
            "expectations": [],
        }
        (run / "grading.json").write_text(json.dumps(grading), encoding="utf-8")
        if timing is not None:
            (run / "timing.json").write_text(json.dumps(timing), encoding="utf-8")
        return run

    def benchmark(self):
        return aggregate.generate_benchmark(self.root, "synthetic-fixture")

    def test_sibling_tokens_are_read_with_nonzero_grading_duration(self):
        self.write_run(grading_timing={"total_duration_seconds": 12},
                       timing={"total_tokens": 123, "total_duration_seconds": 99})
        result = self.benchmark()["runs"][0]["result"]
        self.assertEqual(result["tokens"], 123)
        self.assertEqual(result["time_seconds"], 12)
        self.assertEqual(result["tool_calls"], 2)

    def test_grading_token_measurement_takes_precedence_including_zero(self):
        for tokens in (0, 17):
            with self.subTest(tokens=tokens):
                self.write_run(number=tokens + 1,
                               grading_timing={"total_tokens": tokens},
                               timing={"total_tokens": 123})
        values = [run["result"]["tokens"] for run in self.benchmark()["runs"]]
        self.assertEqual(values, [0, 17])

    def test_null_grading_tokens_fall_back_to_sibling_including_zero(self):
        self.write_run(grading_timing={"total_tokens": None},
                       timing={"total_tokens": 0})
        self.assertEqual(self.benchmark()["runs"][0]["result"]["tokens"], 0)

    def test_output_characters_never_substitute_for_missing_tokens(self):
        self.write_run()
        self.write_run(number=2, timing={"total_tokens": None})
        self.write_run(number=3, timing={"total_duration_seconds": 4})
        self.assertEqual([run["result"]["tokens"] for run in self.benchmark()["runs"]],
                         [None, None, None])

    def test_malformed_timing_warns_and_leaves_tokens_unknown(self):
        run = self.write_run(grading_timing={"total_duration_seconds": 12})
        (run / "timing.json").write_text("{invalid", encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = self.benchmark()["runs"][0]["result"]
        self.assertIsNone(result["tokens"])
        self.assertEqual(result["time_seconds"], 12)
        self.assertIn("timing.json", output.getvalue())

    def test_legacy_layout_still_reads_tokens_and_duration(self):
        self.write_run(legacy=True, timing={"total_tokens": 23, "total_duration_seconds": 4})
        result = self.benchmark()["runs"][0]["result"]
        self.assertEqual(result["tokens"], 23)
        self.assertEqual(result["time_seconds"], 4)

    def test_complete_measurements_keep_stats_and_signed_string_delta(self):
        self.write_run(timing={"total_tokens": 0})
        self.write_run(number=2, timing={"total_tokens": 20})
        self.write_run(config="without_skill", timing={"total_tokens": 4})
        benchmark = self.benchmark()
        self.assertEqual(benchmark["run_summary"]["with_skill"]["tokens"],
                         {"mean": 10.0, "stddev": 14.1421, "min": 0, "max": 20})
        self.assertEqual(benchmark["run_summary"]["delta"]["tokens"], "+6")
        self.assertIn("| Tokens | 10 ± 14 | 4 ± 0 | +6 |",
                      aggregate.generate_markdown(benchmark))

    def test_incomplete_configuration_keeps_runs_but_has_unknown_token_stats(self):
        self.write_run(timing={"total_tokens": 20})
        self.write_run(number=2)
        self.write_run(config="without_skill", timing={"total_tokens": 0})
        benchmark = self.benchmark()
        self.assertEqual([run["result"]["tokens"] for run in benchmark["runs"]],
                         [20, None, 0])
        self.assertEqual(benchmark["run_summary"]["with_skill"]["tokens"],
                         dict.fromkeys(("mean", "stddev", "min", "max")))
        self.assertEqual(benchmark["run_summary"]["with_skill"]["pass_rate"]["mean"], 1)
        self.assertIsNone(benchmark["run_summary"]["delta"]["tokens"])
        markdown = aggregate.generate_markdown(benchmark)
        self.assertIn("| Tokens | N/A | 0 ± 0 | N/A |", markdown)
        self.assertIn("at least one loaded run", markdown)

    def test_empty_configuration_or_no_baseline_has_no_token_delta(self):
        (self.root / "eval-1/without_skill/run-1").mkdir(parents=True)
        self.write_run(timing={"total_tokens": 0})
        with contextlib.redirect_stdout(io.StringIO()):
            benchmark = self.benchmark()
        self.assertIsNone(benchmark["run_summary"]["without_skill"]["tokens"]["mean"])
        self.assertIsNone(benchmark["run_summary"]["delta"]["tokens"])
        for results in ({}, {"with_skill": [{"pass_rate": 1, "time_seconds": 1, "tokens": 0}]}):
            with self.subTest(results=results):
                self.assertIsNone(aggregate.aggregate_results(results)["delta"]["tokens"])

    def test_cli_emits_json_null_and_readable_markdown(self):
        self.write_run()
        completed = subprocess.run([sys.executable, str(SCRIPT), str(self.root)],
                                   capture_output=True, text=True, check=True)
        result = json.loads((self.root / "benchmark.json").read_text(encoding="utf-8"))
        self.assertIsNone(result["runs"][0]["result"]["tokens"])
        self.assertIn("| Tokens | N/A | N/A | N/A |",
                      (self.root / "benchmark.md").read_text(encoding="utf-8"))
        self.assertIn("Generated:", completed.stdout)

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed to exercise the viewer")
    def test_viewer_renders_unknown_and_measured_zero_tokens(self):
        self.write_run()
        self.write_run(config="without_skill", timing={"total_tokens": 0})
        benchmark = self.benchmark()
        # Run the actual renderer with a minimal DOM; no browser or network required.
        source = VIEWER.read_text(encoding="utf-8")
        renderer = source.split("    // ---- Benchmark rendering ----", 1)[1]
        renderer = renderer.split("    // ---- Start ----", 1)[0]
        program = (
            "const elements = {};\n"
            "const document = {getElementById: id => elements[id] ||= {style: {}}};\n"
            "const escapeHtml = value => String(value);\n"
            f"const EMBEDDED_DATA = {{benchmark: {json.dumps(benchmark)}}};\n"
            + renderer + "\nrenderBenchmark();\nconsole.log(elements['benchmark-content'].innerHTML);\n"
        )
        completed = subprocess.run(["node", "-e", program], capture_output=True,
                                   text=True, check=True)
        self.assertIn("<strong>Tokens</strong></td><td>—</td><td>0.0 ± 0.0</td>",
                      completed.stdout)


if __name__ == "__main__":
    unittest.main()
