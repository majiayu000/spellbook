"""Regression tests for the Skill Ecosystem Doctor validator."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "skill-ecosystem-doctor" / "scripts"
CLI = SCRIPT_DIR / "ecosystem_doctor.py"
sys.path.insert(0, str(SCRIPT_DIR))

import ecosystem_checks as validator
import ecosystem_model
import ecosystem_scans


class SkillEcosystemDoctorTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tempdir.name)
        self.registry = self.base / "registry"
        self.registry_skills = self.registry / "skills"
        self.codex = self.base / "codex"
        self.claude = self.base / "claude"
        for path in (self.registry_skills, self.codex, self.claude):
            path.mkdir(parents=True)
        self.governance = self.base / "skill-governance.json"
        self.write_governance()

    def tearDown(self):
        self.tempdir.cleanup()

    def write_governance(self, **overrides):
        data = {
            "schema_version": 1,
            "source_policy": {
                "local_only_canonical_registry": str(self.registry),
                "projection_roots": [str(self.codex), str(self.claude)],
            },
            "retired_skills": ["auto-optimize", "fixflow"],
            "quarantined_skills": ["unsafe-deploy"],
            "projection_denials": [
                {"name": "fable", "status": "expired_experimental", "projection": "deny"}
            ],
        }
        data.update(overrides)
        self.governance.write_text(json.dumps(data), encoding="utf-8")

    @staticmethod
    def write_skill(root, directory, name=None, body="", files=None):
        skill_dir = root / directory
        skill_dir.mkdir(parents=True)
        declared_name = name or directory
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {declared_name}\ndescription: Use when testing.\n---\n\n# Test\n\n{body}\n",
            encoding="utf-8",
        )
        for relative, content in (files or {}).items():
            target = skill_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return skill_dir

    @staticmethod
    def write_file_skill(root, install_name, body=""):
        skill_file = root / f"{install_name}.SKILL.md"
        skill_file.write_text(
            f"---\nname: {install_name}\ndescription: Use when testing.\n---\n\n# Test\n\n{body}\n",
            encoding="utf-8",
        )
        return skill_file

    @staticmethod
    def install_file_skill(root, install_name, source):
        skill_dir = root / install_name
        skill_dir.mkdir()
        os.symlink(source, skill_dir / "SKILL.md")
        return skill_dir

    def validate(self, **kwargs):
        return validator.validate_ecosystem(self.governance, run_loom=False, **kwargs)

    @staticmethod
    def codes(result, severity=None):
        return {
            finding["code"]
            for finding in result["findings"]
            if severity is None or finding["severity"] == severity
        }

    def test_matching_registry_source_and_symlink_projections_pass(self):
        source = self.write_skill(
            self.registry_skills,
            "safe-skill",
            body="Read references/guide.md.",
            files={"references/guide.md": "verified\n"},
        )
        os.symlink(source, self.codex / "safe-skill", target_is_directory=True)
        os.symlink(source, self.claude / "safe-skill", target_is_directory=True)

        result = self.validate()

        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["instances"], 3)
        self.assertEqual(result["summary"]["declared_names"], 1)
        self.assertEqual(result["findings"], [])

    def test_file_skill_and_installed_symlink_projections_are_scanned(self):
        source = self.write_file_skill(self.registry_skills, "brainstorming")
        self.install_file_skill(self.codex, "brainstorming", source)
        self.install_file_skill(self.claude, "brainstorming", source)

        result = self.validate()

        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["instances"], 3)
        self.assertEqual(result["summary"]["declared_names"], 1)
        self.assertEqual(result["summary"]["unique_sources"], 1)
        self.assertNotIn("physical_projection_unpinned", self.codes(result))

    def test_file_skill_content_receives_active_safety_scans(self):
        token = "ghp_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcd"
        source = self.write_file_skill(
            self.registry_skills,
            "legacy-file",
            body=(
                "Read references/missing.md, call auto-optimize, and never embed "
                f"{token}."
            ),
        )
        self.install_file_skill(self.codex, "legacy-file", source)

        result = self.validate()

        codes = self.codes(result, "error")
        self.assertIn("missing_skill_resource", codes)
        self.assertIn("retired_skill_reference", codes)
        self.assertIn("possible_embedded_secret", codes)
        self.assertNotIn(token, json.dumps(result))

    def test_retired_and_denied_skills_are_rejected_in_active_roots(self):
        self.write_skill(self.codex, "auto-optimize")
        self.write_skill(self.claude, "fable")
        self.write_skill(self.codex, "unsafe-deploy")

        result = self.validate()

        self.assertFalse(result["ok"])
        codes = self.codes(result, "error")
        self.assertIn("retired_skill_active", codes)
        self.assertIn("projection_denied_skill_active", codes)
        self.assertIn("quarantined_skill_active", codes)

    def test_duplicate_declared_name_with_different_content_is_an_error(self):
        self.write_skill(self.registry_skills, "shared", body="version one")
        self.write_skill(self.codex, "shared", body="version two")
        self.write_skill(self.claude, "shared", body="version three")

        result = self.validate()

        self.assertIn("duplicate_name_content_conflict", self.codes(result, "error"))
        self.assertIn("physical_projection_unpinned", self.codes(result, "warning"))

    def test_inactive_registry_source_conflict_is_visible_but_not_blocking(self):
        self.write_skill(self.registry_skills, "shared", body="old registry version")
        active = self.write_skill(self.codex, "shared", body="active version")
        os.symlink(active, self.claude / "shared", target_is_directory=True)

        result = self.validate()

        self.assertTrue(result["ok"])
        self.assertIn("registry_projection_content_conflict", self.codes(result, "warning"))

    def test_verified_canonical_path_classifies_inactive_source_variants(self):
        self.write_skill(self.registry_skills, "shared", body="old registry version")
        active = self.write_skill(self.codex, "shared", body="active version")
        os.symlink(active, self.claude / "shared", target_is_directory=True)
        self.write_governance(
            skill_decisions=[
                {
                    "name": "shared",
                    "decision": "keep",
                    "reason": "The active reviewed source is canonical.",
                    "owner": "runtime-owner",
                    "canonical_path": str(active),
                }
            ]
        )

        result = self.validate()

        self.assertTrue(result["ok"])
        self.assertIn("declared_source_variant", self.codes(result, "info"))
        self.assertNotIn(
            "registry_projection_content_conflict",
            self.codes(result, "warning"),
        )

    def test_unknown_decision_canonical_path_fails_closed(self):
        self.write_skill(self.registry_skills, "shared")
        self.write_governance(
            skill_decisions=[
                {
                    "name": "shared",
                    "decision": "keep",
                    "reason": "Test fixture.",
                    "owner": "runtime-owner",
                    "canonical_path": str(self.base / "missing"),
                }
            ]
        )

        result = self.validate()

        self.assertIn(
            "skill_decision_canonical_path_missing",
            self.codes(result, "error"),
        )

    def test_broken_symlink_and_missing_resource_are_errors(self):
        missing_resource = self.write_skill(
            self.registry_skills,
            "missing-resource",
            body="Read references/missing.md before acting.",
        )
        os.symlink(
            missing_resource,
            self.claude / "missing-resource",
            target_is_directory=True,
        )
        os.symlink(self.base / "does-not-exist", self.codex / "broken")

        result = self.validate()

        codes = self.codes(result, "error")
        self.assertIn("broken_projection", codes)
        self.assertIn("missing_skill_resource", codes)

    def test_existing_resource_directory_is_a_valid_reference(self):
        source = self.write_skill(
            self.registry_skills,
            "template-library",
            body="Use [the templates](assets/templates/) as examples.",
        )
        (source / "assets" / "templates").mkdir(parents=True)
        os.symlink(source, self.codex / source.name, target_is_directory=True)

        result = self.validate()

        self.assertNotIn("missing_skill_resource", self.codes(result))

    def test_broken_inner_skill_file_symlink_is_an_error(self):
        missing_target = self.base / "missing-file.SKILL.md"
        broken = self.codex / "broken-file"
        broken.mkdir()
        os.symlink(missing_target, broken / "SKILL.md")

        directory_target = self.base / "not-a-skill-file"
        directory_target.mkdir()
        wrong_type = self.claude / "wrong-type"
        wrong_type.mkdir()
        os.symlink(directory_target, wrong_type / "SKILL.md")

        result = self.validate()

        broken_findings = [
            finding
            for finding in result["findings"]
            if finding["code"] == "broken_projection"
        ]
        broken_paths = {finding["path"] for finding in broken_findings}
        self.assertEqual(len(broken_findings), 2)
        self.assertIn(str(broken / "SKILL.md"), broken_paths)
        self.assertIn(str(wrong_type / "SKILL.md"), broken_paths)
        self.assertFalse(result["ok"])

    def test_skill_directory_without_skill_md_is_an_error(self):
        empty_projection = self.codex / "empty-projection"
        empty_projection.mkdir()

        linked_target = self.base / "linked-empty"
        linked_target.mkdir()
        os.symlink(linked_target, self.claude / "linked-empty", target_is_directory=True)

        empty_source = self.registry_skills / "not-a-skill-dir"
        empty_source.mkdir()

        result = self.validate()

        broken = [
            finding
            for finding in result["findings"]
            if finding["code"] == "broken_projection"
        ]
        broken_paths = {finding["path"] for finding in broken}
        self.assertEqual(len(broken), 2)
        self.assertIn(str(empty_projection), broken_paths)
        self.assertIn(str(self.claude / "linked-empty"), broken_paths)
        missing_source = [
            finding
            for finding in result["findings"]
            if finding["code"] == "skill_entrypoint_missing"
        ]
        self.assertEqual([finding["path"] for finding in missing_source], [str(empty_source)])
        self.assertFalse(result["ok"])

    def test_additional_inventory_roots_are_scanned_with_declared_roles(self):
        spellbook = self.base / "spellbook-skills"
        agents = self.base / "agents-skills"
        spellbook.mkdir()
        agents.mkdir()
        source = self.write_skill(spellbook, "source-only")
        self.write_skill(agents, "managed-only")
        self.write_governance(
            source_policy={
                "local_only_canonical_registry": str(self.registry),
                "projection_roots": [str(self.codex), str(self.claude)],
                "inventory_roots": [
                    {
                        "path": str(spellbook),
                        "kind": "canonical_source",
                        "owner": "spellbook",
                    },
                    {
                        "path": str(agents),
                        "kind": "managed_projection",
                        "owner": "skill-installer",
                    },
                ],
            }
        )

        result = self.validate()

        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["instances"], 2)
        self.assertEqual(result["summary"]["declared_names"], 2)
        self.assertEqual(result["roots"]["inventory"][0]["path"], str(spellbook))
        self.assertNotIn("physical_projection_unpinned", self.codes(result))
        self.assertTrue(source.is_dir())

    def test_skill_decisions_must_cover_every_discovered_name(self):
        self.write_skill(self.registry_skills, "classified")
        self.write_skill(self.registry_skills, "unclassified")
        self.write_governance(
            skill_decisions=[
                {
                    "name": "classified",
                    "decision": "keep",
                    "reason": "Distinct tested capability.",
                    "owner": "local-registry",
                    "evidence": ["manual review"],
                },
                {
                    "name": "future-name",
                    "decision": "repair",
                    "reason": "Expected source has not been restored.",
                    "owner": "unresolved",
                },
            ]
        )

        result = self.validate()

        self.assertIn("skill_decision_missing", self.codes(result, "error"))
        self.assertIn("skill_decision_not_discovered", self.codes(result, "warning"))

    def test_duplicate_or_invalid_skill_decisions_fail_closed(self):
        duplicate = {
            "name": "same",
            "decision": "keep",
            "reason": "Test fixture.",
            "owner": "test",
        }
        self.write_governance(skill_decisions=[duplicate, duplicate])
        with self.assertRaisesRegex(ValueError, "duplicate skill_decisions name: same"):
            self.validate()

        invalid = dict(duplicate, name="invalid", decision="delete-maybe")
        self.write_governance(skill_decisions=[invalid])
        with self.assertRaisesRegex(ValueError, r"skill_decisions\[0\]\.decision"):
            self.validate()

    def test_all_supported_resource_paths_and_file_types_are_checked(self):
        references = (
            "agents/missing.yaml",
            "assets/missing.md",
            "evals/missing.json",
            "reference/missing.md",
            "references/guide.md",
            "scripts/missing.py",
            "./templates/missing.md",
        )
        source = self.write_skill(
            self.registry_skills,
            "missing-support-files",
            body="\n".join(f"Load [{path}]({path})." for path in references),
        )
        (source / "references" / "guide.md").mkdir(parents=True)
        os.symlink(source, self.codex / source.name, target_is_directory=True)

        result = self.validate()

        missing = [
            finding
            for finding in result["findings"]
            if finding["code"] == "missing_skill_resource"
        ]
        self.assertEqual(len(missing), len(references))

    def test_resource_references_cannot_escape_the_skill_root(self):
        source = self.write_skill(
            self.registry_skills,
            "escaping-resource",
            body="Read references/../../outside.md before acting.",
        )
        (source / "references").mkdir()
        (self.registry_skills / "outside.md").write_text("outside\n", encoding="utf-8")
        os.symlink(source, self.codex / source.name, target_is_directory=True)

        result = self.validate()

        self.assertIn("unsafe_skill_resource_reference", self.codes(result, "error"))

    def test_resource_references_in_reachable_support_files_are_scanned(self):
        source = self.write_skill(
            self.registry_skills,
            "nested-resource",
            body="Read references/guide.md before acting.",
            files={"references/guide.md": "Load templates/missing.md before acting.\n"},
        )
        os.symlink(source, self.codex / source.name, target_is_directory=True)

        result = self.validate()

        finding = next(
            item for item in result["findings"] if item["code"] == "missing_skill_resource"
        )
        self.assertEqual(Path(finding["path"]).name, "guide.md")

    def test_retired_reference_in_active_skill_is_an_error(self):
        source = self.write_skill(
            self.registry_skills,
            "new-flow",
            body="Call auto-optimize for the next step.",
        )
        os.symlink(source, self.codex / "new-flow", target_is_directory=True)

        result = self.validate()

        self.assertIn("retired_skill_reference", self.codes(result, "error"))

    def test_retired_reference_in_support_file_is_an_error(self):
        source = self.write_skill(
            self.registry_skills,
            "new-flow",
            body="Read references/guide.md before acting.",
            files={"references/guide.md": "Call auto-optimize for the next step.\n"},
        )
        os.symlink(source, self.codex / "new-flow", target_is_directory=True)

        result = self.validate()

        finding = next(
            item for item in result["findings"] if item["code"] == "retired_skill_reference"
        )
        self.assertEqual(Path(finding["path"]).name, "guide.md")

    def test_retired_name_as_ordinary_prose_is_not_a_reference(self):
        """A retired name colliding with domain vocabulary must not fail the gate."""
        self.write_governance(retired_skills=["wallpaper"])
        source = self.write_skill(
            self.registry_skills,
            "desktop-art",
            body=(
                "Generate a wallpaper for the user.\n"
                "Save each wallpaper as PNG; a wallpaper must be 4K.\n"
            ),
        )
        os.symlink(source, self.codex / "desktop-art", target_is_directory=True)

        result = self.validate()

        self.assertNotIn("retired_skill_reference", self.codes(result))

    def test_explicit_reference_forms_are_still_detected(self):
        forms = {
            "slash_command": "Run /wallpaper to continue.",
            "wiki_link": "See [[wallpaper]] for details.",
            "skill_path": "Read skills/wallpaper/SKILL.md first.",
            "code_span": "Invoke `wallpaper` at this point.",
            "invocation": "Call wallpaper before rendering.",
            "qualified_noun": "The wallpaper skill handles this.",
        }
        for kind, body in forms.items():
            with self.subTest(kind=kind):
                found = ecosystem_scans.find_retired_reference(body, "wallpaper")
                self.assertIsNotNone(found, f"{kind} should be detected")

    def test_retired_reference_finding_carries_verifiable_line_number(self):
        self.write_governance(retired_skills=["wallpaper"])
        source = self.write_skill(
            self.registry_skills,
            "desktop-art",
            body="A wallpaper is an image.\nPick one.\nCall wallpaper now.\n",
        )
        os.symlink(source, self.codex / "desktop-art", target_is_directory=True)

        result = self.validate()

        finding = next(
            item for item in result["findings"] if item["code"] == "retired_skill_reference"
        )
        line = finding["details"]["line"]
        text = Path(finding["path"]).read_text(encoding="utf-8").splitlines()
        self.assertIn("wallpaper", text[line - 1])
        self.assertIn("Call wallpaper", text[line - 1])

    def test_retired_reference_evidence_redacts_secrets(self):
        token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcd"
        found = ecosystem_scans.find_retired_reference(
            f"Call auto-optimize {token} now.", "auto-optimize"
        )
        self.assertIsNotNone(found)
        self.assertNotIn(token, found[1])

    def test_present_non_array_governance_fields_fail_closed(self):
        fields = (
            "retired_skills",
            "quarantined_skills",
            "external_actions",
            "pinned_materializations",
            "projection_denials",
            "retired_reference_allowlist",
        )
        for field in fields:
            with self.subTest(field=field):
                self.write_governance(**{field: ""})
                with self.assertRaisesRegex(ValueError, rf"{field} must be an array"):
                    self.validate()

    def test_present_non_array_resource_mappings_fail_closed(self):
        source_root = self.base / "independent-source"
        source_root.mkdir()
        source = self.write_skill(source_root, "pinned-skill")
        installed = self.write_skill(self.codex, "pinned-skill")
        self.write_governance(
            pinned_materializations=[
                {
                    "name": "pinned-skill",
                    "path": str(installed),
                    "source_path": str(source),
                    "reason": "Installer-managed test fixture.",
                    "resource_mappings": "",
                }
            ]
        )

        with self.assertRaisesRegex(
            ValueError,
            r"pinned_materializations\[0\]\.resource_mappings must be an array",
        ):
            self.validate()

    def test_unknown_governance_fields_fail_closed(self):
        data = json.loads(self.governance.read_text(encoding="utf-8"))
        data["retired_skill"] = ["misspelled"]
        self.governance.write_text(json.dumps(data), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, r"unknown governance field: retired_skill"):
            self.validate()

        self.write_governance()
        data = json.loads(self.governance.read_text(encoding="utf-8"))
        data["source_policy"]["projection_root"] = [str(self.codex)]
        self.governance.write_text(json.dumps(data), encoding="utf-8")

        with self.assertRaisesRegex(
            ValueError,
            r"unknown source_policy field: projection_root",
        ):
            self.validate()

    def test_secret_finding_suppresses_the_value(self):
        token = "ghp_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcd"
        self.write_skill(
            self.registry_skills,
            "secret-skill",
            files={"scripts/run.sh": f"TOKEN={token}\n"},
        )

        result = self.validate()
        serialized = json.dumps(result)

        self.assertIn("possible_embedded_secret", self.codes(result, "error"))
        self.assertNotIn(token, serialized)
        finding = next(
            item for item in result["findings"] if item["code"] == "possible_embedded_secret"
        )
        self.assertEqual(finding["details"]["line"], 1)

    def test_secret_like_eval_fixture_is_a_warning(self):
        token = "sk-" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
        self.write_skill(
            self.registry_skills,
            "fixture-skill",
            files={"evals/fixture/config.py": f"TOKEN = '{token}'\n"},
        )

        result = self.validate()

        self.assertTrue(result["ok"])
        self.assertIn("secret_pattern_in_test_fixture", self.codes(result, "warning"))
        self.assertNotIn(token, json.dumps(result))

    def test_directory_name_mismatch_and_physical_copy_are_warnings(self):
        self.write_skill(self.codex, "folder-name", name="declared-name")

        result = self.validate()

        self.assertTrue(result["ok"])
        codes = self.codes(result, "warning")
        self.assertIn("directory_name_mismatch", codes)
        self.assertIn("physical_projection_unpinned", codes)

    def test_exact_pinned_materialization_is_verified_against_its_source(self):
        source_root = self.base / "independent-source"
        source_root.mkdir()
        source = self.write_skill(source_root, "pinned-skill", body="verified version")
        installed = self.write_skill(self.codex, "pinned-skill", body="verified version")
        self.write_governance(
            pinned_materializations=[
                {
                    "name": "pinned-skill",
                    "path": str(installed),
                    "source_path": str(source),
                    "reason": "Installer-managed test fixture.",
                }
            ]
        )

        result = self.validate()

        self.assertTrue(result["ok"])
        self.assertNotIn("physical_projection_unpinned", self.codes(result))

        (installed / "SKILL.md").write_text(
            "---\nname: pinned-skill\ndescription: Use when testing.\n---\n\n# Drift\n",
            encoding="utf-8",
        )
        drifted = self.validate()

        self.assertFalse(drifted["ok"])
        self.assertIn("pinned_materialization_drift", self.codes(drifted, "error"))

    def test_file_skill_can_pin_a_physical_runtime_materialization(self):
        source_root = self.base / "independent-source"
        source_root.mkdir()
        source = self.write_file_skill(source_root, "pinned-file", body="verified version")
        installed = self.write_skill(self.codex, "pinned-file", body="verified version")
        self.write_governance(
            pinned_materializations=[
                {
                    "name": "pinned-file",
                    "path": str(installed),
                    "source_path": str(source),
                    "reason": "Installer-managed file Skill fixture.",
                }
            ]
        )

        result = self.validate()

        self.assertTrue(result["ok"])
        self.assertNotIn("pinned_materialization_source_missing", self.codes(result))
        self.assertNotIn("physical_projection_unpinned", self.codes(result))

        (installed / "SKILL.md").write_text(
            "---\nname: pinned-file\ndescription: Use when testing.\n---\n\n# Drift\n",
            encoding="utf-8",
        )
        drifted = self.validate()

        self.assertFalse(drifted["ok"])
        self.assertIn("pinned_materialization_drift", self.codes(drifted, "error"))

    def test_missing_pinned_materialization_is_an_error(self):
        source_root = self.base / "independent-source"
        source_root.mkdir()
        source = self.write_skill(source_root, "pinned-skill")
        self.write_governance(
            pinned_materializations=[
                {
                    "name": "pinned-skill",
                    "path": str(self.codex / "missing-skill"),
                    "source_path": str(source),
                    "reason": "Installer-managed test fixture.",
                }
            ]
        )

        result = self.validate()

        self.assertFalse(result["ok"])
        self.assertIn("pinned_materialization_missing", self.codes(result, "error"))

    def test_composite_pinned_materialization_verifies_resource_mapping(self):
        source_root = self.base / "independent-source"
        source_root.mkdir()
        source = self.write_skill(source_root, "composite-skill", body="verified version")
        shared_resource = source_root / "integrations" / "threads.md"
        shared_resource.parent.mkdir()
        shared_resource.write_text("# Threads\n", encoding="utf-8")
        installed = self.write_skill(
            self.codex,
            "composite-skill",
            body="verified version",
            files={"references/threads.md": "# Threads\n"},
        )
        self.write_governance(
            pinned_materializations=[
                {
                    "name": "composite-skill",
                    "path": str(installed),
                    "source_path": str(source),
                    "reason": "Installer-managed composite fixture.",
                    "resource_mappings": [
                        {
                            "source_path": str(shared_resource),
                            "destination_path": "references/threads.md",
                        }
                    ],
                }
            ]
        )

        result = self.validate()
        self.assertTrue(result["ok"])
        self.assertNotIn("physical_projection_unpinned", self.codes(result))

        (installed / "references" / "threads.md").write_text("# Drift\n", encoding="utf-8")
        drifted = self.validate()
        self.assertIn("pinned_materialization_drift", self.codes(drifted, "error"))

    def test_composite_mapping_satisfies_source_resource_reference(self):
        source = self.write_skill(
            self.registry_skills,
            "composite-source",
            body="Read [Threads](references/threads.md).",
        )
        shared_resource = self.base / "integrations" / "threads.md"
        shared_resource.parent.mkdir()
        shared_resource.write_text("# Threads\n", encoding="utf-8")
        installed = self.write_skill(
            self.codex,
            "composite-source",
            body="Read [Threads](references/threads.md).",
            files={"references/threads.md": "# Threads\n"},
        )
        self.write_governance(
            pinned_materializations=[
                {
                    "name": "composite-source",
                    "path": str(installed),
                    "source_path": str(source),
                    "reason": "Installer-managed composite fixture.",
                    "resource_mappings": [
                        {
                            "source_path": str(shared_resource),
                            "destination_path": "references/threads.md",
                        }
                    ],
                }
            ]
        )

        result = self.validate()

        self.assertTrue(result["ok"])
        self.assertNotIn("missing_skill_resource", self.codes(result))

    def test_resource_mapping_cannot_source_from_projection(self):
        source_root = self.base / "independent-source"
        source_root.mkdir()
        source = self.write_skill(source_root, "self-map-skill", body="verified version")
        installed = self.write_skill(
            self.codex,
            "self-map-skill",
            body="verified version",
            files={"references/local.md": "# Local\n"},
        )
        inner_resource = installed / "references" / "local.md"
        self.write_governance(
            pinned_materializations=[
                {
                    "name": "self-map-skill",
                    "path": str(installed),
                    "source_path": str(source),
                    "reason": "Installer-managed self-map fixture.",
                    "resource_mappings": [
                        {
                            "source_path": str(inner_resource),
                            "destination_path": "references/local.md",
                        }
                    ],
                }
            ]
        )

        result = self.validate()

        self.assertFalse(result["ok"])
        self.assertIn("pinned_materialization_self_source", self.codes(result, "error"))
        finding = next(
            item
            for item in result["findings"]
            if item["code"] == "pinned_materialization_self_source"
        )
        self.assertEqual(finding["path"], str(inner_resource))
        self.assertEqual(finding["details"]["projection_path"], str(installed))
        # Must fail closed before digest comparison hides the self-source.
        self.assertNotIn("pinned_materialization_drift", self.codes(result))

    def test_iter_skill_files_skips_special_files(self):
        skill_dir = self.write_skill(
            self.registry_skills,
            "special-nodes",
            files={"references/guide.md": "ok\n"},
        )
        fifo_path = skill_dir / "references" / "hang.fifo"
        os.mkfifo(fifo_path)
        link_to_fifo = skill_dir / "references" / "hang.link"
        os.symlink(fifo_path, link_to_fifo)

        found = list(ecosystem_model.iter_skill_files(skill_dir))
        found_names = {path.name for path in found}

        self.assertIn("SKILL.md", found_names)
        self.assertIn("guide.md", found_names)
        self.assertNotIn("hang.fifo", found_names)
        # Symlink entries remain for digest hashing via readlink.
        self.assertIn("hang.link", found_names)
        self.assertFalse(ecosystem_model.is_regular_content_file(link_to_fifo))

        # Directory digest must also complete without opening the FIFO.
        digest = ecosystem_model.directory_digest(skill_dir)
        self.assertEqual(len(digest), 64)

        # Full content scanners must not hang on symlink→FIFO either.
        os.symlink(skill_dir, self.codex / skill_dir.name, target_is_directory=True)
        result = self.validate()
        self.assertNotIn("skill_unreadable", self.codes(result, "error"))

    def test_loom_doctor_uses_argv_and_reports_pending_operations(self):
        payload = {
            "ok": True,
            "data": {
                "healthy": True,
                "checks": {
                    "projection_drift": {"ok": True},
                    "pending_queue": {"count": 7},
                },
            },
        }
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(payload), stderr=""
        )
        findings = []
        with mock.patch.object(ecosystem_scans.subprocess, "run", return_value=completed) as run:
            ecosystem_scans.run_loom_doctor(findings, "loom-test")

        run.assert_called_once_with(
            ["loom-test", "workspace", "doctor", "--json"],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        self.assertEqual([finding.code for finding in findings], ["loom_pending_ops"])
        self.assertEqual(findings[0].details["count"], 7)

    def test_cli_emits_json_and_uses_documented_exit_codes(self):
        source = self.write_skill(self.registry_skills, "safe-skill")
        os.symlink(source, self.codex / "safe-skill", target_is_directory=True)
        os.symlink(source, self.claude / "safe-skill", target_is_directory=True)

        completed = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "--governance",
                str(self.governance),
                "--skip-loom",
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["summary"]["instances"], 3)

        self.governance.write_text('{"schema_version": 2}', encoding="utf-8")
        invalid = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "--governance",
                str(self.governance),
                "--skip-loom",
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(invalid.returncode, 2)
        self.assertFalse(json.loads(invalid.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
