import io
import importlib.util
import sys
import types
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SKILL_SCRIPT = (
    REPO_ROOT / "skills" / "skill-creator" / "scripts" / "package_skill.py"
)
SAFE_PATHS_SCRIPT = REPO_ROOT / "scripts" / "skill_path_safety.py"


def load_package_skill():
    spec = importlib.util.spec_from_file_location(
        "skill_creator_package_skill",
        PACKAGE_SKILL_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.package_skill


package_skill = load_package_skill()


def load_safe_paths():
    spec = importlib.util.spec_from_file_location(
        "skill_creator_safe_paths_test",
        SAFE_PATHS_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


safe_paths = load_safe_paths()


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

    def test_rejects_unsafe_skill_directory_name(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_path = root / "unsafe name"
            skill_path.mkdir()
            (skill_path / "SKILL.md").write_text(
                "---\n"
                "name: safe-skill\n"
                "description: A safe skill in an unsafe directory name.\n"
                "---\n\n"
                "# Safe Skill\n",
                encoding="utf-8",
            )
            output_dir = root / "dist"

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                archive_path = package_skill(skill_path, output_dir)

            self.assertIsNone(archive_path)
            self.assertIn("skill directory name", stdout.getvalue())
            self.assertFalse(output_dir.exists())

    def test_rejects_backslash_skill_directory_name(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_path = root / "unsafe\\name"
            try:
                skill_path.mkdir()
            except OSError as exc:
                self.skipTest(f"backslash filename is not available: {exc}")
            (skill_path / "SKILL.md").write_text(
                "---\n"
                "name: safe-skill\n"
                "description: A safe skill in an unsafe directory name.\n"
                "---\n\n"
                "# Safe Skill\n",
                encoding="utf-8",
            )
            output_dir = root / "dist"

            with redirect_stdout(io.StringIO()):
                archive_path = package_skill(skill_path, output_dir)

            self.assertIsNone(archive_path)
            self.assertFalse(output_dir.exists())

    def test_safe_output_path_rejects_escape_payloads(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            payloads = [
                "../pwned.skill",
                "../../etc/passwd.skill",
                "/absolute/evil.skill",
                "subdir/../../escape.skill",
                "evil\\name.skill",
            ]

            for payload in payloads:
                with self.subTest(payload=payload):
                    with self.assertRaises(ValueError):
                        safe_paths.safe_output_path(root, payload)
                    self.assertFalse((root.parent / "pwned.skill").exists())

    def test_safe_zip_arcname_rejects_traversal_payloads(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_parent = root / "skills"
            skill_parent.mkdir()
            file_path = skill_parent / "safe-skill" / "SKILL.md"
            file_path.parent.mkdir()
            file_path.write_text("ok", encoding="utf-8")

            self.assertEqual(
                safe_paths.safe_archive_name(*file_path.relative_to(skill_parent).parts),
                "safe-skill/SKILL.md",
            )
            for root_name in ["../pwned", "..\\pwned"]:
                with self.subTest(root_name=root_name):
                    with self.assertRaises(ValueError):
                        safe_paths.safe_archive_name(root_name, "SKILL.md")
            for root_name in ["unsafe name", "unsafe\\name"]:
                with self.subTest(root_name=root_name):
                    with self.assertRaises(ValueError):
                        safe_paths.safe_kebab_name(root_name, kind="skill directory name")

    def test_rejects_rooted_archive_member_after_backslash_normalization(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_path = self.make_skill(root)
            try:
                (skill_path / "\\evil.md").write_text("bad", encoding="utf-8")
            except OSError as exc:
                self.skipTest(f"backslash filename is not available: {exc}")
            output_dir = root / "dist"

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                archive_path = package_skill(skill_path, output_dir)

            self.assertIsNone(archive_path)
            self.assertIn("archive name must be relative", stdout.getvalue())
            self.assertFalse((output_dir / "safe-skill.skill").exists())

    def test_loads_sibling_validator_when_top_level_name_is_taken(self):
        fake_validator = types.ModuleType("quick_validate")

        def fail_if_used(_skill_path):
            raise AssertionError("loaded unrelated quick_validate module")

        fake_validator.validate_skill = fail_if_used
        previous = sys.modules.get("quick_validate")
        sys.modules["quick_validate"] = fake_validator
        try:
            isolated_package_skill = load_package_skill()
            with TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                skill_path = self.make_skill(root)
                output_dir = root / "dist"

                with redirect_stdout(io.StringIO()):
                    archive_path = isolated_package_skill(skill_path, output_dir)

                self.assertEqual(archive_path, (output_dir / "safe-skill.skill").resolve())
                self.assertTrue(archive_path.exists())
        finally:
            if previous is None:
                sys.modules.pop("quick_validate", None)
            else:
                sys.modules["quick_validate"] = previous


if __name__ == "__main__":
    unittest.main()
