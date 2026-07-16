"""Repository-style source coverage for Skill Ecosystem Doctor."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "skill-ecosystem-doctor" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import ecosystem_checks as validator


def write_skill(path: Path, name: str, body: str = "") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Use when testing repository sources.\n---\n{body}\n",
        encoding="utf-8",
    )
    return path


class RepositorySourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tempdir.name)
        self.registry = self.base / "registry"
        self.registry.joinpath("skills").mkdir(parents=True)
        self.codex = self.base / "codex"
        self.codex.mkdir()
        self.repository = self.base / "gstack"
        self.governance = self.base / "governance.json"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def validate(self, **overrides) -> dict:
        policy = {
            "schema_version": 1,
            "source_policy": {
                "local_only_canonical_registry": str(self.registry),
                "projection_roots": [str(self.codex)],
                "inventory_roots": [
                    {
                        "path": str(self.repository),
                        "kind": "repository_source",
                        "owner": "gstack",
                    }
                ],
            },
        }
        policy.update(overrides)
        self.governance.write_text(json.dumps(policy), encoding="utf-8")
        return validator.validate_ecosystem(self.governance, run_loom=False)

    def test_root_and_immediate_child_skills_are_discovered(self) -> None:
        write_skill(self.repository, "gstack")
        write_skill(self.repository / "ship", "ship")
        (self.repository / "docs").mkdir()

        result = self.validate()

        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["instances"], 2)
        self.assertEqual(result["summary"]["declared_names"], 2)
        self.assertEqual(result["findings"], [])

    def test_root_entrypoint_is_required(self) -> None:
        write_skill(self.repository / "ship", "ship")

        result = self.validate()

        self.assertFalse(result["ok"])
        self.assertIn(
            "skill_entrypoint_missing",
            {finding["code"] for finding in result["findings"]},
        )


class ArchiveInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tempdir.name)
        self.registry = self.base / "registry"
        self.registry.joinpath("skills").mkdir(parents=True)
        self.runtime = self.base / "runtime"
        self.runtime.mkdir()
        self.archive = self.base / "archive"
        self.archive.mkdir()
        self.governance = self.base / "governance.json"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def validate(self, **overrides) -> dict:
        policy = {
            "schema_version": 1,
            "source_policy": {
                "local_only_canonical_registry": str(self.registry),
                "projection_roots": [str(self.runtime)],
                "inventory_roots": [
                    {
                        "path": str(self.archive),
                        "kind": "archive",
                        "owner": "recovery-store",
                    }
                ],
            },
        }
        policy.update(overrides)
        self.governance.write_text(json.dumps(policy), encoding="utf-8")
        return validator.validate_ecosystem(self.governance, run_loom=False)

    def test_nested_archive_skills_are_discovered_without_container_errors(self) -> None:
        write_skill(self.archive / "2026-07-14" / "pre-sync" / "saved-copy", "old-skill")
        write_skill(self.archive / "trash-entry" / "skill", "retired-skill")

        result = self.validate()

        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["instances"], 2)
        self.assertEqual(result["summary"]["declared_names"], 2)
        self.assertNotIn(
            "directory_name_mismatch",
            {finding["code"] for finding in result["findings"]},
        )

    def test_archived_retired_and_divergent_copies_do_not_become_active_errors(self) -> None:
        write_skill(self.registry / "skills" / "current", "current", body="current")
        write_skill(self.archive / "old" / "current", "current", body="old")
        write_skill(
            self.archive / "old" / "retired",
            "retired",
            body="Call retired again only when restoring this archive.",
        )

        result = self.validate(retired_skills=["retired"])
        codes = {finding["code"] for finding in result["findings"]}

        self.assertTrue(result["ok"])
        self.assertNotIn("retired_skill_active", codes)
        self.assertNotIn("retired_skill_reference", codes)
        self.assertNotIn("registry_projection_content_conflict", codes)


class ProjectProjectionGlobTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tempdir.name)
        self.registry = self.base / "registry"
        self.registry.joinpath("skills").mkdir(parents=True)
        self.runtime = self.base / "runtime"
        self.runtime.mkdir()
        self.governance = self.base / "governance.json"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def validate(self, pattern: str) -> dict:
        policy = {
            "schema_version": 1,
            "source_policy": {
                "local_only_canonical_registry": str(self.registry),
                "projection_roots": [str(self.runtime)],
                "projection_globs": [pattern],
            },
        }
        self.governance.write_text(json.dumps(policy), encoding="utf-8")
        return validator.validate_ecosystem(self.governance, run_loom=False)

    def test_project_projection_glob_is_scanned_as_active(self) -> None:
        source = write_skill(self.registry / "skills" / "project-skill", "project-skill")
        project_root = self.base / "project-one" / ".codex" / "skills"
        project_root.mkdir(parents=True)
        (project_root / "project-skill").symlink_to(source, target_is_directory=True)

        result = self.validate(str(self.base / "project-*" / ".codex" / "skills"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["instances"], 2)
        self.assertEqual(result["roots"]["project_projections"], [str(project_root)])

    def test_project_projection_glob_must_match(self) -> None:
        result = self.validate(str(self.base / "missing-*" / ".codex" / "skills"))

        self.assertFalse(result["ok"])
        self.assertIn(
            "projection_glob_empty",
            {finding["code"] for finding in result["findings"]},
        )


if __name__ == "__main__":
    unittest.main()
