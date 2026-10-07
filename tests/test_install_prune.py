import os
import subprocess
import sys
import shlex
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

    def test_standard_metadata_filters_install_and_prune_like_legacy_mapping(self):
        for declaration in (
            'compatibility: {runtimes: [codex]}',
            'compatibility: Requires Codex.\nmetadata:\n  spellbook-runtimes: "codex"',
        ):
            with self.subTest(declaration=declaration), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                source_skills = home / ".spellbook" / "skills"
                self.write_skill(source_skills, "runtime-only", declaration)
                self.write_skill(source_skills, "unrestricted", 'compatibility: Requires Python.')
                self.write_skill(source_skills, "portable", 'metadata:\n  spellbook-runtimes: "portable"')
                env = os.environ.copy()
                env["HOME"] = str(home)
                env.pop("CODEX_SKILLS_DIR", None)
                result = subprocess.run([
                    "bash", "-c", 'source ./install.sh; TARGET=all; setup_directories; install_all_skills'
                ], cwd=ROOT, env=env, text=True, capture_output=True, check=False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertFalse((home / ".claude/skills/runtime-only").exists())
                self.assertTrue((home / ".agents/skills/runtime-only/SKILL.md").is_file())
                for runtime_path in (".claude/skills", ".agents/skills"):
                    for name in ("unrestricted", "portable"):
                        self.assertTrue((home / runtime_path / name / "SKILL.md").is_file())

    def test_runtime_filter_requires_pyyaml_and_preserves_runtime_selection(self):
        declarations = (
            'compatibility: Requires Codex.\nmetadata:\n  spellbook-runtimes: "codex"',
            'metadata:\n    spellbook-runtimes: codex',
            'compatibility: {runtimes: [codex]}',
            'compatibility: { runtimes: [codex] }',
            'compatibility: {runtimes:  [codex]}',
        )
        for declaration, has_pyyaml in (
            (declaration, has_pyyaml)
            for declaration in declarations
            for has_pyyaml in (True, False)
        ):
            with self.subTest(declaration=declaration, pyyaml=has_pyyaml), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                source = self.write_skill(home / ".spellbook/skills", "codex-only", declaration)
                bin_dir = home / "bin"
                bin_dir.mkdir()
                python = bin_dir / "python3"
                site_option = "" if has_pyyaml else "-S "
                python.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {site_option}"$@"\n', encoding="utf-8")
                python.chmod(0o755)
                env = os.environ.copy()
                env["HOME"] = str(home)
                env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]
                env.pop("CODEX_SKILLS_DIR", None)
                if not has_pyyaml:
                    env.pop("PYTHONPATH", None)
                for runtime, expected in (("codex", 0), ("claude_code", 1)):
                    with self.subTest(runtime=runtime):
                        result = subprocess.run([
                            "bash", "-c", f'source {shlex.quote(str(ROOT / "install.sh"))}; '
                            f'skill_supports_runtime {shlex.quote(str(source / "SKILL.md"))} {runtime}'
                        ], cwd=home, env=env, text=True, capture_output=True, check=False)
                        output = result.stdout + result.stderr
                        self.assertEqual(result.returncode, expected if has_pyyaml else 1, output)
                        if not has_pyyaml:
                            self.assertIn("requires PyYAML", output)
                if not has_pyyaml:
                    before = sorted(str(path.relative_to(home)) for path in home.rglob("*"))
                    result = subprocess.run([
                        "bash", str(ROOT / "install.sh"), "--target", "codex", "--skills", "codex-only"
                    ], cwd=home, env=env, text=True, capture_output=True, check=False)
                    output = result.stdout + result.stderr
                    self.assertEqual(result.returncode, 1, output)
                    self.assertIn("requires PyYAML", output)
                    self.assertIn("Checking prerequisites", output)
                    self.assertNotIn("Prerequisites check passed", output)
                    self.assertNotIn("Installed", output)
                    self.assertEqual(sorted(str(path.relative_to(home)) for path in home.rglob("*")), before)
                    self.assertFalse(os.path.lexists(home / ".agents/skills/codex-only"))

    def test_invalid_standard_metadata_stops_installer_before_install(self):
        for declaration in (
            'metadata:\n  spellbook-runtimes: "unknown_host"',
            'metadata:\n  spellbook-runtimes: "codex codex"',
            'metadata:\n  spellbook-runtimes: "unspecified"',
            'metadata:\n  spellbook-runtimes: ""',
        ):
            with self.subTest(declaration=declaration), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp)
                source_skills = home / ".spellbook" / "skills"
                self.write_skill(source_skills, "invalid", declaration)
                env = os.environ.copy()
                env["HOME"] = str(home)
                result = subprocess.run([
                    "bash", "-c", 'source ./install.sh; setup_directories; '
                    'install_skills_to_dir "$CLAUDE_SKILLS_DIR" "Claude Code" invalid'
                ], cwd=ROOT, env=env, text=True, capture_output=True, check=False)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("Invalid runtime compatibility", result.stdout + result.stderr)
                self.assertFalse((home / ".claude/skills/invalid").exists())

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

    def test_selected_skill_installs_to_both_runtimes_without_legacy_codex_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            source_skills = home / ".spellbook" / "skills"
            self.write_skill(source_skills, "shared-skill")

            env = os.environ.copy()
            env["HOME"] = str(home)
            env.pop("CODEX_SKILLS_DIR", None)
            env.pop("CODEX_HOME", None)

            result = subprocess.run(
                [
                    "bash",
                    "-e",
                    "-c",
                    (
                        "source ./install.sh; "
                        "TARGET=all; "
                        "setup_directories; "
                        'install_skills "shared-skill"'
                    ),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((home / ".claude" / "skills" / "shared-skill").is_symlink())
            self.assertTrue((home / ".agents" / "skills" / "shared-skill").is_symlink())
            self.assertFalse((home / ".codex" / "skills").exists())

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
