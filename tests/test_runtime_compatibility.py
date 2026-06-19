import contextlib
import importlib.util
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
try:
    import validate_skills
finally:
    sys.path.remove(str(ROOT / "scripts"))


def load_quick_validate():
    script = ROOT / "skills" / "skill-creator" / "scripts" / "quick_validate.py"
    spec = importlib.util.spec_from_file_location("skill_creator_quick_validate_test", script)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


quick_validate = load_quick_validate()


@contextlib.contextmanager
def patched_root(root: Path):
    old_root = validate_skills.ROOT
    validate_skills.ROOT = root
    try:
        yield
    finally:
        validate_skills.ROOT = old_root


@contextlib.contextmanager
def patched_yaml(value):
    old_yaml = validate_skills.yaml
    validate_skills.yaml = value
    try:
        yield
    finally:
        validate_skills.yaml = old_yaml


def write_skill(root: Path, name: str = "fixture-skill", compatibility: str = ""):
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True)
    frontmatter = [
        "---",
        f"name: {name}",
        "description: Use when testing runtime compatibility metadata.",
    ]
    if compatibility:
        frontmatter.extend(compatibility.rstrip().splitlines())
    frontmatter.extend(["---", "", "# Fixture Skill", ""])
    (skill_dir / "SKILL.md").write_text("\n".join(frontmatter), encoding="utf-8")
    entry = validate_skills.SkillEntry(
        install_name=name,
        path=f"skills/{name}/SKILL.md",
        format="directory",
        frontmatter={},
    )
    return skill_dir, entry


class RuntimeCompatibilityTests(unittest.TestCase):
    def test_valid_metadata_validates_and_exports_normalized_registry_object(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_dir, entry = write_skill(
                root,
                compatibility="compatibility:\n  runtimes:\n    - codex\n    - portable",
            )

            with patched_root(root):
                messages = validate_skills.validate_entries([entry])
                frontmatter, parse_messages = validate_skills.parse_frontmatter(skill_dir / "SKILL.md")

            errors = [message for message in messages + parse_messages if message.startswith("ERROR:")]
            self.assertFalse(errors, errors)
            payload = validate_skills.registry_payload([
                validate_skills.SkillEntry("fixture-skill", entry.path, entry.format, frontmatter)
            ])
            self.assertEqual(payload[0]["compatibility"], {"runtimes": ["codex", "portable"]})
            doc = validate_skills.render_registry_doc([
                validate_skills.SkillEntry("fixture-skill", entry.path, entry.format, frontmatter)
            ])
            self.assertIn("| Name | Category | Format | Lang | Runtime | Tags | Path | Description |", doc)
            self.assertIn("| codex, portable |", doc)

    def test_fallback_parser_accepts_block_runtime_metadata_without_pyyaml(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_dir, entry = write_skill(
                root,
                compatibility="compatibility:\n  runtimes:\n    - codex\n    - portable",
            )

            with patched_root(root), patched_yaml(None):
                frontmatter, parse_messages = validate_skills.parse_frontmatter(skill_dir / "SKILL.md")
                messages = validate_skills.validate_entries([entry])

            errors = [message for message in messages + parse_messages if message.startswith("ERROR:")]
            self.assertFalse(errors, errors)
            self.assertEqual(frontmatter["compatibility"], {"runtimes": ["codex", "portable"]})

    def test_fallback_parser_strips_runtime_inline_comments_without_pyyaml(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_dir, entry = write_skill(
                root,
                compatibility="compatibility:\n  runtimes:\n    - codex # Codex-only",
            )

            with patched_root(root), patched_yaml(None):
                frontmatter, parse_messages = validate_skills.parse_frontmatter(skill_dir / "SKILL.md")
                messages = validate_skills.validate_entries([entry])

            errors = [message for message in messages + parse_messages if message.startswith("ERROR:")]
            self.assertFalse(errors, errors)
            self.assertEqual(frontmatter["compatibility"], {"runtimes": ["codex"]})

    def test_absent_metadata_exports_unspecified_runtime(self):
        entry = validate_skills.SkillEntry(
            "fixture-skill",
            "skills/fixture-skill/SKILL.md",
            "directory",
            {"name": "fixture-skill", "description": "Use when testing registry defaults."},
        )

        payload = validate_skills.registry_payload([entry])

        self.assertEqual(payload[0]["compatibility"], {"runtimes": ["unspecified"]})

    def test_invalid_runtime_declarations_are_rejected(self):
        cases = [
            ("compatibility: codex", "compatibility must be a YAML mapping"),
            ("compatibility:\n  runtimes: []", "compatibility.runtimes must be a non-empty list"),
            ("compatibility:\n  runtimes:\n    - made_up", "unsupported runtime made_up"),
            ("compatibility:\n  runtimes:\n    - unspecified", "must not declare unspecified"),
            ("compatibility:\n  runtimes:\n    - codex\n    - codex", "declares duplicate runtime codex"),
            ("compatibility:\n  runtimes:\n    - codex\n  notes: no", "unsupported compatibility keys: notes"),
        ]
        for compatibility, expected in cases:
            with self.subTest(expected=expected):
                with TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    _, entry = write_skill(root, compatibility=compatibility)

                    with patched_root(root):
                        messages = validate_skills.validate_entries([entry])

                    self.assertTrue(any(expected in message for message in messages), messages)

    def test_quick_validate_accepts_mapping_schema_and_rejects_string_schema(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            valid_skill_dir, _ = write_skill(root, compatibility="compatibility:\n  runtimes:\n    - codex")
            invalid_skill_dir, _ = write_skill(root, name="invalid-skill", compatibility="compatibility: codex")

            self.assertEqual(quick_validate.validate_skill(valid_skill_dir), (True, "Skill is valid!"))
            valid, message = quick_validate.validate_skill(invalid_skill_dir)

            self.assertFalse(valid)
            self.assertIn("Compatibility must be a YAML mapping", message)


if __name__ == "__main__":
    unittest.main()
