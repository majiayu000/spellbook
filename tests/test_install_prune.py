import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InstallPruneTests(unittest.TestCase):
    def write_skill(self, skills_dir, name, compatibility=""):
        skill_dir = skills_dir / name
        skill_dir.mkdir(parents=True)
        frontmatter = [
            "---",
            f"name: {name}",
            "description: Use when testing installer runtime compatibility.",
        ]
        if compatibility:
            frontmatter.extend(compatibility.rstrip().splitlines())
        frontmatter.extend(["---", ""])
        (skill_dir / "SKILL.md").write_text("\n".join(frontmatter), encoding="utf-8")
        return skill_dir

    def test_codex_default_skills_dir_uses_agents_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["HOME"] = tmp
            env.pop("CODEX_SKILLS_DIR", None)

            result = subprocess.run(
                ["bash", "-c", 'source ./install.sh; printf "%s" "$CODEX_SKILLS_DIR"'],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, str(Path(tmp) / ".agents" / "skills"))

    def test_prunes_stale_managed_skill_links_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            source_skills = home / ".spellbook" / "skills"
            legacy_source_skills = home / ".claude-arsenal" / "skills"
            target_skills = home / ".claude" / "skills"
            codex_source = source_skills / "codex"
            user_source = home / "custom-skills" / "local-only"
            spellbook_named_user_source = home / "work" / "spellbook-experiments" / "local-only"
            arsenal_named_user_source = home / "work" / "claude-arsenal-not-managed" / "local-only"

            codex_source.mkdir(parents=True)
            (codex_source / "SKILL.md").write_text(
                "---\nname: codex\ndescription: Use when testing.\n---\n",
                encoding="utf-8",
            )
            user_source.mkdir(parents=True)
            spellbook_named_user_source.mkdir(parents=True)
            arsenal_named_user_source.mkdir(parents=True)
            target_skills.mkdir(parents=True)

            stale_link = target_skills / "claude-mem"
            legacy_stale_link = target_skills / "legacy-claude-mem"
            current_link = target_skills / "codex"
            user_link = target_skills / "local-only"
            spellbook_named_user_link = target_skills / "spellbook-local-only"
            arsenal_named_user_link = target_skills / "arsenal-local-only"

            try:
                stale_link.symlink_to(source_skills / "claude-mem", target_is_directory=True)
                legacy_stale_link.symlink_to(
                    legacy_source_skills / "claude-mem",
                    target_is_directory=True,
                )
                current_link.symlink_to(codex_source, target_is_directory=True)
                user_link.symlink_to(user_source, target_is_directory=True)
                spellbook_named_user_link.symlink_to(
                    spellbook_named_user_source,
                    target_is_directory=True,
                )
                arsenal_named_user_link.symlink_to(
                    arsenal_named_user_source,
                    target_is_directory=True,
                )
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlinks are not available: {exc}")

            env = os.environ.copy()
            env["HOME"] = str(home)
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    (
                        "source ./install.sh; "
                        'prune_stale_managed_skills_from_dir "$CLAUDE_SKILLS_DIR" "Claude Code"'
                    ),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(stale_link.is_symlink())
            self.assertFalse(legacy_stale_link.is_symlink())
            self.assertTrue(current_link.is_symlink())
            self.assertTrue(user_link.is_symlink())
            self.assertTrue(spellbook_named_user_link.is_symlink())
            self.assertTrue(arsenal_named_user_link.is_symlink())

    def test_runtime_compatibility_filters_installed_and_pruned_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            source_skills = home / ".spellbook" / "skills"
            claude_skills = home / ".claude" / "skills"
            codex_skills = home / ".agents" / "skills"

            threads_source = self.write_skill(
                source_skills,
                "threads",
                "compatibility: {runtimes: [codex]}",
            )
            self.write_skill(source_skills, "shared-skill")
            claude_skills.mkdir(parents=True)
            codex_skills.mkdir(parents=True)

            try:
                (claude_skills / "threads").symlink_to(threads_source, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlinks are not available: {exc}")

            env = os.environ.copy()
            env["HOME"] = str(home)

            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    (
                        "source ./install.sh; "
                        'install_all_skills_to_dir "$CLAUDE_SKILLS_DIR" "Claude Code"; '
                        'install_all_skills_to_dir "$CODEX_SKILLS_DIR" "Codex"'
                    ),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((claude_skills / "threads").exists())
            self.assertFalse((claude_skills / "threads").is_symlink())
            self.assertTrue((codex_skills / "threads").is_symlink())
            self.assertTrue((claude_skills / "shared-skill").is_symlink())
            self.assertTrue((codex_skills / "shared-skill").is_symlink())

    def test_runtime_compatibility_accepts_yaml_inline_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            source_skills = home / ".spellbook" / "skills"
            threads_source = self.write_skill(
                source_skills,
                "threads",
                "compatibility:\n  runtimes:\n    - codex # Codex-only",
            )

            env = os.environ.copy()
            env["HOME"] = str(home)
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    (
                        "source ./install.sh; "
                        f"skill_supports_runtime {str(threads_source / 'SKILL.md')!r} codex"
                    ),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_selected_incompatible_skill_prunes_managed_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            source_skills = home / ".spellbook" / "skills"
            claude_skills = home / ".claude" / "skills"
            threads_source = self.write_skill(
                source_skills,
                "threads",
                "compatibility: {runtimes: [codex]}",
            )
            claude_skills.mkdir(parents=True)

            try:
                (claude_skills / "threads").symlink_to(threads_source, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlinks are not available: {exc}")

            env = os.environ.copy()
            env["HOME"] = str(home)
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    (
                        "source ./install.sh; "
                        'install_skills_to_dir "$CLAUDE_SKILLS_DIR" "Claude Code" "threads"'
                    ),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((claude_skills / "threads").exists())
            self.assertFalse((claude_skills / "threads").is_symlink())

    def test_prunes_legacy_codex_managed_links_during_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            source_skills = home / ".spellbook" / "skills"
            codex_source = source_skills / "codex"
            legacy_codex_skills = home / ".codex" / "skills"
            user_source = home / "custom-skills" / "codex"

            codex_source.mkdir(parents=True)
            (codex_source / "SKILL.md").write_text(
                "---\nname: codex\ndescription: Use when testing.\n---\n",
                encoding="utf-8",
            )
            user_source.mkdir(parents=True)
            legacy_codex_skills.mkdir(parents=True)

            managed_current_link = legacy_codex_skills / "codex"
            managed_stale_link = legacy_codex_skills / "old-spellbook-skill"
            user_link = legacy_codex_skills / "user-codex"

            try:
                managed_current_link.symlink_to(codex_source, target_is_directory=True)
                managed_stale_link.symlink_to(source_skills / "old-spellbook-skill", target_is_directory=True)
                user_link.symlink_to(user_source, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlinks are not available: {exc}")

            env = os.environ.copy()
            env["HOME"] = str(home)
            env.pop("CODEX_SKILLS_DIR", None)
            env.pop("CODEX_HOME", None)

            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    "source ./install.sh; prune_legacy_codex_skills",
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(managed_current_link.exists())
            self.assertFalse(managed_current_link.is_symlink())
            self.assertFalse(managed_stale_link.exists())
            self.assertFalse(managed_stale_link.is_symlink())
            self.assertTrue(user_link.is_symlink())

    def test_selected_skill_name_cannot_escape_target_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            source_skills = home / ".spellbook" / "skills"
            target_skills = home / ".claude" / "skills"
            source_skills.mkdir(parents=True)
            target_skills.mkdir(parents=True)

            env = os.environ.copy()
            env["HOME"] = str(home)
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    (
                        "source ./install.sh; "
                        'install_skills_to_dir "$CLAUDE_SKILLS_DIR" "Claude Code" "../outside"'
                    ),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Invalid skill name", result.stdout + result.stderr)
            self.assertFalse((home / ".claude" / "outside").exists())


if __name__ == "__main__":
    unittest.main()
