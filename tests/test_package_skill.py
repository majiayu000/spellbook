import io
import importlib.util
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SKILL_SCRIPT = (
    REPO_ROOT / "skills" / "skill-creator" / "scripts" / "package_skill.py"
)


def load_package_skill():
    spec = importlib.util.spec_from_file_location(
        "skill_creator_package_skill",
        PACKAGE_SKILL_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.package_skill


package_skill = load_package_skill()


class PackageSkillTests(unittest.TestCase):
    def make_skill(self, root: Path) -> Path:
        skill_path = root / "safe-skill"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            "---\n"
            "name: safe-skill\n"
            "description: A safe skill for packager tests.\n"
            "---\n\n"
            "# Safe Skill\n",
            encoding="utf-8",
        )
        return skill_path

    def test_packages_regular_files(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_path = self.make_skill(root)
            (skill_path / "references").mkdir()
            (skill_path / "references" / "notes.md").write_text("notes", encoding="utf-8")
            output_dir = root / "dist"

            with redirect_stdout(io.StringIO()):
                archive_path = package_skill(skill_path, output_dir)

            self.assertEqual(archive_path, (output_dir / "safe-skill.skill").resolve())
            self.assertTrue(archive_path.exists())
            with zipfile.ZipFile(archive_path) as archive:
                self.assertEqual(
                    sorted(archive.namelist()),
                    ["safe-skill/SKILL.md", "safe-skill/references/notes.md"],
                )

    def test_rejects_symlink_to_file_outside_skill(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_path = self.make_skill(root)
            outside_file = root / "outside-secret.txt"
            outside_file.write_text("SECRET_TOKEN=leaked", encoding="utf-8")
            symlink_path = skill_path / "secret-link.txt"
            try:
                symlink_path.symlink_to(outside_file)
            except OSError as exc:
                self.skipTest(f"symlinks are not available: {exc}")

            output_dir = root / "dist"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                archive_path = package_skill(skill_path, output_dir)

            self.assertIsNone(archive_path)
            self.assertIn("Symlinks are not allowed", stdout.getvalue())
            self.assertFalse((output_dir / "safe-skill.skill").exists())


if __name__ == "__main__":
    unittest.main()
