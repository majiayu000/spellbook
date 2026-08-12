import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "review-agent-harness"
SCRIPTS = SKILL / "scripts"
DIMENSIONS = (
    "task-contract",
    "execution-control",
    "verification-closure",
    "delivery-safety",
    "learning-retention",
)
CHECKS_BY_DIMENSION = {
    "task-contract": ("goal-understanding", "relevant-context", "scope-boundary"),
    "execution-control": ("instruction-led-start", "supported-operation", "permission-boundary"),
    "verification-closure": ("relevant-check", "failure-repair", "validate-again"),
    "delivery-safety": ("acceptance-evidence", "high-risk-approval", "rollback-recovery"),
    "learning-retention": ("lifecycle-repeat-detection", "loop-engineering", "later-validation"),
}


def run_script(
    name: str,
    *args: str,
    expect: int = 0,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        input=input_text,
    )
    if completed.returncode != expect:
        raise AssertionError(
            f"{name} returned {completed.returncode}, expected {expect}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def reference(kind: str = "file", locator: str = "AGENTS.md:1") -> dict[str, str]:
    return {
        "kind": kind,
        "locator": locator,
        "claim": "The inspected owner supports this bounded claim.",
    }


def boundary_args(*, output_mode: str = "inline") -> tuple[str, ...]:
    return (
        "--locale", "en",
        "--decision", "Assess whether the harness can close the task loop.",
        "--acceptance-boundary", "All five dimensions have bounded evidence states.",
        "--output-mode", output_mode,
    )


def bind_findings_to_evidence(
    document: dict[str, object],
    evidence: dict[str, object],
) -> dict[str, object]:
    """Copy the collector-owned target and snapshot binding into findings."""

    scope = document["scope"]
    evidence_scope = evidence["scope"]
    assert isinstance(scope, dict) and isinstance(evidence_scope, dict)
    scope["target"] = evidence_scope["target"]
    scope["target_id"] = evidence_scope["target_id"]
    scope["snapshot"] = evidence_scope["snapshot"]
    return document


def findings_document(*, include_finding: bool = True) -> dict[str, object]:
    dimensions = []
    checks = []
    finding_id = "verification-closure--test-owner--final-state-not-rechecked"
    for dimension_id in DIMENSIONS:
        if dimension_id == "learning-retention":
            dimensions.append({
                "id": dimension_id,
                "status": "unobserved",
                "evidence_state": "unobserved",
                "confidence": "low",
                "score": 45,
                "score_rationale": "No later comparable Episode supports a stronger score.",
                "summary": "No later comparable Episode was authorized.",
                "evidence_refs": [],
            })
            for check_id in CHECKS_BY_DIMENSION[dimension_id]:
                checks.append({
                    "id": check_id,
                    "dimension": dimension_id,
                    "status": "unobserved",
                    "evidence_state": "unobserved",
                    "confidence": "low",
                    "summary": "The authorized evidence cannot resolve this check.",
                    "evidence_refs": [],
                    "finding_refs": [],
                })
        else:
            constrained = include_finding and dimension_id == "verification-closure"
            dimensions.append({
                "id": dimension_id,
                "status": "constrained" if constrained else "healthy",
                "evidence_state": "exercised" if constrained else "reachable",
                "confidence": "medium",
                "score": 55 if constrained else 80,
                "score_rationale": (
                    "A confirmed final-state validation gap constrains this dimension."
                    if constrained else "All applicable checks expose reachable project-owned routes."
                ),
                "summary": (
                    "The final-state validation route has a confirmed gap."
                    if constrained else "The inspected project exposes a supported route."
                ),
                "evidence_refs": [reference()],
            })
            for check_id in CHECKS_BY_DIMENSION[dimension_id]:
                check_constrained = constrained and check_id == "validate-again"
                checks.append({
                    "id": check_id,
                    "dimension": dimension_id,
                    "status": "constrained" if check_constrained else "healthy",
                    "evidence_state": "exercised" if check_constrained else "reachable",
                    "confidence": "high" if check_constrained else "medium",
                    "summary": (
                        "The final state was not rechecked."
                        if check_constrained else "The project exposes a reachable owner for this check."
                    ),
                    "evidence_refs": [reference()],
                    "finding_refs": [finding_id] if check_constrained else [],
                })
    findings = []
    priority_moves = []
    verification_runs = []
    if include_finding:
        findings.append({
            "id": finding_id,
            "title": "The final state was not rechecked",
            "severity": "high",
            "confidence": "high",
            "primary_dimension": "verification-closure",
            "primary_check": "validate-again",
            "evidence_state": "exercised",
            "consequence": "Completion was reported without final-state validation.",
            "root_cause": "The mapped test ran before the final edit.",
            "owner": "project test workflow",
            "evidence_refs": [reference("command", "targeted-test")],
            "repair_route": "Run the mapped test after the final edit.",
            "verifier": "The mapped test passes on the final state.",
            "verification_state": "confirmed",
            "repair_state": "not_started",
        })
        verification_runs.append({
            "id": "targeted-test",
            "purpose": "targeted_reproduction",
            "result": "supports",
            "exit_code": 1,
            "final_state": True,
            "summary": "The final-state reproduction confirms the validation gap.",
        })
        priority_moves.append(finding_id)
    return {
        "schema_version": 1,
        "kind": "agent-harness-findings",
        "overview": "The review resolves the full work loop while preserving unavailable evidence.",
        "scope": {
            "target": "fixture-project",
            "target_id": f"local-sha256:{'0' * 64}",
            "snapshot": {
                "baseline": "current_checkout",
                "target_relation": "exact_git_root",
                "id": f"git-sha256:{'0' * 64}",
            },
            "mode": "static",
            "locale": "en",
            "providers": ["none"],
            "decision": "Assess whether the harness can close the task loop.",
            "acceptance_boundary": "All five dimensions have bounded evidence states.",
            "output_mode": "durable",
        },
        "evidence_boundary": {
            "included": ["repository-static-evidence"],
            "excluded": [
                "user-home-discovery",
                "memory-bodies",
                "raw-transcripts",
                "secret-values",
                "stable-session-identifiers",
            ],
            "unavailable": ["session-evidence:not_authorized"],
        },
        "dimensions": dimensions,
        "checks": checks,
        "verification_runs": verification_runs,
        "findings": findings,
        "priority_moves": priority_moves,
    }


class ReviewAgentHarnessTests(unittest.TestCase):
    def write_json(self, path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")

    def make_target(self, root: Path) -> Path:
        target = root / "fixture-project"
        (target / ".agents" / "skills" / "deploy").mkdir(parents=True)
        (target / "tests").mkdir()
        (target / ".github" / "workflows").mkdir(parents=True)
        (target / "AGENTS.md").write_text("# Agent rules\nRun focused tests.\n", encoding="utf-8")
        (target / ".agents" / "skills" / "deploy" / "SKILL.md").write_text(
            "---\nname: deploy\ndescription: Use for deploy tasks.\n---\n",
            encoding="utf-8",
        )
        (target / "package.json").write_text(
            json.dumps({"scripts": {"test": "pytest", "build": "echo build"}}),
            encoding="utf-8",
        )
        (target / "tests" / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
        (target / "docs" / "specs").mkdir(parents=True)
        (target / "docs" / "specs" / "contract.md").write_text("# Product specification\n", encoding="utf-8")
        (target / "artifacts").mkdir()
        (target / "artifacts" / "cargo-test.log").write_text("test output\n", encoding="utf-8")
        (target / "templates").mkdir()
        (target / "templates" / "product_spec.md").write_text("# Template\n", encoding="utf-8")
        (target / "src").mkdir()
        (target / "src" / "widget.spec.ts").write_text("export {};\n", encoding="utf-8")
        (target / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
        (target / ".gitignore").write_text(".claude/worktrees/\n.agent-harness-review/\n", encoding="utf-8")
        ignored_worktree = target / ".claude" / "worktrees" / "stale"
        ignored_worktree.mkdir(parents=True)
        (ignored_worktree / "AGENTS.md").write_text("# Ignored duplicate\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=target, check=True)
        (root / "outside-target.txt").write_text("not authorized\n", encoding="utf-8")
        return target

    def test_static_collector_is_repository_bounded(self) -> None:
        with TemporaryDirectory() as temp_dir:
            target = self.make_target(Path(temp_dir))
            completed = run_script(
                "collect_evidence.py", "--target", str(target), "--mode", "static", *boundary_args()
            )
            evidence = json.loads(completed.stdout)

            self.assertEqual(evidence["kind"], "agent-harness-evidence")
            self.assertEqual(evidence["scope"]["target"], "fixture-project")
            self.assertEqual(evidence["sessions"]["status"], "not_authorized")
            self.assertIn("AGENTS.md", evidence["static"]["agent_assets"]["instructions"]["items"])
            self.assertIn(
                ".agents/skills/deploy/SKILL.md",
                evidence["static"]["agent_assets"]["skills"]["items"],
            )
            self.assertEqual(evidence["scope"]["snapshot"]["target_relation"], "exact_git_root")
            self.assertEqual(evidence["static"]["scan"]["source"], "git-index")
            self.assertNotIn(
                ".claude/worktrees/stale/AGENTS.md",
                evidence["static"]["agent_assets"]["instructions"]["items"],
            )
            self.assertIn("tests/test_app.py", evidence["static"]["project"]["tests"]["items"])
            self.assertIn("src/widget.spec.ts", evidence["static"]["project"]["tests"]["items"])
            self.assertNotIn("docs/specs/contract.md", evidence["static"]["project"]["tests"]["items"])
            self.assertNotIn("artifacts/cargo-test.log", evidence["static"]["project"]["tests"]["items"])
            self.assertNotIn("templates/product_spec.md", evidence["static"]["project"]["tests"]["items"])
            self.assertNotIn("outside-target.txt", evidence["static"]["git"]["changed_files"])
            self.assertNotIn(str(target.parent), completed.stdout)

    def test_codex_adapter_redacts_private_content_and_counts_validation(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = self.make_target(root)
            session = root / "codex.jsonl"
            rows = [
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": "Fix /Users/alice/app api_key=supersecret"}],
                    },
                },
                {
                    "type": "response_item",
                    "payload": {"type": "function_call", "name": "apply_patch", "arguments": "{}"},
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "exec_command",
                        "arguments": json.dumps({"cmd": "pytest tests/test_app.py"}),
                    },
                },
                {
                    "type": "response_item",
                    "payload": {"type": "function_call_output", "output": "Process exited with code 1"},
                },
            ]
            session.write_text("\n".join(json.dumps(row) for row in rows) + "\nnot-json\n", encoding="utf-8")

            completed = run_script(
                "collect_evidence.py",
                "--target",
                str(target),
                "--mode",
                "episode",
                "--provider",
                "codex",
                "--session-file",
                str(session),
                "--include-request-summaries",
                *boundary_args(),
            )
            evidence = json.loads(completed.stdout)
            facts = evidence["sessions"]["sessions"][0]

            self.assertEqual(facts["edit_calls"], 1)
            self.assertEqual(facts["validation_calls"], 1)
            self.assertEqual(facts["tool_failures"], 1)
            self.assertEqual(facts["malformed_lines"], 1)
            self.assertIn("<path>", facts["request_summary"])
            self.assertIn("<redacted>", facts["request_summary"])
            self.assertNotIn("supersecret", completed.stdout)
            self.assertNotIn(str(session), completed.stdout)

    def test_claude_adapter_normalizes_tool_use_and_error_result(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = self.make_target(root)
            session = root / "claude.jsonl"
            rows = [
                {"type": "user", "message": {"content": "Run the focused check."}},
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {"type": "tool_use", "name": "Write", "input": {"file_path": "app.py"}},
                            {"type": "tool_use", "name": "Bash", "input": {"command": "python -m pytest"}},
                        ]
                    },
                },
                {
                    "type": "user",
                    "message": {"content": [{"type": "tool_result", "is_error": True, "content": "failed"}]},
                },
            ]
            session.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

            completed = run_script(
                "collect_evidence.py",
                "--target",
                str(target),
                "--mode",
                "episode",
                "--provider",
                "claude",
                "--session-file",
                str(session),
                "--include-request-summaries",
                *boundary_args(),
            )
            facts = json.loads(completed.stdout)["sessions"]["sessions"][0]

            self.assertEqual(facts["user_turns"], 1)
            self.assertEqual(facts["tool_calls"], 2)
            self.assertEqual(facts["edit_calls"], 1)
            self.assertEqual(facts["validation_calls"], 1)
            self.assertEqual(facts["tool_failures"], 1)
            self.assertEqual(facts["request_summary"], "Run the focused check.")

    def test_findings_validator_accepts_contract_and_rejects_private_path(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "findings.json"
            document = findings_document()
            self.write_json(path, document)
            passed = run_script("validate_findings.py", "--input", str(path), "--strict", "--json")
            self.assertEqual(json.loads(passed.stdout)["status"], "pass")

            document["findings"][0]["consequence"] = "Leaked /Users/alice/private.txt into output."
            self.write_json(path, document)
            failed = run_script("validate_findings.py", "--input", str(path), "--json", expect=1)
            result = json.loads(failed.stdout)
            self.assertEqual(result["status"], "fail")
            self.assertTrue(any("privacy rule user-path" in error for error in result["errors"]))

            document = findings_document()
            document["findings"][0]["consequence"] = "See [private evidence](https://internal.example/run/1)."
            self.write_json(path, document)
            failed = run_script("validate_findings.py", "--input", str(path), "--json", expect=1)
            result = json.loads(failed.stdout)
            self.assertTrue(any("privacy rule markdown-destination" in error for error in result["errors"]))

    def test_renderer_writes_validated_atomic_artifacts(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = self.make_target(root)
            findings_path = root / "findings.json"
            evidence_path = root / "evidence.json"
            collected = run_script(
                "collect_evidence.py",
                "--target",
                str(target),
                "--mode",
                "static",
                *boundary_args(output_mode="durable"),
            )
            evidence_path.write_text(collected.stdout, encoding="utf-8")
            evidence = json.loads(collected.stdout)
            self.write_json(
                findings_path,
                bind_findings_to_evidence(findings_document(), evidence),
            )

            completed = run_script(
                "render_report.py",
                "--findings",
                str(findings_path),
                "--evidence",
                str(evidence_path),
                "--target",
                str(target),
                "--out",
                str(target / ".agent-harness-review"),
                "--run-id",
                "run-1",
                "--json",
            )
            result = json.loads(completed.stdout)
            run_dir = target / ".agent-harness-review" / result["run_id"]

            self.assertEqual(result["status"], "pass")
            self.assertEqual(sorted(path.name for path in run_dir.iterdir()), ["evidence.json", "findings.json", "report.md"])
            report = (run_dir / "report.md").read_text(encoding="utf-8")
            self.assertIn("# Agent Harness Review", report)
            self.assertIn("## Fifteen Checks", report)
            self.assertIn("No overall score is computed", report)
            self.assertIn("## Verification Runs", report)
            self.assertIn("The final state was not rechecked", report)
            run_script(
                "render_report.py",
                "--findings", str(findings_path),
                "--evidence", str(evidence_path),
                "--target", str(target),
                "--out", str(target / ".agent-harness-review"),
                "--run-id", "run-1",
                "--json",
                expect=1,
            )
            self.assertEqual((run_dir / "report.md").read_text(encoding="utf-8"), report)

    def test_ledger_requires_spot_check_and_tracks_regression(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "fixture-project"
            target.mkdir()
            findings_path = root / "findings.json"
            ledger_path = target / ".agent-harness-review" / "ledger.json"
            confirmations_path = root / "confirmations.json"
            finding_id = "verification-closure--test-owner--final-state-not-rechecked"
            collected = run_script(
                "collect_evidence.py",
                "--target", str(target),
                "--mode", "static",
                *boundary_args(output_mode="durable"),
            )
            document = bind_findings_to_evidence(findings_document(), json.loads(collected.stdout))
            self.write_json(findings_path, document)

            first = run_script(
                "update_ledger.py", "--findings", str(findings_path), "--target", str(target),
                "--ledger", str(ledger_path),
                "--date", "2026-08-01", "--json",
            )
            self.assertEqual(json.loads(first.stdout)["summary"]["new"], 1)
            second = run_script(
                "update_ledger.py", "--findings", str(findings_path), "--target", str(target),
                "--ledger", str(ledger_path),
                "--date", "2026-08-02", "--json",
            )
            self.assertEqual(json.loads(second.stdout)["summary"]["still_open"], 1)

            document["findings"] = []
            document["priority_moves"] = []
            document["verification_runs"] = []
            verification = next(
                row for row in document["dimensions"] if row["id"] == "verification-closure"
            )
            verification.update({
                "status": "healthy",
                "evidence_state": "reachable",
                "confidence": "medium",
                "score": 80,
                "score_rationale": "All applicable checks expose reachable project-owned routes.",
                "summary": "The inspected project exposes a supported route.",
            })
            for check in document["checks"]:
                if check["id"] == "validate-again":
                    check.update({
                        "status": "healthy",
                        "evidence_state": "reachable",
                        "confidence": "medium",
                        "summary": "The project exposes a reachable owner for this check.",
                        "finding_refs": [],
                    })
            self.write_json(findings_path, document)
            missing = run_script(
                "update_ledger.py", "--findings", str(findings_path), "--target", str(target),
                "--ledger", str(ledger_path),
                "--date", "2026-08-03", "--json",
            )
            self.assertEqual(json.loads(missing.stdout)["summary"]["recheck_required"], 1)
            self.write_json(confirmations_path, {
                "schema_version": 1,
                "kind": "agent-harness-resolution-confirmations",
                "confirmations": [{
                    "id": finding_id,
                    "verifier": "An unrelated check passed.",
                    "evidence_ref": reference("file", "README.md:1"),
                }],
            })
            run_script(
                "update_ledger.py", "--findings", str(findings_path), "--ledger", str(ledger_path),
                "--target", str(target),
                "--date", "2026-08-04", "--resolution-confirmations", str(confirmations_path), "--json",
                expect=1,
            )
            self.write_json(confirmations_path, {
                "schema_version": 1,
                "kind": "agent-harness-resolution-confirmations",
                "confirmations": [{
                    "id": finding_id,
                    "verifier": "The mapped test passes on the final state.",
                    "evidence_ref": reference("command", "targeted-test-final-state"),
                }],
            })
            confirmed = run_script(
                "update_ledger.py", "--findings", str(findings_path), "--ledger", str(ledger_path),
                "--target", str(target),
                "--date", "2026-08-04", "--resolution-confirmations", str(confirmations_path), "--json",
            )
            self.assertEqual(json.loads(confirmed.stdout)["summary"]["resolved"], 1)
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(ledger["target"], "fixture-project")
            self.assertEqual(ledger["findings"][0]["resolution_confirmation"]["evidence_ref"]["kind"], "command")

            fresh_document = bind_findings_to_evidence(findings_document(), json.loads(collected.stdout))
            self.write_json(findings_path, fresh_document)
            regression = run_script(
                "update_ledger.py", "--findings", str(findings_path), "--target", str(target),
                "--ledger", str(ledger_path),
                "--date", "2026-08-05", "--json",
            )
            self.assertEqual(json.loads(regression.stdout)["summary"]["regression"], 1)


if __name__ == "__main__":
    unittest.main()
