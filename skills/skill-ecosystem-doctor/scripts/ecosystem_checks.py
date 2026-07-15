"""Orchestrate deterministic checks across Skill sources and projections."""

from __future__ import annotations

import glob
from dataclasses import asdict
from pathlib import Path

from ecosystem_governance import read_governance
from ecosystem_model import (
    EcosystemFinding,
    SkillInstance,
    expand_path,
    finding_sort_key,
    root_is_active,
)
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
    projection_globs = [
        str(expand_path(value)) for value in source_policy.get("projection_globs") or []
    ]
    project_projection_roots: list[Path] = []
    known_projection_paths = {str(path) for path in projection_roots}
    for pattern in projection_globs:
        matches = sorted(Path(value) for value in glob.glob(pattern))
        if not matches:
            findings.append(
                EcosystemFinding(
                    "error",
                    "projection_glob_empty",
                    "configured project projection glob matched no paths",
                    pattern,
                )
            )
            continue
        for match in matches:
            normalized = str(match)
            if normalized in known_projection_paths:
                continue
            known_projection_paths.add(normalized)
            project_projection_roots.append(match)
    inventory_roots = [
        {
            "path": expand_path(item["path"]),
            "kind": item["kind"],
            "owner": item["owner"],
        }
        for item in source_policy.get("inventory_roots") or []
    ]
    managed_physical_names = set(
        (source_policy.get("managed_physical_skills") or {}).keys()
    )
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
                managed_physical_names,
            )
        )
    for root in project_projection_roots:
        instances.extend(
            scan_root(
                root,
                "managed_projection",
                findings,
                pinned_materializations,
                seen_pins,
            )
        )
    for item in inventory_roots:
        instances.extend(
            scan_root(
                item["path"],
                item["kind"],
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
    declared_canonical_names = _check_decision_canonical_paths(
        by_name,
        findings,
        governance.get("skill_decisions") or [],
    )
    _check_content_conflicts(by_name, findings, declared_canonical_names)
    _check_unique_sources(
        instances,
        findings,
        retired_names,
        retired_reference_allowlist,
        _mapped_resources_by_source(governance.get("pinned_materializations") or []),
    )
    _check_decision_coverage(
        by_name,
        findings,
        governance.get("skill_decisions"),
        retired_names,
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
            "projection_globs": projection_globs,
            "project_projections": [str(path) for path in project_projection_roots],
            "inventory": [
                {
                    "path": str(item["path"]),
                    "kind": item["kind"],
                    "owner": item["owner"],
                }
                for item in inventory_roots
            ],
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
        if instance.name in retired_names and instance.root_kind != "archive":
            findings.append(
                EcosystemFinding(
                    "error",
                    "retired_skill_active",
                    f"retired Skill '{instance.name}' exists outside a recovery archive",
                    instance.path,
                )
            )
        if instance.name in quarantined_names and root_is_active(instance.root_kind):
            findings.append(
                EcosystemFinding(
                    "error",
                    "quarantined_skill_active",
                    f"quarantined Skill '{instance.name}' exists in an active projection root",
                    instance.path,
                )
            )
        denial = denied.get(instance.name)
        if denial and root_is_active(instance.root_kind):
            findings.append(
                EcosystemFinding(
                    "error",
                    "projection_denied_skill_active",
                    f"Skill '{instance.name}' is denied by governance ({denial.get('status', 'denied')})",
                    instance.path,
                )
            )
        elif denial and not root_is_active(instance.root_kind):
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
    declared_canonical_names: set[str],
) -> None:
    for name, named_instances in sorted(by_name.items()):
        named_instances = [
            instance for instance in named_instances if instance.root_kind != "archive"
        ]
        distinct_digests = {instance.digest for instance in named_instances}
        if len(distinct_digests) <= 1:
            continue
        projection_digests = {
            instance.digest
            for instance in named_instances
            if root_is_active(instance.root_kind)
        }
        active_conflict = len(projection_digests) > 1
        has_active = bool(projection_digests)
        source_variant_declared = not active_conflict and name in declared_canonical_names
        findings.append(
            EcosystemFinding(
                "error"
                if active_conflict
                else ("info" if source_variant_declared else "warning"),
                (
                    "duplicate_name_content_conflict"
                    if active_conflict
                    else "declared_source_variant"
                    if source_variant_declared
                    else (
                        "registry_projection_content_conflict"
                        if has_active
                        else "stored_source_content_conflict"
                    )
                ),
                (
                    f"active projections for declared name '{name}' have different content"
                    if active_conflict
                    else f"declared canonical source for '{name}' coexists with reviewed source variants"
                    if source_variant_declared
                    else (
                        f"stored source for declared name '{name}' differs from its active projection"
                        if has_active
                        else f"stored copies for declared name '{name}' have different content"
                    )
                ),
                details={"paths": sorted(instance.path for instance in named_instances)},
            )
        )


def _check_decision_canonical_paths(
    by_name: dict[str, list[SkillInstance]],
    findings: list[EcosystemFinding],
    configured_decisions: list[dict],
) -> set[str]:
    verified_names: set[str] = set()
    for decision in configured_decisions:
        raw_path = decision.get("canonical_path")
        named_instances = by_name.get(decision["name"])
        if not raw_path or not named_instances:
            continue
        canonical_path = str(expand_path(raw_path))
        if any(
            canonical_path
            in {instance.path, instance.resolved_path, instance.skill_file_path}
            for instance in named_instances
        ):
            verified_names.add(decision["name"])
            continue
        findings.append(
            EcosystemFinding(
                "error",
                "skill_decision_canonical_path_missing",
                f"declared canonical path for Skill '{decision['name']}' is not a discovered instance",
                canonical_path,
            )
        )
    return verified_names


def _check_unique_sources(
    instances: list[SkillInstance],
    findings: list[EcosystemFinding],
    retired_names: set[str],
    retired_reference_allowlist: set[tuple[str, str]],
    mapped_resources_by_source: dict[str, set[str]],
) -> None:
    active_resolved = {
        instance.resolved_path
        for instance in instances
        if root_is_active(instance.root_kind)
    }
    unique_sources: dict[str, SkillInstance] = {}
    for instance in instances:
        current = unique_sources.get(instance.resolved_path)
        if current is None or (
            not root_is_active(current.root_kind) and root_is_active(instance.root_kind)
        ):
            unique_sources[instance.resolved_path] = instance
    for instance in unique_sources.values():
        active = instance.resolved_path in active_resolved
        if instance.root_kind != "archive":
            scan_resource_references(
                instance,
                findings,
                active=active,
                provided_resources=mapped_resources_by_source.get(instance.resolved_path),
            )
            scan_retired_references(
                instance,
                retired_names,
                findings,
                active=active,
                allowlist=retired_reference_allowlist,
            )
        scan_secrets(instance, findings)


def _mapped_resources_by_source(pins: list[dict]) -> dict[str, set[str]]:
    mapped: dict[str, set[str]] = {}
    for pin in pins:
        try:
            source = str(expand_path(pin["source_path"]).resolve(strict=True))
        except OSError:
            continue
        destinations = {
            Path(item["destination_path"]).as_posix()
            for item in pin.get("resource_mappings") or []
        }
        if destinations:
            mapped.setdefault(source, set()).update(destinations)
    return mapped


def _check_decision_coverage(
    by_name: dict[str, list[SkillInstance]],
    findings: list[EcosystemFinding],
    configured_decisions: list[dict] | None,
    retired_names: set[str],
) -> None:
    if configured_decisions is None:
        return
    decisions = {item["name"]: item for item in configured_decisions}
    discovered_names = set(by_name)
    for name in sorted(discovered_names - set(decisions)):
        findings.append(
            EcosystemFinding(
                "error",
                "skill_decision_missing",
                f"discovered Skill '{name}' has no governance decision",
            )
        )
    for name in sorted(set(decisions) - discovered_names - retired_names):
        findings.append(
            EcosystemFinding(
                "warning",
                "skill_decision_not_discovered",
                f"governance decision for Skill '{name}' has no discovered instance",
            )
        )
