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
import ecosystem_model as model
import ecosystem_reconcile as reconcile
import ecosystem_runtimes as runtimes_mod
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
    assert str(project / ".agents" / "skills") in normalized["source_policy"][
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


def test_legacy_policy_rejects_non_string_managed_runtime(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    (registry / "skills").mkdir(parents=True)
    managed = write_skill(tmp_path, "managed")
    policy = registry / "SKILL_GOVERNANCE_POLICY.json"
    policy.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project_scopes": {},
                "managed_global_sources": {
                    "managed": {"source": str(managed), "runtimes": [{}]}
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="legacy managed global source is invalid"):
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
        runtime_homes={"codex": codex_home, "claude": claude_home},
    )
    assert set(plan.hardened) == {"global-skill", "project-skill"}
    assert len(plan.global_links_to_remove) == 4
    assert len(plan.project_links_to_create) == 2
    reconcile.apply_plan(plan, text_updates, state_updates)

    repeated, repeated_text, _ = reconcile.build_plan(
        registry,
        policy,
        runtime_homes={"codex": codex_home, "claude": claude_home},
    )
    assert repeated.hardened == ()
    assert repeated_text == {}
    assert repeated.project_links_to_create == ()
    assert "explicit request" in global_skill.joinpath("SKILL.md").read_text()


def test_reconcile_preserves_complete_description_and_applies_override(
    tmp_path: Path,
) -> None:
    registry = tmp_path / "registry"
    registry_skills = registry / "skills"
    registry_skills.mkdir(parents=True)
    description = (
        "Run the named daily discovery workflow and publish its formal report. "
        "Do not use this workflow for one-off web searches, competitor research, "
        "generic recommendations, or borrowing its search style."
    )
    skill = write_skill(registry_skills, "tool-scout", description)
    write_state(registry, ["tool-scout"])
    generic_clause = " Use when explicitly requested; ignore mentions/traces."
    precise_clause = (
        " Use only for an explicit Tool Scout workflow request; "
        "ignore generic research and mentions/traces."
    )
    policy = {
        "trigger_boundary": {
            "clause": generic_clause,
            "overrides": {"tool-scout": precise_clause},
            "max_description_length": 1024,
        },
        "project_scopes": {},
        "cold_storage": [],
        "duplicate_resolution": {"retire_registry_mirror": []},
    }

    plan, text_updates, state_updates = reconcile.build_plan(
        registry,
        policy,
        runtime_homes={
            "codex": tmp_path / "codex",
            "claude": tmp_path / "claude",
        },
    )
    reconcile.apply_plan(plan, text_updates, state_updates)

    hardened = skill.joinpath("SKILL.md").read_text(encoding="utf-8")
    assert description in hardened
    assert precise_clause.strip() in hardened
    assert generic_clause.strip() not in hardened
    assert "…" not in hardened


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
        runtime_homes={
            "codex": tmp_path / "codex",
            "claude": tmp_path / "claude",
        },
    )

    paths = {Path(path) for path, _ in plan.project_links_to_create}
    assert worktree / ".agents" / "skills" / "prod-skill" in paths
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
        for runtime_dir in (".agents", ".claude"):
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
        runtime_homes={"codex": codex_home, "claude": claude_home},
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
        runtime_homes={"codex": codex_home, "claude": claude_home},
    )
    assert repeated.global_links_to_remove == ()
    assert repeated.project_links_to_remove == ()
    assert (project / ".agents" / "skills" / "project-skill").is_symlink()


@pytest.mark.parametrize("transition", ["review", "profile", "move", "glob", "global"])
def test_reconcile_removes_revoked_project_projections(tmp_path: Path, transition: str) -> None:
    registry = tmp_path / "registry"
    source = write_skill(registry / "skills", "demo")
    write_state(registry, ["demo"])
    project = tmp_path / "project"
    other = tmp_path / "work-other"
    project.mkdir()
    other.mkdir()
    homes = {runtime: tmp_path / runtime for runtime in ("codex", "claude")}
    policy = {
        "default_scope": "review",
        "trigger_boundary": {"clause": " Trigger only when explicitly requested."},
        "project_scopes": {str(project): ["demo"], str(other): []},
    }
    if transition == "profile":
        policy["project_scopes"][str(project)] = []
        policy["profiles"] = {"work": ["demo"]}
        policy["profile_scopes"] = {str(project): ["work"]}
    elif transition == "glob":
        policy["project_scope_globs"] = {str(tmp_path / "work-*"): ["demo"]}
    reconcile.apply_plan(*reconcile.build_plan(registry, policy, runtime_homes=homes))
    source_before = (source / "SKILL.md").read_bytes()

    if transition == "profile":
        policy["profile_scopes"][str(project)] = []
    elif transition == "glob":
        policy["project_scope_globs"][str(tmp_path / "work-*")] = []
    else:
        policy["project_scopes"][str(project)] = []
        if transition == "move":
            policy["project_scopes"][str(other)] = ["demo"]
        elif transition == "global":
            policy["global_allowlist"] = ["demo"]

    plan, text_updates, state_updates = reconcile.build_plan(registry, policy, runtime_homes=homes)
    revoked = other if transition == "glob" else project
    expected = {str(revoked / runtime / "skills" / "demo") for runtime in (".agents", ".claude")}
    assert set(plan.project_links_to_remove) == expected
    reconcile.apply_plan(plan, text_updates, state_updates)
    assert all(not Path(path).is_symlink() for path in expected)
    assert (source / "SKILL.md").read_bytes() == source_before
    if transition in {"move", "glob"}:
        retained = other if transition == "move" else project
        for runtime in (".agents", ".claude"):
            assert (retained / runtime / "skills" / "demo").resolve() == source
    repeated, repeated_text, _ = reconcile.build_plan(registry, policy, runtime_homes=homes)
    assert repeated.project_links_to_remove == ()
    assert repeated.project_links_to_create == ()
    assert repeated.project_links_to_replace == ()
    assert repeated_text == {}


@pytest.mark.parametrize("transition", ["review", "retired", "move"])
@pytest.mark.parametrize("registry_copy", [False, True])
def test_reconcile_revokes_external_project_source(tmp_path: Path, transition: str, registry_copy: bool) -> None:
    registry = tmp_path / "registry"
    (registry / "skills").mkdir(parents=True)
    if registry_copy:
        write_skill(registry / "skills", "demo")
    write_state(registry, ["demo"])
    project = tmp_path / "project"
    other = tmp_path / "other"
    project.mkdir()
    other.mkdir()
    source = write_skill(project / "source-skills", "demo")
    homes = {runtime: tmp_path / runtime for runtime in ("codex", "claude")}
    policy = {
        "default_scope": "review",
        "trigger_boundary": {"clause": " Trigger only when explicitly requested."},
        "project_scopes": {str(project): ["demo"], str(other): []},
        "project_source_roots": {str(project): "source-skills"},
    }
    reconcile.apply_plan(*reconcile.build_plan(registry, policy, runtime_homes=homes))
    before = (source / "SKILL.md").read_bytes()
    policy["project_scopes"][str(project)] = []
    if transition == "retired":
        policy["retired"] = ["demo"]
    elif transition == "move":
        write_skill(other / "source-skills", "demo")
        policy["project_scopes"][str(other)] = ["demo"]
        policy["project_source_roots"][str(other)] = "source-skills"
    plan, text_updates, state_updates = reconcile.build_plan(registry, policy, runtime_homes=homes)
    expected = {str(project / runtime / "skills" / "demo") for runtime in (".agents", ".claude")}
    assert set(plan.project_links_to_remove) == expected
    reconcile.apply_plan(plan, text_updates, state_updates)
    assert all(not Path(path).is_symlink() for path in expected)
    assert (source / "SKILL.md").read_bytes() == before
    repeated, _, _ = reconcile.build_plan(registry, policy, runtime_homes=homes)
    assert repeated.project_links_to_remove == ()


def test_revoked_project_preserves_unknown_link_and_reports_conflict(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    source = write_skill(registry / "skills", "demo")
    write_state(registry, ["demo"])
    project = tmp_path / "project"
    target = project / ".agents" / "skills" / "demo"
    target.parent.mkdir(parents=True)
    user_source = write_skill(tmp_path / "user", "demo")
    target.symlink_to(user_source)
    before = (source / "SKILL.md").read_bytes()
    policy = {
        "default_scope": "review",
        "trigger_boundary": {"clause": " Trigger only when explicitly requested."},
        "project_scopes": {str(project): []},
    }
    with pytest.raises(reconcile.ReconcileError, match="unexpected symlink"):
        reconcile.build_plan(registry, policy, runtime_homes={
            "codex": tmp_path / "codex", "claude": tmp_path / "claude"
        })
    assert target.is_symlink()
    assert target.resolve() == user_source
    assert (source / "SKILL.md").read_bytes() == before


@pytest.mark.parametrize("skill_count", [1, 2])
@pytest.mark.parametrize("managed", [False, True])
def test_reconcile_rejects_final_description_budget_before_any_write(
    tmp_path: Path, skill_count: int, managed: bool
) -> None:
    registry = tmp_path / "registry"
    (registry / "skills").mkdir(parents=True)
    sources = registry / "skills" if not managed else tmp_path / "managed"
    names = [f"demo-{index}" for index in range(skill_count)]
    skills = {name: write_skill(sources, name, "Test") for name in names}
    write_state(registry, names)
    homes = {runtime: tmp_path / runtime for runtime in ("codex", "claude")}
    policy = {
        "trigger_boundary": {"clause": " Only an explicit request."},
        "exposure_budget": {"max_managed_description_chars": 4 * skill_count},
    }
    if managed:
        policy["managed_global_sources"] = {
            name: {"source": str(skill), "runtimes": ["codex"]}
            for name, skill in skills.items()
        }
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    with pytest.raises(reconcile.ExposureError, match="managed description budget exceeded"):
        reconcile.build_plan(registry, policy, runtime_homes=homes)

    assert {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before
    assert all(not home.exists() for home in homes.values())


@pytest.mark.parametrize("new_clause", [" Only explicit.", " Only an explicit request."])
@pytest.mark.parametrize("old_clause", [" Short.", " This was a substantially longer trigger restriction."])
def test_reconcile_budget_and_plan_use_override_result(
    tmp_path: Path, new_clause: str, old_clause: str
) -> None:
    registry = tmp_path / "registry"
    source = write_skill(registry / "skills", "demo", "Test" + old_clause)
    write_state(registry, ["demo"])
    homes = {runtime: tmp_path / runtime for runtime in ("codex", "claude")}
    expected_chars = len("Test" + new_clause)
    policy = {
        "trigger_boundary": {"clause": old_clause, "overrides": {"demo": new_clause}},
        "exposure_budget": {"max_managed_description_chars": expected_chars},
    }

    plan, text_updates, state_updates = reconcile.build_plan(registry, policy, runtime_homes=homes)
    assert plan.managed_description_chars == expected_chars
    reconcile.apply_plan(plan, text_updates, state_updates)
    assert reconcile._frontmatter_description((source / "SKILL.md").read_text(), source / "SKILL.md")[0] == "Test" + new_clause
    repeated, repeated_text, _ = reconcile.build_plan(registry, policy, runtime_homes=homes)
    assert repeated.managed_description_chars == expected_chars
    assert repeated_text == {}


@pytest.mark.parametrize("value", ["null", "false", "123", '""', '"   "', '"' + "x" * 501 + '"'])
def test_doctor_rejects_invalid_standard_compatibility(tmp_path: Path, value: str) -> None:
    source = write_skill(tmp_path, "demo") / "SKILL.md"
    source.write_text(source.read_text().replace("description:", f"compatibility: {value}\ndescription:", 1))
    with pytest.raises(reconcile.ReconcileError, match="compatibility must be a non-empty string"):
        reconcile._validate_frontmatter_extensions({}, {"demo": source})


def test_doctor_legacy_compatibility_still_needs_extension_exception(tmp_path: Path) -> None:
    source = write_skill(tmp_path, "demo") / "SKILL.md"
    source.write_text(source.read_text().replace("description:", "compatibility: {runtimes: [codex]}\ndescription:", 1))
    with pytest.raises(reconcile.ReconcileError, match="legacy mappings require an explicit extension exception"):
        reconcile._validate_frontmatter_extensions({}, {"demo": source})
    reconcile._validate_frontmatter_extensions(
        {"frontmatter_extension_exceptions": {"compatibility": ["demo"]}}, {"demo": source}
    )


def test_doctor_standard_compatibility_does_not_allow_unknown_extensions(tmp_path: Path) -> None:
    source = write_skill(tmp_path, "demo") / "SKILL.md"
    source.write_text(source.read_text().replace("description:", 'compatibility: "Python 3"\nprivate-extra: true\ndescription:', 1))
    with pytest.raises(reconcile.ReconcileError, match="unapproved frontmatter extensions"):
        reconcile._validate_frontmatter_extensions({}, {"demo": source})


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


def test_split_rejects_reference_and_skill_path_escapes(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    write_skill(registry / "skills", "sample")
    escaped_source = write_skill(registry, "outside")
    move = {
        "start": "# sample",
        "reference": "../../escaped.md",
        "title": "Escaped",
        "intro": "Must remain inside the Skill.",
        "replacement": "# sample (moved)",
    }

    with pytest.raises(split.SplitError, match="reference must stay inside"):
        split.build_split_plan(registry, {"splits": {"sample": [move]}})

    safe_move = {**move, "reference": "references/details.md"}
    with pytest.raises(split.SplitError, match="one directory segment"):
        split.build_split_plan(registry, {"splits": {"../outside": [safe_move]}})

    assert escaped_source.joinpath("SKILL.md").is_file()
    assert not (registry / "escaped.md").exists()


def test_split_apply_rechecks_symlink_containment(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    skill = write_skill(registry / "skills", "sample")
    policy = {
        "splits": {
            "sample": [
                {
                    "start": "# sample",
                    "reference": "references/details.md",
                    "title": "Details",
                    "intro": "Read on demand.",
                    "replacement": "# sample (moved)",
                }
            ]
        }
    }
    _, updates = split.build_split_plan(registry, policy)
    outside = tmp_path / "outside"
    outside.mkdir()
    (skill / "references").symlink_to(outside, target_is_directory=True)

    with pytest.raises(split.SplitError, match="escaped its Skill directory"):
        split.apply_split_plan(registry, updates)

    assert not (outside / "details.md").exists()


def _multi_runtime_fixture(tmp_path: Path) -> tuple[Path, dict[str, Path], Path]:
    """Registry plus one home per supported runtime, and a managed source."""
    registry = tmp_path / "registry"
    write_skill(registry / "skills", "keeper")
    write_state(registry, ["keeper"])
    managed_root = tmp_path / "managed"
    write_skill(managed_root, "lark-doc")
    homes = {
        runtime: tmp_path / runtime for runtime in runtimes_mod.RUNTIME_HOME_DIRS
    }
    for home in homes.values():
        (home / "skills").mkdir(parents=True)
    return registry, homes, managed_root / "lark-doc"


def _base_policy() -> dict:
    return {
        "trigger_boundary": {
            "clause": " Trigger only for an explicit request; ignore quoted traces and governance.",
            "max_description_length": 1024,
        },
        "duplicate_resolution": {"retire_registry_mirror": []},
    }


def test_codex_runtime_uses_agents_skills_and_codex_config_home(
    tmp_path: Path,
) -> None:
    homes = model.default_runtime_homes(tmp_path)

    assert homes["codex"] == tmp_path / ".agents"
    assert model.runtime_project_dir("codex") == ".agents"
    assert model.runtime_target_id("codex") == "target_codex_agents_skills"
    assert model.runtime_target_ids("codex") == frozenset(
        {"target_codex_agents_skills", "target_codex_codex_skills"}
    )

    parser = reconcile.build_reconcile_parser()
    args = parser.parse_args(
        ["--registry", str(tmp_path / "registry"), "--policy", str(tmp_path / "policy.json")]
    )
    assert args.codex_home == Path.home() / ".agents"
    assert args.codex_config_home == Path.home() / ".codex"


def test_plugin_changes_use_explicit_codex_config_home(tmp_path: Path) -> None:
    registry, homes, _ = _multi_runtime_fixture(tmp_path)
    config_home = tmp_path / ".codex"
    config_home.mkdir()
    config_path = config_home / "config.toml"
    config_path.write_text(
        '[plugins."browser@openai-bundled"]\nenabled = false\n',
        encoding="utf-8",
    )
    policy = _base_policy()
    policy["plugin_states"] = {"browser@openai-bundled": True}

    with pytest.raises(reconcile.ReconcileError, match="codex_config_home is required"):
        reconcile.build_plan(registry, policy, runtime_homes=homes)

    plan, text_updates, _ = reconcile.build_plan(
        registry,
        policy,
        runtime_homes=homes,
        codex_config_home=config_home,
    )

    assert plan.plugin_state_changes == (("browser@openai-bundled", False, True),)
    assert config_path in text_updates
    assert homes["codex"] / "config.toml" not in text_updates


def test_runtime_mirror_removes_current_and_legacy_codex_target_ids(
    tmp_path: Path,
) -> None:
    registry, homes, _ = _multi_runtime_fixture(tmp_path)
    mirror_root = tmp_path / "claude-mirror"
    write_skill(mirror_root, "claude-only")
    write_skill(registry / "skills", "claude-only")
    state = registry / "state" / "registry"
    records = [
        {"skill_id": "claude-only", "target_id": "target_codex_agents_skills"},
        {"skill_id": "claude-only", "target_id": "target_codex_codex_skills"},
        {"skill_id": "claude-only", "target_id": "target_claude_claude_skills"},
    ]
    (state / "rules.json").write_text(
        json.dumps({"schema_version": 1, "rules": records}), encoding="utf-8"
    )
    (state / "projections.json").write_text(
        json.dumps({"schema_version": 1, "projections": records}), encoding="utf-8"
    )
    policy = _base_policy()
    policy["runtime_mirrors"] = {
        "authoritative_root": str(mirror_root),
        "claude_only": ["claude-only"],
    }

    plan, _, state_updates = reconcile.build_plan(
        registry, policy, runtime_homes=homes
    )

    assert plan.state_rules_to_remove == 2
    assert plan.state_projections_to_remove == 2
    assert state_updates[state / "rules.json"]["rules"] == [records[-1]]
    assert state_updates[state / "projections.json"]["projections"] == [records[-1]]


def test_managed_global_source_accepts_gemini_runtime(tmp_path: Path) -> None:
    registry, homes, managed_source = _multi_runtime_fixture(tmp_path)
    policy = _base_policy()
    policy["managed_global_sources"] = {
        "lark-doc": {"source": str(managed_source), "runtimes": ["gemini"]}
    }

    plan, _, _ = reconcile.build_plan(registry, policy, runtime_homes=homes)

    created = {path for path, _ in plan.global_links_to_create}
    assert str(homes["gemini"] / "skills" / "lark-doc") in created
    # The managed entry lands only in the runtime it names.
    lark_links = {path for path in created if path.endswith("lark-doc")}
    assert lark_links == {str(homes["gemini"] / "skills" / "lark-doc")}


def test_reconcile_sees_skill_projected_into_codex_agents_home(tmp_path: Path) -> None:
    """A retired Codex skill linked into ~/.agents is planned for removal."""
    registry, homes, managed_source = _multi_runtime_fixture(tmp_path)
    stale = write_skill(registry / "skills", "stale-skill")
    (homes["codex"] / "skills" / "stale-skill").symlink_to(stale)
    policy = _base_policy()
    policy["retired"] = ["stale-skill"]
    policy["managed_global_sources"] = {
        "lark-doc": {"source": str(managed_source), "runtimes": ["codex"]}
    }

    plan, _, _ = reconcile.build_plan(registry, policy, runtime_homes=homes)

    assert str(homes["codex"] / "skills" / "stale-skill") in plan.global_links_to_remove


def test_projection_runtimes_fan_out_into_gemini_home(tmp_path: Path) -> None:
    registry, homes, _ = _multi_runtime_fixture(tmp_path)
    policy = _base_policy()
    policy["projection_runtimes"] = ["codex", "claude", "gemini"]

    plan, _, _ = reconcile.build_plan(registry, policy, runtime_homes=homes)

    created = {path for path, _ in plan.global_links_to_create}
    assert str(homes["gemini"] / "skills" / "keeper") in created
    assert str(homes["codex"] / "skills" / "keeper") in created
    assert str(homes["cursor"] / "skills" / "keeper") not in created


def test_managed_global_source_rejects_unknown_runtime(tmp_path: Path) -> None:
    registry, homes, managed_source = _multi_runtime_fixture(tmp_path)
    policy = _base_policy()
    policy["managed_global_sources"] = {
        "lark-doc": {"source": str(managed_source), "runtimes": ["windsurf"]}
    }

    with pytest.raises(
        runtimes_mod.RuntimePolicyError, match="managed global runtimes are invalid"
    ):
        reconcile.build_plan(registry, policy, runtime_homes=homes)


def test_projection_runtimes_rejects_unknown_runtime(tmp_path: Path) -> None:
    registry, homes, _ = _multi_runtime_fixture(tmp_path)
    policy = _base_policy()
    policy["projection_runtimes"] = ["codex", "windsurf"]

    with pytest.raises(
        runtimes_mod.RuntimePolicyError, match="projection_runtimes must be"
    ):
        reconcile.build_plan(registry, policy, runtime_homes=homes)


@pytest.mark.parametrize("value", [[{}], [""]])
def test_projection_runtimes_rejects_non_string_or_empty_runtime(
    tmp_path: Path, value: list[object]
) -> None:
    registry, homes, _ = _multi_runtime_fixture(tmp_path)
    policy = _base_policy()
    policy["projection_runtimes"] = value

    with pytest.raises(
        runtimes_mod.RuntimePolicyError, match="projection_runtimes must be"
    ):
        reconcile.build_plan(registry, policy, runtime_homes=homes)


@pytest.mark.parametrize("value", [[{}], [""]])
def test_managed_global_source_rejects_non_string_or_empty_runtime(
    tmp_path: Path, value: list[object]
) -> None:
    registry, homes, managed_source = _multi_runtime_fixture(tmp_path)
    policy = _base_policy()
    policy["managed_global_sources"] = {
        "lark-doc": {"source": str(managed_source), "runtimes": value}
    }

    with pytest.raises(
        runtimes_mod.RuntimePolicyError, match="managed global runtimes are invalid"
    ):
        reconcile.build_plan(registry, policy, runtime_homes=homes)


def test_projection_runtimes_allows_explicit_no_projection_mode(
    tmp_path: Path,
) -> None:
    registry, homes, _ = _multi_runtime_fixture(tmp_path)
    policy = _base_policy()
    policy["projection_runtimes"] = []

    plan, _, _ = reconcile.build_plan(registry, policy, runtime_homes=homes)

    assert runtimes_mod.projection_runtimes(policy) == ()
    assert plan.global_links_to_create == ()
    assert plan.global_links_to_replace == ()
    assert plan.project_links_to_create == ()
    assert plan.project_links_to_replace == ()


def test_legacy_policy_projection_roots_follow_projection_runtimes(
    tmp_path: Path,
) -> None:
    registry = tmp_path / "registry"
    (registry / "skills").mkdir(parents=True)
    project = tmp_path / "project"
    project.mkdir()
    policy = registry / "SKILL_GOVERNANCE_POLICY.json"
    policy.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project_scopes": {str(project): ["scoped"]},
                "projection_runtimes": ["codex", "claude", "gemini"],
            }
        ),
        encoding="utf-8",
    )

    normalized = governance.read_governance(policy)

    source_policy = normalized["source_policy"]
    assert source_policy["projection_roots"] == [
        "~/.agents/skills",
        "~/.claude/skills",
        "~/.gemini/skills",
    ]
    assert str(project / ".gemini" / "skills") in source_policy["projection_globs"]


def test_legacy_policy_manages_physical_agents_catalog_without_projecting(
    tmp_path: Path,
) -> None:
    registry = tmp_path / "registry"
    (registry / "skills").mkdir(parents=True)
    agents_catalog = tmp_path / ".agents" / "skills"
    write_skill(agents_catalog, "physical-skill")
    policy = registry / "SKILL_GOVERNANCE_POLICY.json"
    policy.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project_scopes": {},
                "projection_runtimes": [],
                "inventory_roots": [
                    {
                        "path": str(agents_catalog),
                        "kind": "managed_projection",
                        "owner": "agents-physical-catalog",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    normalized = governance.read_governance(policy)
    result = checks.validate_ecosystem(policy, run_loom=False)

    assert normalized["source_policy"]["projection_roots"] == []
    assert normalized["source_policy"]["projection_globs"] == []
    assert normalized["source_policy"]["inventory_roots"] == [
        {
            "path": str(agents_catalog.resolve()),
            "kind": "managed_projection",
            "owner": "agents-physical-catalog",
        }
    ]
    assert result["ok"] is True
    assert result["summary"]["declared_names"] == 1
    assert "physical_projection_unpinned" not in {
        finding["code"] for finding in result["findings"]
    }
