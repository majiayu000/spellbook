#!/usr/bin/env python3
"""Shared privacy and JSON helpers for review-agent-harness."""

from __future__ import annotations

import json
import hashlib
import os
import re
import subprocess
import tempfile
from pathlib import Path


MAX_TEXT_LENGTH = 400
SNAPSHOT_MAX_DEPTH = 6
SNAPSHOT_MAX_FILES = 3000
SNAPSHOT_SKIP_DIRS = {
    ".agent-harness-review",
    ".git",
    ".venv",
    "build",
    "dist",
    "node_modules",
    "target",
    "vendor",
}

_INJECTED_BLOCK_RE = re.compile(
    r"<(environment_context|skill|codex_internal_context|recommended_plugins)\b[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?P<key>[\"']?(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|secret)[\"']?)"
    r"\s*[:=]\s*(?P<value>\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s,;}\]]+)",
    re.IGNORECASE,
)
_SECRET_FIELD_RE = re.compile(
    r"^(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|secret)$",
    re.IGNORECASE,
)
_SAFE_SECRET_VALUES = {
    "",
    "***",
    "[redacted]",
    "<redacted>",
    "<secret>",
    "false",
    "masked",
    "n/a",
    "none",
    "not configured",
    "not set",
    "null",
    "redacted",
    "unset",
}
_SECRET_TOKEN_RE = re.compile(
    r"\b(?:sk|ghp|github_pat|xox[abprs])[-_][A-Za-z0-9_-]{8,}\b|\bAKIA[0-9A-Z]{12,}\b",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"\b(?:authorization\s*:\s*)?bearer\s+[A-Za-z0-9._~+/=-]{8,}\b", re.IGNORECASE)
_USER_PATH_RE = re.compile(
    r"(?<![\w.-])/(?:Users|home|private|var|tmp|opt)/[^\s\"'`<>]+|[A-Za-z]:\\(?:Users\\)?[^\s\"'`<>]+"
)
_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_STABLE_ID_RE = re.compile(
    r"\b(?:session|thread|task)[-_:](?=[A-Za-z0-9._-]{8,}\b)(?=[A-Za-z0-9._-]*\d)[A-Za-z0-9._-]+\b",
    re.IGNORECASE,
)
_MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]\r\n]*\]\((?:<[^>\r\n]+>|[^)\r\n]+)\)")
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]\r\n]{1,200})\]\((?:<[^>\r\n]+>|[^)\r\n]+)\)")
_MARKDOWN_REFERENCE_LINK_RE = re.compile(r"\[([^\]\r\n]{1,200})\]\[[^\]\r\n]*\]")
_MARKDOWN_REFERENCE_DESTINATION_RE = re.compile(r"^\s*\[[^\]\r\n]+\]:\s*\S+.*$", re.MULTILINE)
_MARKDOWN_AUTOLINK_RE = re.compile(r"<(?:https?://|mailto:)[^>\r\n]+>", re.IGNORECASE)
_BARE_URL_RE = re.compile(r"(?<![\w<])(https?://[^\s<>\"'`]+)", re.IGNORECASE)
_HTML_DESTINATION_RE = re.compile(
    r"<[A-Za-z][^>]*(?:href|src|data|poster|action|formaction|xlink:href)\s*=\s*"
    r"(?:\"[^\"]*\"|'[^']*'|[^\s>]+)[^>]*>",
    re.IGNORECASE,
)
_HTML_META_REFRESH_RE = re.compile(
    r"<meta\b[^>]*http-equiv\s*=\s*(?:\"refresh\"|'refresh'|refresh)[^>]*content\s*=\s*"
    r"(?:\"[^\"]*url=[^\"]*\"|'[^']*url=[^']*'|[^\s>]*url=[^\s>]*)[^>]*>",
    re.IGNORECASE,
)


def sanitize_text(value: object, *, limit: int = MAX_TEXT_LENGTH) -> str:
    """Return bounded reader-safe text without secrets, stable ids, or home paths."""

    text = str(value or "")
    text = _INJECTED_BLOCK_RE.sub(" ", text)
    text = _MARKDOWN_IMAGE_RE.sub(" ", text)
    text = _MARKDOWN_LINK_RE.sub(r"\1", text)
    text = _MARKDOWN_REFERENCE_LINK_RE.sub(r"\1", text)
    text = _MARKDOWN_REFERENCE_DESTINATION_RE.sub(" ", text)
    text = _MARKDOWN_AUTOLINK_RE.sub(" ", text)
    text = _BARE_URL_RE.sub("<destination>", text)
    text = _BEARER_RE.sub("Bearer <redacted>", text)
    text = _SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group('key')}=<redacted>", text)
    text = _SECRET_TOKEN_RE.sub("<secret>", text)
    text = _USER_PATH_RE.sub("<path>", text)
    text = _UUID_RE.sub("<id>", text)
    text = _STABLE_ID_RE.sub("<id>", text)
    text = _HTML_DESTINATION_RE.sub(" ", text)
    text = _HTML_META_REFRESH_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return f"{text[: max(1, limit - 1)]}…"


def private_data_matches(value: object) -> list[str]:
    """Return privacy rule ids still visible in a value after expected sanitization."""

    text = str(value or "")
    matches: list[str] = []
    checks = (
        ("secret-token", _SECRET_TOKEN_RE),
        ("bearer-token", _BEARER_RE),
        ("user-path", _USER_PATH_RE),
        ("stable-uuid", _UUID_RE),
        ("stable-session-id", _STABLE_ID_RE),
        ("markdown-destination", _MARKDOWN_IMAGE_RE),
        ("markdown-destination", _MARKDOWN_LINK_RE),
        ("markdown-destination", _MARKDOWN_REFERENCE_LINK_RE),
        ("markdown-destination", _MARKDOWN_REFERENCE_DESTINATION_RE),
        ("markdown-destination", _MARKDOWN_AUTOLINK_RE),
        ("markdown-destination", _BARE_URL_RE),
        ("html-destination", _HTML_DESTINATION_RE),
        ("html-destination", _HTML_META_REFRESH_RE),
    )
    for rule_id, pattern in checks:
        if pattern.search(text):
            matches.append(rule_id)
    for match in _SECRET_ASSIGNMENT_RE.finditer(text):
        if not _safe_secret_scalar(match.group("value")):
            matches.append("secret-assignment")
            break
    return matches


def _safe_secret_scalar(value: object) -> bool:
    """Return whether an explicitly sensitive field contains no secret material."""

    if value is None or value is False:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value == 0:
        return True
    if not isinstance(value, str):
        return False
    normalized = value.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {"'", '"'}:
        normalized = normalized[1:-1].strip()
    return normalized.casefold() in _SAFE_SECRET_VALUES


def _descendant_scalars(value: object) -> list[object]:
    """Flatten only descendant values, excluding mapping keys."""

    if isinstance(value, dict):
        return [item for entry in value.values() for item in _descendant_scalars(entry)]
    if isinstance(value, list):
        return [item for entry in value for item in _descendant_scalars(entry)]
    return [value]


def all_strings(value: object) -> list[str]:
    """Flatten strings and preserve sensitive key-to-descendant relationships."""

    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for entry in value for item in all_strings(entry)]
    if isinstance(value, dict):
        strings: list[str] = []
        for key, entry in value.items():
            strings.extend(all_strings(key))
            if isinstance(key, str) and _SECRET_FIELD_RE.fullmatch(key.strip()):
                strings.extend(
                    f"{key}={json.dumps(scalar, ensure_ascii=False)}"
                    for scalar in _descendant_scalars(entry)
                    if not _safe_secret_scalar(scalar)
                )
            strings.extend(all_strings(entry))
        return strings
    return []


def privacy_rule_matches(value: object) -> list[str]:
    """Return unique privacy violations from a complete JSON-compatible tree."""

    return sorted({
        rule_id
        for text in all_strings(value)
        for rule_id in private_data_matches(text)
    })


def load_json(path: Path) -> dict[str, object]:
    """Load one JSON object and fail loudly for another top-level type."""

    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def write_json_atomic(path: Path, value: object, *, replace: bool = False) -> None:
    """Write JSON atomically and refuse unintended replacement."""

    privacy_hits = privacy_rule_matches(value)
    if privacy_hits:
        raise ValueError(f"refusing to persist private data: {', '.join(privacy_hits)}")
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not replace:
        raise FileExistsError(f"refusing to replace existing file: {path}")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False, sort_keys=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if replace:
            os.replace(temporary_path, path)
        else:
            try:
                os.link(temporary_path, path)
            except FileExistsError as error:
                raise FileExistsError(f"refusing to replace existing file: {path}") from error
            temporary_path.unlink()
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def target_identity(target: Path) -> str:
    """Return a privacy-safe identity for one concrete local target directory."""

    resolved = target.expanduser().resolve()
    if not resolved.is_dir():
        raise ValueError(f"target is not a directory: {target}")
    metadata = resolved.stat()
    material = f"{metadata.st_dev}:{metadata.st_ino}".encode("ascii")
    return f"local-sha256:{hashlib.sha256(material).hexdigest()}"


def _metadata_snapshot(target: Path) -> str:
    """Hash bounded relative file metadata without persisting private paths."""

    digest = hashlib.sha256()
    observed = 0
    omitted = 0
    for current, directories, names in os.walk(target):
        current_path = Path(current)
        depth = len(current_path.relative_to(target).parts)
        directories[:] = sorted(
            directory for directory in directories
            if directory not in SNAPSHOT_SKIP_DIRS
        )
        if depth >= SNAPSHOT_MAX_DEPTH:
            directories[:] = []
        for name in sorted(names):
            path = current_path / name
            relative = path.relative_to(target).as_posix()
            if observed >= SNAPSHOT_MAX_FILES:
                omitted += 1
                continue
            try:
                metadata = path.lstat()
            except OSError as error:
                raise ValueError(f"cannot freeze target snapshot at {relative}: {error}") from error
            record = (
                f"{relative}\0{metadata.st_mode}\0{metadata.st_size}\0"
                f"{metadata.st_mtime_ns}\0{metadata.st_ctime_ns}\n"
            )
            digest.update(record.encode("utf-8", errors="surrogateescape"))
            observed += 1
    digest.update(f"observed={observed}\0omitted={omitted}".encode("ascii"))
    return digest.hexdigest()


def snapshot_identity(target: Path) -> str:
    """Freeze the current Git or bounded filesystem state into a safe digest."""

    resolved = target.expanduser().resolve()
    metadata_digest = _metadata_snapshot(resolved)
    head = run_command(["git", "rev-parse", "HEAD"], cwd=resolved)
    status = run_command(
        ["git", "status", "--porcelain=v1", "--untracked-files=normal", "--", "."],
        cwd=resolved,
    )
    if (
        head["status"] == "available"
        and head["exit_code"] == 0
        and status["status"] == "available"
        and status["exit_code"] == 0
    ):
        material = (
            f"{str(head['stdout']).strip()}\0{str(status['stdout'])}\0{metadata_digest}"
        ).encode("utf-8", errors="surrogateescape")
        return f"git-sha256:{hashlib.sha256(material).hexdigest()}"
    return f"fsmeta-sha256:{metadata_digest}"


def target_binding(target: Path) -> dict[str, str]:
    """Return the exact local target and snapshot binding used by durable writes."""

    return {
        "target_id": target_identity(target),
        "snapshot_id": snapshot_identity(target),
    }


def validate_target_binding(scope: object, target: Path) -> None:
    """Reject a stale or cross-target findings scope before any durable write."""

    if not isinstance(scope, dict):
        raise ValueError("findings.scope must be an object")
    resolved = target.expanduser().resolve()
    if scope.get("target") != resolved.name:
        raise ValueError("findings target name does not match --target")
    snapshot = scope.get("snapshot")
    if not isinstance(snapshot, dict):
        raise ValueError("findings.scope.snapshot must be an object")
    current = target_binding(resolved)
    if scope.get("target_id") != current["target_id"]:
        raise ValueError("findings target identity does not match --target")
    if snapshot.get("id") != current["snapshot_id"]:
        raise ValueError("findings snapshot is stale; recollect evidence for the current target state")


def require_canonical_artifact_path(path: Path, target: Path, relative: str) -> Path:
    """Require durable artifacts to stay at the target-owned canonical path."""

    resolved = path.expanduser().resolve()
    expected = target.expanduser().resolve() / relative
    if resolved != expected:
        raise ValueError(f"artifact path must be {relative} below --target")
    return resolved


def run_command(args: list[str], *, cwd: Path, timeout: int = 10) -> dict[str, object]:
    """Run a bounded argv command without a shell and return a structured result."""

    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "status": "unavailable",
            "exit_code": None,
            "stdout": "",
            "stderr": sanitize_text(error, limit=200),
        }
    return {
        "status": "available",
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": sanitize_text(completed.stderr, limit=200),
    }


def relative_path(path: Path, root: Path) -> str | None:
    """Return a portable repository-relative path or None outside the root."""

    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def slug(value: str, *, fallback: str = "target") -> str:
    """Build a stable lowercase slug without path separators."""

    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or fallback
