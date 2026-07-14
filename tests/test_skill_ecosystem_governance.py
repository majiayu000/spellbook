"""Extended roots, legacy policy, reconciliation, and split coverage."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "skill-ecosystem-doctor" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ecosystem_checks as checks
import ecosystem_governance as governance
import ecosystem_reconcile as reconcile
import ecosystem_split as split


def write_skill(root: Path, name: str, description: str = "Specific workflow") -> Path:
    target = root / name
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n# {name}\n",
        encoding="utf-8",
    )
    return target


def write_state(registry: Path, names: list[str]) -> None:
    state = registry / "state" / "registry"
    state.mkdir(parents=True)
    (state / "rules.json").write_text(
        json.dumps({"schema_version": 1, "rules": [{"skill_id": name} for name in names]}),
        encoding="utf-8",
    )
    (state / "projections.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "projections": [{"skill_id": name} for name in names],
            }
        ),
        encoding="utf-8",
    )


def test_extended_roots_and_decision_coverage(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    registry_skills = registry / "skills"
    registry_skills.mkdir(parents=True)
    codex = tmp_path / "codex"
    claude = tmp_path / "claude"
    source_root = tmp_path / "external-skills"
    managed_root = tmp_path / "managed-skills"
    for target in (codex, claude, source_root, managed_root):
        target.mkdir()
    write_skill(source_root, "source-only")
    write_skill(managed_root, "managed-only")
    policy = tmp_path / "governance.json"
    policy.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_policy": {
                    "local_only_canonical_registry": str(registry),
                    "projection_roots": [str(codex), str(claude)],
                    "inventory_roots": [
                        {
                            "path": str(source_root),
                            "kind": "canonical_source",
                            "owner": "external",
                        },
                        {
                            "path": str(managed_root),
                            "kind": "managed_projection",
                            "owner": "installer",
                        },
                    ],
                    "projection_globs": [],
                },
                "skill_decisions": [
                    {
                        "name": "source-only",
                        "decision": "keep",
                        "reason": "Maintained source.",
                        "owner": "external",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = checks.validate_ecosystem(policy, run_loom=False)

    codes = {item["code"] for item in result["findings"]}
    assert "skill_decision_missing" in codes
    assert result["summary"]["declared_names"] == 2
    assert result["roots"]["inventory"][0]["owner"] == "external"
    assert "physical_projection_unpinned" not in codes


def test_repository_source_discovers_root_and_child(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    (registry / "skills").mkdir(parents=True)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    repository = tmp_path / "gstack"
    write_skill(tmp_path, "gstack")
    write_skill(repository, "ship")
    policy = tmp_path / "governance.json"
    policy.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_policy": {
                    "local_only_canonical_registry": str(registry),
                    "projection_roots": [str(runtime)],
                    "inventory_roots": [
                        {
                            "path": str(repository),
                            "kind": "repository_source",
                            "owner": "gstack",
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    result = checks.validate_ecosystem(policy, run_loom=False)

    assert result["ok"] is True
    assert result["summary"]["declared_names"] == 2


def test_repository_source_matches_directory_projection(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    (registry / "skills").mkdir(parents=True)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    repository = write_skill(tmp_path, "doctor")
    scripts = repository / "scripts"
    scripts.mkdir()
    (scripts / "audit.py").write_text("print('ok')\n", encoding="utf-8")
    (runtime / "doctor").symlink_to(repository, target_is_directory=True)
    policy = tmp_path / "governance.json"
    policy.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_policy": {
                    "local_only_canonical_registry": str(registry),
                    "projection_roots": [str(runtime)],
                    "inventory_roots": [
                        {
                            "path": str(repository),
                            "kind": "repository_source",
                            "owner": "doctor",
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    result = checks.validate_ecosystem(policy, run_loom=False)

    assert result["ok"] is True
    assert not {
        "duplicate_name_content_conflict",
        "registry_projection_content_conflict",
    } & {item["code"] for item in result["findings"]}


def test_legacy_policy_normalizes_without_second_config(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    (registry / "skills").mkdir(parents=True)
    project = tmp_path / "project"
    project.mkdir()
    managed = tmp_path / "managed"
    write_skill(tmp_path, "managed")
    policy_path = registry / "SKILL_GOVERNANCE_POLICY.json"
    policy_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "trigger_boundary": {
                    "clause": " Trigger only for an explicit request.",
                },
                "default_scope": "review",
                "global_allowlist": [],
                "profiles": {"media": ["profile-skill"]},
                "profile_scopes": {str(project): ["media"]},
                "profile_scope_globs": {str(tmp_path / "project*"): ["media"]},
                "exposure_budget": {
                    "max_managed_global_skills": 10,
                    "max_managed_description_chars": 1000,
                },
                "plugin_states": {"browser@openai-bundled": True},
                "evidence_policy": {"codex_audit_skill_threshold": 8},
                "project_scopes": {str(project): ["project-skill"]},
                "project_scope_globs": {str(tmp_path / "project*"): ["project-skill"]},
                "project_source_roots": {},
                "cold_storage": ["cold-skill"],
                "quarantined": ["quarantined-skill"],
                "retired": ["retired-skill"],
                "managed_global_sources": {
                    "managed": {
                        "source": str(managed),
                        "runtimes": ["codex", "claude"],
                    }
                },
                "managed_physical_skills": {"local-pack": "codex-local"},
                "retired_reference_allowlist": [
                    {"skill": "stats", "retired_name": "retired-skill"}
                ],
            }
        ),
        encoding="utf-8",
    )

    normalized = governance.read_governance(policy_path)

    assert normalized["source_policy"]["local_only_canonical_registry"] == str(registry)
    assert normalized["quarantined_skills"] == [
        "cold-skill",
        "quarantined-skill",
    ]
    assert normalized["retired_skills"] == ["retired-skill"]
    assert any(
        item["kind"] == "repository_source"
        for item in normalized["source_policy"]["inventory_roots"]
    )
    assert normalized["source_policy"]["managed_physical_skills"] == {
        "local-pack": "codex-local"
    }
    assert normalized["retired_reference_allowlist"] == [
        {"skill": "stats", "retired_name": "retired-skill"}
    ]
    assert str(project / ".codex" / "skills") in normalized["source_policy"][
        "projection_globs"
    ]
    assert str(project / ".claude" / "skills") in normalized["source_policy"][
        "projection_globs"
    ]


def test_legacy_policy_rejects_unknown_fields(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    (registry / "skills").mkdir(parents=True)
    policy = registry / "SKILL_GOVERNANCE_POLICY.json"
    policy.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "trigger_boundary": {},
                "project_scopes": {},
                "unexpected": True,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown legacy governance fields"):
        governance.read_governance(policy)


def test_legacy_policy_rejects_invalid_evidence_threshold(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    (registry / "skills").mkdir(parents=True)
    policy = registry / "SKILL_GOVERNANCE_POLICY.json"
    policy.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "trigger_boundary": {},
                "project_scopes": {},
                "evidence_policy": {"codex_audit_skill_threshold": 0},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must be a positive integer"):
        governance.read_governance(policy)


def test_reconcile_hardens_scopes_and_is_idempotent(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    registry_skills = registry / "skills"
    project = tmp_path / "project"
    project.mkdir()
    global_skill = write_skill(registry_skills, "global-skill")
    project_skill = write_skill(registry_skills, "project-skill")
    cold_skill = write_skill(registry_skills, "cold-skill")
    write_state(registry, ["global-skill", "project-skill", "cold-skill"])
    codex_home = tmp_path / "codex"
    claude_home = tmp_path / "claude"
    for home in (codex_home, claude_home):
        (home / "skills").mkdir(parents=True)
        (home / "skills" / "project-skill").symlink_to(project_skill)
        (home / "skills" / "cold-skill").symlink_to(cold_skill)
    policy = {
        "trigger_boundary": {
            "clause": " Trigger only for an explicit request; ignore quoted traces and governance.",
            "max_description_length": 1024,
        },
        "project_scopes": {str(project): ["project-skill"]},
        "cold_storage": ["cold-skill"],
        "duplicate_resolution": {"retire_registry_mirror": []},
    }

    plan, text_updates, state_updates = reconcile.build_plan(
        registry,
        policy,
        codex_home=codex_home,
        claude_home=claude_home,
    )
    assert set(plan.hardened) == {"global-skill", "project-skill"}
    assert len(plan.global_links_to_remove) == 4
    assert len(plan.project_links_to_create) == 2
    reconcile.apply_plan(plan, text_updates, state_updates)

    repeated, repeated_text, _ = reconcile.build_plan(
        registry,
        policy,
        codex_home=codex_home,
        claude_home=claude_home,
    )
    assert repeated.hardened == ()
    assert repeated_text == {}
    assert repeated.project_links_to_create == ()
    assert "explicit request" in global_skill.joinpath("SKILL.md").read_text()


def test_managed_physical_skill_does_not_require_a_pin(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    (registry / "skills").mkdir(parents=True)
    runtime = tmp_path / "runtime"
    write_skill(runtime, "managed-local")
    policy = tmp_path / "governance.json"
    policy.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_policy": {
                    "local_only_canonical_registry": str(registry),
                    "projection_roots": [str(runtime)],
                    "managed_physical_skills": {
                        "managed-local": "runtime-owned"
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    result = checks.validate_ecosystem(policy, run_loom=False)

    assert result["ok"] is True
    assert "physical_projection_unpinned" not in {
        finding["code"] for finding in result["findings"]
    }


def test_reconcile_discovers_new_project_worktree(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    project = tmp_path / "aiproxy"
    worktree = tmp_path / "aiproxy-feature"
    for target in (project, worktree):
        target.mkdir()
    write_skill(registry / "skills", "prod-skill")
    write_state(registry, ["prod-skill"])
    policy = {
        "trigger_boundary": {"clause": " Trigger only when explicitly requested."},
        "project_scopes": {str(project): ["prod-skill"]},
        "project_scope_globs": {str(tmp_path / "aiproxy*"): ["prod-skill"]},
        "cold_storage": [],
        "duplicate_resolution": {"retire_registry_mirror": []},
    }

    plan, _, _ = reconcile.build_plan(
        registry,
        policy,
        codex_home=tmp_path / "codex",
        claude_home=tmp_path / "claude",
    )

    paths = {Path(path) for path, _ in plan.project_links_to_create}
    assert worktree / ".codex" / "skills" / "prod-skill" in paths
    assert worktree / ".claude" / "skills" / "prod-skill" in paths


def test_reconcile_removes_quarantined_and_retired_links(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    project = tmp_path / "aiproxy"
    worktree = tmp_path / "aiproxy-feature"
    for target in (project, worktree):
        target.mkdir()
    unsafe = write_skill(registry / "skills", "unsafe-skill")
    project_skill = write_skill(registry / "skills", "project-skill")
    retired = registry / "skills" / "retired-skill"
    write_state(registry, ["unsafe-skill", "retired-skill", "project-skill"])
    codex_home = tmp_path / "codex"
    claude_home = tmp_path / "claude"
    for home in (codex_home, claude_home):
        (home / "skills").mkdir(parents=True)
        (home / "skills" / "unsafe-skill").symlink_to(unsafe)
        (home / "skills" / "retired-skill").symlink_to(retired)
    for target in (project, worktree):
        for runtime_dir in (".codex", ".claude"):
            skills = target / runtime_dir / "skills"
            skills.mkdir(parents=True)
            (skills / "unsafe-skill").symlink_to(unsafe)
            (skills / "retired-skill").symlink_to(retired)
    policy = {
        "trigger_boundary": {"clause": " Trigger only when explicitly requested."},
        "default_scope": "global",
        "project_scopes": {str(project): ["project-skill"]},
        "project_scope_globs": {str(tmp_path / "aiproxy*"): ["project-skill"]},
        "quarantined": ["unsafe-skill"],
        "retired": ["retired-skill"],
        "duplicate_resolution": {"retire_registry_mirror": []},
    }

    plan, text_updates, state_updates = reconcile.build_plan(
        registry,
        policy,
        codex_home=codex_home,
        claude_home=claude_home,
    )

    assert len(plan.global_links_to_remove) == 4
    assert len(plan.project_links_to_remove) == 8
    assert not {
        "unsafe-skill",
        "retired-skill",
    } & {Path(path).name for path, _ in plan.global_links_to_create}

    reconcile.apply_plan(plan, text_updates, state_updates)
    repeated, _, _ = reconcile.build_plan(
        registry,
        policy,
        codex_home=codex_home,
        claude_home=claude_home,
    )
    assert repeated.global_links_to_remove == ()
    assert repeated.project_links_to_remove == ()
    assert (project / ".codex" / "skills" / "project-skill").is_symlink()


def test_split_is_idempotent(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    skill_file = registry / "skills" / "sample" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text(
        "---\nname: sample\ndescription: sample\n---\n# Sample\n\n"
        "## Core\nkeep\n\n## Details\nmove\n\n## Verify\ncheck\n",
        encoding="utf-8",
    )
    policy = {
        "splits": {
            "sample": [
                {
                    "start": "## Details",
                    "end": "## Verify",
                    "reference": "references/details.md",
                    "title": "Details",
                    "intro": "Read on demand.",
                    "replacement": "## Details (on demand)\n\nRead [details](references/details.md).",
                }
            ]
        }
    }

    plan, updates = split.build_split_plan(registry, policy, max_lines=14)
    split.apply_split_plan(registry, updates)
    repeated, repeated_updates = split.build_split_plan(registry, policy, max_lines=14)

    assert plan.skills == ("sample",)
    assert repeated.skills == ()
    assert repeated_updates == {}
