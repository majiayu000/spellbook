#!/usr/bin/env python3
"""Render validated findings into an atomic durable Markdown run."""

from __future__ import annotations

import argparse
import ctypes
import errno
import json
import os
import shutil
import tempfile
import sys
from datetime import datetime, timezone
from pathlib import Path

from harness_common import all_strings, load_json, private_data_matches, slug, write_json_atomic
from validate_findings import CHECK_IDS, DIMENSION_IDS, validate_document


def _cell(value: object) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("`", "&#96;")
        .replace("|", "\\|")
        .replace("\n", " ")
        .strip()
    )


def _write_text_durable(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _rename_directory_no_replace(source: Path, destination: Path) -> None:
    if os.name == "nt":
        os.rename(source, destination)
        return
    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source)
    destination_bytes = os.fsencode(destination)
    if sys.platform == "darwin" and hasattr(libc, "renamex_np"):
        result = libc.renamex_np(source_bytes, destination_bytes, 0x00000004)
    elif sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        result = libc.renameat2(-100, source_bytes, -100, destination_bytes, 1)
    else:
        raise OSError(errno.ENOTSUP, "atomic no-replace directory rename is unavailable")
    if result != 0:
        error_number = ctypes.get_errno()
        if error_number == errno.EEXIST:
            raise FileExistsError(f"refusing to replace existing run directory: {destination.name}")
        raise OSError(error_number, os.strerror(error_number))


def _render_markdown(document: dict[str, object]) -> str:
    scope = document["scope"]
    dimensions = document["dimensions"]
    checks = document["checks"]
    verification_runs = document["verification_runs"]
    findings = document["findings"]
    priority = document["priority_moves"]
    boundary = document["evidence_boundary"]
    assert isinstance(scope, dict)
    assert isinstance(dimensions, list)
    assert isinstance(checks, list)
    assert isinstance(verification_runs, list)
    assert isinstance(findings, list)
    assert isinstance(priority, list)
    assert isinstance(boundary, dict)
    finding_map = {
        str(finding["id"]): finding
        for finding in findings
        if isinstance(finding, dict) and isinstance(finding.get("id"), str)
    }
    lines = [
        "# Agent Harness Review",
        "",
        _cell(document.get("overview")),
        "",
        f"- Target: {_cell(scope.get('target'))}",
        f"- Mode: {_cell(scope.get('mode'))}",
        f"- Decision: {_cell(scope.get('decision'))}",
        f"- Acceptance boundary: {_cell(scope.get('acceptance_boundary'))}",
        f"- Output mode: {_cell(scope.get('output_mode'))}",
        f"- Providers: {_cell(', '.join(str(item) for item in scope.get('providers', [])))}",
        f"- Snapshot baseline: {_cell(scope.get('snapshot', {}).get('baseline'))}",
        f"- Target relation: {_cell(scope.get('snapshot', {}).get('target_relation'))}",
        "",
        "## Evidence Boundary",
        "",
        f"- Included: {_cell(', '.join(str(item) for item in boundary.get('included', [])) or 'none')}",
        f"- Excluded: {_cell(', '.join(str(item) for item in boundary.get('excluded', [])) or 'none')}",
        f"- Unavailable: {_cell(', '.join(str(item) for item in boundary.get('unavailable', [])) or 'none')}",
        "",
        "## Dimensions",
        "",
        "| Dimension | Score | Status | Evidence | Confidence | Summary | Score basis |",
        "| --- | ---: | --- | --- | --- | --- | --- |",
    ]
    ordered_dimensions = sorted(
        (row for row in dimensions if isinstance(row, dict)),
        key=lambda row: DIMENSION_IDS.index(str(row.get("id"))) if row.get("id") in DIMENSION_IDS else 99,
    )
    for row in ordered_dimensions:
        lines.append(
            f"| {_cell(row.get('id'))} | {_cell(row.get('score'))}/100 | {_cell(row.get('status'))} | "
            f"{_cell(row.get('evidence_state'))} | {_cell(row.get('confidence'))} | {_cell(row.get('summary'))} | "
            f"{_cell(row.get('score_rationale'))} |"
        )
    lines.extend([
        "",
        "No overall score is computed; each dimension keeps its own evidence ceiling.",
        "",
        "## Fifteen Checks",
        "",
        "| Check | Dimension | Status | Evidence | Confidence | Summary | Findings |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    ordered_checks = sorted(
        (row for row in checks if isinstance(row, dict)),
        key=lambda row: CHECK_IDS.index(str(row.get("id"))) if row.get("id") in CHECK_IDS else 99,
    )
    for row in ordered_checks:
        finding_refs = row.get("finding_refs", [])
        lines.append(
            f"| {_cell(row.get('id'))} | {_cell(row.get('dimension'))} | {_cell(row.get('status'))} | "
            f"{_cell(row.get('evidence_state'))} | {_cell(row.get('confidence'))} | "
            f"{_cell(row.get('summary'))} | {_cell(', '.join(str(item) for item in finding_refs) or 'none')} |"
        )
    lines.extend(["", "## Verification Runs", ""])
    if verification_runs:
        lines.extend([
            "| Run | Purpose | Result | Exit | Final state | Summary |",
            "| --- | --- | --- | ---: | --- | --- |",
        ])
        for run in verification_runs:
            if isinstance(run, dict):
                lines.append(
                    f"| {_cell(run.get('id'))} | {_cell(run.get('purpose'))} | {_cell(run.get('result'))} | "
                    f"{_cell(run.get('exit_code'))} | {_cell(run.get('final_state'))} | {_cell(run.get('summary'))} |"
                )
    else:
        lines.append("No structured verification run was retained in this review.")
    lines.extend(["", "## Priority Moves", ""])
    if priority:
        for finding_id in priority:
            finding = finding_map[str(finding_id)]
            lines.append(f"1. **{_cell(finding.get('title'))}** — {_cell(finding.get('repair_route'))}")
    else:
        lines.append("No eligible priority move was supported by the reviewed evidence.")
    lines.extend(["", "## Findings", ""])
    if not findings:
        lines.append("No eligible findings were supported inside the evidence boundary.")
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        lines.extend([
            f"### [{_cell(finding.get('severity')).upper()}] {_cell(finding.get('title'))}",
            "",
            f"- ID: `{_cell(finding.get('id'))}`",
            f"- Dimension: {_cell(finding.get('primary_dimension'))}",
            f"- Primary check: {_cell(finding.get('primary_check'))}",
            f"- Confidence: {_cell(finding.get('confidence'))}",
            f"- Verification: {_cell(finding.get('verification_state'))}",
            f"- Repair state: {_cell(finding.get('repair_state'))}",
            f"- Consequence: {_cell(finding.get('consequence'))}",
            f"- Root cause: {_cell(finding.get('root_cause'))}",
            f"- Owner: {_cell(finding.get('owner'))}",
            f"- Repair route: {_cell(finding.get('repair_route'))}",
            f"- Verifier: {_cell(finding.get('verifier'))}",
            "- Evidence:",
        ])
        for reference in finding.get("evidence_refs", []):
            if isinstance(reference, dict):
                lines.append(
                    f"  - `{_cell(reference.get('kind'))}:{_cell(reference.get('locator'))}` — "
                    f"{_cell(reference.get('claim'))}"
                )
        lines.append("")
    lines.extend([
        "## Interpretation Boundary",
        "",
        "Configured assets do not prove task use. Same-window repair verification updates repair state only; "
        "later comparable outcomes are required for outcome-supported learning claims.",
        "Historical reports are leads, not current findings; recheck every retained finding against the frozen snapshot.",
        "",
    ])
    return "\n".join(lines)


def _validate_evidence_privacy(evidence: dict[str, object]) -> list[str]:
    violations: set[str] = set()
    for text in all_strings(evidence):
        violations.update(private_data_matches(text))
    return sorted(violations)


def _validate_evidence_contract(
    evidence: dict[str, object],
    findings: dict[str, object],
) -> list[str]:
    errors: list[str] = []
    if evidence.get("schema_version") != 1:
        errors.append("evidence.schema_version must equal 1")
    if evidence.get("kind") != "agent-harness-evidence":
        errors.append("evidence.kind must equal agent-harness-evidence")
    evidence_scope = evidence.get("scope")
    findings_scope = findings.get("scope")
    if not isinstance(evidence_scope, dict) or not isinstance(findings_scope, dict):
        return errors + ["evidence and findings scopes must be objects"]
    for key in ("target", "mode", "locale", "decision", "acceptance_boundary", "output_mode"):
        if evidence_scope.get(key) != findings_scope.get(key):
            errors.append(f"evidence.scope.{key} must match findings.scope.{key}")
    if evidence_scope.get("snapshot") != findings_scope.get("snapshot"):
        errors.append("evidence.scope.snapshot must match findings.scope.snapshot")
    provider = evidence_scope.get("provider") or "none"
    providers = findings_scope.get("providers")
    if not isinstance(providers, list) or provider not in providers:
        errors.append("evidence provider must appear in findings.scope.providers")
    evidence_boundary = evidence.get("evidence_boundary")
    findings_boundary = findings.get("evidence_boundary")
    if not isinstance(evidence_boundary, dict) or not isinstance(findings_boundary, dict):
        errors.append("evidence.evidence_boundary must be an object")
    else:
        for key in ("included", "excluded", "unavailable"):
            evidence_values = evidence_boundary.get(key)
            findings_values = findings_boundary.get(key)
            if not isinstance(evidence_values, list) or any(
                not isinstance(value, str) or not value for value in evidence_values
            ):
                errors.append(f"evidence.evidence_boundary.{key} must contain strings")
                continue
            if not isinstance(evidence_values, list) or sorted(evidence_values) != sorted(findings_values or []):
                errors.append(f"evidence.evidence_boundary.{key} must match findings evidence boundary")
        if evidence_boundary.get("session_source_policy") != "explicit-files-or-roots-only":
            errors.append("evidence session_source_policy is invalid")
    for key in ("static", "sessions"):
        stage = evidence.get(key)
        if not isinstance(stage, dict) or stage.get("status") not in {
            "available",
            "constrained",
            "not_authorized",
            "not_applicable",
            "unavailable",
            "unobserved",
        }:
            errors.append(f"evidence.{key} has an invalid status")
    static = evidence.get("static")
    if isinstance(static, dict) and static.get("status") in {"available", "constrained"}:
        for key in ("root_resolution", "scan", "git", "agent_assets", "project"):
            if not isinstance(static.get(key), dict):
                errors.append(f"evidence.static.{key} must be an object")
        scan = static.get("scan")
        if isinstance(scan, dict):
            if scan.get("source") not in {"git-index", "filesystem"}:
                errors.append("evidence.static.scan.source is invalid")
            for key in (
                "files_observed", "files_omitted", "depth_limited_directory_count",
                "depth_limited_directories_omitted", "max_depth",
            ):
                if not isinstance(scan.get(key), int) or int(scan[key]) < 0:
                    errors.append(f"evidence.static.scan.{key} must be a non-negative integer")
            for key in ("depth_limited_directories", "skipped_directories"):
                if not isinstance(scan.get(key), list):
                    errors.append(f"evidence.static.scan.{key} must be an array")
        agent_assets = static.get("agent_assets")
        if isinstance(agent_assets, dict):
            for key in ("instructions", "skills", "hooks_and_settings"):
                value = agent_assets.get(key)
                if not isinstance(value, dict) or not isinstance(value.get("items"), list):
                    errors.append(f"evidence.static.agent_assets.{key} has an invalid shape")
        project = static.get("project")
        if isinstance(project, dict):
            for key in ("manifests", "ci", "tests", "package_scripts", "make_targets"):
                if not isinstance(project.get(key), dict):
                    errors.append(f"evidence.static.project.{key} must be an object")
    sessions = evidence.get("sessions")
    if (
        isinstance(sessions, dict)
        and sessions.get("status") == "unobserved"
        and isinstance(sessions.get("reason"), str)
    ):
        pass
    elif isinstance(sessions, dict) and sessions.get("status") in {"available", "unobserved"}:
        for key, expected_type in (
            ("provider", str),
            ("sessions", list),
            ("summary", dict),
            ("warnings", list),
            ("privacy", dict),
        ):
            if not isinstance(sessions.get(key), expected_type):
                errors.append(f"evidence.sessions.{key} has an invalid type")
        if sessions.get("provider") not in {"codex", "claude"}:
            errors.append("evidence.sessions.provider is invalid")
        summary = sessions.get("summary")
        if isinstance(summary, dict):
            for key in (
                "session_count", "user_turns", "tool_calls", "edit_calls",
                "validation_calls", "tool_failures", "malformed_lines", "unsupported_lines",
            ):
                if not isinstance(summary.get(key), int) or int(summary[key]) < 0:
                    errors.append(f"evidence.sessions.summary.{key} must be a non-negative integer")
    elif isinstance(sessions, dict) and sessions.get("status") in {"not_authorized", "unavailable"}:
        if not isinstance(sessions.get("reason"), str) or not sessions.get("reason"):
            errors.append("evidence.sessions.reason is required")
    return errors


def render_run(
    findings_path: Path,
    out_dir: Path,
    *,
    evidence_paths: list[Path] | None = None,
    run_id: str | None = None,
) -> dict[str, object]:
    findings = load_json(findings_path)
    evidences = [load_json(path) for path in (evidence_paths or [])]
    validation = validate_document(findings, evidence_documents=evidences)
    if validation["status"] != "pass":
        details = list(validation["errors"]) + list(validation["warnings"])
        raise ValueError("strict findings validation failed: " + "; ".join(str(item) for item in details))
    for evidence in evidences:
        contract_errors = _validate_evidence_contract(evidence, findings)
        if contract_errors:
            raise ValueError("evidence contract validation failed: " + "; ".join(contract_errors))
        violations = _validate_evidence_privacy(evidence)
        if violations:
            raise ValueError(f"evidence privacy validation failed: {', '.join(violations)}")

    scope = findings["scope"]
    assert isinstance(scope, dict)
    target_slug = slug(str(scope.get("target") or "target"))
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    resolved_run_id = run_id or f"{timestamp}-{target_slug}"
    if slug(resolved_run_id) != resolved_run_id:
        raise ValueError("run id must be a lowercase slug")
    output_root = out_dir.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = output_root / resolved_run_id
    lock_path = output_root / f".{resolved_run_id}.publish.lock"
    try:
        lock_descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise RuntimeError(f"report publication already in progress: {resolved_run_id}") from error
    stage: Path | None = None
    try:
        if run_dir.exists():
            raise FileExistsError(f"refusing to replace existing run directory: {resolved_run_id}")
        stage = Path(tempfile.mkdtemp(prefix=f".{resolved_run_id}.staging-", dir=output_root))
        try:
            write_json_atomic(stage / "findings.json", findings)
            evidence_artifacts: list[str] = []
            for index, evidence in enumerate(evidences, start=1):
                scope = evidence.get("scope")
                role = scope.get("episode_role") if isinstance(scope, dict) else None
                filename = (
                    "evidence.json"
                    if len(evidences) == 1
                    else f"evidence-{role or index}.json"
                )
                write_json_atomic(stage / filename, evidence)
                evidence_artifacts.append(filename)
            _write_text_durable(stage / "report.md", _render_markdown(findings))
            _fsync_directory(stage)
            if run_dir.exists():
                raise FileExistsError(f"refusing to replace existing run directory: {resolved_run_id}")
            _rename_directory_no_replace(stage, run_dir)
            stage = None
            _fsync_directory(output_root)
        except Exception:
            if stage is not None and stage.exists():
                shutil.rmtree(stage, ignore_errors=False)
            raise
    finally:
        os.close(lock_descriptor)
        lock_path.unlink()
        _fsync_directory(output_root)
    artifacts = ["findings.json", "report.md"] + evidence_artifacts
    return {
        "status": validation["status"],
        "run_id": resolved_run_id,
        "run_dir": f"{out_dir.name}/{resolved_run_id}",
        "artifacts": artifacts,
        "validation": validation,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--findings", required=True)
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--out", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = render_run(
        Path(args.findings),
        Path(args.out),
        evidence_paths=[Path(path) for path in args.evidence],
        run_id=args.run_id,
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"report render: {result['status']}")
        print(f"run directory: {result['run_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
