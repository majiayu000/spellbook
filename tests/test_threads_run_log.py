import json
import os
import subprocess
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
                "authorization": "Bearer should-not-leak",
                "nested": {"api_key": "secret-value", "safe": "ok"},
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
            self.assertEqual(record["authorization"], "[REDACTED]")
            self.assertEqual(record["nested"]["api_key"], "[REDACTED]")
            self.assertEqual(record["nested"]["safe"], "ok")
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


if __name__ == "__main__":
    unittest.main()
