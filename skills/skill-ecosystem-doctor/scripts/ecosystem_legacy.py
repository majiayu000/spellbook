"""Normalize the deployed Loom governance policy into Doctor schema v1."""

from __future__ import annotations

from pathlib import Path

from ecosystem_exposure import expand_profile_scopes
from ecosystem_model import (
    INVENTORY_ROOT_KINDS,
    RUNTIME_HOME_DIRS,
    SUPPORTED_RUNTIMES,
    expand_path,
)
from ecosystem_plugins import PLUGIN_ID_RE
from ecosystem_runtimes import RuntimePolicyError, projection_runtimes


LEGACY_FIELDS = {
    "projection_runtimes",
    "schema_version",
    "default_scope",
    "trigger_boundary",
    "project_scopes",
    "project_scope_globs",
    "project_source_roots",
    "cold_storage",
    "quarantined",
    "retired",
    "global_overrides",
    "global_allowlist",
    "profiles",
    "profile_scopes",
    "profile_scope_globs",
    "exposure_budget",
    "plugin_states",
    "evidence_policy",
    "duplicate_resolution",
    "runtime_mirrors",
    "managed_global_sources",
    "frontmatter_extension_exceptions",
    "splits",
    "managed_physical_skills",
    "inventory_roots",
    "retired_reference_allowlist",
}


def is_legacy_policy(data: dict) -> bool:
    return "source_policy" not in data and (
        "project_scopes" in data or "trigger_boundary" in data
    )


def _reject_unknown_fields(data: dict) -> None:
    unknown = sorted(set(data) - LEGACY_FIELDS)
    if unknown:
        raise ValueError(
            f"unknown legacy governance fields: {', '.join(unknown)}"
        )


def _string_array(data: dict, field: str) -> list[str]:
    values = data.get(field, [])
    if not isinstance(values, list) or not all(
        isinstance(value, str) and value.strip() for value in values
    ):
        raise ValueError(f"legacy policy {field} must be a string array")
    if len(values) != len(set(values)):
        raise ValueError(f"legacy policy {field} contains duplicate values")
    return values


def _scope_map(data: dict, field: str) -> dict[str, list[str]]:
    values = data.get(field, {})
    if not isinstance(values, dict):
        raise ValueError(f"legacy policy {field} must be an object")
    for raw_root, names in values.items():
        if (
            not isinstance(raw_root, str)
            or not raw_root.strip()
            or not isinstance(names, list)
            or not all(isinstance(name, str) and name.strip() for name in names)
        ):
            raise ValueError(
                f"legacy policy {field} must map paths to Skill name arrays"
            )
    return values


def _inventory_roots(data: dict, registry: Path) -> list[dict[str, str]]:
    roots: list[dict[str, str]] = []
    seen: set[str] = set()
    registry_skills = (registry / "skills").resolve(strict=False)

    def add(raw_path: str, kind: str, owner: str) -> None:
        source = expand_path(raw_path).resolve(strict=False)
        if source == registry_skills or source.is_relative_to(registry_skills):
            return
        normalized = str(source)
        if normalized in seen:
            return
        seen.add(normalized)
        roots.append({"path": normalized, "kind": kind, "owner": owner})

    configured_roots = data.get("inventory_roots", [])
    if not isinstance(configured_roots, list):
        raise ValueError("legacy policy inventory_roots must be an array")
    configured_paths: set[str] = set()
    for index, item in enumerate(configured_roots):
        context = f"legacy policy inventory_roots[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{context} must be an object")
        unknown = sorted(set(item) - {"path", "kind", "owner"})
        if unknown:
            raise ValueError(f"{context} has unknown fields: {', '.join(unknown)}")
        raw_path = item.get("path")
        kind = item.get("kind")
        owner = item.get("owner")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError(f"{context}.path must be a non-empty string")
        if kind not in INVENTORY_ROOT_KINDS:
            allowed = ", ".join(sorted(INVENTORY_ROOT_KINDS))
            raise ValueError(f"{context}.kind must be one of: {allowed}")
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError(f"{context}.owner must be a non-empty string")
        normalized = str(expand_path(raw_path).resolve(strict=False))
        if normalized == str(registry_skills) or Path(normalized).is_relative_to(
            registry_skills
        ):
            raise ValueError(f"{context}.path overlaps the canonical registry")
        if normalized in configured_paths:
            raise ValueError(f"duplicate legacy inventory root: {normalized}")
        configured_paths.add(normalized)
        add(raw_path, kind, owner)

    source_roots = data.get("project_source_roots", {})
    if not isinstance(source_roots, dict):
        raise ValueError("legacy policy project_source_roots must be an object")
    for raw_owner, relative in source_roots.items():
        if (
            not isinstance(raw_owner, str)
            or not raw_owner.strip()
            or not isinstance(relative, str)
            or not relative.strip()
        ):
            raise ValueError(
                "legacy policy project_source_roots must map paths to relative directories"
            )
        add(str(expand_path(raw_owner) / relative), "canonical_source", raw_owner)

    managed = data.get("managed_global_sources", {})
    if not isinstance(managed, dict):
        raise ValueError("legacy policy managed_global_sources must be an object")
    for name, value in managed.items():
        if not isinstance(name, str) or not isinstance(value, dict):
            raise ValueError(
                "legacy policy managed_global_sources entries must be objects"
            )
        source = value.get("source")
        runtimes = value.get("runtimes")
        if (
            not isinstance(source, str)
            or not source.strip()
            or not isinstance(runtimes, list)
            or not runtimes
            or not all(runtime in SUPPORTED_RUNTIMES for runtime in runtimes)
        ):
            raise ValueError(f"legacy managed global source is invalid: {name}")
        add(source, "repository_source", f"managed-global:{name}")

    mirrors = data.get("runtime_mirrors", {})
    if not isinstance(mirrors, dict):
        raise ValueError("legacy policy runtime_mirrors must be an object")
    mirror_names = mirrors.get("claude_only", [])
    mirror_root = mirrors.get("authoritative_root")
    if not isinstance(mirror_names, list) or not all(
        isinstance(name, str) for name in mirror_names
    ):
        raise ValueError("legacy policy runtime_mirrors.claude_only must be an array")
    if mirror_names:
        if not isinstance(mirror_root, str) or not mirror_root.strip():
            raise ValueError(
                "legacy policy runtime_mirrors.authoritative_root is required"
            )
        add(mirror_root, "managed_cache", "codex-system")
    return roots


def normalize_legacy_policy(data: dict, path: Path) -> dict:
    _reject_unknown_fields(data)
    if data.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    expanded, _ = expand_profile_scopes(data)
    project_scopes = _scope_map(expanded, "project_scopes")
    project_globs = _scope_map(expanded, "project_scope_globs")
    cold = _string_array(data, "cold_storage")
    quarantined = _string_array(data, "quarantined")
    overlap = set(cold) & set(quarantined)
    if overlap:
        raise ValueError(
            f"legacy policy cold_storage and quarantined overlap: {sorted(overlap)}"
        )
    retired = _string_array(data, "retired")
    _string_array(data, "global_allowlist")
    default_scope = data.get("default_scope", "global")
    if default_scope not in {"global", "review"}:
        raise ValueError("legacy policy default_scope must be 'global' or 'review'")
    plugin_states = data.get("plugin_states", {})
    if not isinstance(plugin_states, dict) or not all(
        isinstance(name, str)
        and PLUGIN_ID_RE.fullmatch(name)
        and isinstance(enabled, bool)
        for name, enabled in plugin_states.items()
    ):
        raise ValueError("legacy policy plugin_states must map plugin ids to booleans")
    evidence_policy = data.get("evidence_policy", {})
    if not isinstance(evidence_policy, dict):
        raise ValueError("legacy policy evidence_policy must be an object")
    unknown_evidence = set(evidence_policy) - {"codex_audit_skill_threshold"}
    if unknown_evidence:
        raise ValueError(
            f"unknown legacy evidence policy field: {sorted(unknown_evidence)[0]}"
        )
    audit_threshold = evidence_policy.get("codex_audit_skill_threshold", 8)
    if not isinstance(audit_threshold, int) or audit_threshold <= 0:
        raise ValueError(
            "legacy evidence policy codex_audit_skill_threshold must be a positive integer"
        )
    exposure_budget = data.get("exposure_budget", {})
    if not isinstance(exposure_budget, dict):
        raise ValueError("legacy policy exposure_budget must be an object")
    for field, value in exposure_budget.items():
        if field not in {
            "max_managed_global_skills",
            "max_managed_description_chars",
        }:
            raise ValueError(f"unknown legacy exposure budget field: {field}")
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"legacy exposure budget {field} must be a positive integer")
    managed_physical = data.get("managed_physical_skills", {})
    if not isinstance(managed_physical, dict) or not all(
        isinstance(name, str)
        and name.strip()
        and isinstance(owner, str)
        and owner.strip()
        for name, owner in managed_physical.items()
    ):
        raise ValueError(
            "legacy policy managed_physical_skills must map Skill names to owners"
        )
    reference_allowlist = data.get("retired_reference_allowlist", [])
    if not isinstance(reference_allowlist, list):
        raise ValueError("legacy policy retired_reference_allowlist must be an array")
    for index, item in enumerate(reference_allowlist):
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("skill"), str)
            or not item["skill"].strip()
            or not isinstance(item.get("retired_name"), str)
            or not item["retired_name"].strip()
        ):
            raise ValueError(
                f"legacy policy retired_reference_allowlist[{index}] is invalid"
            )
    registry = path.parent.resolve(strict=False)
    if not (registry / "skills").is_dir():
        raise ValueError(
            "legacy governance file must live in a registry containing skills/"
        )

    try:
        runtimes = projection_runtimes(data)
    except RuntimePolicyError as exc:
        raise ValueError(f"legacy policy {exc}") from exc

    projection_globs: list[str] = []
    for raw_root in [*project_scopes, *project_globs]:
        root = str(expand_path(raw_root))
        for runtime in runtimes:
            candidate = str(Path(root) / RUNTIME_HOME_DIRS[runtime] / "skills")
            if candidate not in projection_globs:
                projection_globs.append(candidate)

    return {
        "schema_version": 1,
        "source_policy": {
            "local_only_canonical_registry": str(registry),
            "projection_roots": [
                f"~/{RUNTIME_HOME_DIRS[runtime]}/skills" for runtime in runtimes
            ],
            "projection_globs": projection_globs,
            "inventory_roots": _inventory_roots(data, registry),
            "managed_physical_skills": managed_physical,
        },
        "retired_skills": retired,
        "quarantined_skills": [*cold, *quarantined],
        "projection_denials": [],
        "pinned_materializations": [],
        "retired_reference_allowlist": reference_allowlist,
        "external_actions": [],
    }
