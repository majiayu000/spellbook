#!/usr/bin/env python3
"""Validate Spellbook skill metadata and generated registry files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from skill_path_safety import UnsafePathError, safe_kebab_name, safe_output_path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only on minimal user systems.
    yaml = None

from skill_artifact_checks import (
    local_support_references,
    skill_markdown_body,
    unresolved_placeholder_tokens,
)


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
REGISTRY_JSON = ROOT / "registry" / "skills.json"
REGISTRY_DOC = ROOT / "docs" / "skill-registry.md"
TAGS_JSON = ROOT / "registry" / "tags.json"
TAG_OVERRIDES_FILE = ROOT / "registry" / "tag_overrides.yml"

ALLOWED_FRONTMATTER_KEYS = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}

CATEGORY_BY_NAME = {
    # Development architecture
    "typescript-project": "Development Architecture",
    "python-project": "Development Architecture",
    "rust-project": "Development Architecture",
    "golang-web": "Development Architecture",
    "zig-project": "Development Architecture",
    "harmonyos-app": "Development Architecture",
    "architecture-foundation": "Development Architecture",
    "elegant-architecture": "Development Architecture",
    "rust-best-practices": "Development Architecture",
    "react-best-practices": "Development Architecture",
    "react-hooks-best-practices": "Development Architecture",
    # Product lifecycle
    "product-discovery": "Product Lifecycle",
    "prd-master": "Product Lifecycle",
    "technical-spec": "Product Lifecycle",
    "product-analytics": "Product Lifecycle",
    "product-manager-toolkit": "Product Lifecycle",
    "product-ux-expert": "Product Lifecycle",
    # API and backend
    "api-design": "API & Backend",
    "auth-security": "API & Backend",
    "database-patterns": "API & Backend",
    "structured-logging": "API & Backend",
    "structured-logging-lite": "API & Backend",
    # Delivery workflow
    "auto-optimize": "Delivery Workflow",
    "codebase-audit": "Delivery Workflow",
    "contribution-architect": "Delivery Workflow",
    "contributor": "Delivery Workflow",
    "fixflow": "Delivery Workflow",
    "optflow": "Delivery Workflow",
    "plan-flow": "Delivery Workflow",
    "project-health-auditor": "Delivery Workflow",
    "systematic-debugging": "Delivery Workflow",
    "test-driven-development": "Delivery Workflow",
    "comprehensive-testing": "Delivery Workflow",
    "vibeguard": "Delivery Workflow",
    "git-commit-smart": "Delivery Workflow",
    "push-all": "Delivery Workflow",
    "devops-excellence": "Operations & Deploy",
    "observability-sre": "Operations & Deploy",
    # UI and frontend
    "app-ui-design": "UI/UX & Frontend",
    "css-debug": "UI/UX & Frontend",
    "figma-to-code": "UI/UX & Frontend",
    "figma-to-react": "UI/UX & Frontend",
    "frontend-design": "UI/UX & Frontend",
    "playwright-automation": "UI/UX & Frontend",
    "ui-designer": "UI/UX & Frontend",
    "ui-design-system": "UI/UX & Frontend",
    "ui-ux-pro-max": "UI/UX & Frontend",
    "web-asset-generator": "UI/UX & Frontend",
    "web-artifacts-builder": "UI/UX & Frontend",
    # AI and agent workflows
    "ask-opencli": "AI & Agent Workflow",
    "flowguard": "AI & Agent Workflow",
    "brainstorming": "AI & Agent Workflow",
    "codex": "AI & Agent Workflow",
    "codex-agent": "AI & Agent Workflow",
    "codex-fluent": "AI & Agent Workflow",
    "codex-retrospective": "AI & Agent Workflow",
    "multi-ai-research": "AI & Agent Workflow",
    "multi-model-orchestrator": "AI & Agent Workflow",
    "personal-arsenal-lifecycle-doctor": "AI & Agent Workflow",
    "repo-agent-context-audit": "AI & Agent Workflow",
    "skill-creator": "AI & Agent Workflow",
    "skill-audit": "AI & Agent Workflow",
    "strategic-compact": "AI & Agent Workflow",
    "threads": "AI & Agent Workflow",
    # Operations
    "clash-doctor": "Operations & Deploy",
    "clash-routes": "Operations & Deploy",
    "cliproxy-deploy": "Operations & Deploy",
    "cliproxy-newapi-stack": "Operations & Deploy",
    "disk-cleaner": "Operations & Deploy",
    "gemma4-local-deploy": "Operations & Deploy",
    "gpu-use": "Operations & Deploy",
    "openclaw-deploy": "Operations & Deploy",
    "optimize-network": "Operations & Deploy",
    "rustdesk-doctor": "Operations & Deploy",
    "server-deploy": "Operations & Deploy",
    "server-security": "Operations & Deploy",
    "system-doctor": "Operations & Deploy",
    "vscode-doctor": "Operations & Deploy",
    # Content and reporting
    "github-trending": "Content & Research",
    "humanizer": "Content & Research",
    "slides": "Content & Research",
    "trip-planner": "Content & Research",
    "weekly": "Content & Research",
    "xiaohongshu": "Content & Research",
    "xiaohongshu-netfeel-guardian": "Content & Research",
}


# Tag extraction: curated keyword -> tag mapping. Each keyword is matched as a
# whole word against the lower-cased name + description. Word boundaries are
# defined as any non-alphanumeric character (including whitespace, punctuation,
# and the start/end of string). This avoids false positives like "guide" -> "ui".
# Tags stay coarse and stable so the search index is predictable.
TAG_KEYWORDS: dict[str, tuple[str, ...]] = {
    # Languages and runtimes
    "rust": ("rust", "cargo"),
    "python": ("python", "pytest", "uv"),
    "typescript": ("typescript", "ts", "tsx", "tsc"),
    "javascript": ("javascript", "js", "node.js", "nodejs"),
    "go": ("golang", "go"),
    "zig": ("zig",),
    "react": ("react", "next.js", "nextjs"),
    "harmonyos": ("harmonyos", "arkts", "arkui"),
    # Domains
    "frontend": ("frontend", "ui", "css", "tailwind", "html"),
    "backend": ("backend", "api", "rest", "graphql", "grpc"),
    "database": ("database", "postgres", "redis", "sqlite", "sql"),
    "auth": ("auth", "oauth", "jwt", "rbac"),
    "devops": ("devops", "kubernetes", "docker", "ci/cd", "github actions", "terraform"),
    "observability": ("observability", "logging", "tracing", "metric", "prometheus", "grafana"),
    "testing": ("testing", "tdd", "pytest", "jest", "vitest"),
    "security": ("security", "vulnerability", "cve"),
    "performance": ("performance", "optimization"),
    # Workflow style
    "code-review": ("review", "pull request"),
    "debugging": ("debug", "diagnose"),
    "refactoring": ("refactor",),
    "architecture": ("architecture", "system design"),
    "documentation": ("document", "prd", "rfc", "adr"),
    # AI workflows
    "agent": ("agent", "auto-run-agent", "subagent", "orchestrator"),
    "multi-ai": ("multi-ai", "grok", "gemini", "openai"),
    "mcp": ("mcp", "model context protocol"),
    "prompt": ("prompt",),
    "browser": ("browser", "playwright", "chrome", "puppeteer"),
    # Product
    "product-management": ("rice", "moscow", "jtbd", "kano"),
    "ux": ("ux", "wcag", "accessibility"),
    "design-system": ("figma",),
    # Operations
    "proxy": ("proxy", "clash", "mihomo", "vpn"),
    "deploy": ("deploy", "vps"),
    "system": ("disk", "cpu", "memory"),
    # Content
    "content": ("video", "youtube", "xiaohongshu", "wallpaper", "music"),
    "writing": ("blog", "humanize"),
}


_CJK_RE = re.compile(r"[一-鿿]")
_ASCII_LETTER_RE = re.compile(r"[A-Za-z]")


def detect_language(text: str) -> str:
    """Detect the natural language of a description. Returns 'zh', 'en', or 'mixed'."""
    if not isinstance(text, str) or not text:
        return "en"
    has_cjk = bool(_CJK_RE.search(text))
    has_latin = bool(_ASCII_LETTER_RE.search(text))
    if has_cjk and has_latin:
        # Treat predominantly-Chinese descriptions with stray English brand names as zh.
        cjk_count = len(_CJK_RE.findall(text))
        latin_count = len(_ASCII_LETTER_RE.findall(text))
        if cjk_count >= latin_count // 3:
            return "zh"
        return "mixed"
    if has_cjk:
        return "zh"
    return "en"


def load_tag_overrides() -> dict[str, list[str]]:
    """Load manual per-skill tag overrides. Returns {} when the file is missing
    or PyYAML is unavailable. The override file must be a YAML mapping of
    skill-name -> list-of-tags.
    """
    if not TAG_OVERRIDES_FILE.exists():
        return {}
    text = TAG_OVERRIDES_FILE.read_text(encoding="utf-8")
    if yaml is None:
        # Without PyYAML we cannot safely parse arbitrary YAML; treat as empty
        # rather than guess. CI installs PyYAML so the production path is covered.
        return {}
    try:
        loaded = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        return {}
    if not isinstance(loaded, dict):
        return {}
    overrides: dict[str, list[str]] = {}
    for key, value in loaded.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, list):
            overrides[key] = [str(item).strip() for item in value if str(item).strip()]
    return overrides


def _matches_keyword(haystack: str, keyword: str) -> bool:
    """Whole-word match for a keyword inside a lower-cased haystack.

    Word boundaries are any non-alphanumeric character or string edge. Hyphens
    and dots inside multi-word keywords (for example, ``ci/cd`` or ``next.js``)
    are treated as content, so the keyword is matched as one literal token.
    """
    if not keyword:
        return False
    pattern = re.escape(keyword.lower())
    return re.search(rf"(?:^|[^a-z0-9]){pattern}(?:$|[^a-z0-9])", haystack) is not None


def extract_tags(name: str, description: str, overrides: dict[str, list[str]]) -> list[str]:
    """Return a sorted, deduplicated list of tags for a skill.

    Whole-word match against TAG_KEYWORDS, plus any explicit override entries.
    Overrides are unioned with detected tags, never replace them, so the
    automatic safety net stays in place if curators forget a tag.
    """
    haystack = f" {name.lower()} {description.lower()} "
    tags: set[str] = set()
    for tag, keywords in TAG_KEYWORDS.items():
        for keyword in keywords:
            if _matches_keyword(haystack, keyword):
                tags.add(tag)
                break
    for extra in overrides.get(name, []):
        tags.add(extra.lower())
    return sorted(tags)


@dataclass(frozen=True)
class SkillEntry:
    install_name: str
    path: str
    format: str
    frontmatter: dict[str, object]


def error(message: str) -> str:
    return f"ERROR: {message}"


def warning(message: str) -> str:
    return f"WARN: {message}"


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def normalize_scalar(value: object) -> object:
    if not isinstance(value, str):
        return value
    return re.sub(r"\s+", " ", value).strip()


def fallback_parse_frontmatter(frontmatter_text: str, path: Path) -> tuple[dict[str, object], list[str]]:
    frontmatter: dict[str, object] = {}
    messages: list[str] = []
    current_key: str | None = None
    quoted_key: str | None = None
    quote_char: str | None = None
    quoted_parts: list[str] = []

    def finish_quoted_scalar() -> None:
        nonlocal quoted_key, quote_char, quoted_parts
        if quoted_key is not None:
            frontmatter[quoted_key] = normalize_scalar(" ".join(part for part in quoted_parts if part))
        quoted_key = None
        quote_char = None
        quoted_parts = []

    for line in frontmatter_text.splitlines():
        if quoted_key is not None:
            stripped = line.strip()
            if stripped == quote_char:
                finish_quoted_scalar()
                continue
            if stripped.endswith(quote_char or ""):
                stripped = stripped[:-1]
                if quote_char == "'" and "''" in stripped:
                    stripped = stripped.replace("''", "'")
                quoted_parts.append(stripped)
                finish_quoted_scalar()
                continue
            quoted_parts.append(stripped)
            continue

        if not line.strip() or line.lstrip().startswith("#"):
            continue

        key_match = re.match(r"^([A-Za-z0-9_-]+):(?:\s*(.*))?$", line)
        if key_match:
            current_key = key_match.group(1)
            raw_value = key_match.group(2) or ""
            stripped_value = raw_value.strip()

            if stripped_value[:1] in {"'", '"'} and not stripped_value.endswith(stripped_value[0]):
                quoted_key = current_key
                quote_char = stripped_value[0]
                quoted_parts = [stripped_value[1:]]
                continue

            frontmatter[current_key] = normalize_scalar(strip_quotes(stripped_value)) if stripped_value else {}
            continue

        if current_key and line.startswith("- "):
            value = frontmatter.get(current_key)
            if not isinstance(value, list):
                value = []
                frontmatter[current_key] = value
            value.append(strip_quotes(line[2:]))
            continue

        if current_key and line.startswith("  "):
            value = frontmatter.get(current_key)
            if isinstance(value, str):
                frontmatter[current_key] = normalize_scalar(f"{value} {strip_quotes(line)}")
            continue

        messages.append(error(f"{path.relative_to(ROOT)} has unsupported frontmatter line: {line}"))

    if quoted_key is not None:
        messages.append(error(f"{path.relative_to(ROOT)} has unterminated quoted frontmatter value: {quoted_key}"))

    return frontmatter, messages


def parse_frontmatter(path: Path) -> tuple[dict[str, object], list[str]]:
    text = path.read_text(encoding="utf-8")

    if not text.startswith("---\n"):
        return {}, [error(f"{path.relative_to(ROOT)} is missing YAML frontmatter")]

    end = text.find("\n---", 4)
    if end == -1:
        return {}, [error(f"{path.relative_to(ROOT)} has unterminated YAML frontmatter")]

    frontmatter_text = text[4:end]

    if yaml is not None:
        try:
            parsed = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError as exc:
            return {}, [error(f"{path.relative_to(ROOT)} has invalid YAML frontmatter: {exc}")]
        if not isinstance(parsed, dict):
            return {}, [error(f"{path.relative_to(ROOT)} frontmatter must be a YAML mapping")]
        return {str(key): normalize_scalar(value) for key, value in parsed.items()}, []

    return fallback_parse_frontmatter(frontmatter_text, path)


def discover_skills() -> list[SkillEntry]:
    entries: list[SkillEntry] = []

    for skill_dir in sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            frontmatter, _ = parse_frontmatter(skill_md)
            entries.append(
                SkillEntry(
                    install_name=skill_dir.name,
                    path=str(skill_md.relative_to(ROOT)),
                    format="directory",
                    frontmatter=frontmatter,
                )
            )

    for skill_file in sorted(SKILLS_DIR.glob("*.SKILL.md")):
        frontmatter, _ = parse_frontmatter(skill_file)
        entries.append(
            SkillEntry(
                install_name=skill_file.name.removesuffix(".SKILL.md"),
                path=str(skill_file.relative_to(ROOT)),
                format="file",
                frontmatter=frontmatter,
            )
        )

    return sorted(entries, key=lambda entry: entry.install_name)


def validate_entries(entries: list[SkillEntry]) -> list[str]:
    messages: list[str] = []
    seen_install_names: dict[str, str] = {}
    seen_frontmatter_names: dict[str, str] = {}

    for entry in entries:
        try:
            safe_kebab_name(entry.install_name, kind="install name")
            safe_output_path(ROOT, entry.path, kind="skill registry path")
        except UnsafePathError as exc:
            messages.append(error(f"{entry.path} has unsafe registry path or install name: {exc}"))
            continue

        path = ROOT / entry.path
        frontmatter, parse_messages = parse_frontmatter(path)
        messages.extend(parse_messages)

        previous_path = seen_install_names.get(entry.install_name)
        if previous_path:
            messages.append(error(f"duplicate install name {entry.install_name}: {previous_path}, {entry.path}"))
        seen_install_names[entry.install_name] = entry.path

        unexpected = set(frontmatter) - ALLOWED_FRONTMATTER_KEYS
        if unexpected:
            messages.append(
                error(
                    f"{entry.path} has unsupported frontmatter keys: {', '.join(sorted(unexpected))}"
                )
            )

        name = frontmatter.get("name")
        description = frontmatter.get("description")

        if not isinstance(name, str) or not name.strip():
            messages.append(error(f"{entry.path} is missing non-empty name"))
        else:
            name = name.strip()
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
                messages.append(error(f"{entry.path} name is not kebab-case: {name}"))
            if name != entry.install_name:
                messages.append(
                    error(f"{entry.path} name {name} does not match install name {entry.install_name}")
                )
            previous_frontmatter_path = seen_frontmatter_names.get(name)
            if previous_frontmatter_path:
                messages.append(error(f"duplicate frontmatter name {name}: {previous_frontmatter_path}, {entry.path}"))
            seen_frontmatter_names[name] = entry.path

        if not isinstance(description, str) or not description.strip():
            messages.append(error(f"{entry.path} is missing non-empty description"))
        elif len(description.strip()) > 1024:
            messages.append(warning(f"{entry.path} description exceeds 1024 characters"))

        body = skill_markdown_body(path)
        for token in unresolved_placeholder_tokens(body):
            messages.append(error(f"{entry.path} contains unresolved placeholder token: {token}"))

        for ref in local_support_references(
            install_name=entry.install_name,
            entry_path=entry.path,
            entry_format=entry.format,
            body=body,
            root=ROOT,
        ):
            if ref.unsafe_reason:
                messages.append(error(f"{entry.path} references unsafe support path {ref.ref}: {ref.unsafe_reason}"))
            elif not ref.target.exists():
                messages.append(error(f"{entry.path} references missing support file: {ref.ref}"))

        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > 500:
            messages.append(warning(f"{entry.path} is {line_count} lines; consider progressive disclosure"))

    return messages


def registry_payload(entries: list[SkillEntry]) -> list[dict[str, object]]:
    overrides = load_tag_overrides()
    payload: list[dict[str, object]] = []
    for entry in entries:
        description = entry.frontmatter.get("description", "")
        description_text = description if isinstance(description, str) else ""
        tags = extract_tags(entry.install_name, description_text, overrides)
        language = detect_language(description_text)
        payload.append(
            {
                "name": entry.install_name,
                "category": CATEGORY_BY_NAME.get(entry.install_name, "Uncategorized"),
                "format": entry.format,
                "path": entry.path,
                "description": description,
                "language": language,
                "tags": tags,
            }
        )
    return payload


def tags_payload(entries: list[SkillEntry]) -> dict[str, object]:
    """Build a tag -> [skill names] index for fast offline lookup."""
    payload = registry_payload(entries)
    tag_to_names: dict[str, list[str]] = {}
    for item in payload:
        name = str(item["name"])
        for tag in item.get("tags", []) or []:
            tag_to_names.setdefault(str(tag), []).append(name)
    sorted_index = {tag: sorted(set(names)) for tag, names in sorted(tag_to_names.items())}
    counts = {tag: len(names) for tag, names in sorted_index.items()}
    return {
        "total_skills": len(payload),
        "total_tags": len(sorted_index),
        "tag_counts": counts,
        "index": sorted_index,
    }


def render_tags_json(entries: list[SkillEntry]) -> str:
    return json.dumps(tags_payload(entries), ensure_ascii=False, indent=2) + "\n"


def render_registry_json(entries: list[SkillEntry]) -> str:
    return json.dumps(registry_payload(entries), ensure_ascii=False, indent=2) + "\n"


def escape_table_cell(value: object) -> str:
    text = str(value).replace("\n", " ").replace("|", "\\|")
    return re.sub(r"\s+", " ", text).strip()


def render_registry_doc(entries: list[SkillEntry]) -> str:
    payload = registry_payload(entries)
    lines = [
        "# Skill Registry",
        "",
        "<!-- Generated by scripts/validate_skills.py --write. Do not edit manually. -->",
        "",
        f"Total installable skills: {len(payload)}",
        "",
        "| Name | Category | Format | Lang | Tags | Path | Description |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in payload:
        path = escape_table_cell(item["path"])
        tags = ", ".join(item.get("tags", []) or [])
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{escape_table_cell(item['name'])}`",
                    escape_table_cell(item["category"]),
                    escape_table_cell(item["format"]),
                    escape_table_cell(item.get("language", "en")),
                    escape_table_cell(tags),
                    f"[{path}](../{path})",
                    escape_table_cell(item["description"]),
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append(
        "Tag index: see [`registry/tags.json`](../registry/tags.json). Run "
        "`python3 scripts/validate_skills.py search <query>` for offline lookup."
    )
    return "\n".join(lines) + "\n"


def check_file(path: Path, expected: str) -> list[str]:
    if not path.exists():
        return [error(f"{path.relative_to(ROOT)} is missing; run scripts/validate_skills.py --write")]

    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        return [error(f"{path.relative_to(ROOT)} is out of date; run scripts/validate_skills.py --write")]
    return []


def check_readme_counts(skill_count: int) -> list[str]:
    messages: list[str] = []
    checks = [
        (ROOT / "README.md", rf"{skill_count} Cross-Runtime Skills", rf"skills-{skill_count}-"),
        (ROOT / "README_CN.md", rf"{skill_count} 个跨 Runtime Skills", rf"skills-{skill_count}-"),
        (ROOT / "install.sh", rf"{skill_count} Skills | 7 Agents", None),
    ]

    for path, required_text, badge_text in checks:
        text = path.read_text(encoding="utf-8")
        if required_text not in text:
            messages.append(error(f"{path.relative_to(ROOT)} does not contain current count text: {required_text}"))
        if badge_text and badge_text not in text:
            messages.append(error(f"{path.relative_to(ROOT)} does not contain current badge count: {badge_text}"))

    return messages


def write_generated_files(entries: list[SkillEntry]) -> None:
    REGISTRY_JSON.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_JSON.write_text(render_registry_json(entries), encoding="utf-8")
    REGISTRY_DOC.write_text(render_registry_doc(entries), encoding="utf-8")
    TAGS_JSON.write_text(render_tags_json(entries), encoding="utf-8")


def search_skills(
    entries: list[SkillEntry],
    query: str,
    *,
    tag_filter: str | None = None,
    language_filter: str | None = None,
) -> list[dict[str, object]]:
    """Offline keyword + tag + language search over the registry.

    The query is split on whitespace; every token must match somewhere in name,
    description, category, or tags (AND semantics, case-insensitive). When a
    tag filter is supplied the skill must carry that tag. When a language
    filter is supplied the skill description must match it.
    """
    payload = registry_payload(entries)
    tokens = [token.strip().lower() for token in re.split(r"\s+", query or "") if token.strip()]
    results: list[dict[str, object]] = []
    for item in payload:
        if language_filter and item.get("language") != language_filter:
            continue
        if tag_filter and tag_filter.lower() not in [t.lower() for t in item.get("tags", []) or []]:
            continue
        haystack = " ".join(
            [
                str(item.get("name", "")),
                str(item.get("description", "")),
                str(item.get("category", "")),
                " ".join(item.get("tags", []) or []),
            ]
        ).lower()
        if all(token in haystack for token in tokens):
            results.append(item)
    return results


def render_search_results(results: list[dict[str, object]]) -> str:
    if not results:
        return "No skills match the query.\n"
    lines = [f"Found {len(results)} skill(s):", ""]
    for item in results:
        tags = ", ".join(item.get("tags", []) or []) or "-"
        description = str(item.get("description", "")).strip().replace("\n", " ")
        if len(description) > 160:
            description = description[:157] + "..."
        lines.append(f"- {item['name']} [{item.get('category','')}] ({item.get('language','en')})")
        lines.append(f"    tags: {tags}")
        lines.append(f"    path: {item['path']}")
        lines.append(f"    {description}")
    return "\n".join(lines) + "\n"


def run_search_command(args: argparse.Namespace) -> int:
    entries = discover_skills()
    results = search_skills(
        entries,
        " ".join(args.query),
        tag_filter=args.tag,
        language_filter=args.language,
    )
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(render_search_results(results), end="")
    return 0 if results else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check generated registry files and README counts")
    parser.add_argument("--write", action="store_true", help="Regenerate registry files")
    subparsers = parser.add_subparsers(dest="command")

    search_parser = subparsers.add_parser(
        "search",
        help="Search skills by keyword, tag, or language (offline, no network).",
    )
    search_parser.add_argument("query", nargs="*", help="Free-text query tokens (AND semantics)")
    search_parser.add_argument("--tag", help="Restrict results to a single tag, e.g. --tag rust")
    search_parser.add_argument(
        "--language",
        choices=["en", "zh", "mixed"],
        help="Restrict results by description language",
    )
    search_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    args = parser.parse_args()

    if args.command == "search":
        return run_search_command(args)

    entries = discover_skills()
    messages = validate_entries(entries)

    validation_errors = [message for message in messages if message.startswith("ERROR:")]

    if args.write and not validation_errors:
        write_generated_files(entries)

    if args.check:
        messages.extend(check_file(REGISTRY_JSON, render_registry_json(entries)))
        messages.extend(check_file(REGISTRY_DOC, render_registry_doc(entries)))
        messages.extend(check_file(TAGS_JSON, render_tags_json(entries)))
        messages.extend(check_readme_counts(len(entries)))

    errors = [message for message in messages if message.startswith("ERROR:")]
    warnings = [message for message in messages if message.startswith("WARN:")]

    for message in errors + warnings:
        print(message)

    print(f"Validated {len(entries)} installable skills: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
