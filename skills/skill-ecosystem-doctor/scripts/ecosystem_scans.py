"""Deterministic filesystem, reference, secret, and Loom scans."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from ecosystem_model import (
    ACTION_RESOURCE_REFERENCE,
    RESOURCE_LINK,
    SECRET_RULES,
    EcosystemFinding,
    SkillInstance,
    directory_digest,
    expand_path,
    file_skill_digest,
    frontmatter_name,
    is_regular_content_file,
    iter_skill_files,
    materialization_digest,
    root_is_active,
    root_is_source,
)


LOOM_DOCTOR_TIMEOUT_SECONDS = 300


def scan_root(
    root: Path,
    root_kind: str,
    findings: list[EcosystemFinding],
    pinned_materializations: dict[str, dict],
    seen_pins: set[str],
    managed_physical_names: set[str] | None = None,
) -> list[SkillInstance]:
    instances: list[SkillInstance] = []
    if not root.is_dir():
        findings.append(
            EcosystemFinding("error", "root_missing", "configured Skill root is missing", str(root))
        )
        return instances
    try:
        children = sorted(root.iterdir(), key=lambda path: path.name)
    except OSError as exc:
        findings.append(
            EcosystemFinding("error", "root_unreadable", f"cannot read Skill root: {exc}", str(root))
        )
        return instances

    if root_kind == "repository_source":
        root_skill = root / "SKILL.md"
        if not root_skill.is_file():
            findings.append(
                EcosystemFinding(
                    "error",
                    "skill_entrypoint_missing",
                    "repository Skill source has no usable root SKILL.md",
                    str(root),
                )
            )
            return instances
        entries = [root]
        entries.extend(
            entry
            for entry in children
            if (
                (entry.is_file() and entry.name.endswith(".SKILL.md"))
                or (
                    entry.is_dir()
                    and (
                        (entry / "SKILL.md").is_file()
                        or (entry / "SKILL.md").is_symlink()
                    )
                )
            )
        )
    elif root_kind == "archive":
        entries = _archive_entries(root)
    else:
        entries = children

    for entry in entries:
        if entry.name.startswith("."):
            continue
        if entry.is_symlink() and not entry.exists():
            findings.append(
                EcosystemFinding(
                    "error",
                    "broken_projection",
                    "Skill symlink target does not exist",
                    str(entry),
                )
            )
            continue
        is_repository_root = root_kind == "repository_source" and entry == root
        is_file_skill = entry.is_file() and entry.name.endswith(".SKILL.md")
        if is_repository_root:
            skill_file = root / "SKILL.md"
            install_name = root.name
            # A repository-style Skill owns its support files as well as its
            # SKILL.md. Hashing only the entrypoint makes a symlinked runtime
            # projection of the same directory look divergent whenever the
            # Skill has scripts, references, or evals.
            layout = "directory"
        elif is_file_skill:
            skill_file = entry
            install_name = entry.name.removesuffix(".SKILL.md")
            layout = "file"
        elif entry.is_dir():
            skill_file = entry / "SKILL.md"
            if (
                root_is_active(root_kind)
                and skill_file.is_symlink()
                and not skill_file.is_file()
            ):
                findings.append(
                    EcosystemFinding(
                        "error",
                        "broken_projection",
                        "projected SKILL.md symlink target is missing or is not a file",
                        str(skill_file),
                    )
                )
                continue
            if not skill_file.is_file():
                if root_is_active(root_kind):
                    findings.append(
                        EcosystemFinding(
                            "error",
                            "broken_projection",
                            "projection directory has no usable SKILL.md",
                            str(entry),
                        )
                    )
                elif root_is_source(root_kind):
                    findings.append(
                        EcosystemFinding(
                            "error",
                            "skill_entrypoint_missing",
                            "source Skill directory has no usable SKILL.md",
                            str(entry),
                        )
                    )
                continue
            install_name = entry.name
            layout = (
                "file"
                if root_is_active(root_kind)
                and not entry.is_symlink()
                and skill_file.is_symlink()
                else "directory"
            )
        else:
            continue
        name = frontmatter_name(skill_file)
        if not name:
            findings.append(
                EcosystemFinding(
                    "error",
                    "frontmatter_name_missing",
                    "SKILL.md has no parseable frontmatter name",
                    str(skill_file),
                )
            )
            continue
        try:
            resolved = (
                skill_file.resolve(strict=True)
                if layout == "file"
                else entry.resolve(strict=True)
            )
            digest = (
                file_skill_digest(skill_file)
                if layout == "file"
                else directory_digest(entry)
            )
        except OSError as exc:
            findings.append(
                EcosystemFinding(
                    "error",
                    "skill_unreadable",
                    f"cannot hash Skill contents: {exc}",
                    str(entry),
                )
            )
            continue

        if install_name != name and root_kind != "archive":
            findings.append(
                EcosystemFinding(
                    "warning",
                    "directory_name_mismatch",
                    f"install name '{install_name}' differs from declared name '{name}'",
                    str(entry),
                )
            )
        managed_projection = entry.is_symlink() or (
            root_is_active(root_kind) and layout == "file" and skill_file.is_symlink()
        )
        if (
            root_kind == "projection"
            and not managed_projection
            and name not in (managed_physical_names or set())
        ):
            _verify_physical_projection(
                entry,
                name,
                resolved,
                digest,
                findings,
                pinned_materializations,
                seen_pins,
            )
        instances.append(
            SkillInstance(
                name=name,
                path=str(entry),
                resolved_path=str(resolved),
                root_kind=root_kind,
                digest=digest,
                is_symlink=managed_projection,
                layout=layout,
                skill_file_path=str(skill_file.resolve(strict=True)),
            )
        )
    return instances


def _archive_entries(root: Path) -> list[Path]:
    """Find nested archived Skills without treating container folders as Skills."""
    entries: list[Path] = []
    for current, dir_names, file_names in os.walk(root, followlinks=False):
        dir_names[:] = sorted(
            name
            for name in dir_names
            if name not in {".git", "__pycache__", ".pytest_cache", ".mypy_cache"}
            and not name.startswith(".git")
        )
        current_path = Path(current)
        if "SKILL.md" in file_names:
            entries.append(current_path)
            dir_names[:] = []
            continue
        entries.extend(
            current_path / file_name
            for file_name in sorted(file_names)
            if file_name.endswith(".SKILL.md")
        )
    return sorted(entries, key=lambda path: str(path))


def _verify_physical_projection(
    entry: Path,
    name: str,
    resolved: Path,
    digest: str,
    findings: list[EcosystemFinding],
    pinned_materializations: dict[str, dict],
    seen_pins: set[str],
) -> None:
    entry_path = str(entry)
    pin = pinned_materializations.get(entry_path)
    if pin is None:
        findings.append(
            EcosystemFinding(
                "warning",
                "physical_projection_unpinned",
                "physical runtime copy requires an exact pinned materialization or managed projection",
                entry_path,
                {"declared_name": name},
            )
        )
        return

    seen_pins.add(entry_path)
    if pin["name"] != name:
        findings.append(
            EcosystemFinding(
                "error",
                "pinned_materialization_name_mismatch",
                "pinned materialization name differs from its declared Skill name",
                entry_path,
                {"expected_name": pin["name"], "declared_name": name},
            )
        )

    source_path = expand_path(pin["source_path"])
    if not source_path.is_dir() and not source_path.is_file():
        findings.append(
            EcosystemFinding(
                "error",
                "pinned_materialization_source_missing",
                "pinned materialization source file or directory is missing",
                str(source_path),
                {"projection_path": entry_path},
            )
        )
        return

    resource_mappings = pin.get("resource_mappings") or []
    try:
        projection_resolved = Path(entry_path).resolve(strict=True)
    except OSError as exc:
        findings.append(
            EcosystemFinding(
                "error",
                "skill_unreadable",
                f"cannot resolve projection path: {exc}",
                entry_path,
            )
        )
        return

    missing_resources: list[str] = []
    self_sourced_resources: list[str] = []
    for mapping in resource_mappings:
        mapping_source = expand_path(mapping["source_path"])
        if not mapping_source.is_file():
            missing_resources.append(str(mapping_source))
            continue
        try:
            mapping_resolved = mapping_source.resolve(strict=True)
        except OSError:
            missing_resources.append(str(mapping_source))
            continue
        if mapping_resolved == projection_resolved or mapping_resolved.is_relative_to(
            projection_resolved
        ):
            self_sourced_resources.append(str(mapping_source))

    for missing_resource in missing_resources:
        findings.append(
            EcosystemFinding(
                "error",
                "pinned_materialization_resource_missing",
                "pinned materialization resource source file is missing",
                missing_resource,
                {"projection_path": entry_path},
            )
        )
    for self_sourced_resource in self_sourced_resources:
        findings.append(
            EcosystemFinding(
                "error",
                "pinned_materialization_self_source",
                "pinned materialization resource mapping cannot source from the projection",
                self_sourced_resource,
                {"projection_path": entry_path},
            )
        )
    skip_digest = bool(missing_resources or self_sourced_resources)
    try:
        source_resolved = source_path.resolve(strict=True)
        source_digest = (
            None
            if skip_digest
            else materialization_digest(source_path, resource_mappings)
        )
    except OSError as exc:
        findings.append(
            EcosystemFinding(
                "error",
                "pinned_materialization_source_unreadable",
                f"cannot hash pinned materialization source: {exc}",
                str(source_path),
                {"projection_path": entry_path},
            )
        )
        return
    installed_skill_file = resolved / "SKILL.md"
    self_source = source_resolved == resolved or (
        source_resolved.is_file()
        and installed_skill_file.is_file()
        and source_resolved == installed_skill_file.resolve(strict=True)
    )
    if self_source:
        findings.append(
            EcosystemFinding(
                "error",
                "pinned_materialization_self_source",
                "pinned materialization cannot use itself as its source",
                entry_path,
            )
        )
    elif source_digest is not None and source_digest != digest:
        findings.append(
            EcosystemFinding(
                "error",
                "pinned_materialization_drift",
                "physical runtime copy differs from its pinned source",
                entry_path,
                {"source_path": str(source_path)},
            )
        )


def scan_resource_references(
    instance: SkillInstance,
    findings: list[EcosystemFinding],
    *,
    active: bool,
    provided_resources: set[str] | None = None,
) -> None:
    skill_file = Path(instance.skill_file_path)
    base = skill_file.parent
    resolved_base = base.resolve(strict=True)
    pending = [skill_file]
    visited: set[Path] = set()
    while pending:
        source_file = pending.pop()
        try:
            resolved_source = source_file.resolve(strict=True)
        except OSError as exc:
            findings.append(
                EcosystemFinding(
                    "error" if active else "warning",
                    "skill_unreadable",
                    f"cannot resolve Skill resource while scanning references: {exc}",
                    str(source_file),
                )
            )
            continue
        if resolved_source in visited:
            continue
        visited.add(resolved_source)
        if not is_regular_content_file(source_file):
            continue
        try:
            if source_file.stat().st_size > 2 * 1024 * 1024:
                continue
            text = source_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            findings.append(
                EcosystemFinding(
                    "error" if active else "warning",
                    "skill_unreadable",
                    f"cannot read Skill resource while scanning references: {exc}",
                    str(source_file),
                )
            )
            continue
        references = {
            match.rstrip(".,;:!?")
            for pattern in (RESOURCE_LINK, ACTION_RESOURCE_REFERENCE)
            for match in pattern.findall(text)
        }
        for reference in sorted(references):
            normalized = reference.removeprefix("./")
            relative = Path(normalized)
            candidate = base / relative
            try:
                resolved_candidate = candidate.resolve(strict=False)
                stays_inside = resolved_candidate.is_relative_to(resolved_base)
            except OSError:
                stays_inside = False
            if ".." in relative.parts or not stays_inside:
                findings.append(
                    EcosystemFinding(
                        "error" if active else "warning",
                        "unsafe_skill_resource_reference",
                        f"declared Skill resource escapes the Skill root: {reference}",
                        str(source_file),
                    )
                )
                continue
            resource_exists = candidate.is_file() or (
                reference.endswith("/") and candidate.is_dir()
            )
            if not resource_exists and normalized not in (provided_resources or set()):
                findings.append(
                    EcosystemFinding(
                        "error" if active else "warning",
                        "missing_skill_resource",
                        f"declared Skill resource does not exist: {reference}",
                        str(source_file),
                    )
                )
                continue
            if not candidate.is_file():
                continue
            pending.append(candidate)


# Retired-entry detection must key on syntax that denotes a Skill reference.
# A bare word-boundary match over prose flags ordinary vocabulary that happens to
# collide with a retired Skill name (for example the noun "wallpaper" against a
# retired entry with that name), which produced false gate failures.
_REFERENCE_FORMS: tuple[tuple[str, str], ...] = (
    # Structural forms: the name sits in a position that can only mean a Skill.
    ("slash_command", r"(?<![\w./-])/{name}(?![\w-])"),
    ("wiki_link", r"\[\[\s*{name}\s*\]\]"),
    ("skill_path", r"(?<![\w-])skills?/{name}(?![\w-])"),
    ("skill_file", r"(?<![\w-]){name}/SKILL\.md\b"),
    ("code_span", r"`\s*/?{name}\s*`"),
    ("skill_call", r"\bskill\s*\(\s*[\"']?{name}[\"']?\s*\)"),
    ("skill_field", r"\bskill[_-]?(?:name)?\s*[:=]\s*[\"']?{name}(?![\w-])"),
    ("markdown_link", r"\]\([^)]*(?<![\w-]){name}(?![\w-])[^)]*\)"),
    # Invocation phrasing: an imperative aimed at the name.
    (
        "invocation",
        r"\b(?:call|calls|called|invoke|invokes|invoking|run|runs|use|uses|using"
        r"|load|loads|loading|trigger|triggers|see|via|replace[sd]?|delegate to"
        r"|hand off to|defer to)\s+(?:the\s+)?{name}(?![\w-])",
    ),
    ("qualified_noun", r"(?<![\w-]){name}\s+(?:skill|workflow|command|entrypoint)\b"),
)

_REFERENCE_CACHE: dict[str, tuple[tuple[str, re.Pattern[str]], ...]] = {}


def _redact_secrets(fragment: str) -> str:
    """Strip credential-shaped values so evidence never republishes a secret."""
    for rule_name, pattern in SECRET_RULES:
        fragment = pattern.sub(f"[redacted:{rule_name}]", fragment)
    return fragment


def _reference_patterns(retired: str) -> tuple[tuple[str, re.Pattern[str]], ...]:
    cached = _REFERENCE_CACHE.get(retired)
    if cached is None:
        name = re.escape(retired)
        cached = tuple(
            (kind, re.compile(template.format(name=name), re.IGNORECASE))
            for kind, template in _REFERENCE_FORMS
        )
        _REFERENCE_CACHE[retired] = cached
    return cached


def _find_retired_reference_in_lines(
    lines: list[str], retired: str
) -> tuple[int, str, str] | None:
    """Locate an explicit retired reference in already-split text lines."""
    patterns = _reference_patterns(retired)
    for index, line in enumerate(lines, start=1):
        for kind, pattern in patterns:
            match = pattern.search(line)
            if match:
                return index, _redact_secrets(match.group(0)[:200]), kind
    return None


def find_retired_reference(text: str, retired: str) -> tuple[int, str, str] | None:
    """Locate an explicit reference to a retired Skill name.

    Returns ``(line_number, evidence, match_kind)`` for the first line carrying a
    Skill-denoting reference, or ``None`` when the name only appears as prose.
    The line number is reported so findings cite a verifiable location instead of
    leaving callers to guess one.
    """
    return _find_retired_reference_in_lines(text.splitlines(), retired)


def scan_retired_references(
    instance: SkillInstance,
    retired_names: set[str],
    findings: list[EcosystemFinding],
    *,
    active: bool,
    allowlist: set[tuple[str, str]],
) -> None:
    base = Path(instance.resolved_path)
    files = (
        [Path(instance.skill_file_path)]
        if instance.layout == "file"
        else iter_skill_files(base)
    )
    for file_path in files:
        if not is_regular_content_file(file_path):
            continue
        try:
            if file_path.stat().st_size > 2 * 1024 * 1024:
                continue
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            findings.append(
                EcosystemFinding(
                    "error" if active else "warning",
                    "skill_unreadable",
                    f"cannot scan retired references: {exc}",
                    str(file_path),
                )
            )
            continue
        lines = text.splitlines()
        folded_text = text.casefold()
        for retired in sorted(retired_names):
            if (instance.name, retired) in allowlist:
                continue
            if retired.casefold() not in folded_text:
                continue
            hit = _find_retired_reference_in_lines(lines, retired)
            if hit is None:
                continue
            line_number, evidence, kind = hit
            findings.append(
                EcosystemFinding(
                    "error" if active else "warning",
                    "retired_skill_reference",
                    f"active Skill still references retired entry '{retired}'"
                    f" ({kind}) at line {line_number}",
                    str(file_path),
                    {
                        "retired": retired,
                        "line": line_number,
                        "match_kind": kind,
                        "evidence": evidence,
                    },
                )
            )


def scan_secrets(instance: SkillInstance, findings: list[EcosystemFinding]) -> None:
    base = Path(instance.resolved_path)
    files = (
        [Path(instance.skill_file_path)]
        if instance.layout == "file"
        else iter_skill_files(base)
    )
    for file_path in files:
        if not is_regular_content_file(file_path):
            continue
        try:
            if file_path.stat().st_size > 2 * 1024 * 1024:
                continue
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            findings.append(
                EcosystemFinding(
                    "warning",
                    "file_unreadable_for_secret_scan",
                    f"cannot read file during secret scan: {exc}",
                    str(file_path),
                )
            )
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for rule_name, pattern in SECRET_RULES:
                if not pattern.search(line):
                    continue
                relative_parts = set(file_path.relative_to(base).parts)
                fixture_only = bool(
                    relative_parts & {"test", "tests", "evals", "fixture", "fixtures"}
                )
                findings.append(
                    EcosystemFinding(
                        "warning" if fixture_only else "error",
                        (
                            "secret_pattern_in_test_fixture"
                            if fixture_only
                            else "possible_embedded_secret"
                        ),
                        (
                            f"secret-like fixture pattern detected ({rule_name}); value suppressed"
                            if fixture_only
                            else f"high-confidence secret pattern detected ({rule_name}); value suppressed"
                        ),
                        str(file_path),
                        {"line": line_number, "rule": rule_name},
                    )
                )


def run_loom_doctor(findings: list[EcosystemFinding], loom_binary: str) -> None:
    try:
        process = subprocess.run(
            [loom_binary, "workspace", "doctor", "--json"],
            capture_output=True,
            text=True,
            timeout=LOOM_DOCTOR_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        findings.append(EcosystemFinding("error", "loom_missing", "Loom CLI is not available"))
        return
    except subprocess.TimeoutExpired:
        findings.append(
            EcosystemFinding(
                "error",
                "loom_timeout",
                f"Loom doctor exceeded {LOOM_DOCTOR_TIMEOUT_SECONDS} seconds",
            )
        )
        return
    if process.returncode != 0:
        findings.append(
            EcosystemFinding(
                "error",
                "loom_doctor_failed",
                f"Loom doctor exited {process.returncode}; output suppressed",
            )
        )
        return
    try:
        envelope = json.loads(process.stdout)
    except json.JSONDecodeError:
        findings.append(
            EcosystemFinding("error", "loom_output_invalid", "Loom doctor returned invalid JSON")
        )
        return
    data = envelope.get("data") or {}
    checks = data.get("checks") or {}
    projection_drift = checks.get("projection_drift") or {}
    if not envelope.get("ok") or not data.get("healthy") or not projection_drift.get("ok"):
        findings.append(
            EcosystemFinding(
                "error",
                "loom_unhealthy",
                "Loom workspace or projection drift check is unhealthy",
            )
        )
    pending_count = (checks.get("pending_queue") or {}).get("count") or 0
    if pending_count:
        findings.append(
            EcosystemFinding(
                "warning",
                "loom_pending_ops",
                "Loom has local operations pending remote synchronization",
                details={"count": pending_count},
            )
        )
