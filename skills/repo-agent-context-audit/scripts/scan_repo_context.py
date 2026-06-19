#!/usr/bin/env python3
"""Read-only scanner for repository agent context files."""

from __future__ import annotations

import argparse
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="repository root to scan")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    high_context = []
    supporting_docs = []
    skills = []
    specs = []

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
        if (
            relative.startswith(".agents/skills/")
            or re.match(r"^skills/[^/]+/SKILL\.md$", relative)
        ) and path.name == "SKILL.md":
            skills.append(path)
        if "/specs/" in f"/{relative}" and path.name in SPEC_NAMES:
            specs.append(path)

    print(f"# Repo Agent Context Scan: {root}")
    print()

    print("## High-Context Files")
    if not high_context:
        print("- none found")
    for path in sorted(high_context):
        stats = text_stats(path)
        print(
            f"- `{rel(path, root)}`: {stats['lines']} lines, "
            f"{stats['headings']} headings, {stats['code_fences']} code fences"
        )
    print()

    print("## Supporting README Files")
    if not supporting_docs:
        print("- none found")
    else:
        print(f"- files: {len(supporting_docs)}")
        for path in sorted(supporting_docs)[:40]:
            stats = text_stats(path)
            print(f"- `{rel(path, root)}`: {stats['lines']} lines")
        if len(supporting_docs) > 40:
            print(f"- ... {len(supporting_docs) - 40} more")
    print()

    print("## Repo Skills")
    if not skills:
        print("- none found")
    for path in sorted(skills):
        stats = text_stats(path)
        print(f"- `{rel(path, root)}`: {stats['lines']} lines")
    print()

    print("## Specs")
    if not specs:
        print("- none found")
    else:
        by_name: dict[str, int] = {}
        by_dir: dict[str, set[str]] = {}
        for path in specs:
            by_name[path.name] = by_name.get(path.name, 0) + 1
            parent = rel(path.parent, root)
            by_dir.setdefault(parent, set()).add(path.name)
        print(f"- files: {len(specs)}")
        for name in sorted(by_name):
            print(f"- {name}: {by_name[name]}")
        print("- directories:")
        for directory in sorted(by_dir)[:80]:
            names = ", ".join(sorted(by_dir[directory]))
            print(f"  - `{directory}`: {names}")
        if len(by_dir) > 80:
            print(f"  - ... {len(by_dir) - 80} more")
    print()

    print("## Quick Signals")
    top = [p for p in high_context if p.parent == root and p.name in {"AGENTS.md", "CLAUDE.md", "WARP.md"}]
    print(f"- top-level router candidates: {len(top)}")
    print(f"- repo-local skills: {len(skills)}")
    print(f"- spec contract files: {len(specs)}")
    overloaded = [p for p in high_context if text_stats(p)["lines"] > 200]
    if overloaded:
        names = ", ".join(f"`{rel(p, root)}`" for p in overloaded)
        print(f"- possible overloaded high-context files: {names}")
    else:
        print("- possible overloaded high-context files: none")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
