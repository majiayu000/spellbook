"""Installer ownership stops at the managed link, including layout changes."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def run_installer(tmp_path: Path, command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash", "-c",
            'source "$1/install.sh"\n'
            'INSTALL_DIR="$2/checkout"\n'
            'LEGACY_INSTALL_DIR="$2/legacy"\n' + command,
            "ownership-test", str(ROOT), str(tmp_path),
        ],
        cwd=ROOT,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        check=False,
    )


def source_skill(tmp_path: Path, layout: str) -> Path:
    source = tmp_path / "checkout" / "skills"
    source.mkdir(parents=True)
    skill_file = source / "demo.SKILL.md" if layout == "file" else source / "demo" / "SKILL.md"
    skill_file.parent.mkdir(exist_ok=True)
    skill_file.write_text("---\nname: demo\ndescription: Installer test.\n---\n")
    return skill_file


def install_command(mode: str) -> str:
    if mode == "all":
        return 'install_all_skills_to_dir "$2/runtime" "Claude Code"'
    return 'install_skills_to_dir "$2/runtime" "Claude Code" demo'


@pytest.mark.parametrize("command", [
    'uninstall_from_skills_dir "$2/runtime"',
    'prune_stale_managed_skills_from_dir "$2/runtime" "Claude Code"',
    'prune_all_managed_skills_from_dir "$2/runtime" "legacy Codex"',
    'prune_managed_skill_target "$2/runtime" retired',
])
def test_cleanup_preserves_user_files_inside_managed_wrapper(tmp_path: Path, command: str) -> None:
    source = source_skill(tmp_path, "file")
    target = tmp_path / "runtime" / "retired"
    target.mkdir(parents=True)
    (target / "SKILL.md").symlink_to(source)
    (target / "notes.txt").write_bytes(b"user notes\x00\xff")
    (target / ".private").mkdir()
    (target / ".private" / "more.txt").write_bytes(b"keep hidden children")

    result = run_installer(tmp_path, command)

    assert result.returncode == 0, result.stdout + result.stderr
    assert not (target / "SKILL.md").is_symlink()
    assert (target / "notes.txt").read_bytes() == b"user notes\x00\xff"
    assert (target / ".private" / "more.txt").read_bytes() == b"keep hidden children"
    assert source.is_file()
    assert "Preserving remaining files" in result.stdout


def test_uninstall_removes_empty_wrapper_and_directory_link_only(tmp_path: Path) -> None:
    source = source_skill(tmp_path, "directory")
    runtime = tmp_path / "runtime"
    wrapper = runtime / "wrapped"
    wrapper.mkdir(parents=True)
    (wrapper / "SKILL.md").symlink_to(source)
    (runtime / "linked").symlink_to(source.parent, target_is_directory=True)
    (source.parent / "notes.txt").write_text("source data")

    result = run_installer(tmp_path, 'uninstall_from_skills_dir "$2/runtime"')

    assert result.returncode == 0, result.stdout + result.stderr
    assert not wrapper.exists()
    assert not (runtime / "linked").is_symlink()
    assert source.is_file()
    assert (source.parent / "notes.txt").read_text() == "source data"


@pytest.mark.parametrize("mode", ["all", "selected"])
@pytest.mark.parametrize("layout", ["file", "directory"])
@pytest.mark.parametrize("existing", ["directory", "symlink", "file"])
def test_unmanaged_install_target_is_preserved_and_not_counted(
    tmp_path: Path, mode: str, layout: str, existing: str
) -> None:
    source_skill(tmp_path, layout)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    target = runtime / "demo"
    if existing == "directory":
        target.mkdir()
        (target / "SKILL.md").write_bytes(b"user skill")
    elif existing == "symlink":
        user = tmp_path / "user-skill"
        user.mkdir()
        (user / "SKILL.md").write_bytes(b"user skill")
        target.symlink_to(user, target_is_directory=True)
    else:
        target.write_bytes(b"user skill")

    result = run_installer(tmp_path, install_command(mode))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Installed 0 skills" in result.stdout
    assert "Skipping demo: unmanaged" in result.stdout
    if existing == "file":
        assert target.read_bytes() == b"user skill"
    else:
        assert (target / "SKILL.md").read_bytes() == b"user skill"
        assert not (target / "demo").exists()
        assert target.is_symlink() == (existing == "symlink")


@pytest.mark.parametrize("mode", ["all", "selected"])
@pytest.mark.parametrize("user_files", [False, True])
def test_file_to_directory_layout_change_preserves_extra_files(
    tmp_path: Path, mode: str, user_files: bool
) -> None:
    source = source_skill(tmp_path, "directory")
    target = tmp_path / "runtime" / "demo"
    target.mkdir(parents=True)
    (target / "SKILL.md").symlink_to(tmp_path / "checkout" / "skills" / "demo.SKILL.md")
    if user_files:
        (target / "notes.txt").write_text("keep this")

    result = run_installer(tmp_path, install_command(mode))

    assert result.returncode == 0, result.stdout + result.stderr
    if user_files:
        assert (target / "notes.txt").read_text() == "keep this"
        assert not target.is_symlink()
        assert not (target / "SKILL.md").is_symlink()
        assert not (target / "demo").exists()
        assert "Installed 0 skills" in result.stdout
    else:
        assert target.is_symlink()
        assert target.resolve() == source.parent
        assert "Installed 1 skills" in result.stdout


def test_file_skill_update_keeps_user_files_and_replaces_only_owned_entry(tmp_path: Path) -> None:
    source = source_skill(tmp_path, "file")
    target = tmp_path / "runtime" / "demo"
    target.mkdir(parents=True)
    (target / "SKILL.md").symlink_to(tmp_path / "legacy" / "skills" / "demo.SKILL.md")
    (target / "notes.txt").write_text("keep this")

    result = run_installer(tmp_path, install_command("selected"))

    assert result.returncode == 0, result.stdout + result.stderr
    assert (target / "SKILL.md").resolve() == source
    assert (target / "notes.txt").read_text() == "keep this"
    assert "Installed 1 skills" in result.stdout
