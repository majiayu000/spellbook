#!/usr/bin/env python3
"""Report non-blocking quality signals for Spellbook skills."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys

from skill_artifact_checks import (
    SUPPORT_DIR_NAMES,
    has_executable_bit_or_shebang,
    is_script_reference,
    legacy_argument_tokens,
    local_support_references,
    skill_markdown_body,
    unresolved_placeholder_tokens,
)
from validate_skills import CATEGORY_BY_NAME, ROOT, SkillEntry, discover_skills, parse_frontmatter

TRIGGER_CUES = (
    "use when",
    "use this skill",
    "whenever",
    "when the user",
    "trigger",
    "当用户",
    "用于",
    "适用",
)

GOTCHA_CUES = (
    "gotcha",
    "gotchas",
    "pitfall",
    "pitfalls",
    "footgun",
    "failure mode",
    "common failure",
    "troubleshoot",
    "troubleshooting",
    "edge case",
    "caveat",
    "注意",
    "踩坑",
    "常见问题",
    "风险",
    "失败",
    "排查",
    "故障",
)

VERIFICATION_CUES = (
    "assert",
    "check",
    "health check",
    "playwright",
    "smoke",
    "test",
    "tests",
    "validate",
    "validation",
    "verification",
    "verify",
    "断言",
    "检查",
    "验证",
    "测试",
    "自检",
)

VERIFICATION_CATEGORIES = {
    "API & Backend",
    "Delivery Workflow",
    "Development Architecture",
    "Operations & Deploy",
    "UI/UX & Frontend",
}

OPERATING_CONTRACT_CATEGORIES = {
    "API & Backend",
    "AI & Agent Workflow",
    "Delivery Workflow",
    "Development Architecture",
    "Operations & Deploy",
}

OPERATING_CONTRACT_SECTION_RE = re.compile(r"(?im)^##+\s+Operating Contract\s*$")

OPERATING_CONTRACT_FIELDS = (
    "Direct actions:",
    "Escalate before:",
    "Evidence-backed pushback:",
    "Feedback loop:",
)


@dataclass(frozen=True)
class QualityFinding:
    severity: str
    skill: str
    path: str
    check: str
    message: str


def contains_any(text: str, cues: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(cue.lower() in lowered for cue in cues)


def operating_contract_section(body: str) -> str | None:
    match = OPERATING_CONTRACT_SECTION_RE.search(body)
    if not match:
        return None

    start = match.end()
    next_heading = re.search(r"(?m)^##+\s+", body[start:])
    end = start + next_heading.start() if next_heading else len(body)
    return body[start:end]


def missing_operating_contract_fields(body: str) -> list[str]:
    section = operating_contract_section(body)
    if section is None:
        return list(OPERATING_CONTRACT_FIELDS)

    section_lower = section.lower()
    return [field for field in OPERATING_CONTRACT_FIELDS if field.lower() not in section_lower]


def support_dirs_for(entry: SkillEntry) -> list[str]:
    if entry.format != "directory":
        return []
    skill_dir = (ROOT / entry.path).parent
    return sorted(
        child.name
        for child in skill_dir.iterdir()
        if child.is_dir() and child.name in SUPPORT_DIR_NAMES
    )


def audit_entry(entry: SkillEntry) -> list[QualityFinding]:
    path = ROOT / entry.path
    frontmatter, _ = parse_frontmatter(path)
    description = frontmatter.get("description", "")
    description_text = description if isinstance(description, str) else ""
    body = skill_markdown_body(path)
    searchable_text = f"{description_text}\n{body}"
    line_count = len(path.read_text(encoding="utf-8").splitlines())
    category = CATEGORY_BY_NAME.get(entry.install_name, "Uncategorized")
    findings: list[QualityFinding] = []

    if description_text and not contains_any(description_text, TRIGGER_CUES):
        findings.append(
            QualityFinding(
                "WARN",
                entry.install_name,
                entry.path,
                "trigger-description",
                "description reads like a summary; add model-facing trigger cues such as 'Use when' or user phrasing",
            )
        )

    if 0 < len(description_text.strip()) < 80:
        findings.append(
            QualityFinding(
                "INFO",
                entry.install_name,
                entry.path,
                "short-description",
                "description is short; verify it includes enough intent, symptoms, and near-boundary context",
            )
        )

    if not contains_any(body, GOTCHA_CUES):
        findings.append(
            QualityFinding(
                "INFO",
                entry.install_name,
                entry.path,
                "gotchas",
                "SKILL.md has no obvious gotchas/failure-mode section; add one when real failure patterns are known",
            )
        )

    if category in VERIFICATION_CATEGORIES and not contains_any(searchable_text, VERIFICATION_CUES):
        findings.append(
            QualityFinding(
                "WARN",
                entry.install_name,
                entry.path,
                "verification",
                "workflow category has no obvious verification signal; add checks, scripts, assertions, or explicit done-when proof",
            )
        )

    if category in OPERATING_CONTRACT_CATEGORIES:
        missing_contract_fields = missing_operating_contract_fields(body)
        if missing_contract_fields == list(OPERATING_CONTRACT_FIELDS):
            findings.append(
                QualityFinding(
                    "INFO",
                    entry.install_name,
                    entry.path,
                    "operating-contract",
                    "high-impact workflow has no explicit '## Operating Contract' section",
                )
            )
        elif missing_contract_fields:
            findings.append(
                QualityFinding(
                    "INFO",
                    entry.install_name,
                    entry.path,
                    "operating-contract",
                    "Operating Contract section is missing field(s): "
                    + ", ".join(missing_contract_fields),
                )
            )

    if entry.format == "file" and line_count > 160:
        findings.append(
            QualityFinding(
                "WARN",
                entry.install_name,
                entry.path,
                "file-size",
                "large file skill should migrate to directory layout before adding references, scripts, assets, or evals",
            )
        )

    support_dirs = support_dirs_for(entry)
    if entry.format == "directory" and line_count > 300 and not support_dirs:
        findings.append(
            QualityFinding(
                "WARN",
                entry.install_name,
                entry.path,
                "progressive-disclosure",
                "long SKILL.md has no support directory; split detailed material into references, scripts, templates, assets, or evals",
            )
        )

    body_lower = body.lower()
    for support_dir in support_dirs:
        if support_dir.lower() not in body_lower:
            findings.append(
                QualityFinding(
                    "WARN",
                    entry.install_name,
                    entry.path,
                    "support-reference",
                    f"support directory '{support_dir}/' exists but is not referenced from SKILL.md",
                )
            )

    for token in unresolved_placeholder_tokens(body):
        findings.append(
            QualityFinding(
                "WARN",
                entry.install_name,
                entry.path,
                "unresolved-placeholder",
                f"SKILL.md contains unresolved placeholder token '{token}'",
            )
        )

    for token in legacy_argument_tokens(body):
        findings.append(
            QualityFinding(
                "INFO",
                entry.install_name,
                entry.path,
                "legacy-argument-token",
                f"SKILL.md uses legacy runtime argument token '{token}'; verify this is intentional for the target runtime",
            )
        )

    for ref in local_support_references(
        install_name=entry.install_name,
        entry_path=entry.path,
        entry_format=entry.format,
        body=body,
        root=ROOT,
    ):
        if ref.unsafe_reason:
            findings.append(
                QualityFinding(
                    "WARN",
                    entry.install_name,
                    entry.path,
                    "unsafe-support-reference",
                    f"support reference '{ref.ref}' is unsafe: {ref.unsafe_reason}",
                )
            )
        elif not ref.target.exists():
            findings.append(
                QualityFinding(
                    "WARN",
                    entry.install_name,
                    entry.path,
                    "missing-support-file",
                    f"referenced support file '{ref.ref}' does not exist at {ref.target.relative_to(ROOT)}",
                )
            )
        elif is_script_reference(ref.ref) and not has_executable_bit_or_shebang(ref.target):
            findings.append(
                QualityFinding(
                    "WARN",
                    entry.install_name,
                    entry.path,
                    "script-reference",
                    f"referenced script '{ref.ref}' is not executable and has no shebang/interpreter marker",
                )
            )

    return findings


def audit_skills(entries: list[SkillEntry], skill_names: set[str] | None = None) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    for entry in entries:
        if skill_names and entry.install_name not in skill_names:
            continue
        findings.extend(audit_entry(entry))
    return findings


def render_text(findings: list[QualityFinding], total_skills: int) -> str:
    counts = Counter(finding.severity for finding in findings)
    lines = [
        f"Audited {total_skills} skill(s): {counts.get('WARN', 0)} warnings, {counts.get('INFO', 0)} info",
    ]
    if not findings:
        return "\n".join(lines) + "\n"

    lines.append("")
    check_counts = Counter(finding.check for finding in findings)
    lines.append("Finding counts:")
    for check, count in sorted(check_counts.items()):
        lines.append(f"- {check}: {count}")

    lines.append("")
    for finding in findings:
        lines.append(
            f"{finding.severity}: {finding.skill} [{finding.check}] {finding.message} ({finding.path})"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skills", nargs="*", help="Optional install names to audit")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--fail-on-warn", action="store_true", help="Exit non-zero when WARN findings exist")
    args = parser.parse_args()

    entries = discover_skills()
    known_names = {entry.install_name for entry in entries}
    requested_names = set(args.skills)
    unknown_names = requested_names - known_names
    if unknown_names:
        print(f"Unknown skill(s): {', '.join(sorted(unknown_names))}", file=sys.stderr)
        return 2

    findings = audit_skills(entries, requested_names or None)
    audited_count = len(requested_names) if requested_names else len(entries)

    if args.json:
        payload = {
            "audited_skills": audited_count,
            "summary": dict(Counter(finding.severity for finding in findings)),
            "findings": [asdict(finding) for finding in findings],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(findings, audited_count), end="")

    has_warnings = any(finding.severity == "WARN" for finding in findings)
    return 1 if args.fail_on_warn and has_warnings else 0


if __name__ == "__main__":
    sys.exit(main())
