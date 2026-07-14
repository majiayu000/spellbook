from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).parents[1] / "skills" / "skill-ecosystem-doctor" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ecosystem_exposure as exposure
import ecosystem_plugins as plugins
import ecosystem_reconcile as reconcile


def write_skill(root: Path, name: str, description: str = "Specific workflow") -> Path:
    target = root / name
    target.mkdir(parents=True)
    skill_file = target / "SKILL.md"
    skill_file.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n# {name}\n",
        encoding="utf-8",
    )
    return skill_file


def test_review_default_is_fail_closed_and_budgeted(tmp_path: Path) -> None:
    sources = {
        name: write_skill(tmp_path, name)
        for name in ("global", "project", "profile", "cold", "new")
    }
    policy = {
        "default_scope": "review",
        "global_allowlist": ["global"],
        "cold_storage": ["cold"],
        "exposure_budget": {
            "max_managed_global_skills": 1,
            "max_managed_description_chars": 100,
        },
    }

    result = exposure.classify_exposure(
        policy,
        sources,
        project_names={"project"},
        profile_names={"profile"},
        managed_names=set(),
        runtime_mirror_names=set(),
    )

    assert result.global_names == {"global"}
    assert result.review_names == {"new"}
    assert result.hidden_names == {"project", "profile", "cold", "new"}


def test_profile_bindings_expand_to_project_contract() -> None:
    policy = {
        "profiles": {"media": ["video", "image"]},
        "profile_scopes": {"/repo/media": ["media"]},
        "profile_scope_globs": {"/repo/media*": ["media"]},
    }

    expanded, names = exposure.expand_profile_scopes(policy)

    assert names == {"video", "image"}
    assert expanded["project_scopes"]["/repo/media"] == ["video", "image"]
    assert expanded["project_scope_globs"]["/repo/media*"] == ["video", "image"]


def test_budget_overflow_fails_closed(tmp_path: Path) -> None:
    sources = {name: write_skill(tmp_path, name) for name in ("one", "two")}
    with pytest.raises(exposure.ExposureError, match="budget exceeded"):
        exposure.classify_exposure(
            {
                "default_scope": "review",
                "global_allowlist": ["one", "two"],
                "exposure_budget": {"max_managed_global_skills": 1},
            },
            sources,
            project_names=set(),
            profile_names=set(),
            managed_names=set(),
            runtime_mirror_names=set(),
        )


def test_plugin_plan_changes_only_exact_enabled_line(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        'model = "gpt"\n\n[plugins."visualize@openai-bundled"]\nenabled = true\n',
        encoding="utf-8",
    )

    changes, updated = plugins.plan_plugin_states(
        config, {"plugin_states": {"visualize@openai-bundled": False}}
    )

    assert changes == (("visualize@openai-bundled", True, False),)
    assert updated == 'model = "gpt"\n\n[plugins."visualize@openai-bundled"]\nenabled = false\n'


def test_plugin_apply_creates_backup_outside_named_codex_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "runtime" / "config.toml"
    config.parent.mkdir()
    original = '[plugins."visualize@openai-bundled"]\nenabled = true\n'
    config.write_text(original, encoding="utf-8")
    plan = reconcile.ReconcilePlan(
        hardened=(),
        global_links_to_remove=(),
        global_links_to_create=(),
        global_links_to_replace=(),
        project_links_to_remove=(),
        project_links_to_create=(),
        project_links_to_replace=(),
        review_skills=(),
        profile_skills=(),
        managed_global_skill_count=0,
        managed_description_chars=0,
        plugin_state_changes=(("visualize@openai-bundled", True, False),),
        state_rules_to_remove=(),
        state_projections_to_remove=(),
    )

    class FrozenDateTime:
        @classmethod
        def now(cls) -> datetime:
            return datetime(2026, 7, 14, 12, 0, 0)

    monkeypatch.setattr(reconcile, "datetime", FrozenDateTime)
    reconcile.apply_plan(
        plan,
        {config: original.replace("true", "false")},
        {},
    )

    backup = config.with_name("config.toml.bak-skill-governance-20260714T120000")
    assert backup.read_text(encoding="utf-8") == original
    assert "enabled = false" in config.read_text(encoding="utf-8")
