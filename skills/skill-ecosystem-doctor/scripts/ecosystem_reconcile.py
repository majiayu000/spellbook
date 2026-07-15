#!/usr/bin/env python3
"""Dry-run or apply trigger and exposure policy to a local Skill registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

import yaml

from ecosystem_exposure import ExposureError, classify_exposure, expand_profile_scopes
from ecosystem_plugins import PluginPolicyError, plan_plugin_states


CODEX_TARGET = "target_codex_codex_skills"
QUOTED_CONTEXT_RE = re.compile(r"quoted|trace|tool output|引用|引述|日志记录", re.I)
GOVERNANCE_CONTEXT_RE = re.compile(r"governance|audit|skill 治理|技能治理|审计", re.I)
FRONTMATTER_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*:")
PORTABLE_FRONTMATTER_KEYS = {"name", "description", "license", "metadata", "allowed-tools"}


class ReconcileError(RuntimeError):
    """Raised when reconciliation would overwrite an unexpected path."""


@dataclass(frozen=True)
class ReconcilePlan:
    hardened: tuple[str, ...]
    global_links_to_remove: tuple[str, ...]
    global_links_to_create: tuple[tuple[str, str], ...]
    global_links_to_replace: tuple[tuple[str, str], ...]
    project_links_to_remove: tuple[str, ...]
    project_links_to_create: tuple[tuple[str, str], ...]
    project_links_to_replace: tuple[tuple[str, str], ...]
    review_skills: tuple[str, ...]
    profile_skills: tuple[str, ...]
    managed_global_skill_count: int
    managed_description_chars: int
    plugin_state_changes: tuple[tuple[str, bool, bool], ...]
    state_rules_to_remove: int
    state_projections_to_remove: int

    def as_dict(self) -> dict:
        return {
            "hardened": list(self.hardened),
            "global_links_to_remove": list(self.global_links_to_remove),
            "global_links_to_create": [
                {"path": path, "target": target}
                for path, target in self.global_links_to_create
            ],
            "global_links_to_replace": [
                {"path": path, "target": target}
                for path, target in self.global_links_to_replace
            ],
            "project_links_to_remove": list(self.project_links_to_remove),
            "project_links_to_create": [
                {"path": path, "target": target}
                for path, target in self.project_links_to_create
            ],
            "project_links_to_replace": [
                {"path": path, "target": target}
                for path, target in self.project_links_to_replace
            ],
            "review_skills": list(self.review_skills),
            "profile_skills": list(self.profile_skills),
            "managed_global_skill_count": self.managed_global_skill_count,
            "managed_description_chars": self.managed_description_chars,
            "plugin_state_changes": [
                {"plugin": plugin, "from": current, "to": desired}
                for plugin, current, desired in self.plugin_state_changes
            ],
            "state_rules_to_remove": self.state_rules_to_remove,
            "state_projections_to_remove": self.state_projections_to_remove,
        }


def _load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileError(f"JSON file does not exist: {path}") from exc
    except OSError as exc:
        raise ReconcileError(f"JSON file cannot be read: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReconcileError(f"{path} must contain a JSON object")
    return value


def _atomic_write(path: Path, text: str) -> None:
    temp = path.with_name(f".{path.name}.governance-{os.getpid()}")
    try:
        temp.write_text(text, encoding="utf-8")
        os.chmod(temp, path.stat().st_mode)
        os.replace(temp, path)
    except OSError:
        temp.unlink(missing_ok=True)
        raise


def _frontmatter_description(text: str, path: Path) -> tuple[str, int, int]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ReconcileError(f"{path} has no YAML frontmatter")
    try:
        closing = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration as exc:
        raise ReconcileError(f"{path} has unterminated YAML frontmatter") from exc
    try:
        data = yaml.safe_load("\n".join(lines[1:closing]))
    except yaml.YAMLError as exc:
        raise ReconcileError(f"invalid YAML frontmatter in {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("description"), str):
        raise ReconcileError(f"{path} has no string description")
    start = next(
        (index for index in range(1, closing) if lines[index].startswith("description:")),
        None,
    )
    if start is None:
        raise ReconcileError(f"{path} has no top-level description field")
    end = closing
    for index in range(start + 1, closing):
        if lines[index] and not lines[index][0].isspace() and FRONTMATTER_KEY_RE.match(lines[index]):
            end = index
            break
    return data["description"].strip(), start, end


def _hardened_text(
    path: Path,
    clause: str,
    max_length: int,
    *,
    replace_clause: str | None = None,
) -> tuple[str, bool]:
    original = path.read_text(encoding="utf-8")
    description, start, end = _frontmatter_description(original, path)
    if clause in description:
        return original, False
    if replace_clause and replace_clause in description:
        updated = description.replace(replace_clause, clause)
    elif QUOTED_CONTEXT_RE.search(description) and GOVERNANCE_CONTEXT_RE.search(
        description
    ):
        return original, False
    else:
        updated = description.rstrip() + clause
    if len(updated) > max_length:
        raise ReconcileError(
            f"{path} description would exceed {max_length} characters ({len(updated)})"
        )
    lines = original.splitlines()
    replacement = f"description: {json.dumps(updated, ensure_ascii=False)}"
    result = "\n".join([*lines[:start], replacement, *lines[end:]])
    if original.endswith("\n"):
        result += "\n"
    return result, True


def _scope_map(policy: dict) -> dict[str, Path]:
    result: dict[str, Path] = {}
    project_scopes = policy.get("project_scopes", {})
    if not isinstance(project_scopes, dict):
        raise ReconcileError("project_scopes must be an object")
    for raw_root, raw_skills in project_scopes.items():
        if not isinstance(raw_root, str) or not isinstance(raw_skills, list):
            raise ReconcileError("project_scopes entries must map paths to skill arrays")
        root = Path(raw_root).expanduser()
        if not root.is_dir():
            raise ReconcileError(f"project scope root does not exist: {root}")
        for skill in raw_skills:
            if not isinstance(skill, str):
                raise ReconcileError("project skill names must be strings")
            if skill in result:
                raise ReconcileError(f"skill has multiple project owners: {skill}")
            result[skill] = root
    return result


def _scope_roots(policy: dict, scope_map: dict[str, Path]) -> dict[str, tuple[Path, ...]]:
    result: dict[str, set[Path]] = {skill: {owner} for skill, owner in scope_map.items()}
    raw_globs = policy.get("project_scope_globs", {})
    if not isinstance(raw_globs, dict):
        raise ReconcileError("project_scope_globs must be an object")
    for raw_pattern, raw_skills in raw_globs.items():
        if not isinstance(raw_pattern, str) or not isinstance(raw_skills, list):
            raise ReconcileError("project_scope_globs entries must map patterns to skill arrays")
        pattern = Path(raw_pattern).expanduser()
        if not pattern.is_absolute():
            raise ReconcileError(f"project scope glob must be absolute: {raw_pattern}")
        parent = pattern.parent
        if any(char in str(parent) for char in "*?["):
            raise ReconcileError("project scope glob wildcards are allowed only in the basename")
        matches = sorted(path for path in parent.glob(pattern.name) if path.is_dir())
        if not matches:
            raise ReconcileError(f"project scope glob has no directory matches: {raw_pattern}")
        for skill in raw_skills:
            if not isinstance(skill, str):
                raise ReconcileError("project scope glob skill names must be strings")
            if skill not in scope_map:
                raise ReconcileError(f"project scope glob skill has no primary owner: {skill}")
            result[skill].update(matches)
    return {skill: tuple(sorted(roots)) for skill, roots in result.items()}


def _declared_project_roots(policy: dict) -> tuple[Path, ...]:
    roots: set[Path] = set()
    raw_scopes = policy.get("project_scopes", {})
    if not isinstance(raw_scopes, dict):
        raise ReconcileError("project_scopes must be an object")
    for raw_root in raw_scopes:
        if not isinstance(raw_root, str):
            raise ReconcileError("project scope roots must be strings")
        root = Path(raw_root).expanduser()
        if not root.is_dir():
            raise ReconcileError(f"project scope root does not exist: {root}")
        roots.add(root)

    raw_globs = policy.get("project_scope_globs", {})
    if not isinstance(raw_globs, dict):
        raise ReconcileError("project_scope_globs must be an object")
    for raw_pattern in raw_globs:
        if not isinstance(raw_pattern, str):
            raise ReconcileError("project scope glob patterns must be strings")
        pattern = Path(raw_pattern).expanduser()
        if not pattern.is_absolute():
            raise ReconcileError(f"project scope glob must be absolute: {raw_pattern}")
        parent = pattern.parent
        if any(char in str(parent) for char in "*?["):
            raise ReconcileError("project scope glob wildcards are allowed only in the basename")
        matches = sorted(path for path in parent.glob(pattern.name) if path.is_dir())
        if not matches:
            raise ReconcileError(f"project scope glob has no directory matches: {raw_pattern}")
        roots.update(matches)
    return tuple(sorted(roots))


def _policy_name_set(policy: dict, field: str) -> set[str]:
    values = policy.get(field, [])
    if not isinstance(values, list) or not all(
        isinstance(value, str) and value for value in values
    ):
        raise ReconcileError(f"{field} must be a string array")
    if len(values) != len(set(values)):
        raise ReconcileError(f"{field} contains duplicate names")
    return set(values)


def _project_sources(
    policy: dict, scope_map: dict[str, Path], registry: Path
) -> dict[str, Path]:
    configured = policy.get("project_source_roots", {})
    if not isinstance(configured, dict):
        raise ReconcileError("project_source_roots must be an object")
    unknown = set(configured) - {str(root) for root in scope_map.values()}
    if unknown:
        raise ReconcileError(f"project source root has no matching scope: {sorted(unknown)}")
    result: dict[str, Path] = {}
    for skill, owner in scope_map.items():
        relative = configured.get(str(owner))
        if relative is None:
            source = registry / "skills" / skill
        else:
            if not isinstance(relative, str) or not relative:
                raise ReconcileError("project source paths must be non-empty strings")
            source = owner / relative / skill
        if not (source / "SKILL.md").is_file():
            raise ReconcileError(f"project source is missing: {source}")
        result[skill] = source
    return result


def _runtime_mirrors(policy: dict) -> tuple[Path | None, set[str]]:
    config = policy.get("runtime_mirrors", {})
    if not isinstance(config, dict):
        raise ReconcileError("runtime_mirrors must be an object")
    names = config.get("claude_only", [])
    root = config.get("authoritative_root")
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        raise ReconcileError("runtime_mirrors.claude_only must be a string array")
    if names and not isinstance(root, str):
        raise ReconcileError("runtime_mirrors.authoritative_root is required")
    return (Path(root).expanduser() if isinstance(root, str) else None, set(names))


def _managed_global_sources(policy: dict) -> dict[str, tuple[Path, frozenset[str]]]:
    configured = policy.get("managed_global_sources", {})
    if not isinstance(configured, dict):
        raise ReconcileError("managed_global_sources must be an object")
    result: dict[str, tuple[Path, frozenset[str]]] = {}
    for name, raw in configured.items():
        if not isinstance(name, str) or not isinstance(raw, dict):
            raise ReconcileError("managed_global_sources entries must be objects")
        source = raw.get("source")
        runtimes = raw.get("runtimes")
        if not isinstance(source, str) or not source:
            raise ReconcileError(f"managed global source is missing for {name}")
        if (
            not isinstance(runtimes, list)
            or not runtimes
            or not all(runtime in {"codex", "claude"} for runtime in runtimes)
        ):
            raise ReconcileError(f"managed global runtimes are invalid for {name}")
        source_path = Path(source).expanduser()
        if not (source_path / "SKILL.md").is_file():
            raise ReconcileError(f"managed global source is missing: {source_path}")
        result[name] = (source_path, frozenset(runtimes))
    return result


def _validate_frontmatter_extensions(policy: dict, sources: dict[str, Path]) -> None:
    configured = policy.get("frontmatter_extension_exceptions", {})
    if not isinstance(configured, dict):
        raise ReconcileError("frontmatter_extension_exceptions must be an object")
    allowed_by_skill: dict[str, set[str]] = {}
    for key, names in configured.items():
        if not isinstance(key, str) or not isinstance(names, list) or not all(
            isinstance(name, str) for name in names
        ):
            raise ReconcileError(
                "frontmatter_extension_exceptions must map keys to skill arrays"
            )
        for name in names:
            if name not in sources:
                raise ReconcileError(f"frontmatter exception references unknown skill: {name}")
            allowed_by_skill.setdefault(name, set()).add(key)
    for name, skill_file in sorted(sources.items()):
        text = skill_file.read_text(encoding="utf-8")
        lines = text.splitlines()
        try:
            closing = next(
                index for index in range(1, len(lines)) if lines[index].strip() == "---"
            )
            data = yaml.safe_load("\n".join(lines[1:closing]))
        except (StopIteration, yaml.YAMLError) as exc:
            raise ReconcileError(f"invalid frontmatter in {skill_file}: {exc}") from exc
        if not isinstance(data, dict):
            raise ReconcileError(f"frontmatter is not a mapping: {skill_file}")
        keys = set(data)
        unexpected = keys - PORTABLE_FRONTMATTER_KEYS - allowed_by_skill.get(name, set())
        if unexpected:
            raise ReconcileError(
                f"unapproved frontmatter extensions for {name}: {sorted(unexpected)}"
            )
        missing = allowed_by_skill.get(name, set()) - keys
        if missing:
            raise ReconcileError(
                f"stale frontmatter extension exceptions for {name}: {sorted(missing)}"
            )


def _directory_manifest(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _resolved_link(path: Path) -> Path:
    target = Path(os.readlink(path))
    return target if target.is_absolute() else (path.parent / target).resolve()


def _validate_removable_link(path: Path, expected: Path) -> bool:
    if path.is_symlink():
        if _resolved_link(path) != expected.resolve():
            raise ReconcileError(f"refusing to remove unexpected symlink: {path}")
        return True
    if path.exists():
        raise ReconcileError(f"refusing to remove non-symlink path: {path}")
    return False


def _project_link_action(path: Path, expected: Path, managed_previous: Path) -> str | None:
    if path.is_symlink():
        current = _resolved_link(path)
        if current == expected.resolve():
            return None
        if current == managed_previous.resolve():
            return "replace"
        raise ReconcileError(f"project link points elsewhere: {path}")
    if path.exists():
        raise ReconcileError(f"project path already exists and is not a symlink: {path}")
    return "create"


def _filtered_state(
    path: Path,
    collection: str,
    hidden: set[str],
    codex_only_mirrors: set[str],
) -> tuple[dict, int]:
    data = _load_json(path)
    values = data.get(collection)
    if not isinstance(values, list):
        raise ReconcileError(f"{path} has no {collection} array")
    retained = []
    for item in values:
        remove = isinstance(item, dict) and (
            item.get("skill_id") in hidden
            or (
                item.get("skill_id") in codex_only_mirrors
                and item.get("target_id") == CODEX_TARGET
            )
        )
        if not remove:
            retained.append(item)
    removed = len(values) - len(retained)
    data[collection] = retained
    return data, removed


def build_plan(
    registry: Path,
    policy: dict,
    *,
    codex_home: Path,
    claude_home: Path,
) -> tuple[ReconcilePlan, dict[Path, str], dict[Path, dict]]:
    skills_root = registry / "skills"
    policy, profile_names = expand_profile_scopes(policy)
    scope_map = _scope_map(policy)
    scope_roots = _scope_roots(policy, scope_map)
    declared_project_roots = _declared_project_roots(policy)
    project_sources = _project_sources(policy, scope_map, registry)
    managed_globals = _managed_global_sources(policy)
    retired = _policy_name_set(policy, "retired")
    quarantined = _policy_name_set(policy, "quarantined")
    blocked = retired | quarantined
    if retired & quarantined:
        raise ReconcileError(
            f"retired and quarantined overlap: {sorted(retired & quarantined)}"
        )
    trigger = policy.get("trigger_boundary", {})
    clause = trigger.get("clause")
    overrides = trigger.get("overrides", {})
    max_length = trigger.get("max_description_length", 1024)
    if not isinstance(clause, str) or not clause.startswith(" "):
        raise ReconcileError("trigger boundary clause must be a space-prefixed string")
    if not isinstance(overrides, dict) or not all(
        isinstance(name, str) and isinstance(value, str) and value.startswith(" ")
        for name, value in overrides.items()
    ):
        raise ReconcileError("trigger boundary overrides must be space-prefixed strings")
    if not isinstance(max_length, int) or max_length <= 0:
        raise ReconcileError("max_description_length must be a positive integer")

    duplicate_resolution = policy.get("duplicate_resolution", {})
    if not isinstance(duplicate_resolution, dict):
        raise ReconcileError("duplicate_resolution must be an object")
    retired_mirrors = set(duplicate_resolution.get("retire_registry_mirror", []))
    mirror_root, runtime_mirrors = _runtime_mirrors(policy)
    managed_names = set(managed_globals)
    canonical_sources = {
        skill_file.parent.name: skill_file
        for skill_file in skills_root.glob("*/SKILL.md")
        if skill_file.parent.name not in retired_mirrors
    }
    canonical_sources.update(
        {skill: source / "SKILL.md" for skill, source in project_sources.items()}
    )
    canonical_sources.update(
        {skill: source / "SKILL.md" for skill, (source, _) in managed_globals.items()}
    )
    explicit_global = _policy_name_set(policy, "global_allowlist") | _policy_name_set(
        policy, "global_overrides"
    )
    explicit_exposure = set(scope_map) | profile_names | managed_names | runtime_mirrors | explicit_global
    if blocked & explicit_exposure:
        raise ReconcileError(
            f"retired or quarantined skills overlap active exposure: {sorted(blocked & explicit_exposure)}"
        )
    exposed_sources = {
        name: source for name, source in canonical_sources.items() if name not in blocked
    }
    classification = classify_exposure(
        policy,
        exposed_sources,
        project_names=set(scope_map),
        profile_names=profile_names,
        managed_names=managed_names,
        runtime_mirror_names=runtime_mirrors,
    )
    cold = set(classification.cold_names)
    hidden = set(classification.hidden_names)
    overlap = managed_names & (hidden | runtime_mirrors)
    if overlap:
        raise ReconcileError(
            f"managed global sources overlap scoped, cold, or runtime mirror skills: {sorted(overlap)}"
        )
    _validate_frontmatter_extensions(policy, canonical_sources)
    for skill in runtime_mirrors:
        authoritative = mirror_root / skill if mirror_root else None
        mirror = skills_root / skill
        if authoritative is None or not (authoritative / "SKILL.md").is_file():
            raise ReconcileError(f"runtime mirror source is missing: {skill}")
        if not (mirror / "SKILL.md").is_file():
            raise ReconcileError(f"registry runtime mirror is missing: {skill}")
        if _directory_manifest(authoritative) != _directory_manifest(mirror):
            raise ReconcileError(f"runtime mirror drift: {skill}")

    external_project_skills = {
        skill
        for skill, source in project_sources.items()
        if source != skills_root / skill
    }
    inactive_hidden = hidden - set(scope_map)
    harden_exclusions = (
        inactive_hidden
        | blocked
        | retired_mirrors
        | runtime_mirrors
        | external_project_skills
        | managed_names
    )
    text_updates: dict[Path, str] = {}
    hardened: list[str] = []
    for skill_file in sorted(skills_root.glob("*/SKILL.md")):
        skill = skill_file.parent.name
        if skill in harden_exclusions:
            continue
        selected_clause = overrides.get(skill, clause)
        updated, changed = _hardened_text(
            skill_file,
            selected_clause,
            max_length,
            replace_clause=clause if selected_clause != clause else None,
        )
        if changed:
            text_updates[skill_file] = updated
            hardened.append(skill)

    for skill in sorted(external_project_skills):
        skill_file = project_sources[skill] / "SKILL.md"
        selected_clause = overrides.get(skill, clause)
        updated, changed = _hardened_text(
            skill_file,
            selected_clause,
            max_length,
            replace_clause=clause if selected_clause != clause else None,
        )
        if changed:
            text_updates[skill_file] = updated
            hardened.append(skill)

    for skill, (source, _) in sorted(managed_globals.items()):
        selected_clause = overrides.get(skill, clause)
        updated, changed = _hardened_text(
            source / "SKILL.md",
            selected_clause,
            max_length,
            replace_clause=clause if selected_clause != clause else None,
        )
        if changed:
            text_updates[source / "SKILL.md"] = updated
            hardened.append(skill)

    global_links: list[str] = []
    global_creations: list[tuple[str, str]] = []
    global_replacements: list[tuple[str, str]] = []
    project_removals: list[str] = []
    project_links: list[tuple[str, str]] = []
    project_replacements: list[tuple[str, str]] = []
    for skill in sorted(blocked):
        source = skills_root / skill
        for home in (codex_home, claude_home):
            global_path = home / "skills" / skill
            if _validate_removable_link(global_path, source):
                global_links.append(str(global_path))
        for owner in declared_project_roots:
            for runtime_dir in (".codex", ".claude"):
                project_path = owner / runtime_dir / "skills" / skill
                if _validate_removable_link(project_path, source):
                    project_removals.append(str(project_path))

    for skill in sorted(hidden):
        source = project_sources.get(skill, skills_root / skill)
        if not (source / "SKILL.md").is_file():
            raise ReconcileError(f"policy references missing skill source: {skill}")
        for home in (codex_home, claude_home):
            global_path = home / "skills" / skill
            if _validate_removable_link(global_path, source):
                global_links.append(str(global_path))
        for owner in scope_roots.get(skill, ()):
            for runtime_dir in (".codex", ".claude"):
                project_path = owner / runtime_dir / "skills" / skill
                action = _project_link_action(project_path, source, skills_root / skill)
                pair = (str(project_path), str(source))
                if action == "create":
                    project_links.append(pair)
                elif action == "replace":
                    project_replacements.append(pair)

    runtime_homes = {"codex": codex_home, "claude": claude_home}
    for skill, (source, runtimes) in sorted(managed_globals.items()):
        for runtime in sorted(runtimes):
            global_path = runtime_homes[runtime] / "skills" / skill
            action = _project_link_action(global_path, source, skills_root / skill)
            pair = (str(global_path), str(source))
            if action == "create":
                global_creations.append(pair)
            elif action == "replace":
                global_replacements.append(pair)

    for skill in sorted(classification.global_names):
        source = canonical_sources[skill].parent
        for home in (codex_home, claude_home):
            global_path = home / "skills" / skill
            action = _project_link_action(global_path, source, skills_root / skill)
            pair = (str(global_path), str(source))
            if action == "create":
                global_creations.append(pair)
            elif action == "replace":
                global_replacements.append(pair)

    for skill in sorted(runtime_mirrors):
        global_path = codex_home / "skills" / skill
        if _validate_removable_link(global_path, skills_root / skill):
            global_links.append(str(global_path))

    state_updates: dict[Path, dict] = {}
    rules_path = registry / "state" / "registry" / "rules.json"
    projections_path = registry / "state" / "registry" / "projections.json"
    rules, removed_rules = _filtered_state(
        rules_path, "rules", hidden | blocked | managed_names, runtime_mirrors
    )
    projections, removed_projections = _filtered_state(
        projections_path, "projections", hidden | blocked | managed_names, runtime_mirrors
    )
    state_updates[rules_path] = rules
    state_updates[projections_path] = projections
    plugin_changes, plugin_text = plan_plugin_states(codex_home / "config.toml", policy)
    if plugin_text is not None:
        text_updates[codex_home / "config.toml"] = plugin_text
    return (
        ReconcilePlan(
            hardened=tuple(hardened),
            global_links_to_remove=tuple(global_links),
            global_links_to_create=tuple(global_creations),
            global_links_to_replace=tuple(global_replacements),
            project_links_to_remove=tuple(project_removals),
            project_links_to_create=tuple(project_links),
            project_links_to_replace=tuple(project_replacements),
            review_skills=tuple(sorted(classification.review_names)),
            profile_skills=tuple(sorted(classification.profile_names)),
            managed_global_skill_count=classification.global_skill_count,
            managed_description_chars=classification.global_description_chars,
            plugin_state_changes=plugin_changes,
            state_rules_to_remove=removed_rules,
            state_projections_to_remove=removed_projections,
        ),
        text_updates,
        state_updates,
    )


def apply_plan(
    plan: ReconcilePlan,
    text_updates: dict[Path, str],
    state_updates: dict[Path, dict],
) -> None:
    if plan.plugin_state_changes:
        config_paths = [path for path in text_updates if path.name == "config.toml"]
        if len(config_paths) != 1:
            raise ReconcileError(
                "plugin changes require exactly one config.toml text update"
            )
        config_path = config_paths[0]
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        backup = config_path.with_name(f"config.toml.bak-skill-governance-{stamp}")
        if backup.exists():
            raise ReconcileError(f"plugin config backup already exists: {backup}")
        shutil.copy2(config_path, backup)
    for path, text in text_updates.items():
        _atomic_write(path, text)
    for path, value in state_updates.items():
        _atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    for raw_path in plan.global_links_to_remove:
        Path(raw_path).unlink()
    for raw_path in plan.project_links_to_remove:
        Path(raw_path).unlink()
    for raw_path, raw_target in [
        *plan.global_links_to_replace,
        *plan.global_links_to_create,
        *plan.project_links_to_replace,
        *plan.project_links_to_create,
    ]:
        path = Path(raw_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            path.unlink()
        path.symlink_to(Path(raw_target))


def build_reconcile_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--claude-home", type=Path, default=Path.home() / ".claude")
    parser.add_argument("--apply", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_reconcile_parser().parse_args(argv)
    registry = args.registry.expanduser().resolve()
    policy = _load_json(args.policy.expanduser().resolve())
    try:
        plan, text_updates, state_updates = build_plan(
            registry,
            policy,
            codex_home=args.codex_home.expanduser(),
            claude_home=args.claude_home.expanduser(),
        )
        if args.apply:
            apply_plan(plan, text_updates, state_updates)
    except (OSError, ExposureError, PluginPolicyError, ReconcileError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(
        json.dumps(
            {"ok": True, "applied": args.apply, **plan.as_dict()},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
