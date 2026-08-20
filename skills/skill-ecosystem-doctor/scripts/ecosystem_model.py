"""Shared data structures and deterministic content hashing."""

from __future__ import annotations

import hashlib
import os
import re
import stat
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


# Single source of truth for governed runtimes.
#
# Key = runtime id used by the governance policy (managed_global_sources.runtimes,
# projection_runtimes). Value = the runtime's Skill directory name, used both
# for the global Skill home (``~/<dir>``) and for the per-project projection
# directory (``<project>/<dir>/skills``). Codex configuration still lives under
# ``~/.codex``; its current Skill catalog is ``~/.agents/skills``. Every runtime
# whitelist, Skill-home mapping, project directory, and Loom target id in the
# doctor is derived from this mapping; do not duplicate the list elsewhere.
RUNTIME_HOME_DIRS: dict[str, str] = {
    "codex": ".agents",
    "claude": ".claude",
    "gemini": ".gemini",
    "cursor": ".cursor",
}
# State written by earlier Doctor releases may still name Codex's retired Skill
# target. Keep migration aliases beside the runtime mapping so reconciliation can
# remove stale mirror records without treating the legacy path as active.
LEGACY_RUNTIME_TARGET_IDS: dict[str, frozenset[str]] = {
    "codex": frozenset({"target_codex_codex_skills"}),
}
SUPPORTED_RUNTIMES = frozenset(RUNTIME_HOME_DIRS)
# Runtimes projected automatically when a policy does not say otherwise. Keep
# the historical runtime set while resolving Codex through its current Skill path.
DEFAULT_PROJECTION_RUNTIMES: tuple[str, ...] = ("codex", "claude")

IGNORED_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache"}
IGNORED_FILES = {".DS_Store"}
ACTIVE_ROOT_KINDS = {"projection", "managed_projection"}
SOURCE_ROOT_KINDS = {"registry", "canonical_source", "repository_source"}
INVENTORY_ROOT_KINDS = {
    "canonical_source",
    "repository_source",
    "managed_projection",
    "managed_cache",
    "archive",
}
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


def root_is_active(root_kind: str) -> bool:
    return root_kind in ACTIVE_ROOT_KINDS


def root_is_source(root_kind: str) -> bool:
    return root_kind in SOURCE_ROOT_KINDS


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


def runtime_home_flag(runtime: str) -> str:
    """CLI flag name that overrides one runtime home."""
    return f"--{runtime}-home"


def runtime_home_dest(runtime: str) -> str:
    """argparse destination for :func:`runtime_home_flag`."""
    return f"{runtime}_home"


def default_runtime_homes(base: Path | None = None) -> dict[str, Path]:
    """Default home directory per governed runtime.

    Homes are derived from the user's home directory exactly the way the
    original ``--codex-home``/``--claude-home`` defaults were: no absolute path
    is hardcoded, and every runtime stays overridable through its own
    ``--<runtime>-home`` flag.
    """
    root = base if base is not None else Path.home()
    return {runtime: root / directory for runtime, directory in RUNTIME_HOME_DIRS.items()}


def runtime_project_dir(runtime: str) -> str:
    """Per-project projection directory name for a runtime (e.g. ``.agents``)."""
    return RUNTIME_HOME_DIRS[runtime]


def runtime_target_id(runtime: str) -> str:
    """Loom registry target id for a runtime's global skills directory."""
    directory = RUNTIME_HOME_DIRS[runtime].lstrip(".")
    return f"target_{runtime}_{directory}_skills"


def runtime_target_ids(runtime: str) -> frozenset[str]:
    """Current and retired Loom target ids recognized during state migration."""
    return frozenset({runtime_target_id(runtime)}) | LEGACY_RUNTIME_TARGET_IDS.get(
        runtime, frozenset()
    )


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


def is_regular_content_file(path: Path) -> bool:
    """True only for regular files after following one symlink hop.

    Symlinks to FIFOs/devices must not be opened for content scans: open()
    can block forever on a FIFO even though the walk entry is a symlink.
    """
    try:
        mode = path.stat().st_mode
    except OSError:
        return False
    return stat.S_ISREG(mode)


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
            # Fail closed: unreadable entries must surface to directory_digest
            # callers as skill_unreadable rather than silently omitting bytes.
            mode = path.lstat().st_mode
            # Skip direct FIFOs, devices, and sockets so later open() cannot hang.
            # Symlinks are still yielded so digests can hash link targets via
            # readlink; content scanners must use is_regular_content_file.
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
