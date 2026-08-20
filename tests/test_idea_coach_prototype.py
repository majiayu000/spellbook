from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/idea-to-product/scripts/verify_prototype.py"
SPEC = importlib.util.spec_from_file_location("verify_prototype", SCRIPT)
assert SPEC and SPEC.loader
verify_prototype = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_prototype)


def valid_html(extra_head: str = "", extra_body: str = "") -> str:
    return f"""<!doctype html>
<html><head><style>
@media (prefers-color-scheme: dark) {{ body {{ color: white; }} }}
@media (max-width: 640px) {{ body {{ width: auto; }} }}
{extra_head}
</style></head><body>{extra_body}<script>
document.addEventListener('click', () => {{}});
function showStep() {{}}
showStep(1);
</script></body></html>"""


def test_accepts_bounded_offline_prototype(tmp_path: Path) -> None:
    prototype = tmp_path / "prototype.html"
    prototype.write_text(valid_html(), encoding="utf-8")
    assert verify_prototype.verify(prototype) == []


def test_rejects_external_attributes_regardless_of_order_or_quotes(
    tmp_path: Path,
) -> None:
    prototype = tmp_path / "prototype.html"
    prototype.write_text(
        valid_html(extra_body="<script defer src='https://cdn.example/app.js'></script>"),
        encoding="utf-8",
    )
    errors = verify_prototype.verify(prototype)
    assert any("script src" in error for error in errors)
    assert any("remote src" in error for error in errors)


def test_rejects_remote_css_and_network_calls(tmp_path: Path) -> None:
    prototype = tmp_path / "prototype.html"
    prototype.write_text(
        valid_html(
            extra_head="@import url(//cdn.example/theme.css);",
            extra_body="<script>fetch('https://api.example/data')</script>",
        ),
        encoding="utf-8",
    )
    errors = verify_prototype.verify(prototype)
    assert "remote CSS @import" in errors
    assert "remote fetch" in errors


def test_rejects_placeholders_and_missing_initial_progress(tmp_path: Path) -> None:
    prototype = tmp_path / "prototype.html"
    text = valid_html(extra_body="{{unsafe_value}}")
    prototype.write_text(text.replace("showStep(1);", ""), encoding="utf-8")
    errors = verify_prototype.verify(prototype)
    assert "unresolved template placeholder" in errors
    assert "missing initial progress state" in errors


def test_rejects_inline_handlers_and_javascript_urls(tmp_path: Path) -> None:
    prototype = tmp_path / "prototype.html"
    prototype.write_text(
        valid_html(
            extra_body=(
                '<img src="x" onerror="alert(1)">'
                '<a href="javascript:alert(2)">unsafe</a>'
            )
        ),
        encoding="utf-8",
    )
    errors = verify_prototype.verify(prototype)
    assert any("inline event handler" in error for error in errors)
    assert any("javascript URL" in error for error in errors)
