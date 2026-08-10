import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from test_review_agent_harness import boundary_args, findings_document, reference


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "review-agent-harness" / "scripts"


def run_script(name: str, *args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != expect:
        raise AssertionError(
            f"{name} returned {completed.returncode}, expected {expect}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


class ReviewAgentHarnessBoundaryTests(unittest.TestCase):
    def write_json(self, path: Path, value: object) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")

    def test_all_malformed_or_unsupported_session_is_unobserved(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "target"
            target.mkdir()
            session = root / "session.jsonl"
            session.write_text(
                "not-json\n[]\n{\"unknown\": true}\n"
                "{\"type\":\"response_item\",\"payload\":{\"type\":\"message\","
                "\"role\":\"user\",\"content\":{\"unexpected\":1}}}\n"
                "{\"type\":\"response_item\",\"payload\":{\"type\":\"function_call\"}}\n",
                encoding="utf-8",
            )
            completed = run_script(
                "collect_evidence.py",
                "--target", str(target),
                "--mode", "episode",
                "--provider", "codex",
                "--session-file", str(session),
                *boundary_args(),
            )
            sessions = json.loads(completed.stdout)["sessions"]
            self.assertEqual(sessions["status"], "unobserved")
            self.assertEqual(sessions["sessions"][0]["evidence_state"], "unobserved")
            self.assertEqual(sessions["summary"]["malformed_lines"], 1)
            self.assertEqual(sessions["summary"]["unsupported_lines"], 4)

    def test_depth_limit_and_external_manifest_symlinks_are_visible(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "target"
            deep = target.joinpath(*("level" for _ in range(8)))
            deep.mkdir(parents=True)
            (deep / "AGENTS.md").write_text("outside scan depth\n", encoding="utf-8")
            outside = root / "outside-package.json"
            outside.write_text(json.dumps({"scripts": {"secret": "outside"}}), encoding="utf-8")
            (target / "package.json").symlink_to(outside)

            completed = run_script(
                "collect_evidence.py", "--target", str(target), "--mode", "static", *boundary_args()
            )
            static = json.loads(completed.stdout)["static"]
            self.assertEqual(static["status"], "constrained")
            self.assertGreater(static["scan"]["depth_limited_directory_count"], 0)
            self.assertEqual(static["project"]["package_scripts"]["status"], "unavailable")
            self.assertNotIn('"secret": "outside"', completed.stdout)

    def test_nested_git_parent_is_constrained_and_not_scanned_as_the_repo(self) -> None:
        with TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir) / "workspace-parent"
            nested = parent / "actual-repo"
            nested.mkdir(parents=True)
            subprocess.run(["git", "init", "-q"], cwd=nested, check=True)
            (nested / "AGENTS.md").write_text("# Nested instructions\n", encoding="utf-8")

            completed = run_script(
                "collect_evidence.py", "--target", str(parent), "--mode", "static", *boundary_args()
            )
            evidence = json.loads(completed.stdout)
            self.assertEqual(evidence["scope"]["snapshot"]["target_relation"], "contains_nested_git_root")
            self.assertEqual(evidence["static"]["status"], "constrained")
            self.assertEqual(evidence["static"]["root_resolution"]["nested_git_roots"], ["actual-repo"])
            self.assertEqual(evidence["static"]["agent_assets"]["instructions"]["items"], [])

    def test_renderer_rejects_warn_findings_and_mismatched_evidence(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            findings_path = root / "findings.json"
            evidence_path = root / "evidence.json"
            document = findings_document()
            document["findings"][0]["verification_state"] = "unverified"
            self.write_json(findings_path, document)
            failed = run_script(
                "render_report.py",
                "--findings", str(findings_path),
                "--out", str(root / "reports"),
                "--run-id", "warn-run",
                expect=1,
            )
            self.assertFalse((root / "reports" / "warn-run").exists())

            document = findings_document()
            self.write_json(findings_path, document)
            evidence = {
                "schema_version": 1,
                "kind": "agent-harness-evidence",
                "scope": {
                    "target": "fixture-project",
                    "snapshot": {
                        "baseline": "current_checkout",
                        "target_relation": "exact_git_root",
                    },
                    "mode": "static",
                    "provider": None,
                    "locale": "en",
                    "decision": document["scope"]["decision"],
                    "acceptance_boundary": document["scope"]["acceptance_boundary"],
                    "output_mode": "durable",
                },
                "evidence_boundary": {
                    "included": ["invented-source"],
                    "excluded": document["evidence_boundary"]["excluded"],
                    "unavailable": document["evidence_boundary"]["unavailable"],
                    "session_source_policy": "explicit-files-or-roots-only",
                },
                "static": {"status": "available"},
                "sessions": {"status": "not_authorized"},
            }
            self.write_json(evidence_path, evidence)
            failed = run_script(
                "render_report.py",
                "--findings", str(findings_path),
                "--evidence", str(evidence_path),
                "--out", str(root / "reports"),
                "--run-id", "mismatch-run",
                expect=1,
            )
            self.assertIn("evidence.static.scan", failed.stderr)
            self.assertIn("evidence.evidence_boundary.included", failed.stderr)
            self.assertFalse((root / "reports" / "mismatch-run").exists())

    def test_renderer_accepts_collector_compact_unobserved_session(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "fixture-project"
            target.mkdir()
            document = findings_document()
            document["scope"]["mode"] = "episode"
            document["scope"]["snapshot"] = {
                "baseline": "filesystem_state",
                "target_relation": "non_git_directory",
            }
            document["evidence_boundary"]["unavailable"] = ["session-evidence:unobserved"]
            findings_path = root / "findings.json"
            evidence_path = root / "evidence.json"
            self.write_json(findings_path, document)
            collected = run_script(
                "collect_evidence.py",
                "--target", str(target),
                "--mode", "episode",
                *boundary_args(output_mode="durable"),
            )
            evidence_path.write_text(collected.stdout, encoding="utf-8")
            rendered = run_script(
                "render_report.py",
                "--findings", str(findings_path),
                "--evidence", str(evidence_path),
                "--out", str(root / "reports"),
                "--run-id", "unobserved-run",
                "--json",
            )
            self.assertEqual(json.loads(rendered.stdout)["status"], "pass")

    def test_validator_rejects_json_secrets_and_html_destinations(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "findings.json"
            document = findings_document()
            document["findings"][0]["consequence"] = '{"api_key": "supersecret"}'
            self.write_json(path, document)
            failed = run_script("validate_findings.py", "--input", str(path), "--json", expect=1)
            self.assertIn("secret-assignment", failed.stdout)

            document = findings_document()
            document["findings"][0]["consequence"] = '<img src="https://internal.example/private">'
            self.write_json(path, document)
            failed = run_script("validate_findings.py", "--input", str(path), "--json", expect=1)
            self.assertIn("html-destination", failed.stdout)

            for private_text in (
                "[private][run]\n[run]: https://internal.example/run/1",
                "<https://internal.example/run/1>",
                "https://internal.example/run/1",
                '<object data="https://internal.example/run/1">',
                '<meta http-equiv="refresh" content="0;url=https://internal.example/run/1">',
            ):
                document = findings_document()
                document["findings"][0]["consequence"] = private_text
                self.write_json(path, document)
                failed = run_script("validate_findings.py", "--input", str(path), "--json", expect=1)
                self.assertIn("destination", failed.stdout)

    def test_outcome_supported_requires_five_bound_evidence_purposes(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "findings.json"
            document = findings_document()
            learning = next(row for row in document["dimensions"] if row["id"] == "learning-retention")
            learning.update({
                "status": "healthy",
                "evidence_state": "outcome_supported",
                "confidence": "high",
                "score": 94,
                "score_rationale": "All three checks were exercised and later validation has outcome evidence.",
                "summary": "A comparable later Episode improved without regression.",
                "evidence_refs": [reference()],
            })
            for check in document["checks"]:
                if check["dimension"] == "learning-retention":
                    check.update({
                        "status": "healthy",
                        "evidence_state": (
                            "outcome_supported" if check["id"] == "later-validation" else "exercised"
                        ),
                        "confidence": "high",
                        "summary": "The lifecycle route is exercised with bounded evidence.",
                        "evidence_refs": [reference()],
                    })
            self.write_json(path, document)
            failed = run_script("validate_findings.py", "--input", str(path), "--json", expect=1)
            self.assertIn("missing purposes", failed.stdout)

            learning["evidence_refs"] = [
                {**reference("session_fact", "episode:baseline"), "purpose": "baseline_episode", "comparison_basis": "same task class", "mechanism_category": "validation"},
                {**reference("session_fact", "episode:later"), "purpose": "later_episode", "comparison_basis": "same task class", "mechanism_category": "validation"},
                {**reference("policy", "AGENTS.md:10"), "purpose": "route_mapping"},
                {**reference("command", "targeted-outcome-check"), "purpose": "outcome_check"},
                {**reference("artifact", "guardrail-report"), "purpose": "guardrail_check"},
            ]
            document["scope"]["mode"] = "longitudinal"
            document["scope"]["snapshot"] = {
                "baseline": "filesystem_state",
                "target_relation": "non_git_directory",
            }
            document["scope"]["providers"] = ["codex"]
            document["evidence_boundary"]["included"] = [
                "repository-static-evidence",
                "explicit-session-sources",
            ]
            document["evidence_boundary"]["unavailable"] = []
            self.write_json(path, document)
            target = Path(temp_dir) / "fixture-project"
            target.mkdir()
            session = Path(temp_dir) / "session.jsonl"
            session.write_text(json.dumps({
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "name": "exec_command",
                    "arguments": json.dumps({"cmd": "pytest"}),
                },
            }) + "\n", encoding="utf-8")
            evidence_paths = []
            for role in ("baseline", "later"):
                collected = run_script(
                    "collect_evidence.py",
                    "--target", str(target),
                    "--mode", "longitudinal",
                    "--provider", "codex",
                    "--session-file", str(session),
                    "--mechanism-category", "validation",
                    "--episode-role", role,
                    "--comparison-basis", "same task class",
                    *boundary_args(output_mode="durable"),
                )
                evidence_path = Path(temp_dir) / f"{role}.json"
                evidence_path.write_text(collected.stdout, encoding="utf-8")
                evidence_paths.append(evidence_path)
            passed = run_script(
                "validate_findings.py", "--input", str(path), "--strict", "--json",
                "--evidence", str(evidence_paths[0]), "--evidence", str(evidence_paths[1]),
            )
            self.assertEqual(json.loads(passed.stdout)["status"], "pass")
            rendered = run_script(
                "render_report.py",
                "--findings", str(path),
                "--evidence", str(evidence_paths[0]),
                "--evidence", str(evidence_paths[1]),
                "--out", str(Path(temp_dir) / "reports"),
                "--run-id", "later-effect-run",
                "--json",
            )
            self.assertEqual(
                sorted(json.loads(rendered.stdout)["artifacts"]),
                ["evidence-baseline.json", "evidence-later.json", "findings.json", "report.md"],
            )
            for evidence_ref in learning["evidence_refs"][:2]:
                evidence_ref["mechanism_category"] = "edit"
            self.write_json(path, document)
            failed = run_script(
                "validate_findings.py", "--input", str(path), "--strict", "--json",
                "--evidence", str(evidence_paths[0]), "--evidence", str(evidence_paths[1]),
                expect=1,
            )
            self.assertIn("references must match evidence mechanism_category", failed.stdout)

    def test_invalid_existing_ledger_is_not_reinitialized(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            findings_path = root / "findings.json"
            ledger_path = root / "ledger.json"
            self.write_json(findings_path, findings_document())
            self.write_json(ledger_path, {})
            run_script(
                "update_ledger.py",
                "--findings", str(findings_path),
                "--ledger", str(ledger_path),
                expect=1,
            )
            self.assertEqual(json.loads(ledger_path.read_text(encoding="utf-8")), {})

            ledger_path.unlink()
            run_script(
                "update_ledger.py",
                "--findings", str(findings_path),
                "--ledger", str(ledger_path),
                "--date", "not-a-date",
                expect=1,
            )
            self.assertFalse(ledger_path.exists())


if __name__ == "__main__":
    unittest.main()
