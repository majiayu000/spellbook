import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_skills.py"


def load_validate_skills():
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        spec = importlib.util.spec_from_file_location("validate_skills_path_safety_test", VALIDATE_SCRIPT)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(ROOT / "scripts"))
        sys.modules.pop("validate_skills_path_safety_test", None)


validate_skills = load_validate_skills()


class ValidateSkillsPathSafetyTests(unittest.TestCase):
    def test_validate_entries_rejects_unsafe_install_name_before_reading_path(self):
        entry = validate_skills.SkillEntry(
            install_name="../outside",
            path="../outside/SKILL.md",
            format="directory",
            frontmatter={},
        )

        messages = validate_skills.validate_entries([entry])

        self.assertTrue(any("unsafe registry path or install name" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
