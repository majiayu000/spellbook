#!/usr/bin/env python3
"""Read-only scanner for repository agent context files."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "target",
    "dist",
    "build",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".turbo",
    ".venv",
    "venv",
    "__pycache__",
}

HIGH_CONTEXT_ANY_NAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "WARP.md",
    "RULES.md",
}

TOP_LEVEL_CONTEXT_NAMES = {
    "CONTRIBUTING.md",
    "README.md",
}

HIGH_CONTEXT_REL = {
    ".claude/instructions.md",
    ".github/copilot-instructions.md",
}

SPEC_NAMES = {
    "PRODUCT.md",
    "product.md",
    "TECH.md",
    "tech.md",
}

MANIFEST_NAMES = {
    "Cargo.toml",
    "go.mod",
    "package.json",
    "pnpm-workspace.yaml",
    "pyproject.toml",
    "pytest.ini",
    "requirements.txt",
    "tsconfig.json",
}

SCOPED_AGENT_DIRS = {
    ".github": "CI, issue templates, and automation contracts",
    "app": "application entrypoints and user-facing behavior",
    "apps": "multi-app workspace conventions",
    "cmd": "command entrypoints",
    "crates": "Rust workspace crate conventions",
    "docs": "documentation and generated-doc boundaries",
    "internal": "internal packages and service boundaries",
    "migrations": "database migration safety and rollback rules",
    "packages": "package workspace conventions",
    "registry": "generated metadata and source-of-truth rules",
    "scripts": "operational script behavior and validation commands",
    "skills": "repo-local skill authoring rules",
    "src": "main source-tree implementation conventions",
    "tests": "test fixtures, helpers, and assertion style",
}

SOURCE_EXTENSIONS = {
    ".go",
    ".js",
    ".jsx",
    ".py",
    ".rs",
    ".ts",
    ".tsx",
}


def iter_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        current = Path(dirpath)
        for filename in filenames:
            yield current / filename


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def text_stats(path: Path) -> dict[str, int]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    return {
        "lines": len(lines),
        "headings": sum(1 for line in lines if line.startswith("#")),
        "tables": sum(1 for line in lines if line.startswith("|")),
        "code_fences": sum(1 for line in lines if line.startswith("```")),
        "numbered": sum(1 for line in lines if re.match(r"^\s*\d+\.\s+", line)),
    }


def file_entry(path: Path, root: Path) -> dict[str, object]:
    stats = text_stats(path)
    return {
        "path": rel(path, root),
        "lines": stats["lines"],
        "headings": stats["headings"],
        "tables": stats["tables"],
        "code_fences": stats["code_fences"],
        "numbered": stats["numbered"],
    }


def is_skill_file(relative: str) -> bool:
    return (
        re.match(r"^\.agents/skills/[^/]+/SKILL\.md$", relative) is not None
        or re.match(r"^skills/[^/]+/SKILL\.md$", relative) is not None
        or re.match(r"^skills/[^/]+\.SKILL\.md$", relative) is not None
    )


def package_json_script_hints(path: Path) -> list[dict[str, str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    scripts = payload.get("scripts")
    if not isinstance(scripts, dict):
        return []
    hints = []
    for name in ("build", "typecheck", "test", "lint", "format"):
        command = scripts.get(name)
        if isinstance(command, str):
            hints.append(
                {
                    "kind": name,
                    "command": f"npm run {name}",
                    "evidence": rel(path, path.parent),
                }
            )
    return hints


def command_hints(root: Path, manifests: list[Path]) -> list[dict[str, str]]:
    hints: list[dict[str, str]] = []
    manifest_names = {path.name for path in manifests}

    for path in manifests:
        if path.name == "package.json":
            for hint in package_json_script_hints(path):
                hint["evidence"] = rel(path, root)
                hints.append(hint)

    if "Cargo.toml" in manifest_names:
        hints.extend(
            [
                {"kind": "build", "command": "cargo check", "evidence": "Cargo.toml"},
                {"kind": "test", "command": "cargo test", "evidence": "Cargo.toml"},
                {"kind": "format", "command": "cargo fmt", "evidence": "Cargo.toml"},
            ]
        )
    if "go.mod" in manifest_names:
        hints.extend(
            [
                {"kind": "build", "command": "go build ./...", "evidence": "go.mod"},
                {"kind": "test", "command": "go test ./...", "evidence": "go.mod"},
            ]
        )
    if "pyproject.toml" in manifest_names or "pytest.ini" in manifest_names:
        evidence = "pyproject.toml" if "pyproject.toml" in manifest_names else "pytest.ini"
        hints.append({"kind": "test", "command": "pytest", "evidence": evidence})
    if "tsconfig.json" in manifest_names:
        hints.append({"kind": "typecheck", "command": "npx tsc --noEmit", "evidence": "tsconfig.json"})

    seen = set()
    deduped = []
    for hint in hints:
        key = (hint["kind"], hint["command"])
        if key not in seen:
            seen.add(key)
            deduped.append(hint)
    return deduped


def top_level_source_file_count(root: Path, dirname: str) -> int:
    directory = root / dirname
    if not directory.is_dir():
        return 0
    count = 0
    for path in directory.rglob("*"):
        if path.is_file() and path.suffix in SOURCE_EXTENSIONS:
            count += 1
            if count >= 5:
                return count
    return count


def scoped_agent_candidates(root: Path, high_context: list[Path]) -> list[dict[str, object]]:
    existing = {rel(path, root) for path in high_context if path.name == "AGENTS.md"}
    candidates = []
    for dirname, focus in sorted(SCOPED_AGENT_DIRS.items()):
        directory = root / dirname
        if not directory.is_dir():
            continue
        candidate_path = f"{dirname}/AGENTS.md"
        if candidate_path in existing:
            continue
        source_count = top_level_source_file_count(root, dirname)
        child_count = sum(1 for child in directory.iterdir() if child.name not in IGNORE_DIRS)
        if dirname in {"src", "app", "apps", "cmd", "crates", "internal", "packages"} and source_count == 0:
            continue
        candidates.append(
            {
                "path": candidate_path,
                "directory": dirname,
                "reason": focus,
                "signals": {
                    "children": child_count,
                    "source_files_sampled": source_count,
                },
            }
        )
    return candidates


def build_scan(root: Path) -> dict[str, object]:
    high_context = []
    supporting_docs = []
    skills = []
    specs = []
    manifests = []

    for path in iter_files(root):
        relative = rel(path, root)
        if (
            path.name in HIGH_CONTEXT_ANY_NAMES
            or relative in HIGH_CONTEXT_REL
            or (path.parent == root and path.name in TOP_LEVEL_CONTEXT_NAMES)
        ):
            high_context.append(path)
        elif path.name == "README.md":
            supporting_docs.append(path)
        if is_skill_file(relative):
            skills.append(path)
        if "/specs/" in f"/{relative}" and path.name in SPEC_NAMES:
            specs.append(path)
        if path.name in MANIFEST_NAMES and path.parent == root:
            manifests.append(path)

    top = [p for p in high_context if p.parent == root and p.name in {"AGENTS.md", "CLAUDE.md", "WARP.md"}]
    overloaded = [p for p in high_context if text_stats(p)["lines"] > 200]

    spec_by_name: dict[str, int] = {}
    spec_by_dir: dict[str, list[str]] = {}
    for path in specs:
        spec_by_name[path.name] = spec_by_name.get(path.name, 0) + 1
        parent = rel(path.parent, root)
        spec_by_dir.setdefault(parent, []).append(path.name)

    return {
        "root": root.as_posix(),
        "high_context_files": [file_entry(path, root) for path in sorted(high_context)],
        "supporting_readmes": [file_entry(path, root) for path in sorted(supporting_docs)],
        "repo_skills": [file_entry(path, root) for path in sorted(skills)],
        "specs": {
            "files": [file_entry(path, root) for path in sorted(specs)],
            "by_name": dict(sorted(spec_by_name.items())),
            "by_dir": {key: sorted(value) for key, value in sorted(spec_by_dir.items())},
        },
        "manifests": [rel(path, root) for path in sorted(manifests)],
        "command_hints": command_hints(root, sorted(manifests)),
        "scoped_agent_candidates": scoped_agent_candidates(root, high_context),
        "quick_signals": {
            "top_level_router_candidates": len(top),
            "repo_local_skills": len(skills),
            "spec_contract_files": len(specs),
            "overloaded_high_context_files": [rel(path, root) for path in sorted(overloaded)],
        },
    }


def print_markdown(scan: dict[str, object]) -> None:
    root = Path(str(scan["root"]))
    high_context = scan["high_context_files"]
    supporting_docs = scan["supporting_readmes"]
    skills = scan["repo_skills"]
    specs = scan["specs"]
    manifests = scan["manifests"]
    hints = scan["command_hints"]
    candidates = scan["scoped_agent_candidates"]
    quick = scan["quick_signals"]

    print(f"# Repo Agent Context Scan: {root}")
    print()

    print("## High-Context Files")
    if not high_context:
        print("- none found")
    for entry in high_context:
        print(
            f"- `{entry['path']}`: {entry['lines']} lines, "
            f"{entry['headings']} headings, {entry['code_fences']} code fences"
        )
    print()

    print("## Supporting README Files")
    if not supporting_docs:
        print("- none found")
    else:
        print(f"- files: {len(supporting_docs)}")
        for entry in supporting_docs[:40]:
            print(f"- `{entry['path']}`: {entry['lines']} lines")
        if len(supporting_docs) > 40:
            print(f"- ... {len(supporting_docs) - 40} more")
    print()

    print("## Repo Skills")
    if not skills:
        print("- none found")
    for entry in skills:
        print(f"- `{entry['path']}`: {entry['lines']} lines")
    print()

    print("## Specs")
    spec_files = specs["files"]
    if not spec_files:
        print("- none found")
    else:
        print(f"- files: {len(spec_files)}")
        for name, count in specs["by_name"].items():
            print(f"- {name}: {count}")
        print("- directories:")
        directories = list(specs["by_dir"].items())
        for directory, names in directories[:80]:
            print(f"  - `{directory}`: {', '.join(names)}")
        if len(directories) > 80:
            print(f"  - ... {len(directories) - 80} more")
    print()

    print("## Project Signals")
    if manifests:
        print("- manifests: " + ", ".join(f"`{path}`" for path in manifests))
    else:
        print("- manifests: none found")
    if hints:
        print("- command hints:")
        for hint in hints:
            print(f"  - {hint['kind']}: `{hint['command']}` from `{hint['evidence']}`")
    else:
        print("- command hints: none inferred")
    print()

    print("## Scoped AGENTS Candidates")
    if not candidates:
        print("- none inferred")
    for candidate in candidates:
        signals = candidate["signals"]
        print(
            f"- `{candidate['path']}`: {candidate['reason']} "
            f"({signals['children']} children, {signals['source_files_sampled']} source files sampled)"
        )
    print()

    print("## Quick Signals")
    print(f"- top-level router candidates: {quick['top_level_router_candidates']}")
    print(f"- repo-local skills: {quick['repo_local_skills']}")
    print(f"- spec contract files: {quick['spec_contract_files']}")
    overloaded = quick["overloaded_high_context_files"]
    if overloaded:
        names = ", ".join(f"`{path}`" for path in overloaded)
        print(f"- possible overloaded high-context files: {names}")
    else:
        print("- possible overloaded high-context files: none")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="repository root to scan")
    parser.add_argument("--json", action="store_true", help="emit structured JSON instead of Markdown")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    scan = build_scan(root)
    if args.json:
        print(json.dumps(scan, indent=2, sort_keys=True))
    else:
        print_markdown(scan)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
