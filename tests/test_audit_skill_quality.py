import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AuditSkillQualityTests(unittest.TestCase):
    def test_missing_yaml_fails_search_and_audit_instead_of_using_empty_frontmatter(self):
        commands = [
            ["scripts/validate_skills.py", "search", "dashboard"],
            ["scripts/audit_skill_quality.py", "codex"],
        ]
        for command in commands:
            with self.subTest(command=command):
                result = subprocess.run(
                    [sys.executable, "-S", *command], cwd=ROOT,
                    text=True, capture_output=True, check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("requires PyYAML", result.stdout + result.stderr)
                self.assertNotIn("No skills match", result.stdout)
                self.assertNotIn("Audited 1 skill", result.stdout)

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
