"""Load and validate Skill ecosystem governance documents."""

from __future__ import annotations

import json
from pathlib import Path

from ecosystem_model import expand_path


TOP_LEVEL_FIELDS = {
    "schema_version",
    "source_policy",
    "retired_skills",
    "quarantined_skills",
    "projection_denials",
    "pinned_materializations",
    "retired_reference_allowlist",
    "external_actions",
}
SOURCE_POLICY_FIELDS = {
    "local_only_canonical_registry",
    "projection_roots",
}


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

    _validate_string_array(data, "retired_skills")
    _validate_string_array(data, "quarantined_skills")
    _validate_string_array(data, "external_actions")
    _validate_pins(data)
    _validate_object_arrays(data)
    return data
