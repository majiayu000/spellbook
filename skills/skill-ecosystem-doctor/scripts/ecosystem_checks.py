"""Orchestrate deterministic checks across Skill sources and projections."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ecosystem_governance import read_governance
from ecosystem_model import EcosystemFinding, SkillInstance, expand_path, finding_sort_key
from ecosystem_scans import (
    run_loom_doctor,
    scan_resource_references,
    scan_retired_references,
    scan_root,
    scan_secrets,
)


def validate_ecosystem(
    governance_path: Path,
    *,
    run_loom: bool = True,
    loom_binary: str = "loom",
) -> dict:
    governance = read_governance(governance_path)
    findings: list[EcosystemFinding] = []
    source_policy = governance["source_policy"]
    registry_root = expand_path(source_policy["local_only_canonical_registry"]) / "skills"
    projection_roots = [
        expand_path(value) for value in source_policy["projection_roots"]
    ]
    pinned_materializations = {
        str(expand_path(item["path"])): item
        for item in governance.get("pinned_materializations") or []
    }
    seen_pins: set[str] = set()
    retired_names = set(governance.get("retired_skills") or [])
    quarantined_names = set(governance.get("quarantined_skills") or [])
    denied = {
        item.get("name"): item
        for item in governance.get("projection_denials") or []
        if isinstance(item, dict) and item.get("name")
    }
    retired_reference_allowlist = {
        (item.get("skill"), item.get("retired_name"))
        for item in governance.get("retired_reference_allowlist") or []
        if isinstance(item, dict) and item.get("skill") and item.get("retired_name")
    }

    instances = scan_root(
        registry_root,
        "registry",
        findings,
        pinned_materializations,
        seen_pins,
    )
    for root in projection_roots:
        instances.extend(
            scan_root(
                root,
                "projection",
                findings,
                pinned_materializations,
                seen_pins,
            )
        )
    for missing_path in sorted(set(pinned_materializations) - seen_pins):
        findings.append(
            EcosystemFinding(
                "error",
                "pinned_materialization_missing",
                "configured pinned materialization is missing or is no longer a physical copy",
                missing_path,
                {"name": pinned_materializations[missing_path]["name"]},
            )
        )

    by_name = _index_by_name(instances)
    _check_governance_states(
        instances,
        findings,
        retired_names,
        quarantined_names,
        denied,
    )
    _check_content_conflicts(by_name, findings)
    _check_unique_sources(
        instances,
        findings,
        retired_names,
        retired_reference_allowlist,
    )

    if run_loom:
        run_loom_doctor(findings, loom_binary)

    findings.sort(key=finding_sort_key)
    errors = sum(finding.severity == "error" for finding in findings)
    warnings = sum(finding.severity == "warning" for finding in findings)
    unique_sources = {instance.resolved_path for instance in instances}
    return {
        "schema_version": 1,
        "ok": errors == 0,
        "summary": {
            "errors": errors,
            "warnings": warnings,
            "instances": len(instances),
            "declared_names": len(by_name),
            "unique_sources": len(unique_sources),
        },
        "roots": {
            "registry": str(registry_root),
            "projections": [str(path) for path in projection_roots],
        },
        "findings": [asdict(finding) for finding in findings],
    }


def _index_by_name(instances: list[SkillInstance]) -> dict[str, list[SkillInstance]]:
    by_name: dict[str, list[SkillInstance]] = {}
    for instance in instances:
        by_name.setdefault(instance.name, []).append(instance)
    return by_name


def _check_governance_states(
    instances: list[SkillInstance],
    findings: list[EcosystemFinding],
    retired_names: set[str],
    quarantined_names: set[str],
    denied: dict[str, dict],
) -> None:
    for instance in instances:
        if instance.name in retired_names:
            findings.append(
                EcosystemFinding(
                    "error",
                    "retired_skill_active",
                    f"retired Skill '{instance.name}' exists in an active root",
                    instance.path,
                )
            )
        if instance.name in quarantined_names and instance.root_kind == "projection":
            findings.append(
                EcosystemFinding(
                    "error",
                    "quarantined_skill_active",
                    f"quarantined Skill '{instance.name}' exists in an active projection root",
                    instance.path,
                )
            )
        denial = denied.get(instance.name)
        if denial and instance.root_kind == "projection":
            findings.append(
                EcosystemFinding(
                    "error",
                    "projection_denied_skill_active",
                    f"Skill '{instance.name}' is denied by governance ({denial.get('status', 'denied')})",
                    instance.path,
                )
            )
        elif denial and instance.root_kind == "registry":
            findings.append(
                EcosystemFinding(
                    "warning",
                    "denied_skill_in_registry",
                    f"denied Skill '{instance.name}' is stored locally but not projected",
                    instance.path,
                )
            )


def _check_content_conflicts(
    by_name: dict[str, list[SkillInstance]],
    findings: list[EcosystemFinding],
) -> None:
    for name, named_instances in sorted(by_name.items()):
        distinct_digests = {instance.digest for instance in named_instances}
        if len(distinct_digests) <= 1:
            continue
        projection_digests = {
            instance.digest
            for instance in named_instances
            if instance.root_kind == "projection"
        }
        active_conflict = len(projection_digests) > 1
        findings.append(
            EcosystemFinding(
                "error" if active_conflict else "warning",
                (
                    "duplicate_name_content_conflict"
                    if active_conflict
                    else "registry_projection_content_conflict"
                ),
                (
                    f"active projections for declared name '{name}' have different content"
                    if active_conflict
                    else f"stored source for declared name '{name}' differs from its active projection"
                ),
                details={"paths": sorted(instance.path for instance in named_instances)},
            )
        )


def _check_unique_sources(
    instances: list[SkillInstance],
    findings: list[EcosystemFinding],
    retired_names: set[str],
    retired_reference_allowlist: set[tuple[str, str]],
) -> None:
    active_resolved = {
        instance.resolved_path
        for instance in instances
        if instance.root_kind == "projection"
    }
    unique_sources: dict[str, SkillInstance] = {}
    for instance in instances:
        current = unique_sources.get(instance.resolved_path)
        if current is None or (
            current.root_kind != "projection" and instance.root_kind == "projection"
        ):
            unique_sources[instance.resolved_path] = instance
    for instance in unique_sources.values():
        active = instance.resolved_path in active_resolved
        scan_resource_references(instance, findings, active=active)
        scan_retired_references(
            instance,
            retired_names,
            findings,
            active=active,
            allowlist=retired_reference_allowlist,
        )
        scan_secrets(instance, findings)
