#!/usr/bin/env python3
"""Update a longitudinal findings ledger without guessing resolution."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

from harness_common import (
    all_strings,
    load_json,
    private_data_matches,
    require_canonical_artifact_path,
    validate_target_binding,
    write_json_atomic,
)
from validate_findings import (
    DIMENSION_IDS,
    FINDING_ID_RE,
    REFERENCE_KINDS,
    REPAIR_STATES,
    SEVERITIES,
    validate_document,
)


def load_resolution_confirmations(path: Path | None) -> dict[str, dict[str, object]]:
    if path is None:
        return {}
    document = load_json(path)
    if document.get("schema_version") != 1 or document.get("kind") != "agent-harness-resolution-confirmations":
        raise ValueError("unsupported resolution confirmations contract")
    items = document.get("confirmations")
    if not isinstance(items, list):
        raise ValueError("resolution confirmations must contain a confirmations array")
    confirmations: dict[str, dict[str, object]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"confirmations[{index}] must be an object")
        finding_id = item.get("id")
        verifier = item.get("verifier")
        reference = item.get("evidence_ref")
        if not isinstance(finding_id, str) or not finding_id:
            raise ValueError(f"confirmations[{index}].id must be a non-empty string")
        if finding_id in confirmations:
            raise ValueError(f"duplicate resolution confirmation id: {finding_id}")
        if not isinstance(verifier, str) or not verifier.strip():
            raise ValueError(f"confirmations[{index}].verifier must be a non-empty string")
        if not isinstance(reference, dict):
            raise ValueError(f"confirmations[{index}].evidence_ref must be an object")
        if reference.get("kind") not in REFERENCE_KINDS:
            raise ValueError(f"confirmations[{index}].evidence_ref.kind is invalid")
        for key in ("locator", "claim"):
            if not isinstance(reference.get(key), str) or not str(reference[key]).strip():
                raise ValueError(f"confirmations[{index}].evidence_ref.{key} must be non-empty")
        privacy_hits = {
            rule_id
            for text in all_strings(item)
            for rule_id in private_data_matches(text)
        }
        if privacy_hits:
            raise ValueError(f"confirmation {finding_id} violates privacy: {', '.join(sorted(privacy_hits))}")
        confirmations[finding_id] = item
    return confirmations


def _validated_previous_ledger(
    previous: dict[str, object] | None,
    *,
    target: str,
    target_id: str,
) -> dict[str, object]:
    if previous is None:
        return {
            "schema_version": 1,
            "kind": "agent-harness-ledger",
            "target": target,
            "target_id": target_id,
            "runs": [],
            "findings": [],
        }
    if previous.get("schema_version") != 1 or previous.get("kind") != "agent-harness-ledger":
        raise ValueError("unsupported ledger contract")
    if previous.get("target") != target:
        raise ValueError("ledger target does not match findings target")
    if previous.get("target_id") != target_id:
        raise ValueError("ledger target identity does not match findings target")
    privacy_hits = {
        rule_id
        for text in all_strings(previous)
        for rule_id in private_data_matches(text)
    }
    if privacy_hits:
        raise ValueError(f"ledger violates privacy: {', '.join(sorted(privacy_hits))}")
    runs = previous.get("runs")
    items = previous.get("findings")
    if not isinstance(runs, list) or any(not isinstance(item, dict) for item in runs):
        raise ValueError("ledger.runs must contain only objects")
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise ValueError("ledger.findings must contain only objects")
    for index, run in enumerate(runs):
        try:
            date.fromisoformat(str(run.get("date")))
        except ValueError as error:
            raise ValueError(f"ledger.runs[{index}].date must be an ISO date") from error
        if (
            run.get("target") != target
            or run.get("target_id") != target_id
            or run.get("mode") not in {"static", "episode", "longitudinal"}
        ):
            raise ValueError(f"ledger.runs[{index}] has an invalid target or mode")
        for key in ("finding_count", "resolution_confirmation_count"):
            if not isinstance(run.get(key), int) or int(run[key]) < 0:
                raise ValueError(f"ledger.runs[{index}].{key} must be a non-negative integer")
    required_entry_fields = {
        "id", "dimension", "severity", "title", "owner", "verifier", "status",
        "repair_state", "first_seen", "last_seen", "regression", "recheck_required",
    }
    for index, item in enumerate(items):
        missing = sorted(required_entry_fields - set(item))
        if missing:
            raise ValueError(f"ledger.findings[{index}] missing fields: {', '.join(missing)}")
        if not isinstance(item.get("id"), str) or not FINDING_ID_RE.fullmatch(str(item["id"])):
            raise ValueError(f"ledger.findings[{index}].id is invalid")
        for key in ("title", "owner", "verifier"):
            if not isinstance(item.get(key), str) or not str(item[key]).strip():
                raise ValueError(f"ledger.findings[{index}].{key} must be non-empty")
        if item.get("status") not in {"open", "resolved"}:
            raise ValueError(f"ledger.findings[{index}].status is invalid")
        if item.get("dimension") not in DIMENSION_IDS:
            raise ValueError(f"ledger.findings[{index}].dimension is invalid")
        if item.get("severity") not in SEVERITIES:
            raise ValueError(f"ledger.findings[{index}].severity is invalid")
        if item.get("repair_state") not in REPAIR_STATES:
            raise ValueError(f"ledger.findings[{index}].repair_state is invalid")
        for key in ("first_seen", "last_seen"):
            try:
                date.fromisoformat(str(item.get(key)))
            except ValueError as error:
                raise ValueError(f"ledger.findings[{index}].{key} must be an ISO date") from error
        if not isinstance(item.get("regression"), bool) or not isinstance(item.get("recheck_required"), bool):
            raise ValueError(f"ledger.findings[{index}] regression fields must be booleans")
        if item.get("status") == "resolved":
            confirmation = item.get("resolution_confirmation")
            if not isinstance(confirmation, dict):
                raise ValueError(f"ledger.findings[{index}] resolved status requires confirmation")
            if confirmation.get("verifier") != item.get("verifier"):
                raise ValueError(f"ledger.findings[{index}] resolution verifier is invalid")
            try:
                date.fromisoformat(str(confirmation.get("date")))
            except ValueError as error:
                raise ValueError(f"ledger.findings[{index}] resolution date is invalid") from error
            evidence_ref = confirmation.get("evidence_ref")
            if not isinstance(evidence_ref, dict):
                raise ValueError(f"ledger.findings[{index}] resolution evidence is required")
            if evidence_ref.get("kind") not in REFERENCE_KINDS or any(
                not isinstance(evidence_ref.get(key), str) or not str(evidence_ref[key]).strip()
                for key in ("locator", "claim")
            ):
                raise ValueError(f"ledger.findings[{index}] resolution evidence is invalid")
    ids = [item.get("id") for item in items]
    if len(set(ids)) != len(ids):
        raise ValueError("ledger contains duplicate finding ids")
    return previous


def _ledger_entry(finding: dict[str, object], *, run_date: str) -> dict[str, object]:
    return {
        "id": finding["id"],
        "dimension": finding["primary_dimension"],
        "severity": finding["severity"],
        "title": finding["title"],
        "owner": finding["owner"],
        "verifier": finding["verifier"],
        "status": "open",
        "repair_state": finding["repair_state"],
        "first_seen": run_date,
        "last_seen": run_date,
        "regression": False,
        "recheck_required": False,
    }


def update_ledger(
    findings: dict[str, object],
    previous: dict[str, object] | None,
    *,
    run_date: str,
    resolution_confirmations: dict[str, dict[str, object]],
    evidence_documents: list[dict[str, object]],
) -> tuple[dict[str, object], dict[str, int]]:
    try:
        date.fromisoformat(run_date)
    except ValueError as error:
        raise ValueError("run_date must be an ISO date") from error
    validation = validate_document(findings, evidence_documents=evidence_documents)
    if validation["status"] != "pass":
        details = list(validation["errors"]) + list(validation["warnings"])
        raise ValueError("strict findings validation failed: " + "; ".join(str(item) for item in details))
    scope = findings.get("scope")
    assert isinstance(scope, dict)
    target = str(scope["target"])
    target_id = str(scope["target_id"])
    ledger = _validated_previous_ledger(previous, target=target, target_id=target_id)
    previous_items = ledger.get("findings")
    if not isinstance(previous_items, list):
        raise ValueError("ledger.findings must be an array")
    previous_by_id = {
        str(item["id"]): dict(item)
        for item in previous_items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    current_items = findings.get("findings")
    assert isinstance(current_items, list)
    current_by_id = {
        str(item["id"]): item
        for item in current_items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    eligible_confirmations = {
        finding_id
        for finding_id, entry in previous_by_id.items()
        if finding_id not in current_by_id and entry.get("status") != "resolved"
    }
    invalid_confirmations = sorted(set(resolution_confirmations) - eligible_confirmations)
    if invalid_confirmations:
        raise ValueError(
            "cannot confirm present, resolved, or unknown finding ids: "
            + ", ".join(invalid_confirmations)
        )

    summary = {"new": 0, "still_open": 0, "resolved": 0, "regression": 0, "recheck_required": 0}
    next_items: list[dict[str, object]] = []
    for finding_id, finding in current_by_id.items():
        previous_entry = previous_by_id.get(finding_id)
        if previous_entry is None:
            next_items.append(_ledger_entry(finding, run_date=run_date))
            summary["new"] += 1
            continue
        if previous_entry.get("verifier") != finding.get("verifier"):
            raise ValueError(f"finding verifier drifted for {finding_id}")
        was_resolved = previous_entry.get("status") == "resolved"
        previous_entry.update({
            "dimension": finding["primary_dimension"],
            "severity": finding["severity"],
            "title": finding["title"],
            "owner": finding["owner"],
            "status": "open",
            "repair_state": finding["repair_state"],
            "last_seen": run_date,
            "regression": was_resolved,
            "recheck_required": False,
        })
        next_items.append(previous_entry)
        if was_resolved:
            summary["regression"] += 1
        else:
            summary["still_open"] += 1

    for finding_id, previous_entry in previous_by_id.items():
        if finding_id in current_by_id:
            continue
        if previous_entry.get("status") == "resolved":
            next_items.append(previous_entry)
            continue
        confirmation = resolution_confirmations.get(finding_id)
        if confirmation is not None:
            if confirmation["verifier"] != previous_entry.get("verifier"):
                raise ValueError(f"resolution verifier does not match locked finding verifier: {finding_id}")
            previous_entry.update({
                "status": "resolved",
                "last_seen": run_date,
                "recheck_required": False,
                "resolution_confirmation": {
                    "date": run_date,
                    "verifier": confirmation["verifier"],
                    "evidence_ref": confirmation["evidence_ref"],
                },
            })
            summary["resolved"] += 1
        else:
            previous_entry["recheck_required"] = True
            summary["recheck_required"] += 1
        next_items.append(previous_entry)

    runs = ledger.get("runs")
    if not isinstance(runs, list):
        raise ValueError("ledger.runs must be an array")
    runs.append({
        "date": run_date,
        "target": scope.get("target"),
        "target_id": scope.get("target_id"),
        "mode": scope.get("mode"),
        "finding_count": len(current_by_id),
        "resolution_confirmation_count": summary["resolved"],
    })
    ledger["runs"] = runs
    ledger["findings"] = sorted(next_items, key=lambda item: str(item.get("id")))
    return ledger, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--findings", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--resolution-confirmations")
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = Path(args.target).expanduser().resolve()
    findings = load_json(Path(args.findings))
    validate_target_binding(findings.get("scope"), target)
    ledger_path = require_canonical_artifact_path(
        Path(args.ledger),
        target,
        ".agent-harness-review/ledger.json",
    )
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = ledger_path.with_name(f".{ledger_path.name}.lock")
    try:
        lock_descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise RuntimeError(f"ledger update already in progress: {lock_path.name}") from error
    try:
        previous = load_json(ledger_path) if ledger_path.exists() else None
        updated, summary = update_ledger(
            findings,
            previous,
            run_date=args.date,
            resolution_confirmations=load_resolution_confirmations(
                Path(args.resolution_confirmations) if args.resolution_confirmations else None
            ),
            evidence_documents=[load_json(Path(path)) for path in args.evidence],
        )
        write_json_atomic(ledger_path, updated, replace=ledger_path.exists())
    finally:
        os.close(lock_descriptor)
        lock_path.unlink()
    result = {"status": "pass", "ledger": ledger_path.name, "summary": summary}
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"ledger update: pass ({summary})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
