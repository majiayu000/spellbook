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


class RequirementParseError(ValueError):
    """Raised when requirements.txt includes cannot be resolved safely."""


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


def _requirement_include_path(requirements_path: Path, include_path: str) -> Path:
    include = (requirements_path.parent / include_path).resolve()
    requirements_root = requirements_path.parent.resolve()
    try:
        include.relative_to(requirements_root)
    except ValueError as exc:
        raise RequirementParseError(f"requirements include escapes skill folder: {include_path}") from exc
    if not include.exists():
        raise RequirementParseError(f"requirements include not found: {include_path}")
    return include


def declared_requirements(requirements_path: Path, seen: set[Path] | None = None) -> set[str]:
    """Return normalized package names from a requirements.txt file."""
    if not requirements_path.exists():
        return set()

    resolved_requirements_path = requirements_path.resolve()
    seen = seen or set()
    if resolved_requirements_path in seen:
        return set()
    seen.add(resolved_requirements_path)

    packages: set[str] = set()
    for line in requirements_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("-r ") or stripped.startswith("--requirement "):
            include_path = stripped.split(maxsplit=1)[1].split(maxsplit=1)[0]
            packages.update(declared_requirements(_requirement_include_path(requirements_path, include_path), seen))
            continue

        if stripped.startswith("-"):
            continue

        # Marker-gated declarations do not satisfy unconditional script imports.
        if ";" in stripped:
            continue

        name = re.split(r"\s|<|>|=|!|~|\[", stripped, maxsplit=1)[0]
        if name:
            packages.add(_normalize_package_name(name))
    return packages


def _is_beautifulsoup_call(node: ast.Call) -> bool:
    if isinstance(node.func, ast.Name):
        return node.func.id == "BeautifulSoup"
    if isinstance(node.func, ast.Attribute):
        return node.func.attr == "BeautifulSoup"
    return False


def _string_literal_contains_lxml(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value == "lxml"
    if isinstance(node, (ast.List, ast.Tuple)):
        return any(_string_literal_contains_lxml(item) for item in node.elts)
    return False


def beautifulsoup_lxml_dependencies(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_beautifulsoup_call(node):
            continue
        if any(_string_literal_contains_lxml(arg) for arg in node.args[1:]):
            return {"lxml"}
        for keyword in node.keywords:
            if keyword.arg in {"features", "builder"} and _string_literal_contains_lxml(keyword.value):
                return {"lxml"}
    return set()


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
        requirements.update(beautifulsoup_lxml_dependencies(script))
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

    try:
        declared = declared_requirements(requirements_path)
    except RequirementParseError as exc:
        return [error(f"{rel_requirements_path} has invalid requirements include: {exc}")]

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
