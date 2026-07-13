"""Shared data structures and deterministic content hashing."""

from __future__ import annotations

import hashlib
import os
import re
import stat
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


IGNORED_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache"}
IGNORED_FILES = {".DS_Store"}
NAME_LINE = re.compile(r"^name\s*:\s*(.+?)\s*$", re.MULTILINE)
SUPPORT_DIR_PATTERN = r"(?:agents|assets|evals|reference|references|scripts|templates)"
RESOURCE_LINK = re.compile(
    rf"\[[^\]]+\]\(\s*<?((?:\./)?{SUPPORT_DIR_PATTERN}/[A-Za-z0-9_.@+/-]+)"
)
ACTION_RESOURCE_REFERENCE = re.compile(
    r"(?im)\b(?:read|open|load|run|execute|读取|打开|加载|运行)\s+"
    rf"`?((?:\./)?{SUPPORT_DIR_PATTERN}/[A-Za-z0-9_.@+/-]+)"
)
SECRET_RULES = (
    (
        "private_key",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
    (
        "github_token",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b"),
    ),
    (
        "openai_api_key",
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b"),
    ),
    (
        "aws_access_key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "literal_bearer_token",
        re.compile(
            r"(?i)\bauthorization\b[^\n]{0,32}\bbearer\s+[A-Za-z0-9._~-]{24,}"
        ),
    ),
)


@dataclass(frozen=True)
class SkillInstance:
    name: str
    path: str
    resolved_path: str
    root_kind: str
    digest: str
    is_symlink: bool
    layout: str
    skill_file_path: str


@dataclass(frozen=True)
class EcosystemFinding:
    severity: str
    code: str
    message: str
    path: str | None = None
    details: dict | None = None


def expand_path(raw_path: str) -> Path:
    """Expand environment and user markers without invoking a shell."""
    return Path(os.path.expandvars(raw_path)).expanduser()


def frontmatter_name(skill_file: Path) -> str | None:
    try:
        text = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    match = NAME_LINE.search(text[3:end])
    if not match:
        return None
    return match.group(1).strip().strip("'\"") or None


def iter_skill_files(base: Path) -> Iterator[Path]:
    for current, dir_names, file_names in os.walk(base, followlinks=False):
        dir_names[:] = sorted(
            name
            for name in dir_names
            if name not in IGNORED_DIRS and not name.startswith(".git")
        )
        current_path = Path(current)
        for file_name in sorted(file_names):
            if file_name in IGNORED_FILES or file_name.endswith((".pyc", ".pyo")):
                continue
            path = current_path / file_name
            try:
                mode = path.lstat().st_mode
            except OSError:
                continue
            # Skip FIFOs, devices, and sockets so later open() cannot hang.
            if not (stat.S_ISREG(mode) or stat.S_ISLNK(mode)):
                continue
            yield path


def files_digest(files: dict[str, Path]) -> str:
    digest = hashlib.sha256()
    for relative, file_path in sorted(files.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        if file_path.is_symlink():
            digest.update(b"LINK\0")
            digest.update(os.readlink(file_path).encode("utf-8", "surrogateescape"))
        else:
            with file_path.open("rb") as handle:
                while chunk := handle.read(1024 * 1024):
                    digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def directory_digest(base: Path) -> str:
    resolved = base.resolve(strict=True)
    files = {
        file_path.relative_to(resolved).as_posix(): file_path
        for file_path in iter_skill_files(resolved)
    }
    return files_digest(files)


def file_skill_digest(skill_file: Path) -> str:
    resolved = skill_file.resolve(strict=True)
    return files_digest({"SKILL.md": resolved})


def materialization_digest(base: Path, mappings: list[dict]) -> str:
    resolved = base.resolve(strict=True)
    files = (
        {"SKILL.md": resolved}
        if resolved.is_file()
        else {
            file_path.relative_to(resolved).as_posix(): file_path
            for file_path in iter_skill_files(resolved)
        }
    )
    for mapping in mappings:
        source = expand_path(mapping["source_path"]).resolve(strict=True)
        files[Path(mapping["destination_path"]).as_posix()] = source
    return files_digest(files)


def finding_sort_key(finding: EcosystemFinding) -> tuple[int, str, str]:
    severity_order = {"error": 0, "warning": 1, "info": 2}
    return (
        severity_order.get(finding.severity, 9),
        finding.code,
        finding.path or "",
    )
