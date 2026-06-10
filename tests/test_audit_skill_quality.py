import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AuditSkillQualityTests(unittest.TestCase):
    def test_api_backend_skills_require_operating_contract_signal(self):
        result = subprocess.run(
            [sys.executable, "scripts/audit_skill_quality.py", "auth-security"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("auth-security [operating-contract]", result.stdout)


if __name__ == "__main__":
    unittest.main()
