"""Load and validate Skill ecosystem governance documents."""

from __future__ import annotations

import json
from pathlib import Path

from ecosystem_legacy import is_legacy_policy, normalize_legacy_policy
from ecosystem_model import expand_path


TOP_LEVEL_FIELDS = {
    "schema_version",
    "updated_at",
    "source_policy",
    "retired_skills",
    "stale_runtime_skills",
    "quarantined_skills",
    "quarantine_reasons",
    "codex_reserved_names",
    "projection_denials",
    "pinned_materializations",
    "retired_reference_allowlist",
    "external_actions",
    "skill_decisions",
}
SOURCE_POLICY_FIELDS = {
    "local_only_canonical_registry",
    "projection_roots",
    "projection_globs",
    "inventory_roots",
    "managed_physical_skills",
    "independent_git_is_canonical_when_present",
    "projection_rule",
}
INVENTORY_ROOT_FIELDS = {"path", "kind", "owner"}
INVENTORY_ROOT_KINDS = {
    "canonical_source",
    "repository_source",
    "managed_projection",
    "managed_cache",
    "archive",
}
DECISION_FIELDS = {
    "name",
    "decision",
    "reason",
    "owner",
    "target",
    "canonical_path",
    "evidence",
}
DECISIONS = {"keep", "repair", "merge", "quarantine", "retire", "managed", "archive"}


def _reject_unknown_fields(data: dict, allowed: set[str], context: str) -> None:
    unknown = sorted(set(data) - allowed)
    if not unknown:
        return
    label = "field" if len(unknown) == 1 else "fields"
    raise ValueError(f"unknown {context} {label}: {', '.join(unknown)}")


def _require_string(item: dict, field: str, context: str) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}.{field} must be a non-empty string")
    return value


def _optional_array(data: dict, field: str, *, context: str | None = None) -> list:
    field_context = context or field
    if field not in data:
        return []
    values = data[field]
    if not isinstance(values, list):
        raise ValueError(f"{field_context} must be an array")
    return values


def _validate_string_array(data: dict, field: str) -> list[str]:
    values = _optional_array(data, field)
    normalized: list[str] = []
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field}[{index}] must be a non-empty string")
        if value in normalized:
            raise ValueError(f"{field} contains duplicate value: {value}")
        normalized.append(value)
    return normalized


def _validate_pins(data: dict) -> None:
    pins = _optional_array(data, "pinned_materializations")
    pinned_paths: set[str] = set()
    for index, item in enumerate(pins):
        context = f"pinned_materializations[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{context} must be an object")
        for field in ("name", "path", "source_path", "reason"):
            _require_string(item, field, context)
        normalized_path = str(expand_path(item["path"]))
        if normalized_path in pinned_paths:
            raise ValueError(f"duplicate pinned materialization path: {normalized_path}")
        pinned_paths.add(normalized_path)

        mappings = _optional_array(
            item,
            "resource_mappings",
            context=f"{context}.resource_mappings",
        )
        destinations: set[str] = set()
        for mapping_index, mapping in enumerate(mappings):
            mapping_context = f"{context}.resource_mappings[{mapping_index}]"
            if not isinstance(mapping, dict):
                raise ValueError(f"{mapping_context} must be an object")
            for field in ("source_path", "destination_path"):
                _require_string(mapping, field, mapping_context)
            destination = Path(mapping["destination_path"])
            if destination.is_absolute() or ".." in destination.parts:
                raise ValueError(
                    f"{mapping_context}.destination_path must stay inside the materialization"
                )
            normalized_destination = destination.as_posix()
            if normalized_destination in destinations:
                raise ValueError(
                    f"duplicate resource mapping destination: {normalized_destination}"
                )
            destinations.add(normalized_destination)


def _validate_object_arrays(data: dict) -> None:
    denials = _optional_array(data, "projection_denials")
    for index, item in enumerate(denials):
        context = f"projection_denials[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{context} must be an object")
        _require_string(item, "name", context)
        projection = _require_string(item, "projection", context)
        if projection != "deny":
            raise ValueError(f"{context}.projection must be 'deny'")

    allowlist = _optional_array(data, "retired_reference_allowlist")
    for index, item in enumerate(allowlist):
        context = f"retired_reference_allowlist[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{context} must be an object")
        _require_string(item, "skill", context)
        _require_string(item, "retired_name", context)


def _validate_inventory_roots(source_policy: dict, reserved_paths: set[str]) -> None:
    roots = _optional_array(
        source_policy,
        "inventory_roots",
        context="source_policy.inventory_roots",
    )
    seen_paths = set(reserved_paths)
    for index, item in enumerate(roots):
        context = f"source_policy.inventory_roots[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{context} must be an object")
        _reject_unknown_fields(item, INVENTORY_ROOT_FIELDS, context)
        path = _require_string(item, "path", context)
        kind = _require_string(item, "kind", context)
        _require_string(item, "owner", context)
        if kind not in INVENTORY_ROOT_KINDS:
            allowed = ", ".join(sorted(INVENTORY_ROOT_KINDS))
            raise ValueError(f"{context}.kind must be one of: {allowed}")
        normalized = str(expand_path(path))
        if normalized in seen_paths:
            raise ValueError(f"duplicate Skill root: {normalized}")
        seen_paths.add(normalized)


def _validate_skill_decisions(data: dict) -> None:
    decisions = _optional_array(data, "skill_decisions")
    seen_names: set[str] = set()
    for index, item in enumerate(decisions):
        context = f"skill_decisions[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{context} must be an object")
        _reject_unknown_fields(item, DECISION_FIELDS, context)
        name = _require_string(item, "name", context)
        decision = _require_string(item, "decision", context)
        _require_string(item, "reason", context)
        _require_string(item, "owner", context)
        if decision not in DECISIONS:
            allowed = ", ".join(sorted(DECISIONS))
            raise ValueError(f"{context}.decision must be one of: {allowed}")
        if name in seen_names:
            raise ValueError(f"duplicate skill_decisions name: {name}")
        seen_names.add(name)
        if "target" in item:
            _require_string(item, "target", context)
        if "canonical_path" in item:
            _require_string(item, "canonical_path", context)
        evidence = _optional_array(item, "evidence", context=f"{context}.evidence")
        for evidence_index, value in enumerate(evidence):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{context}.evidence[{evidence_index}] must be a non-empty string"
                )


def read_governance(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"governance file does not exist: {path}") from exc
    except OSError as exc:
        raise ValueError(f"governance file cannot be read: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"governance JSON is invalid: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("governance JSON root must be an object")
    if is_legacy_policy(data):
        return normalize_legacy_policy(data, path)
    _reject_unknown_fields(data, TOP_LEVEL_FIELDS, "governance")
    if data.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")

    source_policy = data.get("source_policy")
    if not isinstance(source_policy, dict):
        raise ValueError("source_policy must be an object")
    _reject_unknown_fields(source_policy, SOURCE_POLICY_FIELDS, "source_policy")
    _require_string(
        source_policy,
        "local_only_canonical_registry",
        "source_policy",
    )
    projection_roots = source_policy.get("projection_roots")
    if not isinstance(projection_roots, list):
        raise ValueError("source_policy.projection_roots must be an array")
    normalized_roots: set[str] = set()
    for index, value in enumerate(projection_roots):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"source_policy.projection_roots[{index}] must be a non-empty string"
            )
        normalized = str(expand_path(value))
        if normalized in normalized_roots:
            raise ValueError(f"duplicate projection root: {normalized}")
        normalized_roots.add(normalized)

    projection_globs = _optional_array(
        source_policy,
        "projection_globs",
        context="source_policy.projection_globs",
    )
    seen_globs: set[str] = set()
    for index, value in enumerate(projection_globs):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"source_policy.projection_globs[{index}] must be a non-empty string"
            )
        normalized = str(expand_path(value))
        if normalized in seen_globs:
            raise ValueError(f"duplicate projection glob: {normalized}")
        seen_globs.add(normalized)

    registry_skills = str(
        expand_path(source_policy["local_only_canonical_registry"]) / "skills"
    )
    _validate_inventory_roots(source_policy, normalized_roots | {registry_skills})
    if "independent_git_is_canonical_when_present" in source_policy and not isinstance(
        source_policy["independent_git_is_canonical_when_present"], bool
    ):
        raise ValueError(
            "source_policy.independent_git_is_canonical_when_present must be a boolean"
        )
    if "projection_rule" in source_policy:
        _require_string(source_policy, "projection_rule", "source_policy")
    managed_physical = source_policy.get("managed_physical_skills", {})
    if not isinstance(managed_physical, dict) or not all(
        isinstance(name, str)
        and name.strip()
        and isinstance(owner, str)
        and owner.strip()
        for name, owner in managed_physical.items()
    ):
        raise ValueError(
            "source_policy.managed_physical_skills must map Skill names to owners"
        )

    _validate_string_array(data, "retired_skills")
    _validate_string_array(data, "stale_runtime_skills")
    _validate_string_array(data, "quarantined_skills")
    _validate_string_array(data, "codex_reserved_names")
    _validate_string_array(data, "external_actions")
    if "updated_at" in data:
        _require_string(data, "updated_at", "governance")
    if "quarantine_reasons" in data:
        reasons = data["quarantine_reasons"]
        if not isinstance(reasons, dict):
            raise ValueError("quarantine_reasons must be an object")
        for name, reason in reasons.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("quarantine_reasons keys must be non-empty strings")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError(
                    f"quarantine_reasons.{name} must be a non-empty string"
                )
    _validate_pins(data)
    _validate_object_arrays(data)
    _validate_skill_decisions(data)
    return data
