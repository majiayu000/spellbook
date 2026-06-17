"""Validate machine-readable dependency metadata for skill helper scripts."""

from __future__ import annotations

import ast
import re
from pathlib import Path


IMPORT_TO_REQUIREMENT = {
    "PIL": "Pillow",
    "anthropic": "anthropic",
    "bs4": "beautifulsoup4",
    "pilmoji": "pilmoji",
    "requests": "requests",
    "yaml": "PyYAML",
}

LOCAL_SCRIPT_IMPORT_ROOTS = {
    "scripts",
}


def _normalize_package_name(name: str) -> str:
    return name.lower().replace("_", "-")


def python_import_roots(path: Path) -> set[str]:
    """Return top-level import names used by one Python source file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root:
                    imports.add(root)
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".", 1)[0]
            if root:
                imports.add(root)
    return imports


def declared_requirements(requirements_path: Path) -> set[str]:
    """Return normalized package names from a requirements.txt file."""
    if not requirements_path.exists():
        return set()

    packages: set[str] = set()
    for line in requirements_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        name = re.split(r"\s|<|>|=|!|~|;|\[", stripped, maxsplit=1)[0]
        if name:
            packages.add(_normalize_package_name(name))
    return packages


def required_script_dependencies(skill_dir: Path) -> set[str]:
    """Infer third-party package requirements for Python helper scripts."""
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.exists():
        return set()

    requirements: set[str] = set()
    for script in sorted(scripts_dir.rglob("*.py")):
        for import_root in python_import_roots(script):
            if import_root in LOCAL_SCRIPT_IMPORT_ROOTS:
                continue
            requirement = IMPORT_TO_REQUIREMENT.get(import_root)
            if requirement:
                requirements.add(requirement)
    return requirements


def validate_script_dependencies(
    *,
    root: Path,
    entry_path: str,
    entry_format: str,
    error,
) -> list[str]:
    if entry_format != "directory":
        return []

    skill_dir = (root / entry_path).parent
    required = required_script_dependencies(skill_dir)
    if not required:
        return []

    requirements_path = skill_dir / "requirements.txt"
    rel_requirements_path = requirements_path.relative_to(root)
    if not requirements_path.exists():
        required_list = ", ".join(sorted(required))
        return [
            error(
                f"{entry_path} imports third-party script packages but is missing "
                f"{rel_requirements_path}: {required_list}"
            )
        ]

    declared = declared_requirements(requirements_path)
    missing = sorted(
        requirement
        for requirement in required
        if _normalize_package_name(requirement) not in declared
    )
    if missing:
        return [
            error(
                f"{rel_requirements_path} is missing script package declaration(s): "
                + ", ".join(missing)
            )
        ]
    return []
