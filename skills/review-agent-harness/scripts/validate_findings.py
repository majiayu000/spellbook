#!/usr/bin/env python3
"""Validate the review-agent-harness findings contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from harness_common import all_strings, load_json, private_data_matches


DIMENSION_IDS = (
    "task-contract",
    "execution-control",
    "verification-closure",
    "delivery-safety",
    "learning-retention",
)
CHECK_IDS_BY_DIMENSION = {
    "task-contract": ("goal-understanding", "relevant-context", "scope-boundary"),
    "execution-control": ("instruction-led-start", "supported-operation", "permission-boundary"),
    "verification-closure": ("relevant-check", "failure-repair", "validate-again"),
    "delivery-safety": ("acceptance-evidence", "high-risk-approval", "rollback-recovery"),
    "learning-retention": ("lifecycle-repeat-detection", "loop-engineering", "later-validation"),
}
CHECK_IDS = tuple(check_id for dimension_id in DIMENSION_IDS for check_id in CHECK_IDS_BY_DIMENSION[dimension_id])
DIMENSION_STATUSES = {"healthy", "constrained", "blocked", "unobserved", "not_applicable"}
EVIDENCE_STATES = {
    "present",
    "reachable",
    "exercised",
    "outcome_supported",
    "missing",
    "unobserved",
    "not_applicable",
}
SEVERITIES = {"critical", "high", "medium", "low"}
CONFIDENCE_LEVELS = {"high", "medium", "low"}
VERIFICATION_STATES = {"confirmed", "unverified", "unavailable", "not_required"}
REPAIR_STATES = {"not_started", "partial", "verified", "blocked"}
SNAPSHOT_BASELINES = {"current_checkout", "historical_artifact", "mixed_snapshot", "filesystem_state"}
TARGET_RELATIONS = {
    "exact_git_root",
    "inside_git_worktree",
    "contains_nested_git_root",
    "non_git_directory",
    "unknown",
}
VERIFICATION_PURPOSES = {"candidate_refutation", "targeted_reproduction", "mapped_check", "final_recheck"}
VERIFICATION_RESULTS = {"supports", "refutes", "passes", "fails", "inconclusive", "unavailable"}
EVIDENCE_SCORE_CEILINGS = {
    "present": 74,
    "reachable": 84,
    "exercised": 94,
    "outcome_supported": 100,
    "missing": 59,
    "unobserved": 59,
}
REFERENCE_KINDS = {"file", "command", "artifact", "session_fact", "policy", "runtime"}
REFERENCE_PURPOSES = {
    "baseline_episode",
    "later_episode",
    "route_mapping",
    "outcome_check",
    "guardrail_check",
}
FINDING_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:--[a-z0-9]+(?:-[a-z0-9]+)*){2,}$")
RUN_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _require_object(value: object, location: str, errors: list[str]) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    errors.append(f"{location} must be an object")
    return {}


def _require_list(value: object, location: str, errors: list[str]) -> list[object]:
    if isinstance(value, list):
        return value
    errors.append(f"{location} must be an array")
    return []


def _require_text(owner: dict[str, object], key: str, location: str, errors: list[str]) -> str:
    value = owner.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{location}.{key} must be a non-empty string")
        return ""
    return value.strip()


def _validate_references(value: object, location: str, errors: list[str]) -> list[dict[str, object]]:
    references = _require_list(value, location, errors)
    normalized: list[dict[str, object]] = []
    for index, item in enumerate(references):
        ref_location = f"{location}[{index}]"
        reference = _require_object(item, ref_location, errors)
        kind = _require_text(reference, "kind", ref_location, errors)
        _require_text(reference, "locator", ref_location, errors)
        _require_text(reference, "claim", ref_location, errors)
        if kind and kind not in REFERENCE_KINDS:
            errors.append(f"{ref_location}.kind must be one of {sorted(REFERENCE_KINDS)}")
        purpose = reference.get("purpose")
        if purpose is not None and purpose not in REFERENCE_PURPOSES:
            errors.append(f"{ref_location}.purpose is invalid")
        normalized.append(reference)
    return normalized


def _validate_later_effect_references(
    references: list[dict[str, object]],
    location: str,
    errors: list[str],
) -> None:
    by_purpose = {
        str(reference.get("purpose")): reference
        for reference in references
        if reference.get("purpose") in REFERENCE_PURPOSES
    }
    purpose_counts = {
        purpose: sum(1 for reference in references if reference.get("purpose") == purpose)
        for purpose in REFERENCE_PURPOSES
    }
    duplicates = sorted(purpose for purpose, count in purpose_counts.items() if count > 1)
    if duplicates:
        errors.append(f"{location}: outcome_supported has duplicate purposes: {', '.join(duplicates)}")
    missing = sorted(REFERENCE_PURPOSES - set(by_purpose))
    if missing:
        errors.append(f"{location}: outcome_supported is missing purposes: {', '.join(missing)}")
        return
    baseline = by_purpose["baseline_episode"]
    later = by_purpose["later_episode"]
    for purpose, reference in (("baseline_episode", baseline), ("later_episode", later)):
        if reference.get("kind") != "session_fact":
            errors.append(f"{location}: {purpose} must use a session_fact reference")
        if not isinstance(reference.get("comparison_basis"), str) or not str(reference["comparison_basis"]).strip():
            errors.append(f"{location}: {purpose} requires comparison_basis")
        if reference.get("mechanism_category") not in {"edit", "validation"}:
            errors.append(f"{location}: {purpose} requires edit or validation mechanism_category")
    if baseline.get("comparison_basis") != later.get("comparison_basis"):
        errors.append(f"{location}: baseline and later comparison_basis must match")
    if baseline.get("mechanism_category") != later.get("mechanism_category"):
        errors.append(f"{location}: baseline and later mechanism_category must match")
    if baseline.get("locator") != "episode:baseline" or later.get("locator") != "episode:later":
        errors.append(f"{location}: Episode locators must be episode:baseline and episode:later")
    if by_purpose["route_mapping"].get("kind") not in {"file", "policy"}:
        errors.append(f"{location}: route_mapping must use file or policy evidence")
    for purpose in ("outcome_check", "guardrail_check"):
        if by_purpose[purpose].get("kind") not in {"command", "artifact", "runtime"}:
            errors.append(f"{location}: {purpose} must use command, artifact, or runtime evidence")


def _validate_later_effect_envelopes(
    findings: dict[str, object],
    evidence_documents: list[dict[str, object]],
    errors: list[str],
) -> None:
    if len(evidence_documents) != 2:
        errors.append("outcome_supported requires exactly two evidence envelopes")
        return
    findings_scope = findings.get("scope")
    assert isinstance(findings_scope, dict)
    by_role: dict[str, dict[str, object]] = {}
    for index, evidence in enumerate(evidence_documents):
        if evidence.get("schema_version") != 1 or evidence.get("kind") != "agent-harness-evidence":
            errors.append(f"evidence[{index}] is not an agent-harness-evidence envelope")
            continue
        scope = evidence.get("scope")
        sessions = evidence.get("sessions")
        if not isinstance(scope, dict) or not isinstance(sessions, dict):
            errors.append(f"evidence[{index}] requires scope and sessions objects")
            continue
        for key in ("target", "snapshot", "mode", "locale", "decision", "acceptance_boundary", "output_mode"):
            if scope.get(key) != findings_scope.get(key):
                errors.append(f"evidence[{index}].scope.{key} must match findings")
        role = scope.get("episode_role")
        if role not in {"baseline", "later"} or role in by_role:
            errors.append(f"evidence[{index}] requires a unique baseline or later episode_role")
            continue
        if scope.get("provider") not in {"codex", "claude"}:
            errors.append(f"evidence[{index}] requires a supported provider")
        if scope.get("provider") not in findings_scope.get("providers", []):
            errors.append(f"evidence[{index}] provider must appear in findings.scope.providers")
        if sessions.get("status") != "available":
            errors.append(f"evidence[{index}] Session stage must be available")
        by_role[str(role)] = evidence
    if set(by_role) != {"baseline", "later"}:
        return
    baseline_scope = by_role["baseline"]["scope"]
    later_scope = by_role["later"]["scope"]
    assert isinstance(baseline_scope, dict) and isinstance(later_scope, dict)
    for key in ("comparison_basis", "mechanism_category"):
        if not baseline_scope.get(key) or baseline_scope.get(key) != later_scope.get(key):
            errors.append(f"baseline and later evidence must share {key}")
    dimensions = findings.get("dimensions")
    learning = next(
        (
            row
            for row in dimensions
            if isinstance(row, dict) and row.get("id") == "learning-retention"
        ),
        None,
    ) if isinstance(dimensions, list) else None
    references = learning.get("evidence_refs") if isinstance(learning, dict) else None
    baseline_reference = next(
        (
            reference
            for reference in references
            if isinstance(reference, dict) and reference.get("purpose") == "baseline_episode"
        ),
        None,
    ) if isinstance(references, list) else None
    if isinstance(baseline_reference, dict):
        for key in ("comparison_basis", "mechanism_category"):
            if baseline_reference.get(key) != baseline_scope.get(key):
                errors.append(f"learning-retention references must match evidence {key}")
    mechanism = later_scope.get("mechanism_category")
    if mechanism not in {"edit", "validation"}:
        errors.append("later evidence mechanism_category is invalid")
        return
    summary = by_role["later"].get("sessions", {}).get("summary", {})
    count_key = "edit_calls" if mechanism == "edit" else "validation_calls"
    if not isinstance(summary, dict) or not isinstance(summary.get(count_key), int) or int(summary[count_key]) < 1:
        errors.append(f"later evidence must exercise the declared {mechanism} mechanism")


def validate_document(
    document: dict[str, object],
    *,
    evidence_documents: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Return errors, warnings, and a compact validation summary."""

    errors: list[str] = []
    warnings: list[str] = []
    if document.get("schema_version") != 1:
        errors.append("schema_version must equal 1")
    if document.get("kind") != "agent-harness-findings":
        errors.append("kind must equal agent-harness-findings")
    _require_text(document, "overview", "document", errors)

    scope = _require_object(document.get("scope"), "scope", errors)
    _require_text(scope, "target", "scope", errors)
    mode = _require_text(scope, "mode", "scope", errors)
    if mode and mode not in {"static", "episode", "longitudinal"}:
        errors.append("scope.mode must be static, episode, or longitudinal")
    locale = _require_text(scope, "locale", "scope", errors)
    if locale and locale not in {"en", "zh-CN"}:
        errors.append("scope.locale must be en or zh-CN")
    providers = _require_list(scope.get("providers"), "scope.providers", errors)
    if any(not isinstance(provider, str) or provider not in {"codex", "claude", "none"} for provider in providers):
        errors.append("scope.providers contains an unsupported provider")
    _require_text(scope, "decision", "scope", errors)
    _require_text(scope, "acceptance_boundary", "scope", errors)
    output_mode = _require_text(scope, "output_mode", "scope", errors)
    if output_mode and output_mode not in {"inline", "durable"}:
        errors.append("scope.output_mode must be inline or durable")
    snapshot = _require_object(scope.get("snapshot"), "scope.snapshot", errors)
    baseline = _require_text(snapshot, "baseline", "scope.snapshot", errors)
    target_relation = _require_text(snapshot, "target_relation", "scope.snapshot", errors)
    if baseline and baseline not in SNAPSHOT_BASELINES:
        errors.append("scope.snapshot.baseline is invalid")
    if target_relation and target_relation not in TARGET_RELATIONS:
        errors.append("scope.snapshot.target_relation is invalid")
    if target_relation == "contains_nested_git_root":
        errors.append("scope.snapshot.target_relation contains a nested Git root; retarget the exact repository before scoring")

    boundary = _require_object(document.get("evidence_boundary"), "evidence_boundary", errors)
    for key in ("included", "excluded", "unavailable"):
        values = _require_list(boundary.get(key), f"evidence_boundary.{key}", errors)
        if any(not isinstance(value, str) or not value.strip() for value in values):
            errors.append(f"evidence_boundary.{key} must contain non-empty strings")

    dimensions = _require_list(document.get("dimensions"), "dimensions", errors)
    seen_dimensions: set[str] = set()
    dimensions_by_id: dict[str, dict[str, object]] = {}
    claims_later_effect = False
    for index, item in enumerate(dimensions):
        location = f"dimensions[{index}]"
        dimension = _require_object(item, location, errors)
        dimension_id = _require_text(dimension, "id", location, errors)
        status = _require_text(dimension, "status", location, errors)
        evidence_state = _require_text(dimension, "evidence_state", location, errors)
        confidence = _require_text(dimension, "confidence", location, errors)
        _require_text(dimension, "summary", location, errors)
        _require_text(dimension, "score_rationale", location, errors)
        score = dimension.get("score")
        if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
            errors.append(f"{location}.score must be an integer from 0 through 100")
        references = _validate_references(dimension.get("evidence_refs"), f"{location}.evidence_refs", errors)
        if dimension_id:
            if dimension_id not in DIMENSION_IDS:
                errors.append(f"{location}.id is not a supported dimension")
            if dimension_id in seen_dimensions:
                errors.append(f"duplicate dimension id: {dimension_id}")
            seen_dimensions.add(dimension_id)
            dimensions_by_id[dimension_id] = dimension
        if status and status not in DIMENSION_STATUSES:
            errors.append(f"{location}.status is invalid")
        if evidence_state and evidence_state not in EVIDENCE_STATES:
            errors.append(f"{location}.evidence_state is invalid")
        if confidence and confidence not in CONFIDENCE_LEVELS:
            errors.append(f"{location}.confidence is invalid")
        if status == "healthy" and evidence_state not in {"reachable", "exercised", "outcome_supported"}:
            errors.append(f"{location}: healthy requires reachable or stronger evidence")
        if status == "unobserved" and evidence_state != "unobserved":
            errors.append(f"{location}: unobserved status requires unobserved evidence")
        if status == "not_applicable" and evidence_state != "not_applicable":
            errors.append(f"{location}: not_applicable status requires not_applicable evidence")
        if dimension_id == "learning-retention" and status == "healthy" and evidence_state != "outcome_supported":
            errors.append(f"{location}: healthy learning-retention requires a later outcome")
        if dimension_id == "learning-retention" and evidence_state == "outcome_supported":
            claims_later_effect = True
            _validate_later_effect_references(references, location, errors)
        if status not in {"unobserved", "not_applicable"} and not references:
            errors.append(f"{location}: observed dimension requires at least one evidence ref")
    missing_dimensions = sorted(set(DIMENSION_IDS) - seen_dimensions)
    if missing_dimensions:
        errors.append(f"dimensions missing required ids: {', '.join(missing_dimensions)}")
    if len(dimensions) != len(DIMENSION_IDS):
        errors.append(f"dimensions must contain exactly {len(DIMENSION_IDS)} rows")

    checks = _require_list(document.get("checks"), "checks", errors)
    checks_by_id: dict[str, dict[str, object]] = {}
    check_finding_refs: dict[str, set[str]] = {}
    for index, item in enumerate(checks):
        location = f"checks[{index}]"
        check = _require_object(item, location, errors)
        check_id = _require_text(check, "id", location, errors)
        dimension_id = _require_text(check, "dimension", location, errors)
        status = _require_text(check, "status", location, errors)
        evidence_state = _require_text(check, "evidence_state", location, errors)
        confidence = _require_text(check, "confidence", location, errors)
        _require_text(check, "summary", location, errors)
        references = _validate_references(check.get("evidence_refs"), f"{location}.evidence_refs", errors)
        finding_refs = _require_list(check.get("finding_refs"), f"{location}.finding_refs", errors)
        if any(not isinstance(value, str) or not value for value in finding_refs):
            errors.append(f"{location}.finding_refs must contain non-empty strings")
        if len(set(finding_refs)) != len(finding_refs):
            errors.append(f"{location}.finding_refs must not contain duplicates")
        if check_id:
            if check_id not in CHECK_IDS:
                errors.append(f"{location}.id is not a supported check")
            if check_id in checks_by_id:
                errors.append(f"duplicate check id: {check_id}")
            checks_by_id[check_id] = check
            check_finding_refs[check_id] = {str(value) for value in finding_refs if isinstance(value, str)}
        if dimension_id not in DIMENSION_IDS:
            errors.append(f"{location}.dimension is invalid")
        elif check_id and check_id not in CHECK_IDS_BY_DIMENSION[dimension_id]:
            errors.append(f"{location}.id does not belong to {dimension_id}")
        if status not in DIMENSION_STATUSES:
            errors.append(f"{location}.status is invalid")
        if evidence_state not in EVIDENCE_STATES:
            errors.append(f"{location}.evidence_state is invalid")
        if confidence not in CONFIDENCE_LEVELS:
            errors.append(f"{location}.confidence is invalid")
        if status == "healthy" and evidence_state not in {"reachable", "exercised", "outcome_supported"}:
            errors.append(f"{location}: healthy requires reachable or stronger evidence")
        if status == "unobserved" and evidence_state != "unobserved":
            errors.append(f"{location}: unobserved status requires unobserved evidence")
        if status == "not_applicable" and evidence_state != "not_applicable":
            errors.append(f"{location}: not_applicable status requires not_applicable evidence")
        if status not in {"unobserved", "not_applicable"} and not references:
            errors.append(f"{location}: observed check requires at least one evidence ref")
    missing_checks = sorted(set(CHECK_IDS) - set(checks_by_id))
    if missing_checks:
        errors.append(f"checks missing required ids: {', '.join(missing_checks)}")
    if len(checks) != len(CHECK_IDS):
        errors.append(f"checks must contain exactly {len(CHECK_IDS)} rows")

    for dimension_id, dimension in dimensions_by_id.items():
        dimension_checks = [checks_by_id.get(check_id) for check_id in CHECK_IDS_BY_DIMENSION[dimension_id]]
        if any(check is None for check in dimension_checks):
            continue
        applicable_checks = [
            check for check in dimension_checks
            if isinstance(check, dict) and check.get("evidence_state") != "not_applicable"
        ]
        ceilings = [
            EVIDENCE_SCORE_CEILINGS[str(check.get("evidence_state"))]
            for check in applicable_checks
            if check.get("evidence_state") in EVIDENCE_SCORE_CEILINGS
        ]
        score = dimension.get("score")
        if isinstance(score, int) and not isinstance(score, bool):
            ceiling = min(ceilings) if ceilings else 59
            if score > ceiling:
                errors.append(f"dimension {dimension_id}.score exceeds evidence ceiling {ceiling}")
        if dimension.get("status") == "healthy" and any(
            isinstance(check, dict) and check.get("status") not in {"healthy", "not_applicable"}
            for check in dimension_checks
        ):
            errors.append(f"dimension {dimension_id} cannot be healthy while a check is unresolved")

    verification_runs = _require_list(document.get("verification_runs"), "verification_runs", errors)
    runs_by_id: dict[str, dict[str, object]] = {}
    for index, item in enumerate(verification_runs):
        location = f"verification_runs[{index}]"
        run = _require_object(item, location, errors)
        run_id = _require_text(run, "id", location, errors)
        purpose = _require_text(run, "purpose", location, errors)
        result = _require_text(run, "result", location, errors)
        _require_text(run, "summary", location, errors)
        final_state = run.get("final_state")
        exit_code = run.get("exit_code")
        if run_id:
            if not RUN_ID_RE.fullmatch(run_id):
                errors.append(f"{location}.id must be a lowercase slug")
            if run_id in runs_by_id:
                errors.append(f"duplicate verification run id: {run_id}")
            runs_by_id[run_id] = run
        if purpose not in VERIFICATION_PURPOSES:
            errors.append(f"{location}.purpose is invalid")
        if result not in VERIFICATION_RESULTS:
            errors.append(f"{location}.result is invalid")
        if not isinstance(final_state, bool):
            errors.append(f"{location}.final_state must be boolean")
        if result == "unavailable":
            if exit_code is not None:
                errors.append(f"{location}.exit_code must be null when unavailable")
        elif isinstance(exit_code, bool) or not isinstance(exit_code, int) or exit_code < 0:
            errors.append(f"{location}.exit_code must be a non-negative integer")
    if claims_later_effect:
        if mode != "longitudinal" or not any(provider in {"codex", "claude"} for provider in providers):
            errors.append("outcome_supported requires longitudinal mode and a supported provider")
        _validate_later_effect_envelopes(document, evidence_documents or [], errors)

    findings = _require_list(document.get("findings"), "findings", errors)
    finding_ids: set[str] = set()
    for index, item in enumerate(findings):
        location = f"findings[{index}]"
        finding = _require_object(item, location, errors)
        finding_id = _require_text(finding, "id", location, errors)
        for key in ("title", "consequence", "root_cause", "owner", "repair_route", "verifier"):
            _require_text(finding, key, location, errors)
        severity = _require_text(finding, "severity", location, errors)
        confidence = _require_text(finding, "confidence", location, errors)
        primary_dimension = _require_text(finding, "primary_dimension", location, errors)
        primary_check = _require_text(finding, "primary_check", location, errors)
        evidence_state = _require_text(finding, "evidence_state", location, errors)
        verification_state = _require_text(finding, "verification_state", location, errors)
        repair_state = _require_text(finding, "repair_state", location, errors)
        references = _validate_references(finding.get("evidence_refs"), f"{location}.evidence_refs", errors)
        if finding_id:
            if not FINDING_ID_RE.fullmatch(finding_id):
                errors.append(f"{location}.id must be three or more stable slug segments separated by --")
            if finding_id in finding_ids:
                errors.append(f"duplicate finding id: {finding_id}")
            finding_ids.add(finding_id)
        if severity and severity not in SEVERITIES:
            errors.append(f"{location}.severity is invalid")
        if confidence and confidence not in CONFIDENCE_LEVELS:
            errors.append(f"{location}.confidence is invalid")
        if primary_dimension and primary_dimension not in DIMENSION_IDS:
            errors.append(f"{location}.primary_dimension is invalid")
        if primary_check and primary_check not in CHECK_IDS:
            errors.append(f"{location}.primary_check is invalid")
        elif primary_dimension in DIMENSION_IDS and primary_check not in CHECK_IDS_BY_DIMENSION[primary_dimension]:
            errors.append(f"{location}.primary_check does not belong to primary_dimension")
        if evidence_state and evidence_state not in EVIDENCE_STATES - {"unobserved", "not_applicable"}:
            errors.append(f"{location}.evidence_state cannot be unobserved or not_applicable")
        if verification_state and verification_state not in VERIFICATION_STATES:
            errors.append(f"{location}.verification_state is invalid")
        if repair_state and repair_state not in REPAIR_STATES:
            errors.append(f"{location}.repair_state is invalid")
        if not references:
            errors.append(f"{location}: finding requires at least one evidence ref")
        if severity in {"critical", "high"} and verification_state != "confirmed":
            warnings.append(f"{location}: {severity} finding is not independently confirmed")
        if severity in {"critical", "high"} and verification_state == "confirmed":
            command_locators = {
                str(reference.get("locator"))
                for reference in references
                if reference.get("kind") == "command"
            }
            supporting_runs = [
                runs_by_id[run_id]
                for run_id in command_locators & set(runs_by_id)
                if runs_by_id[run_id].get("purpose") in {"candidate_refutation", "targeted_reproduction"}
                and runs_by_id[run_id].get("result") == "supports"
                and runs_by_id[run_id].get("final_state") is True
            ]
            if not supporting_runs:
                errors.append(f"{location}: confirmed {severity} finding requires a final-state adversarial verification run")
        if finding_id and primary_check and finding_id not in check_finding_refs.get(primary_check, set()):
            errors.append(f"{location}: primary check must reverse-link the finding id")

    for check_id, references in check_finding_refs.items():
        unknown = sorted(references - finding_ids)
        if unknown:
            errors.append(f"check {check_id} references unknown findings: {', '.join(unknown)}")

    priority_moves = _require_list(document.get("priority_moves"), "priority_moves", errors)
    if len(priority_moves) > 3:
        errors.append("priority_moves may contain at most three finding ids")
    for index, finding_id in enumerate(priority_moves):
        if not isinstance(finding_id, str) or finding_id not in finding_ids:
            errors.append(f"priority_moves[{index}] must reference an existing finding id")
    if len(set(priority_moves)) != len(priority_moves):
        errors.append("priority_moves must not contain duplicates")

    privacy_hits: dict[str, int] = {}
    for text in all_strings(document):
        for rule_id in private_data_matches(text):
            privacy_hits[rule_id] = privacy_hits.get(rule_id, 0) + 1
    for rule_id, count in sorted(privacy_hits.items()):
        errors.append(f"reader output violates privacy rule {rule_id} ({count} occurrence(s))")

    return {
        "status": "fail" if errors else "warn" if warnings else "pass",
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "dimension_count": len(dimensions),
            "check_count": len(checks),
            "finding_count": len(findings),
            "priority_move_count": len(priority_moves),
            "verification_run_count": len(verification_runs),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--evidence", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.input == "-":
        document = json.load(sys.stdin)
        if not isinstance(document, dict):
            raise ValueError("expected a JSON object on stdin")
    else:
        document = load_json(Path(args.input))
    result = validate_document(
        document,
        evidence_documents=[load_json(Path(path)) for path in args.evidence],
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"findings validation: {result['status']}")
        for error in result["errors"]:
            print(f"ERROR: {error}")
        for warning in result["warnings"]:
            print(f"WARN: {warning}")
    if result["status"] == "fail":
        return 1
    if args.strict and result["status"] == "warn":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
