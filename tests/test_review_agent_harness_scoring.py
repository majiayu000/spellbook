import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from test_review_agent_harness import findings_document, run_script


class ReviewAgentHarnessScoringTests(unittest.TestCase):
    def validate_failure(self, document: dict[str, object]) -> str:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "findings.json"
            path.write_text(json.dumps(document) + "\n", encoding="utf-8")
            completed = run_script(
                "validate_findings.py", "--input", str(path), "--json", expect=1
            )
            return "\n".join(json.loads(completed.stdout)["errors"])

    def test_requires_exact_repository_before_scoring(self) -> None:
        document = findings_document()
        document["scope"]["snapshot"]["target_relation"] = "contains_nested_git_root"
        errors = self.validate_failure(document)
        self.assertIn("retarget the exact repository before scoring", errors)

    def test_requires_all_fifteen_stable_checks(self) -> None:
        document = findings_document()
        document["checks"].pop()
        errors = self.validate_failure(document)
        self.assertIn("checks must contain exactly 15 rows", errors)
        self.assertIn("later-validation", errors)

    def test_dimension_score_cannot_exceed_weakest_check_evidence(self) -> None:
        document = findings_document()
        task_contract = next(
            row for row in document["dimensions"] if row["id"] == "task-contract"
        )
        task_contract["score"] = 85
        errors = self.validate_failure(document)
        self.assertIn("task-contract.score exceeds evidence ceiling 84", errors)

    def test_confirmed_high_finding_requires_final_state_adversarial_run(self) -> None:
        document = findings_document()
        document["verification_runs"] = []
        errors = self.validate_failure(document)
        self.assertIn("requires a final-state adversarial verification run", errors)

    def test_primary_check_must_reverse_link_finding(self) -> None:
        document = findings_document()
        validate_again = next(
            row for row in document["checks"] if row["id"] == "validate-again"
        )
        validate_again["finding_refs"] = []
        errors = self.validate_failure(document)
        self.assertIn("primary check must reverse-link the finding id", errors)


if __name__ == "__main__":
    unittest.main()
