"""Shared artifact checks for Spellbook skill validation and audit tools."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
import stat


SUPPORT_DIR_NAMES = {
    "agents",
    "assets",
    "evals",
    "reference",
    "references",
    "scripts",
    "templates",
}

IGNORED_MISSING_REFS = {
    ("skill-creator", "evals/evals.json"),
}

LOCAL_SUPPORT_REF_RE = re.compile(
    r"(?<![/\w.-])"
    r"((?:skills/[^\s`'\"<>\[\]()]+/)?"
    r"(?:agents|assets|evals|reference|references|scripts|templates)"
    r"/[^\s`'\"<>\[\]()]+\.[^\s`'\"<>\[\]()]+)"
)

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")

STRICT_PLACEHOLDER_RE = re.compile(
    r"(?<!\{)\{(?:SCRIPT|ARGS|ARGUMENTS)\}(?!\})|<TODO>"
)
LEGACY_ARGUMENT_TOKEN_RE = re.compile(r"\$ARGUMENTS")


@dataclass(frozen=True)
class SupportReference:
    ref: str
    target: Path
    source: str
    unsafe_reason: str | None = None


def skill_markdown_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---", 4)
    if end == -1:
        return text
    return text[end + len("\n---") :]


def unresolved_placeholder_tokens(text: str) -> list[str]:
    return sorted({match.group(0) for match in STRICT_PLACEHOLDER_RE.finditer(text)})


def legacy_argument_tokens(text: str) -> list[str]:
    return sorted({match.group(0) for match in LEGACY_ARGUMENT_TOKEN_RE.finditer(text)})


def _strip_link_target(raw_target: str) -> str:
    target = raw_target.strip().strip("<>")
    target = target.split("#", 1)[0].split("?", 1)[0]
    target = target.rstrip(".,:;)")
    return target


def _support_ref_candidate(raw_ref: str) -> str | None:
    ref = _strip_link_target(raw_ref)
    if not ref or ref.startswith(("http://", "https://", "mailto:", "#")):
        return None

    parts = PurePosixPath(ref).parts
    if not parts:
        return None
    start = 1 if PurePosixPath(ref).is_absolute() else 0
    if len(parts) > start and parts[start] in SUPPORT_DIR_NAMES:
        return ref
    if len(parts) >= start + 4 and parts[start] == "skills" and parts[start + 2] in SUPPORT_DIR_NAMES:
        return ref
    return None


def _unsafe_reference_reason(ref: str) -> str | None:
    if "\\" in ref:
        return "contains backslash path separator"
    path = PurePosixPath(ref)
    if path.is_absolute():
        return "is absolute"
    if any(part in {"", ".", ".."} for part in path.parts):
        return "contains unsafe path component"
    return None


def _target_for_ref(
    ref: str,
    *,
    root: Path,
    entry_path: str,
    entry_format: str,
) -> Path:
    relative_ref = ref.lstrip("/")
    if relative_ref.startswith("skills/"):
        return root / relative_ref
    if entry_format == "directory":
        return (root / entry_path).parent / relative_ref
    return root / "skills" / relative_ref


def local_support_references(
    *,
    install_name: str,
    entry_path: str,
    entry_format: str,
    body: str,
    root: Path,
) -> list[SupportReference]:
    refs: list[SupportReference] = []
    seen: set[str] = set()

    candidates: list[tuple[str, str]] = []
    candidates.extend(("markdown-link", match.group(1)) for match in MARKDOWN_LINK_RE.finditer(body))
    candidates.extend(("plain-reference", match.group(1)) for match in LOCAL_SUPPORT_REF_RE.finditer(body))

    for source, raw_ref in candidates:
        ref = _support_ref_candidate(raw_ref)
        if ref is None or (install_name, ref) in IGNORED_MISSING_REFS or ref in seen:
            continue
        seen.add(ref)
        refs.append(
            SupportReference(
                ref=ref,
                target=_target_for_ref(
                    ref,
                    root=root,
                    entry_path=entry_path,
                    entry_format=entry_format,
                ),
                source=source,
                unsafe_reason=_unsafe_reference_reason(ref),
            )
        )

    return refs


def is_script_reference(ref: str) -> bool:
    parts = PurePosixPath(ref).parts
    return "scripts" in parts


def has_executable_bit_or_shebang(path: Path) -> bool:
    mode = path.stat().st_mode
    if mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
        return True
    try:
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
    except IndexError:
        return False
    return first_line.startswith("#!")
