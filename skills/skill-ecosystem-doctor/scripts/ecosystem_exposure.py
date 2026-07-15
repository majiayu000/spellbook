"""Validate explicit global, project, profile, cold, and review exposure."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path

import yaml


class ExposureError(ValueError):
    """Raised when exposure policy is incomplete or contradictory."""


@dataclass(frozen=True)
class ExposureClassification:
    global_names: frozenset[str]
    project_names: frozenset[str]
    profile_names: frozenset[str]
    cold_names: frozenset[str]
    review_names: frozenset[str]
    hidden_names: frozenset[str]
    global_skill_count: int
    global_description_chars: int


def _name_array(value: object, context: str) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ExposureError(f"{context} must be a string array")
    if len(value) != len(set(value)):
        raise ExposureError(f"{context} contains duplicate values")
    return value


def expand_profile_scopes(policy: dict) -> tuple[dict, set[str]]:
    """Expand named profiles into the existing project scope contract."""
    expanded = copy.deepcopy(policy)
    raw_profiles = expanded.get("profiles", {})
    if not isinstance(raw_profiles, dict):
        raise ExposureError("profiles must be an object")
    profiles: dict[str, list[str]] = {}
    profile_skills: set[str] = set()
    for name, raw_skills in sorted(raw_profiles.items()):
        if not isinstance(name, str) or not name.strip():
            raise ExposureError("profile names must be non-empty strings")
        skills = _name_array(raw_skills, f"profiles.{name}")
        overlap = profile_skills & set(skills)
        if overlap:
            raise ExposureError(f"Skills belong to multiple profiles: {sorted(overlap)}")
        profiles[name] = skills
        profile_skills.update(skills)

    for source_field, target_field in (
        ("profile_scopes", "project_scopes"),
        ("profile_scope_globs", "project_scope_globs"),
    ):
        bindings = expanded.get(source_field, {})
        if not isinstance(bindings, dict):
            raise ExposureError(f"{source_field} must be an object")
        target = expanded.setdefault(target_field, {})
        if not isinstance(target, dict):
            raise ExposureError(f"{target_field} must be an object")
        for root, raw_names in sorted(bindings.items()):
            if not isinstance(root, str) or not root.strip():
                raise ExposureError(f"{source_field} paths must be non-empty strings")
            profile_names = _name_array(raw_names, f"{source_field}.{root}")
            unknown = set(profile_names) - set(profiles)
            if unknown:
                raise ExposureError(
                    f"{source_field} references unknown profiles: {sorted(unknown)}"
                )
            existing = target.setdefault(root, [])
            if not isinstance(existing, list):
                raise ExposureError(f"{target_field}.{root} must be a string array")
            for profile_name in profile_names:
                for skill in profiles[profile_name]:
                    if skill not in existing:
                        existing.append(skill)
    return expanded, profile_skills


def _description_length(skill_file: Path) -> int:
    text = skill_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ExposureError(f"Skill has no frontmatter: {skill_file}")
    try:
        closing = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
        data = yaml.safe_load("\n".join(lines[1:closing]))
    except (StopIteration, yaml.YAMLError) as exc:
        raise ExposureError(f"invalid Skill frontmatter: {skill_file}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("description"), str):
        raise ExposureError(f"Skill has no string description: {skill_file}")
    return len(data["description"].strip())


def classify_exposure(
    policy: dict,
    sources: dict[str, Path],
    *,
    project_names: set[str],
    profile_names: set[str],
    managed_names: set[str],
    runtime_mirror_names: set[str],
) -> ExposureClassification:
    default_scope = policy.get("default_scope", "global")
    if default_scope not in {"global", "review"}:
        raise ExposureError("default_scope must be 'global' or 'review'")
    globals_raw = _name_array(policy.get("global_allowlist", []), "global_allowlist")
    cold_raw = _name_array(policy.get("cold_storage", []), "cold_storage")
    global_names = set(globals_raw)
    cold_names = set(cold_raw)
    known_names = set(sources)
    categorized = global_names | cold_names | project_names | profile_names | managed_names
    unknown = categorized - known_names
    if unknown:
        raise ExposureError(f"exposure policy references unknown Skills: {sorted(unknown)}")
    overlap = global_names & (cold_names | project_names | profile_names | managed_names)
    if overlap:
        raise ExposureError(f"global Skills overlap another exposure: {sorted(overlap)}")
    overlap = cold_names & (project_names | profile_names | managed_names)
    if overlap:
        raise ExposureError(f"cold Skills overlap another exposure: {sorted(overlap)}")

    reserved_global = managed_names | runtime_mirror_names
    unclassified = known_names - categorized - runtime_mirror_names
    if default_scope == "global":
        global_names.update(unclassified)
        review_names: set[str] = set()
    else:
        review_names = unclassified
    hidden_names = cold_names | project_names | profile_names | review_names
    effective_global = global_names | reserved_global
    description_chars = sum(_description_length(sources[name]) for name in effective_global)

    budget = policy.get("exposure_budget", {})
    if not isinstance(budget, dict):
        raise ExposureError("exposure_budget must be an object")
    max_count = budget.get("max_managed_global_skills")
    max_chars = budget.get("max_managed_description_chars")
    for field, value in (
        ("max_managed_global_skills", max_count),
        ("max_managed_description_chars", max_chars),
    ):
        if value is not None and (not isinstance(value, int) or value <= 0):
            raise ExposureError(f"exposure_budget.{field} must be a positive integer")
    if max_count is not None and len(effective_global) > max_count:
        raise ExposureError(
            f"managed global Skill budget exceeded: {len(effective_global)} > {max_count}"
        )
    if max_chars is not None and description_chars > max_chars:
        raise ExposureError(
            f"managed description budget exceeded: {description_chars} > {max_chars}"
        )
    return ExposureClassification(
        global_names=frozenset(global_names),
        project_names=frozenset(project_names),
        profile_names=frozenset(profile_names),
        cold_names=frozenset(cold_names),
        review_names=frozenset(review_names),
        hidden_names=frozenset(hidden_names),
        global_skill_count=len(effective_global),
        global_description_chars=description_chars,
    )
