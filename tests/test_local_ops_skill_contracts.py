from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LocalOpsSkillContractsTest(unittest.TestCase):
    def read_skill(self, name: str) -> str:
        return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")

    def test_app_user_story_qa_defaults_to_report_only(self) -> None:
        contract = self.read_skill("app-user-story-qa")
        for required in (
            "`report_only` is the default",
            "`apply_fixes` requires the current user request",
            "generic request to \"test everything\" do not authorize fixes",
            "In `report_only`",
        ):
            self.assertIn(required, contract)

        self.assertNotIn(
            "document failures, and fix narrow in-scope",
            contract,
        )

    def test_codex_log_guard_separates_protection_and_cleanup(self) -> None:
        contract = self.read_skill("codex-log-guard")
        for required in (
            "`diagnose_only` is the default",
            "selects `protect`, not `cleanup`",
            "Do not delete or vacuum rows",
            "successful `PRAGMA quick_check`",
            "Protection success does not authorize cleanup",
            "CODEX_LOG_DB",
            "refusing unexpected Codex log database path",
        ):
            self.assertIn(required, contract)

        self.assertNotIn("db=~/.codex/logs_2.sqlite", contract)
        self.assertNotIn('db="$HOME/.codex/logs_2.sqlite"', contract)


if __name__ == "__main__":
    unittest.main()
