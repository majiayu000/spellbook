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

DOCTOR_SCRIPTS = ROOT / "skills" / "skill-ecosystem-doctor" / "scripts"
sys.path.insert(0, str(DOCTOR_SCRIPTS))
try:
    import ecosystem_reconcile
finally:
    sys.path.remove(str(DOCTOR_SCRIPTS))


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

    def test_frontmatter_requires_pyyaml_instead_of_guessing_scalar_types(self):
        for raw in ('false', 'null', '123', '"false"', '"null"', '"123"'):
            with self.subTest(raw=raw), TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                skill_dir, entry = write_skill(root, compatibility=f"compatibility: {raw}")
                with patched_root(root), patched_yaml(None):
                    frontmatter, messages = validate_skills.parse_frontmatter(skill_dir / "SKILL.md")
                    validation = validate_skills.validate_entries([entry])
                self.assertEqual(frontmatter, {})
                self.assertTrue(any("requires PyYAML" in message for message in messages), messages)
                self.assertTrue(any("requires PyYAML" in message for message in validation), validation)

    def test_pyyaml_distinguishes_plain_scalars_from_quoted_text(self):
        for raw in ('false', 'null', '123', '"false"', '"null"', '"123"'):
            with self.subTest(raw=raw), TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                skill_dir, entry = write_skill(root, compatibility=f"compatibility: {raw}")
                with patched_root(root):
                    messages = validate_skills.validate_entries([entry])
                self.assertEqual(bool(messages), not raw.startswith('"'), messages)
                self.assertEqual(quick_validate.validate_skill(skill_dir)[0], raw.startswith('"'))

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
            ("compatibility: 123", "compatibility must be a non-empty string"),
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

    def test_standard_text_and_metadata_preserve_registry_and_quick_validation(self):
        for yaml_parser in (validate_skills.yaml,):
            with self.subTest(fallback=yaml_parser is None), TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                skill_dir, entry = write_skill(root, compatibility=(
                    'compatibility: Requires a compatible host and Python.\n'
                    'metadata:\n  author: Example\n'
                    '  spellbook-runtimes: "portable codex" # runtime IDs\n'
                ))
                with patched_root(root), patched_yaml(yaml_parser):
                    frontmatter, parse_messages = validate_skills.parse_frontmatter(skill_dir / "SKILL.md")
                    messages = validate_skills.validate_entries([entry])
                self.assertFalse(parse_messages + messages, parse_messages + messages)
                entry = validate_skills.SkillEntry(entry.install_name, entry.path, entry.format, frontmatter)
                self.assertEqual(validate_skills.registry_payload([entry])[0]["compatibility"],
                                 {"runtimes": ["codex", "portable"]})
                self.assertEqual(quick_validate.validate_skill(skill_dir), (True, "Skill is valid!"))

    def test_standard_text_alone_does_not_infer_runtime(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_dir, entry = write_skill(root, compatibility="compatibility: codex")
            with patched_root(root):
                self.assertFalse(validate_skills.validate_entries([entry]))
                frontmatter, _ = validate_skills.parse_frontmatter(skill_dir / "SKILL.md")
            entry = validate_skills.SkillEntry(entry.install_name, entry.path, entry.format, frontmatter)
            self.assertEqual(validate_skills.registry_payload([entry])[0]["compatibility"],
                             {"runtimes": ["unspecified"]})
            self.assertEqual(quick_validate.validate_skill(skill_dir), (True, "Skill is valid!"))

    def test_metadata_errors_are_rejected_by_both_validators(self):
        cases = [
            'metadata:\n  spellbook-runtimes: ""',
            'metadata:\n  spellbook-runtimes: [codex]',
            'metadata:\n  spellbook-runtimes: false',
            'metadata:\n  spellbook-runtimes: "made_up"',
            'metadata:\n  spellbook-runtimes: "unspecified"',
            'metadata:\n  spellbook-runtimes: "codex codex"',
            'compatibility: {runtimes: [codex]}\nmetadata:\n  spellbook-runtimes: "claude_code"',
            'compatibility: ""',
            'compatibility: 123',
            'compatibility: ' + 'x' * 501,
            'metadata: "codex"',
        ]
        for value in cases:
            with self.subTest(value=value), TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                skill_dir, entry = write_skill(root, compatibility=value)
                with patched_root(root):
                    messages = validate_skills.validate_entries([entry])
                self.assertTrue(any(message.startswith("ERROR:") for message in messages), messages)
                self.assertFalse(quick_validate.validate_skill(skill_dir)[0])

    def test_compatibility_length_uses_parsed_text_before_whitespace_normalization(self):
        values = ("a" + "   a" * 200, " " + "x" * 500, "x" * 500 + " ", " " + "x" * 500 + " ")
        for value in values:
            for yaml_parser in (validate_skills.yaml,):
                with self.subTest(fallback=yaml_parser is None, length=len(value)), TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    skill_dir, entry = write_skill(root, compatibility=f'compatibility: "{value}"')
                    with patched_root(root), patched_yaml(yaml_parser):
                        frontmatter, parse_messages = validate_skills.parse_frontmatter(skill_dir / "SKILL.md")
                        messages = validate_skills.validate_entries([entry])
                    self.assertFalse(parse_messages, parse_messages)
                    self.assertEqual(frontmatter["compatibility"], value)
                    self.assertTrue(any("at most 500 characters" in message for message in messages), messages)
                    self.assertFalse(quick_validate.validate_skill(skill_dir)[0])
                    with self.assertRaisesRegex(ecosystem_reconcile.ReconcileError, "500 characters"):
                        ecosystem_reconcile._validate_frontmatter_extensions({}, {skill_dir.name: skill_dir / "SKILL.md"})

    def test_compatibility_limit_counts_whitespace_without_rejecting_valid_text(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_dir, entry = write_skill(root, compatibility='compatibility: " ' + 'x' * 498 + ' "')
            with patched_root(root):
                self.assertFalse(validate_skills.validate_entries([entry]))
            self.assertEqual(quick_validate.validate_skill(skill_dir), (True, "Skill is valid!"))
            ecosystem_reconcile._validate_frontmatter_extensions({}, {skill_dir.name: skill_dir / "SKILL.md"})

    def test_quoted_multiline_compatibility_keeps_blank_lines_in_length(self):
        for quote in ("'", '"'):
            with self.subTest(quote=quote), TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                declaration = f"compatibility: {quote}x\n" + "\n" * 500 + f"x{quote}"
                skill_dir, entry = write_skill(root, compatibility=declaration)
                with patched_root(root):
                    frontmatter, parse_messages = validate_skills.parse_frontmatter(skill_dir / "SKILL.md")
                    messages = validate_skills.validate_entries([entry])
                self.assertFalse(parse_messages, parse_messages)
                self.assertEqual(frontmatter["compatibility"], "x" + "\n" * 500 + "x")
                self.assertTrue(any("at most 500 characters" in message for message in messages), messages)
                self.assertFalse(quick_validate.validate_skill(skill_dir)[0])
                with self.assertRaisesRegex(ecosystem_reconcile.ReconcileError, "500 characters"):
                    ecosystem_reconcile._validate_frontmatter_extensions({}, {skill_dir.name: skill_dir / "SKILL.md"})
                with patched_root(root), patched_yaml(None):
                    frontmatter, messages = validate_skills.parse_frontmatter(skill_dir / "SKILL.md")
                self.assertEqual(frontmatter, {})
                self.assertTrue(any("requires PyYAML" in message for message in messages), messages)

    def test_fallback_requires_yaml_for_compatibility_block_scalars(self):
        for marker in (">-", "|-"):
            with self.subTest(marker=marker), TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                skill_dir, entry = write_skill(root, compatibility=f"compatibility: {marker}\n  " + "x" * 498)
                with patched_root(root):
                    frontmatter, messages = validate_skills.parse_frontmatter(skill_dir / "SKILL.md")
                    self.assertFalse(messages)
                    self.assertEqual(frontmatter["compatibility"], "x" * 498)
                with patched_root(root), patched_yaml(None):
                    _, messages = validate_skills.parse_frontmatter(skill_dir / "SKILL.md")
                    self.assertTrue(any("requires PyYAML" in message for message in messages), messages)
                    self.assertTrue(validate_skills.validate_entries([entry]))

    def test_legacy_mapping_remains_readable_by_both_validators(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill_dir, entry = write_skill(root, compatibility="compatibility: {runtimes: [codex]}")
            with patched_root(root):
                self.assertFalse(validate_skills.validate_entries([entry]))
            self.assertEqual(quick_validate.validate_skill(skill_dir), (True, "Skill is valid!"))

    def test_migrated_skill_frontmatter_conforms_to_standard_field_contract(self):
        # Agent Skills specification: compatibility is a string <= 500 chars;
        # metadata maps strings to strings. Host execution is a separate check.
        for name in ("codex", "codex-agent", "threads"):
            with self.subTest(name=name):
                path = ROOT / "skills" / name / "SKILL.md"
                frontmatter, messages = validate_skills.parse_frontmatter(path)
                self.assertFalse(messages)
                self.assertIsInstance(frontmatter["compatibility"], str)
                self.assertTrue(1 <= len(frontmatter["compatibility"]) <= 500)
                self.assertTrue(all(isinstance(k, str) and isinstance(v, str)
                                    for k, v in frontmatter["metadata"].items()))
                self.assertEqual(quick_validate.validate_skill(path.parent), (True, "Skill is valid!"))
                ecosystem_reconcile._validate_frontmatter_extensions({}, {name: path})
                with patched_yaml(None):
                    fallback, messages = validate_skills.parse_frontmatter(path)
                self.assertEqual(fallback, {})
                self.assertTrue(any("requires PyYAML" in message for message in messages), messages)

    def test_fallback_metadata_never_silently_drops_runtime_declarations(self):
        cases = [
            'metadata:\n    spellbook-runtimes: unsupported_host',
            'metadata:\n  "spellbook-runtimes": codex',
            'metadata:\n  author: Example\n    spellbook-runtimes: codex',
        ]
        for value in cases:
            with self.subTest(value=value), TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                _, entry = write_skill(root, compatibility=value)
                with patched_root(root), patched_yaml(None):
                    messages = validate_skills.validate_entries([entry])
                self.assertTrue(any(message.startswith("ERROR:") for message in messages), messages)

    def test_fallback_parser_does_not_treat_unknown_legacy_mapping_as_text(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, entry = write_skill(root, compatibility='compatibility: {runtimes: [codex], unknown: yes}')
            with patched_root(root), patched_yaml(None):
                messages = validate_skills.validate_entries([entry])
            self.assertTrue(any("requires PyYAML" in message for message in messages), messages)

    def test_fallback_parser_does_not_silently_drop_flow_metadata(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, entry = write_skill(root, compatibility='metadata: {spellbook-runtimes: codex}')
            with patched_root(root), patched_yaml(None):
                messages = validate_skills.validate_entries([entry])
            self.assertTrue(any("requires PyYAML" in message for message in messages), messages)


if __name__ == "__main__":
    unittest.main()
