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

    def test_defaults_to_project_local_log_path(self):
        with TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            (project_root / ".git").mkdir()
            expected_log = project_root.resolve() / ".codex" / "threads" / "run-log.jsonl"
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
