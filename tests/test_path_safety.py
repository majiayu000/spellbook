import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
PATH_SAFETY_SCRIPT = ROOT / "scripts" / "skill_path_safety.py"


def load_path_safety():
    spec = importlib.util.spec_from_file_location("spellbook_path_safety_test", PATH_SAFETY_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


path_safety = load_path_safety()


class PathSafetyTests(unittest.TestCase):
    def test_safe_kebab_name_rejects_unsafe_names(self):
        for payload in ["", ".", "..", "../pwned", "unsafe name", "safe\\..\\evil", "UPPER"]:
            with self.subTest(payload=payload):
                with self.assertRaises(path_safety.UnsafePathError):
                    path_safety.safe_kebab_name(payload)

    def test_safe_output_path_rejects_escape_payloads(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for payload in [
                "../pwned",
                "../../etc/passwd",
                "/absolute/evil",
                "subdir/../../escape",
                "..\\pwned",
                "safe\\..\\evil",
            ]:
                with self.subTest(payload=payload):
                    with self.assertRaises(path_safety.UnsafePathError):
                        path_safety.safe_output_path(root, payload)

    def test_safe_output_path_allows_contained_relative_path(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.assertEqual(
                path_safety.safe_output_path(root, "dist/safe-skill.skill"),
                root.resolve() / "dist" / "safe-skill.skill",
            )

    def test_safe_archive_name_rejects_traversal_payloads(self):
        for payload in [
            ("../pwned",),
            ("../../etc/passwd",),
            ("/absolute/evil",),
            ("subdir/../../escape",),
            ("..\\pwned",),
            ("safe\\..\\evil",),
        ]:
            with self.subTest(payload=payload):
                with self.assertRaises(path_safety.UnsafePathError):
                    path_safety.safe_archive_name(*payload)

    def test_safe_archive_name_uses_posix_separators(self):
        self.assertEqual(
            path_safety.safe_archive_name("safe-skill", "references", "guide.md"),
            "safe-skill/references/guide.md",
        )


if __name__ == "__main__":
    unittest.main()
