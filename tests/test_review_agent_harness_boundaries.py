import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from test_review_agent_harness import (
    bind_findings_to_evidence,
    boundary_args,
    findings_document,
    reference,
)


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
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")

    def bound_document(
        self,
        target: Path,
        *,
        include_finding: bool = True,
    ) -> dict[str, object]:
        collected = run_script(
            "collect_evidence.py",
            "--target", str(target),
            "--mode", "static",
            *boundary_args(output_mode="durable"),
        )
        return bind_findings_to_evidence(
            findings_document(include_finding=include_finding),
            json.loads(collected.stdout),
        )

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

    def test_session_adapter_bounds_input_and_warning_retention(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "target"
            target.mkdir()
            session = root / "session.jsonl"
            session.write_text("not-json\n" * 20, encoding="utf-8")

            completed = run_script(
                "collect_evidence.py",
                "--target", str(target),
                "--mode", "episode",
                "--provider", "codex",
                "--session-file", str(session),
                "--max-session-lines", "3",
                "--max-session-warnings", "2",
                *boundary_args(),
            )
            sessions = json.loads(completed.stdout)["sessions"]
            facts = sessions["sessions"][0]
            self.assertEqual(sessions["status"], "constrained")
            self.assertTrue(facts["input_truncated"])
            self.assertEqual(facts["truncation_reasons"], ["session-line-limit"])
            self.assertEqual(facts["lines_observed"], 3)
            self.assertEqual(len(sessions["warnings"]), 2)
            self.assertEqual(sessions["warnings_omitted"], 1)

    def test_tool_failure_count_prefers_structure_and_ignores_zero_prose(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "target"
            target.mkdir()
            session = root / "session.jsonl"
            rows = [
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call_output",
                        "output": {"exit_code": 0, "summary": "error count: 7"},
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call_output",
                        "output": "No error detected; failed tests: 0",
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call_output",
                        "output": {"exit_code": 2, "summary": "completed"},
                    },
                },
            ]
            session.write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n",
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
            facts = json.loads(completed.stdout)["sessions"]["sessions"][0]
            self.assertEqual(facts["tool_failures"], 1)

    def test_adapter_counts_messages_and_exact_edit_tools(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "target"
            target.mkdir()
            session = root / "session.jsonl"
            rows = [
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": "First block"},
                            {"type": "input_text", "text": "Second block"},
                        ],
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "write_stdin",
                        "arguments": "{}",
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "functions.apply_patch",
                        "arguments": "{}",
                    },
                },
            ]
            session.write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n",
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
            facts = json.loads(completed.stdout)["sessions"]["sessions"][0]
            self.assertEqual(facts["user_turns"], 1)
            self.assertEqual(facts["tool_calls"], 2)
            self.assertEqual(facts["edit_calls"], 1)

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

    def test_nested_git_resolution_is_recursive_ambiguous_and_does_not_follow_links(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parent = root / "workspace-parent"
            first = parent / "group" / "repo-a"
            second = parent / "other" / "deeper" / "repo-b"
            outside = root / "outside-repo"
            for nested in (first, second, outside):
                nested.mkdir(parents=True)
                subprocess.run(["git", "init", "-q"], cwd=nested, check=True)
                (nested / "AGENTS.md").write_text(
                    f"# Instructions from {nested.name}\n",
                    encoding="utf-8",
                )
            (parent / "linked-repo").symlink_to(outside, target_is_directory=True)

            completed = run_script(
                "collect_evidence.py", "--target", str(parent), "--mode", "static", *boundary_args()
            )
            evidence = json.loads(completed.stdout)
            resolution = evidence["static"]["root_resolution"]
            self.assertEqual(evidence["scope"]["snapshot"]["target_relation"], "contains_nested_git_root")
            self.assertEqual(resolution["status"], "constrained")
            self.assertEqual(resolution["reason"], "multiple-nested-git-roots-require-explicit-target")
            self.assertEqual(resolution["nested_git_roots"], ["group/repo-a", "other/deeper/repo-b"])
            self.assertEqual(resolution["nested_git_root_count"], 2)
            self.assertTrue(resolution["nested_git_search_complete"])
            self.assertNotIn("linked-repo", resolution["nested_git_roots"])
            self.assertEqual(evidence["static"]["agent_assets"]["instructions"]["items"], [])
            self.assertNotIn("Instructions from outside-repo", completed.stdout)

    def test_nested_git_resolution_reports_a_bounded_incomplete_search(self) -> None:
        with TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir) / "workspace-parent"
            too_deep = parent.joinpath(*("level" for _ in range(7)), "repo")
            too_deep.mkdir(parents=True)
            subprocess.run(["git", "init", "-q"], cwd=too_deep, check=True)

            completed = run_script(
                "collect_evidence.py", "--target", str(parent), "--mode", "static", *boundary_args()
            )
            resolution = json.loads(completed.stdout)["static"]["root_resolution"]
            self.assertEqual(resolution["status"], "constrained")
            self.assertEqual(resolution["relation"], "non_git_directory")
            self.assertEqual(resolution["reason"], "nested-git-root-search-bounded")
            self.assertFalse(resolution["nested_git_search_complete"])
            self.assertGreater(resolution["nested_git_search_depth_limited_count"], 0)

    def test_static_session_root_fails_before_target_or_session_resolution(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            failed = run_script(
                "collect_evidence.py",
                "--target", str(root / "missing-target"),
                "--mode", "static",
                "--session-root", str(root / "missing-session-root"),
                *boundary_args(),
                expect=1,
            )
            self.assertIn("static mode does not accept session sources", failed.stderr)
            self.assertNotIn("target is not a directory", failed.stderr)

    def test_renderer_rejects_warn_findings_and_mismatched_evidence(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "fixture-project"
            target.mkdir()
            findings_path = root / "findings.json"
            evidence_path = root / "evidence.json"
            document = self.bound_document(target)
            document["findings"][0]["verification_state"] = "unverified"
            self.write_json(findings_path, document)
            failed = run_script(
                "render_report.py",
                "--findings", str(findings_path),
                "--target", str(target),
                "--out", str(target / ".agent-harness-review"),
                "--run-id", "warn-run",
                expect=1,
            )
            self.assertFalse((target / ".agent-harness-review" / "warn-run").exists())

            document = self.bound_document(target)
            self.write_json(findings_path, document)
            evidence = {
                "schema_version": 1,
                "kind": "agent-harness-evidence",
                "scope": {
                    "target": "fixture-project",
                    "target_id": document["scope"]["target_id"],
                    "snapshot": document["scope"]["snapshot"],
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
                "--target", str(target),
                "--out", str(target / ".agent-harness-review"),
                "--run-id", "mismatch-run",
                expect=1,
            )
            self.assertIn("evidence.static.scan", failed.stderr)
            self.assertIn("evidence.evidence_boundary.included", failed.stderr)
            self.assertFalse((target / ".agent-harness-review" / "mismatch-run").exists())

    def test_renderer_accepts_collector_compact_unobserved_session(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "fixture-project"
            target.mkdir()
            document = findings_document()
            document["scope"]["mode"] = "episode"
            document["evidence_boundary"]["unavailable"] = ["session-evidence:unobserved"]
            findings_path = root / "findings.json"
            evidence_path = root / "evidence.json"
            collected = run_script(
                "collect_evidence.py",
                "--target", str(target),
                "--mode", "episode",
                *boundary_args(output_mode="durable"),
            )
            evidence_path.write_text(collected.stdout, encoding="utf-8")
            bind_findings_to_evidence(document, json.loads(collected.stdout))
            self.write_json(findings_path, document)
            rendered = run_script(
                "render_report.py",
                "--findings", str(findings_path),
                "--evidence", str(evidence_path),
                "--target", str(target),
                "--out", str(target / ".agent-harness-review"),
                "--run-id", "unobserved-run",
                "--json",
            )
            self.assertEqual(json.loads(rendered.stdout)["status"], "pass")

    def test_renderer_rejects_cross_target_stale_snapshot_and_wrong_output(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "fixture-project"
            other = root / "copy" / "fixture-project"
            target.mkdir()
            other.mkdir(parents=True)
            evidence_path = root / "evidence.json"
            findings_path = root / "findings.json"
            collected = run_script(
                "collect_evidence.py",
                "--target", str(target),
                "--mode", "static",
                *boundary_args(output_mode="durable"),
            )
            evidence = json.loads(collected.stdout)
            evidence_path.write_text(collected.stdout, encoding="utf-8")
            self.write_json(
                findings_path,
                bind_findings_to_evidence(findings_document(), evidence),
            )

            cross_target = run_script(
                "render_report.py",
                "--findings", str(findings_path),
                "--evidence", str(evidence_path),
                "--target", str(other),
                "--out", str(other / ".agent-harness-review"),
                "--run-id", "cross-target",
                expect=1,
            )
            self.assertIn("target identity does not match", cross_target.stderr)

            wrong_output = run_script(
                "render_report.py",
                "--findings", str(findings_path),
                "--evidence", str(evidence_path),
                "--target", str(target),
                "--out", str(root / "reports"),
                "--run-id", "wrong-output",
                expect=1,
            )
            self.assertIn("artifact path must be", wrong_output.stderr)

            (target / "changed.txt").write_text("new state\n", encoding="utf-8")
            stale = run_script(
                "render_report.py",
                "--findings", str(findings_path),
                "--evidence", str(evidence_path),
                "--target", str(target),
                "--out", str(target / ".agent-harness-review"),
                "--run-id", "stale-snapshot",
                expect=1,
            )
            self.assertIn("snapshot is stale", stale.stderr)
            self.assertFalse((target / ".agent-harness-review").exists())

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

    def test_findings_privacy_checks_sensitive_dictionary_keys(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "findings.json"
            document = findings_document()
            document["api_key"] = "supersecret"
            self.write_json(path, document)

            failed = run_script("validate_findings.py", "--input", str(path), "--json", expect=1)
            self.assertIn("privacy rule secret-assignment", failed.stdout)

    def test_evidence_privacy_checks_sensitive_dictionary_keys(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "fixture-project"
            target.mkdir()
            findings_path = root / "findings.json"
            evidence_path = root / "evidence.json"
            collected = run_script(
                "collect_evidence.py",
                "--target", str(target),
                "--mode", "static",
                *boundary_args(output_mode="durable"),
            )
            evidence = json.loads(collected.stdout)
            evidence["static"]["metadata"] = [
                {"credentials": {"api_key": {"value": "supersecret"}}},
            ]
            self.write_json(evidence_path, evidence)
            document = bind_findings_to_evidence(findings_document(), evidence)
            self.write_json(findings_path, document)

            failed = run_script(
                "render_report.py",
                "--findings", str(findings_path),
                "--evidence", str(evidence_path),
                "--target", str(target),
                "--out", str(target / ".agent-harness-review"),
                "--run-id", "key-privacy-run",
                expect=1,
            )
            self.assertIn("evidence privacy validation failed: secret-assignment", failed.stderr)

    def test_ledger_privacy_checks_sensitive_dictionary_keys(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "fixture-project"
            target.mkdir()
            findings_path = root / "findings.json"
            ledger_path = target / ".agent-harness-review" / "ledger.json"
            self.write_json(findings_path, self.bound_document(target))
            run_script(
                "update_ledger.py",
                "--findings", str(findings_path),
                "--target", str(target),
                "--ledger", str(ledger_path),
                "--date", "2026-08-01",
            )
            clean_ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            poisoned_ledger = dict(clean_ledger)
            poisoned_ledger["metadata"] = {"credentials": [{"api_key": "supersecret"}]}
            self.write_json(ledger_path, poisoned_ledger)

            failed = run_script(
                "update_ledger.py",
                "--findings", str(findings_path),
                "--target", str(target),
                "--ledger", str(ledger_path),
                "--date", "2026-08-02",
                expect=1,
            )
            self.assertIn("ledger violates privacy: secret-assignment", failed.stderr)
            self.assertEqual(json.loads(ledger_path.read_text(encoding="utf-8")), poisoned_ledger)

    def test_resolution_confirmation_privacy_checks_sensitive_dictionary_keys(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "fixture-project"
            target.mkdir()
            findings_path = root / "findings.json"
            ledger_path = target / ".agent-harness-review" / "ledger.json"
            confirmations_path = root / "confirmations.json"
            finding_id = "verification-closure--test-owner--final-state-not-rechecked"
            self.write_json(findings_path, self.bound_document(target))
            run_script(
                "update_ledger.py",
                "--findings", str(findings_path),
                "--target", str(target),
                "--ledger", str(ledger_path),
                "--date", "2026-08-01",
            )
            self.write_json(findings_path, self.bound_document(target, include_finding=False))
            self.write_json(confirmations_path, {
                "schema_version": 1,
                "kind": "agent-harness-resolution-confirmations",
                "confirmations": [{
                    "id": finding_id,
                    "verifier": "The mapped test passes on the final state.",
                    "evidence_ref": reference("command", "targeted-test-final-state"),
                    "metadata": [{"credentials": {"api_key": ["supersecret"]}}],
                }],
            })

            failed = run_script(
                "update_ledger.py",
                "--findings", str(findings_path),
                "--target", str(target),
                "--ledger", str(ledger_path),
                "--date", "2026-08-02",
                "--resolution-confirmations", str(confirmations_path),
                expect=1,
            )
            self.assertIn("violates privacy: secret-assignment", failed.stderr)
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(ledger["findings"][0]["status"], "open")

    def test_sensitive_dictionary_fields_allow_explicitly_safe_values(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "findings.json"
            safe_values = (
                "",
                "[REDACTED]",
                "<redacted>",
                "masked",
                "not configured",
                None,
                False,
                0,
                [],
                {"value": "[REDACTED]", "configured": False},
            )
            for index, safe_value in enumerate(safe_values):
                with self.subTest(index=index, safe_value=safe_value):
                    document = findings_document()
                    document["metadata"] = {
                        "credentials": [{"api_key": safe_value}],
                        "secretary": "supersecret",
                    }
                    self.write_json(path, document)
                    passed = run_script(
                        "validate_findings.py",
                        "--input", str(path),
                        "--strict",
                        "--json",
                    )
                    self.assertEqual(json.loads(passed.stdout)["status"], "pass")

    def test_collector_rejects_private_tree_without_output_or_artifact(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cases = (
                ("target-token", "ghp_1234567890abcdef", None, "ghp_1234567890abcdef"),
                (
                    "package-key-value",
                    "fixture-project",
                    {"scripts": {"api_key=supersecret": "echo safe"}},
                    "supersecret",
                ),
            )
            for case_name, target_name, package, private_text in cases:
                with self.subTest(case=case_name):
                    target = root / case_name / target_name
                    target.mkdir(parents=True)
                    if package is not None:
                        (target / "package.json").write_text(
                            json.dumps(package),
                            encoding="utf-8",
                        )
                    output = root / case_name / "artifacts" / "evidence.json"
                    failed = run_script(
                        "collect_evidence.py",
                        "--target", str(target),
                        "--mode", "static",
                        "--output", str(output),
                        *boundary_args(output_mode="durable"),
                        expect=1,
                    )
                    self.assertEqual(failed.stdout, "")
                    self.assertNotIn(private_text, failed.stdout)
                    self.assertNotIn(private_text, failed.stderr)
                    self.assertIn("collected evidence violates privacy", failed.stderr)
                    self.assertFalse(output.exists())
                    self.assertFalse(output.parent.exists())

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
            bind_findings_to_evidence(
                document,
                json.loads(evidence_paths[0].read_text(encoding="utf-8")),
            )
            self.write_json(path, document)
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
                "--target", str(target),
                "--out", str(target / ".agent-harness-review"),
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
            target = root / "fixture-project"
            target.mkdir()
            findings_path = root / "findings.json"
            ledger_path = target / ".agent-harness-review" / "ledger.json"
            self.write_json(findings_path, self.bound_document(target))
            self.write_json(ledger_path, {})
            run_script(
                "update_ledger.py",
                "--findings", str(findings_path),
                "--target", str(target),
                "--ledger", str(ledger_path),
                expect=1,
            )
            self.assertEqual(json.loads(ledger_path.read_text(encoding="utf-8")), {})

            ledger_path.unlink()
            run_script(
                "update_ledger.py",
                "--findings", str(findings_path),
                "--target", str(target),
                "--ledger", str(ledger_path),
                "--date", "not-a-date",
                expect=1,
            )
            self.assertFalse(ledger_path.exists())


if __name__ == "__main__":
    unittest.main()
