from __future__ import annotations

import os
from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "xray" / "scripts" / "render-check.sh"


def _fake_tools(tmp_path: Path, *, direct_playwright: bool) -> tuple[Path, Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    npx_trace = tmp_path / "npx-argv.txt"
    playwright_trace = tmp_path / "playwright-argv.txt"
    executable = bin_dir / "npx"
    executable.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$@\" >> \"$XRAY_NPX_TRACE\"\n"
        "if [ \"${1:-}\" = '--no-install' ] && [ \"${2:-}\" = 'playwright' ] "
        "&& [ \"${3:-}\" = '--version' ]; then exit 0; fi\n"
        "if [ \"${XRAY_PLAYWRIGHT_FAIL:-0}\" = '1' ]; then exit 7; fi\n"
        "for last do :; done\n"
        "mkdir -p \"$(dirname \"$last\")\"\n"
        ": > \"$last\"\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    if direct_playwright:
        executable = bin_dir / "playwright"
        executable.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' \"$@\" >> \"$XRAY_PLAYWRIGHT_TRACE\"\n"
            "if [ \"${1:-}\" = '--version' ]; then exit 0; fi\n"
            "if [ \"${XRAY_PLAYWRIGHT_FAIL:-0}\" = '1' ]; then exit 7; fi\n"
            "for last do :; done\n"
            "mkdir -p \"$(dirname \"$last\")\"\n"
            ": > \"$last\"\n",
            encoding="utf-8",
        )
        executable.chmod(0o755)
    return bin_dir, npx_trace, playwright_trace


def _run(
    tmp_path: Path,
    *arguments: Path,
    direct_playwright: bool = False,
    fail: bool = False,
) -> subprocess.CompletedProcess[str]:
    bin_dir, npx_trace, playwright_trace = _fake_tools(
        tmp_path, direct_playwright=direct_playwright
    )
    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{bin_dir}:{environment['PATH']}",
            "TMPDIR": str(tmp_path / "temporary"),
            "XRAY_NPX_TRACE": str(npx_trace),
            "XRAY_PLAYWRIGHT_TRACE": str(playwright_trace),
            "XRAY_PLAYWRIGHT_FAIL": "1" if fail else "0",
        }
    )
    (tmp_path / "temporary").mkdir()
    result = subprocess.run(
        [str(SCRIPT), *(str(argument) for argument in arguments)],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )
    result.trace = npx_trace  # type: ignore[attr-defined]
    result.playwright_trace = playwright_trace  # type: ignore[attr-defined]
    return result


def test_render_check_uses_encoded_file_uri_and_full_page_capture(tmp_path: Path) -> None:
    page_dir = tmp_path / "folder #1"
    page_dir.mkdir()
    page = page_dir / "explain?this.html"
    page.write_text("<main>evidence</main>", encoding="utf-8")
    output = tmp_path / "captures"

    result = _run(tmp_path, page, output)

    assert result.returncode == 0, result.stderr
    trace = result.trace.read_text(encoding="utf-8")  # type: ignore[attr-defined]
    assert trace.count("--full-page") == 2
    assert "folder%20%231/explain%3Fthis.html" in trace
    assert "--viewport-size\n1280, 720" in trace
    assert "--viewport-size\n390, 844" in trace
    assert (output / "render-wide.png").is_file()
    assert (output / "render-narrow.png").is_file()


def test_render_check_refuses_to_overwrite_an_existing_output_directory(
    tmp_path: Path,
) -> None:
    page = tmp_path / "page.html"
    page.write_text("<main>evidence</main>", encoding="utf-8")
    output = tmp_path / "captures"
    output.mkdir()

    result = _run(tmp_path, page, output)

    assert result.returncode != 0
    assert "output directory already exists" in result.stderr
    assert not result.trace.exists()  # type: ignore[attr-defined]


def test_render_check_uses_a_fresh_temporary_directory_by_default(
    tmp_path: Path,
) -> None:
    page = tmp_path / "page.html"
    page.write_text("<main>evidence</main>", encoding="utf-8")
    sibling = tmp_path / "render-wide.png"
    sibling.write_text("keep", encoding="utf-8")

    result = _run(tmp_path, page)

    assert result.returncode == 0, result.stderr
    assert sibling.read_text(encoding="utf-8") == "keep"
    output = Path(result.stdout.splitlines()[-1].removeprefix("wrote "))
    assert output.parent == tmp_path / "temporary"
    assert output.name.startswith("xray-render.")
    assert (output / "render-wide.png").is_file()
    assert (output / "render-narrow.png").is_file()


def test_render_check_prefers_playwright_on_path(tmp_path: Path) -> None:
    page = tmp_path / "page.html"
    page.write_text("<main>evidence</main>", encoding="utf-8")

    result = _run(tmp_path, page, direct_playwright=True)

    assert result.returncode == 0, result.stderr
    assert result.playwright_trace.exists()  # type: ignore[attr-defined]
    assert not result.trace.exists()  # type: ignore[attr-defined]


def test_render_check_removes_its_output_directory_after_failure(tmp_path: Path) -> None:
    page = tmp_path / "page.html"
    page.write_text("<main>evidence</main>", encoding="utf-8")
    output = tmp_path / "captures"

    result = _run(tmp_path, page, output, fail=True)

    assert result.returncode != 0
    assert not output.exists()


def test_visual_contract_distinguishes_svg_and_canvas_label_checks() -> None:
    contract = (
        REPO_ROOT / "skills" / "xray" / "references" / "visual-explanation.md"
    ).read_text(encoding="utf-8")

    assert "getBBox()" in contract
    assert "measureText()" in contract
