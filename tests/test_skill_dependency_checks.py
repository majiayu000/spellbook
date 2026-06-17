import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
DEPENDENCY_CHECKS_SCRIPT = ROOT / "scripts" / "skill_dependency_checks.py"


def load_dependency_checks():
    spec = importlib.util.spec_from_file_location(
        "skill_dependency_checks_test",
        DEPENDENCY_CHECKS_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dependency_checks = load_dependency_checks()


def format_error(message: str) -> str:
    return f"ERROR: {message}"


class SkillDependencyChecksTests(unittest.TestCase):
    def write_demo_skill(self, root: Path, script_text: str, requirements_text: str | None = None) -> Path:
        skill_dir = root / "skills" / "demo-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            "name: demo-skill\n"
            "description: Use when testing script dependency validation.\n"
            "---\n\n"
            "# Demo Skill\n",
            encoding="utf-8",
        )
        (scripts_dir / "tool.py").write_text(script_text, encoding="utf-8")
        if requirements_text is not None:
            (skill_dir / "requirements.txt").write_text(requirements_text, encoding="utf-8")
        return skill_dir

    def validate_demo_skill(self, root: Path) -> list[str]:
        return dependency_checks.validate_script_dependencies(
            root=root,
            entry_path="skills/demo-skill/SKILL.md",
            entry_format="directory",
            error=format_error,
        )

    def test_missing_requirements_file_reports_third_party_imports(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_demo_skill(root, "import requests\nfrom PIL import Image\nfrom pilmoji import Pilmoji\n")

            messages = self.validate_demo_skill(root)

            self.assertEqual(len(messages), 1)
            self.assertIn("missing skills/demo-skill/requirements.txt", messages[0])
            self.assertIn("Pillow", messages[0])
            self.assertIn("pilmoji", messages[0])
            self.assertIn("requests", messages[0])

    def test_existing_requirements_file_must_declare_all_detected_packages(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_demo_skill(root, "import requests\nfrom PIL import Image\n", "requests>=2\n")

            messages = self.validate_demo_skill(root)

            self.assertEqual(len(messages), 1)
            self.assertIn("missing script package declaration(s): Pillow", messages[0])

    def test_declared_requirements_pass_and_local_script_imports_are_ignored(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_demo_skill(
                root,
                "from scripts.utils import parse_skill_md\nimport yaml\n",
                "PyYAML\n",
            )

            self.assertEqual(self.validate_demo_skill(root), [])

    def test_lxml_parser_usage_requires_lxml_declaration(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_demo_skill(
                root,
                "from bs4 import BeautifulSoup\nsoup = BeautifulSoup(requests.get(url).text, \"lxml\")\n",
                "beautifulsoup4\n",
            )

            messages = self.validate_demo_skill(root)

            self.assertEqual(len(messages), 1)
            self.assertIn("missing script package declaration(s): lxml", messages[0])

    def test_lxml_parser_usage_passes_when_declared(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_demo_skill(
                root,
                "from bs4 import BeautifulSoup\nsoup = BeautifulSoup(html, 'lxml')\n",
                "beautifulsoup4\nlxml\n",
            )

            self.assertEqual(self.validate_demo_skill(root), [])

    def test_requirements_include_file_satisfies_dependency(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_dir = self.write_demo_skill(root, "import requests\n", "-r common.txt\n")
            (skill_dir / "common.txt").write_text("requests\n", encoding="utf-8")

            self.assertEqual(self.validate_demo_skill(root), [])

    def test_marker_gated_requirement_does_not_satisfy_unconditional_import(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_demo_skill(root, "import requests\n", 'requests; python_version < "3.0"\n')

            messages = self.validate_demo_skill(root)

            self.assertEqual(len(messages), 1)
            self.assertIn("missing script package declaration(s): requests", messages[0])

    def test_stdlib_only_scripts_do_not_require_requirements_file(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_demo_skill(root, "import json\nfrom pathlib import Path\n")

            self.assertEqual(self.validate_demo_skill(root), [])


if __name__ == "__main__":
    unittest.main()
