"""Deterministic filesystem, reference, secret, and Loom scans."""

from __future__ import annotations

import json
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
    iter_skill_files,
    materialization_digest,
)


def scan_root(
    root: Path,
    root_kind: str,
    findings: list[EcosystemFinding],
    pinned_materializations: dict[str, dict],
    seen_pins: set[str],
) -> list[SkillInstance]:
    instances: list[SkillInstance] = []
    if not root.is_dir():
        findings.append(
            EcosystemFinding("error", "root_missing", "configured Skill root is missing", str(root))
        )
        return instances
    try:
        entries = sorted(root.iterdir(), key=lambda path: path.name)
    except OSError as exc:
        findings.append(
            EcosystemFinding("error", "root_unreadable", f"cannot read Skill root: {exc}", str(root))
        )
        return instances

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
        is_file_skill = entry.is_file() and entry.name.endswith(".SKILL.md")
        if is_file_skill:
            skill_file = entry
            install_name = entry.name.removesuffix(".SKILL.md")
            layout = "file"
        elif entry.is_dir():
            skill_file = entry / "SKILL.md"
            if not skill_file.is_file():
                continue
            install_name = entry.name
            layout = (
                "file"
                if root_kind == "projection"
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

        if install_name != name:
            findings.append(
                EcosystemFinding(
                    "warning",
                    "directory_name_mismatch",
                    f"install name '{install_name}' differs from declared name '{name}'",
                    str(entry),
                )
            )
        managed_projection = entry.is_symlink() or (
            root_kind == "projection" and layout == "file" and skill_file.is_symlink()
        )
        if root_kind == "projection" and not managed_projection:
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
    if not source_path.is_dir():
        findings.append(
            EcosystemFinding(
                "error",
                "pinned_materialization_source_missing",
                "pinned materialization source directory is missing",
                str(source_path),
                {"projection_path": entry_path},
            )
        )
        return

    resource_mappings = pin.get("resource_mappings") or []
    missing_resources = [
        str(expand_path(mapping["source_path"]))
        for mapping in resource_mappings
        if not expand_path(mapping["source_path"]).is_file()
    ]
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
    try:
        source_resolved = source_path.resolve(strict=True)
        source_digest = (
            materialization_digest(source_path, resource_mappings)
            if not missing_resources
            else None
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
    if source_resolved == resolved:
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
) -> None:
    skill_file = Path(instance.skill_file_path)
    base = skill_file.parent
    try:
        text = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        findings.append(
            EcosystemFinding("error", "skill_unreadable", f"cannot read SKILL.md: {exc}", str(skill_file))
        )
        return
    references = {
        match.rstrip(".,;:!?")
        for pattern in (RESOURCE_LINK, ACTION_RESOURCE_REFERENCE)
        for match in pattern.findall(text)
    }
    for reference in sorted(references):
        if not (base / reference).is_file():
            findings.append(
                EcosystemFinding(
                    "error" if active else "warning",
                    "missing_skill_resource",
                    f"declared Skill resource does not exist: {reference}",
                    str(skill_file),
                )
            )


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
        for retired in sorted(retired_names):
            if (instance.name, retired) in allowlist:
                continue
            if re.search(
                rf"(?<![A-Za-z0-9_-]){re.escape(retired)}(?![A-Za-z0-9_-])",
                text,
            ):
                findings.append(
                    EcosystemFinding(
                        "error" if active else "warning",
                        "retired_skill_reference",
                        f"active Skill still references retired entry '{retired}'",
                        str(file_path),
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
            timeout=60,
            check=False,
        )
    except FileNotFoundError:
        findings.append(EcosystemFinding("error", "loom_missing", "Loom CLI is not available"))
        return
    except subprocess.TimeoutExpired:
        findings.append(EcosystemFinding("error", "loom_timeout", "Loom doctor exceeded 60 seconds"))
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
