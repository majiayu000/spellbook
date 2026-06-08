import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InstallPruneTests(unittest.TestCase):
    def test_prunes_stale_managed_skill_links_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            source_skills = home / ".spellbook" / "skills"
            target_skills = home / ".claude" / "skills"
            codex_source = source_skills / "codex"
            user_source = home / "custom-skills" / "local-only"

            codex_source.mkdir(parents=True)
            (codex_source / "SKILL.md").write_text(
                "---\nname: codex\ndescription: Use when testing.\n---\n",
                encoding="utf-8",
            )
            user_source.mkdir(parents=True)
            target_skills.mkdir(parents=True)

            stale_link = target_skills / "claude-mem"
            current_link = target_skills / "codex"
            user_link = target_skills / "local-only"

            try:
                stale_link.symlink_to(source_skills / "claude-mem", target_is_directory=True)
                current_link.symlink_to(codex_source, target_is_directory=True)
                user_link.symlink_to(user_source, target_is_directory=True)
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
            self.assertTrue(current_link.is_symlink())
            self.assertTrue(user_link.is_symlink())


if __name__ == "__main__":
    unittest.main()
