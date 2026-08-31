import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_skills.py"


def load_validate_skills():
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        spec = importlib.util.spec_from_file_location(
            "validate_skills_browser_test", VALIDATE_SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(ROOT / "scripts"))
        sys.modules.pop("validate_skills_browser_test", None)


validate_skills = load_validate_skills()


def entry(name: str, description: str = "A useful skill"):
    return validate_skills.SkillEntry(
        install_name=name,
        path=f"skills/{name}/SKILL.md",
        format="directory",
        frontmatter={"description": description},
    )


def browser_template(block: str) -> str:
    return f"<html><head><title>Keep me</title></head><body>\n{block}\n<script>keep();</script>\n</body></html>\n"


def test_render_browser_document_replaces_only_the_generated_data_block():
    old_block = (
        f"{validate_skills.BROWSER_DATA_START}\n"
        "const SKILLS = [];\n"
        f"{validate_skills.BROWSER_DATA_END}"
    )
    original = browser_template(old_block)

    rendered = validate_skills.render_browser_document(original, [entry("alpha")])

    assert "<title>Keep me</title>" in rendered
    assert "<script>keep();</script>" in rendered
    assert '"name":"alpha"' in rendered
    assert rendered.count(validate_skills.BROWSER_DATA_START) == 1
    assert rendered.count(validate_skills.BROWSER_DATA_END) == 1


def test_render_browser_document_rejects_missing_or_duplicate_markers():
    with pytest.raises(ValueError, match="exactly one generated data block"):
        validate_skills.render_browser_document("<html></html>", [entry("alpha")])

    duplicate = browser_template(
        f"{validate_skills.BROWSER_DATA_START}\n"
        f"{validate_skills.BROWSER_DATA_END}\n"
        f"{validate_skills.BROWSER_DATA_START}\n"
        f"{validate_skills.BROWSER_DATA_END}"
    )
    with pytest.raises(ValueError, match="exactly one generated data block"):
        validate_skills.render_browser_document(duplicate, [entry("alpha")])

    reversed_markers = browser_template(
        f"{validate_skills.BROWSER_DATA_END}\n"
        f"{validate_skills.BROWSER_DATA_START}"
    )
    with pytest.raises(ValueError, match="ordered generated data block"):
        validate_skills.render_browser_document(reversed_markers, [entry("alpha")])


def test_render_browser_data_is_deterministic_and_uses_registry_fields():
    entries = [entry("beta", 'Use <beta> & "ship"'), entry("alpha")]

    first = validate_skills.render_browser_data_block(entries)
    second = validate_skills.render_browser_data_block(entries)

    assert first == second
    assert '"name":"beta"' in first
    assert '"description":"Use \\u003cbeta\\u003e \\u0026 \\"ship\\""' in first
    assert "</script>" not in first
    assert '"compatibility"' not in first
    assert '"format"' not in first


def test_browser_page_has_canonical_and_social_metadata():
    page = (ROOT / "docs" / "skills.html").read_text(encoding="utf-8")

    assert '<link rel="canonical" href="https://majiayu000.github.io/spellbook/skills.html">' in page
    assert '<meta property="og:url" content="https://majiayu000.github.io/spellbook/skills.html">' in page
    assert '<meta name="twitter:card" content="summary">' in page
