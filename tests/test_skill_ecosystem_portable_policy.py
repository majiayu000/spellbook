"""Portable governance fields, archives, and dynamic projection coverage."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "skill-ecosystem-doctor" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ecosystem_checks as checks


def write_skill(root: Path, name: str, body: str = "") -> Path:
    target = root / name
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Portable policy fixture.\n---\n{body}\n",
        encoding="utf-8",
    )
    return target


def write_policy(
    path: Path,
    registry: Path,
    runtime: Path,
    **overrides: object,
) -> None:
    data: dict[str, object] = {
        "schema_version": 1,
        "source_policy": {
            "local_only_canonical_registry": str(registry),
            "projection_roots": [str(runtime)],
        },
    }
    data.update(overrides)
    path.write_text(json.dumps(data), encoding="utf-8")


def finding_codes(result: dict, severity: str | None = None) -> set[str]:
    return {
        item["code"]
        for item in result["findings"]
        if severity is None or item["severity"] == severity
    }


def test_verified_canonical_path_classifies_inactive_variant(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    registry_skills = registry / "skills"
    registry_skills.mkdir(parents=True)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    write_skill(registry_skills, "shared", "stored variant")
    canonical = write_skill(runtime, "shared", "active canonical")
    policy = tmp_path / "governance.json"
    write_policy(
        policy,
        registry,
        runtime,
        skill_decisions=[
            {
                "name": "shared",
                "decision": "keep",
                "reason": "Reviewed active source.",
                "owner": "runtime-owner",
                "canonical_path": str(canonical),
            }
        ],
    )

    result = checks.validate_ecosystem(policy, run_loom=False)

    assert result["ok"] is True
    assert "declared_source_variant" in finding_codes(result, "info")
    assert "registry_projection_content_conflict" not in finding_codes(
        result, "warning"
    )


def test_unknown_canonical_path_fails_closed(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    registry_skills = registry / "skills"
    registry_skills.mkdir(parents=True)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    write_skill(registry_skills, "shared")
    policy = tmp_path / "governance.json"
    write_policy(
        policy,
        registry,
        runtime,
        skill_decisions=[
            {
                "name": "shared",
                "decision": "keep",
                "reason": "Fixture.",
                "owner": "runtime-owner",
                "canonical_path": str(tmp_path / "missing"),
            }
        ],
    )

    result = checks.validate_ecosystem(policy, run_loom=False)

    assert "skill_decision_canonical_path_missing" in finding_codes(result, "error")


def test_nested_archive_is_inactive_recovery_evidence(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    registry_skills = registry / "skills"
    registry_skills.mkdir(parents=True)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    archive = tmp_path / "archive"
    write_skill(registry_skills, "current", "current")
    write_skill(archive / "2026-07-14" / "old", "current", "old")
    write_skill(archive / "trash" / "entry", "retired", "Call retired.")
    policy = tmp_path / "governance.json"
    write_policy(
        policy,
        registry,
        runtime,
        retired_skills=["retired"],
        source_policy={
            "local_only_canonical_registry": str(registry),
            "projection_roots": [str(runtime)],
            "inventory_roots": [
                {"path": str(archive), "kind": "archive", "owner": "recovery"}
            ],
        },
    )

    result = checks.validate_ecosystem(policy, run_loom=False)

    assert result["ok"] is True
    assert result["summary"]["instances"] == 3
    assert not {
        "retired_skill_active",
        "retired_skill_reference",
        "registry_projection_content_conflict",
        "directory_name_mismatch",
    } & finding_codes(result)


def test_projection_glob_is_active_and_must_match(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    registry_skills = registry / "skills"
    registry_skills.mkdir(parents=True)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    source = write_skill(registry_skills, "project-skill")
    project_root = tmp_path / "project-one" / ".codex" / "skills"
    project_root.mkdir(parents=True)
    (project_root / "project-skill").symlink_to(source, target_is_directory=True)
    policy = tmp_path / "governance.json"
    pattern = str(tmp_path / "project-*" / ".codex" / "skills")
    write_policy(
        policy,
        registry,
        runtime,
        source_policy={
            "local_only_canonical_registry": str(registry),
            "projection_roots": [str(runtime)],
            "projection_globs": [pattern],
        },
    )

    result = checks.validate_ecosystem(policy, run_loom=False)

    assert result["ok"] is True
    assert result["roots"]["project_projections"] == [str(project_root)]

    missing_policy = tmp_path / "missing.json"
    write_policy(
        missing_policy,
        registry,
        runtime,
        source_policy={
            "local_only_canonical_registry": str(registry),
            "projection_roots": [str(runtime)],
            "projection_globs": [str(tmp_path / "missing-*" / "skills")],
        },
    )
    missing = checks.validate_ecosystem(missing_policy, run_loom=False)
    assert "projection_glob_empty" in finding_codes(missing, "error")


def test_resource_mapping_satisfies_source_reference(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    registry_skills = registry / "skills"
    registry_skills.mkdir(parents=True)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    source = write_skill(
        registry_skills,
        "composite",
        "Read [Threads](references/threads.md).",
    )
    shared = tmp_path / "integrations" / "threads.md"
    shared.parent.mkdir()
    shared.write_text("# Threads\n", encoding="utf-8")
    installed = write_skill(
        runtime,
        "composite",
        "Read [Threads](references/threads.md).",
    )
    (installed / "references").mkdir()
    (installed / "references" / "threads.md").write_text(
        "# Threads\n", encoding="utf-8"
    )
    policy = tmp_path / "governance.json"
    write_policy(
        policy,
        registry,
        runtime,
        pinned_materializations=[
            {
                "name": "composite",
                "path": str(installed),
                "source_path": str(source),
                "reason": "Composite installer fixture.",
                "resource_mappings": [
                    {
                        "source_path": str(shared),
                        "destination_path": "references/threads.md",
                    }
                ],
            }
        ],
    )

    result = checks.validate_ecosystem(policy, run_loom=False)

    assert result["ok"] is True
    assert "missing_skill_resource" not in finding_codes(result)
