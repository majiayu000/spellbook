import contextlib
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
try:
    import audit_skill_quality
    import validate_skills
finally:
    sys.path.remove(str(ROOT / "scripts"))


@contextlib.contextmanager
def patched_roots(root: Path):
    old_validate_root = validate_skills.ROOT
    old_audit_root = audit_skill_quality.ROOT
    validate_skills.ROOT = root
    audit_skill_quality.ROOT = root
    try:
        yield
    finally:
        validate_skills.ROOT = old_validate_root
        audit_skill_quality.ROOT = old_audit_root


def write_skill(root: Path, name: str, body: str) -> validate_skills.SkillEntry:
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        f"name: {name}\n"
        "description: Use when testing artifact validation fixtures.\n"
        "---\n\n"
        f"{body}\n",
        encoding="utf-8",
    )
    return validate_skills.SkillEntry(
        install_name=name,
        path=f"skills/{name}/SKILL.md",
        format="directory",
        frontmatter={},
    )


class SkillArtifactCheckTests(unittest.TestCase):
    def test_validate_entries_rejects_missing_support_reference_fixture(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            entry = write_skill(root, "fixture-skill", "Read [the guide](references/missing.md).")

            with patched_roots(root):
                messages = validate_skills.validate_entries([entry])

            self.assertTrue(
                any("references missing support file: references/missing.md" in message for message in messages),
                messages,
            )

    def test_validate_entries_accepts_existing_support_reference(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            entry = write_skill(root, "fixture-skill", "Read [the guide](references/guide.md).")
            support_file = root / "skills" / "fixture-skill" / "references" / "guide.md"
            support_file.parent.mkdir()
            support_file.write_text("guide", encoding="utf-8")

            with patched_roots(root):
                messages = validate_skills.validate_entries([entry])

            self.assertFalse([message for message in messages if "support file" in message], messages)

    def test_validate_entries_rejects_unresolved_runtime_placeholder(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            entry = write_skill(root, "fixture-skill", "Run `{SCRIPT}` before publishing.")

            with patched_roots(root):
                messages = validate_skills.validate_entries([entry])

            self.assertTrue(
                any("contains unresolved placeholder token: {SCRIPT}" in message for message in messages),
                messages,
            )

    def test_validate_entries_rejects_absolute_support_link(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            entry = write_skill(root, "fixture-skill", "Read [setup](/references/setup.md).")

            with patched_roots(root):
                messages = validate_skills.validate_entries([entry])

            self.assertTrue(
                any("references unsafe support path /references/setup.md: is absolute" in message for message in messages),
                messages,
            )

    def test_validate_entries_detects_non_ascii_plain_support_reference(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            entry = write_skill(root, "fixture-skill", "Read references/真实高赞网感示例.md first.")

            with patched_roots(root):
                messages = validate_skills.validate_entries([entry])

            self.assertTrue(
                any("references missing support file: references/真实高赞网感示例.md" in message for message in messages),
                messages,
            )

    def test_audit_reports_missing_support_reference_with_actionable_path(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            entry = write_skill(root, "fixture-skill", "Read references/missing.md first.")

            with patched_roots(root):
                findings = audit_skill_quality.audit_entry(entry)

            missing = [finding for finding in findings if finding.check == "missing-support-file"]
            self.assertEqual(len(missing), 1, findings)
            self.assertEqual(missing[0].path, "skills/fixture-skill/SKILL.md")
            self.assertIn("references/missing.md", missing[0].message)

    def test_audit_reports_script_reference_without_executable_or_shebang(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            entry = write_skill(root, "fixture-skill", "Run [helper](scripts/helper.py).")
            script_file = root / "skills" / "fixture-skill" / "scripts" / "helper.py"
            script_file.parent.mkdir()
            script_file.write_text("print('missing shebang')\n", encoding="utf-8")

            with patched_roots(root):
                findings = audit_skill_quality.audit_entry(entry)

            self.assertTrue(any(finding.check == "script-reference" for finding in findings), findings)


if __name__ == "__main__":
    unittest.main()
