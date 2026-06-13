"""Path safety helpers for skill packaging and generation scripts."""

from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath, PureWindowsPath


class UnsafePathError(ValueError):
    """Raised when an untrusted path or name would escape its container."""


SAFE_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def is_relative_to(path: Path, directory: Path) -> bool:
    """Return whether ``path`` is contained by ``directory``."""
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def safe_kebab_name(value: str, *, kind: str = "name") -> str:
    """Validate a single untrusted kebab-case path component."""
    if not value:
        raise UnsafePathError(f"{kind} must not be empty")
    if value in {".", ".."}:
        raise UnsafePathError(f"{kind} must not be {value!r}")
    if "/" in value or "\\" in value:
        raise UnsafePathError(f"{kind} must not contain path separators: {value!r}")
    if not SAFE_KEBAB_RE.fullmatch(value):
        raise UnsafePathError(
            f"{kind} must be kebab-case lowercase letters, digits, and hyphens: {value!r}"
        )
    if len(value) > 64:
        raise UnsafePathError(f"{kind} is too long ({len(value)} characters); maximum is 64")
    return value


def _reject_absolute_or_drive(path: Path | str, *, kind: str) -> None:
    raw = str(path)
    if Path(raw).is_absolute() or PureWindowsPath(raw).is_absolute() or PureWindowsPath(raw).drive:
        raise UnsafePathError(f"{kind} must be relative: {raw!r}")


def safe_output_path(base: Path, candidate: Path | str, *, kind: str = "output") -> Path:
    """Join ``candidate`` under ``base`` and reject traversal or absolute paths."""
    _reject_absolute_or_drive(candidate, kind=kind)
    candidate_path = Path(candidate)
    if any(part in {"", ".", ".."} for part in candidate_path.parts):
        raise UnsafePathError(f"{kind} contains unsafe component: {candidate!r}")
    if any("\\" in part for part in candidate_path.parts):
        raise UnsafePathError(f"{kind} contains unsafe separator: {candidate!r}")

    base_path = Path(base).expanduser().resolve()
    output = Path(os.path.normpath(base_path / candidate_path))
    if not is_relative_to(output, base_path):
        raise UnsafePathError(f"{kind} escapes destination directory: {output}")
    return output


def safe_archive_name(*parts: Path | str) -> str:
    """Build a portable relative archive member name."""
    raw_parts: list[str] = []
    for part in parts:
        _reject_absolute_or_drive(part, kind="archive name")
        normalized = PurePosixPath(str(part).replace("\\", "/"))
        if normalized.is_absolute():
            raise UnsafePathError(f"archive name must be relative: {part!r}")
        raw_parts.extend(normalized.parts)

    if not raw_parts:
        raise UnsafePathError("archive name must not be empty")
    if any(part in {"", ".", "..", "/"} for part in raw_parts):
        raise UnsafePathError(f"archive name contains unsafe component: {'/'.join(raw_parts)!r}")
    if any("\\" in part for part in raw_parts):
        raise UnsafePathError(f"archive name contains unsafe separator: {'/'.join(raw_parts)!r}")
    return PurePosixPath(*raw_parts).as_posix()
