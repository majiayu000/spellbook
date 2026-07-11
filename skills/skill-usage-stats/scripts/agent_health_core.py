"""Shared, evidence-bounded helpers for the agent health scanner."""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping


STATUS_ICON = {"ok": "✅", "warn": "⚠️", "fail": "❌", "info": "ℹ️"}


@dataclass(frozen=True)
class ParseIssue:
    """A structured parse or schema error that is safe to render."""

    path: str
    kind: str
    message: str
    line: int | None = None


@dataclass
class Check:
    """One health check and its structured evidence."""

    key: str
    title: str
    status: str = "ok"
    lines: list[str] = field(default_factory=list)
    data: dict[str, object] = field(default_factory=dict)
    errors: list[ParseIssue] = field(default_factory=list)

    def add(self, line: str) -> None:
        self.lines.append(line)

    def add_errors(self, issues: Iterable[ParseIssue]) -> None:
        for issue in issues:
            self.errors.append(issue)
        if self.errors:
            self.status = "fail"
            self.data["parse_error_count"] = len(self.errors)


@dataclass(frozen=True)
class ObjectResult:
    """Result of reading a configuration object."""

    data: dict[str, object] | None
    errors: list[ParseIssue]


@dataclass(frozen=True)
class TranscriptRecord:
    """A parsed JSONL object with source provenance."""

    path: Path
    line: int
    data: dict[str, object]


def msg(lang: str, english: str, chinese: str) -> str:
    return english if lang == "en" else chinese


def object_value(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def string_value(value: object) -> str | None:
    return value if isinstance(value, str) else None


def read_json_object(path: Path) -> ObjectResult:
    """Read a JSON object, rejecting invalid JSON and non-object roots."""

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        issue = ParseIssue(str(path), "read_error", str(exc))
        return ObjectResult(None, [issue])
    try:
        raw: Any = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        line = exc.lineno if isinstance(exc, json.JSONDecodeError) else None
        issue = ParseIssue(str(path), "invalid_json", str(exc), line)
        return ObjectResult(None, [issue])
    data = object_value(raw)
    if data is None:
        issue = ParseIssue(str(path), "non_object_root", "expected a JSON object")
        return ObjectResult(None, [issue])
    return ObjectResult(data, [])


def read_toml_object(path: Path) -> ObjectResult:
    """Read a TOML object when Python's standard TOML parser is available."""

    try:
        import tomllib
    except ModuleNotFoundError:
        issue = ParseIssue(str(path), "unsupported_parser", "Python tomllib is unavailable")
        return ObjectResult(None, [issue])
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        issue = ParseIssue(str(path), "read_error", str(exc))
        return ObjectResult(None, [issue])
    try:
        raw: Any = tomllib.loads(text)
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        issue = ParseIssue(str(path), "invalid_toml", str(exc))
        return ObjectResult(None, [issue])
    data = object_value(raw)
    if data is None:  # Defensive: tomllib currently always returns a dict.
        issue = ParseIssue(str(path), "non_object_root", "expected a TOML table")
        return ObjectResult(None, [issue])
    return ObjectResult(data, [])


def read_frontmatter(path: Path) -> ObjectResult:
    """Read the simple scalar frontmatter fields used by local skill files."""

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        issue = ParseIssue(str(path), "read_error", str(exc))
        return ObjectResult(None, [issue])
    if not text.startswith("---\n"):
        return ObjectResult({}, [])
    end = text.find("\n---", 4)
    if end < 0:
        issue = ParseIssue(str(path), "invalid_frontmatter", "missing closing delimiter")
        return ObjectResult(None, [issue])
    values: dict[str, object] = {}
    for line in text[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if match is None:
            continue
        values[match.group(1)] = match.group(2).strip().strip("'\"")
    return ObjectResult(values, [])


def read_jsonl_objects(paths: Iterable[Path]) -> tuple[list[TranscriptRecord], list[ParseIssue]]:
    """Parse JSONL objects without silently discarding malformed records."""

    records: list[TranscriptRecord] = []
    errors: list[ParseIssue] = []
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(ParseIssue(str(path), "read_error", str(exc)))
            continue
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                raw: Any = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(ParseIssue(str(path), "invalid_jsonl", str(exc), line_number))
                continue
            data = object_value(raw)
            if data is None:
                errors.append(ParseIssue(
                    str(path), "non_object_record", "expected a JSON object", line_number
                ))
                continue
            records.append(TranscriptRecord(path, line_number, data))
    return records, errors


def recent_files(root: Path, pattern: str, limit: int) -> list[Path]:
    """Return recent files, reporting absence as an empty evidence set."""

    if not root.is_dir():
        return []
    files = [path for path in root.rglob(pattern) if path.is_file()]
    try:
        files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    except OSError:
        files.sort(key=str)
    return files[:limit]


_SHELL_COMPOSITION = re.compile(r"(?:\n|\r|&&|\|\||[;|<>`]|\$\()")
_SAFE_SIMPLE = {"pwd", "ls", "which", "wc", "head", "tail", "tree"}
_UNSAFE_GIT_FLAGS = ("--output", "--ext-diff", "--textconv")
_UNSAFE_GH_FLAGS = {"--web", "-w"}


def safe_readonly_rule(command: str) -> str | None:
    """Return one exact allow-rule only for a conservative read-only command."""

    stripped = command.strip()
    if (
        not stripped
        or _SHELL_COMPOSITION.search(stripped)
        or any(character in stripped for character in ("$", "*", "?", "[", "]", "{", "}"))
    ):
        return None
    try:
        tokens = shlex.split(stripped, posix=True)
    except ValueError:
        return None
    if not tokens:
        return None
    if tokens[0] == "tree" and any(
        token == "-o" or token.startswith("-o") or token == "--output"
        or token.startswith("--output=")
        for token in tokens[1:]
    ):
        return None
    if any(
        token == flag or token.startswith(f"{flag}=")
        for token in tokens
        for flag in _UNSAFE_GIT_FLAGS
    ):
        return None

    safe = False
    if tokens[0] in _SAFE_SIMPLE:
        safe = tokens[0] != "pwd" or len(tokens) == 1
    elif tokens[0] == "git" and len(tokens) >= 2:
        subcommand = tokens[1]
        if subcommand in {"status", "log", "diff", "show"}:
            safe = True
        elif subcommand == "branch":
            safe = tokens == ["git", "branch", "--list"]
    elif tokens[0] == "gh" and len(tokens) >= 3:
        safe = (
            tokens[1] == "pr"
            and tokens[2] in {"view", "list"}
            and not any(token in _UNSAFE_GH_FLAGS for token in tokens[3:])
        )
    if not safe:
        return None
    return f"Bash({shlex.join(tokens)})"


_DENIAL_MARKERS = (
    "command denied",
    "denied by",
    "permission denied",
    "not approved",
    "rejected by sandbox",
    "blocked by policy",
    "tool denial",
)


def contains_denial(value: object) -> bool:
    """Detect explicit denial evidence without assuming an undocumented status field."""

    if isinstance(value, str):
        lowered = value.lower()
        return any(marker in lowered for marker in _DENIAL_MARKERS)
    if isinstance(value, Mapping):
        return any(contains_denial(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_denial(item) for item in value)
    return False


def candidate_rules(commands: Iterable[str], minimum_count: int = 2) -> list[str]:
    """Aggregate only exact commands that pass the conservative classifier."""

    counts: dict[str, int] = {}
    for command in commands:
        rule = safe_readonly_rule(command)
        if rule is not None:
            counts[rule] = counts.get(rule, 0) + 1
    return sorted(rule for rule, count in counts.items() if count >= minimum_count)


def semver(value: str) -> tuple[int, ...]:
    base = value.split("+", 1)[0].strip()
    parts = re.findall(r"\d+", base)
    return tuple(int(part) for part in parts[:3]) or (0,)
