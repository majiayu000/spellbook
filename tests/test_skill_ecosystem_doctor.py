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
            timeout=60,
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
