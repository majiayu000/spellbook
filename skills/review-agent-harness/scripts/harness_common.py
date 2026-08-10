#!/usr/bin/env python3
"""Shared privacy and JSON helpers for review-agent-harness."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


MAX_TEXT_LENGTH = 400

_INJECTED_BLOCK_RE = re.compile(
    r"<(environment_context|skill|codex_internal_context|recommended_plugins)\b[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?P<key>[\"']?(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|secret)[\"']?)"
    r"\s*[:=]\s*(?P<value>\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s,;}\]]+)",
    re.IGNORECASE,
)
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
        if not any(marker in match.group("value").lower() for marker in ("<redacted>", "<secret>")):
            matches.append("secret-assignment")
            break
    return matches


def all_strings(value: object) -> list[str]:
    """Flatten reader-visible strings from nested JSON-compatible values."""

    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for entry in value for item in all_strings(entry)]
    if isinstance(value, dict):
        return [item for entry in value.values() for item in all_strings(entry)]
    return []


def load_json(path: Path) -> dict[str, object]:
    """Load one JSON object and fail loudly for another top-level type."""

    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def write_json_atomic(path: Path, value: object, *, replace: bool = False) -> None:
    """Write JSON atomically and refuse unintended replacement."""

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
