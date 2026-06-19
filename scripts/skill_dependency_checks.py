"""Validate machine-readable dependency metadata for skill helper scripts."""

from __future__ import annotations

import ast
import re
import shlex
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


def _requirement_include_path(requirements_path: Path, include_path: str, requirements_root: Path) -> Path:
    include = (requirements_path.parent / include_path).resolve()
    try:
        include.relative_to(requirements_root)
    except ValueError as exc:
        raise RequirementParseError(f"requirements include escapes skill folder: {include_path}") from exc
    if not include.exists():
        raise RequirementParseError(f"requirements include not found: {include_path}")
    if not include.is_file():
        raise RequirementParseError(f"requirements include is not a file: {include_path}")
    return include


def _strip_inline_comment(line: str) -> str:
    in_single_quote = False
    in_double_quote = False
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            continue
        if (
            char == "#"
            and not in_single_quote
            and not in_double_quote
            and (index == 0 or line[index - 1].isspace())
        ):
            return line[:index].rstrip()
    return line


def _requirement_tokens(line: str) -> list[str]:
    try:
        return shlex.split(line, comments=True)
    except ValueError as exc:
        raise RequirementParseError(f"invalid requirements line: {line}") from exc


def _requirement_include_value(line: str) -> str | None:
    tokens = _requirement_tokens(line)
    if not tokens:
        return None

    option = tokens[0]
    if option in {"-r", "--requirement"}:
        if len(tokens) < 2 or not tokens[1]:
            raise RequirementParseError(f"requirements include missing file: {option}")
        return tokens[1]
    if option.startswith("--requirement="):
        include_path = option.split("=", 1)[1]
        if not include_path:
            raise RequirementParseError(f"requirements include missing file: --requirement")
        return include_path
    if option.startswith("-r"):
        include_path = option[2:]
        if not include_path:
            raise RequirementParseError(f"requirements include missing file: -r")
        return include_path
    return None


def _editable_requirement_value(line: str) -> str | None:
    tokens = _requirement_tokens(line)
    if not tokens:
        return None

    option = tokens[0]
    if option in {"-e", "--editable"}:
        if len(tokens) < 2 or not tokens[1]:
            raise RequirementParseError(f"editable requirement missing target: {option}")
        return tokens[1]
    if option.startswith("--editable="):
        editable_path = option.split("=", 1)[1]
        if not editable_path:
            raise RequirementParseError("editable requirement missing target: --editable")
        return editable_path
    if option.startswith("-e"):
        editable_path = option[2:]
        if not editable_path:
            raise RequirementParseError("editable requirement missing target: -e")
        return editable_path
    return None


def declared_requirements(
    requirements_path: Path,
    seen: set[Path] | None = None,
    requirements_root: Path | None = None,
) -> set[str]:
    """Return normalized package names from a requirements.txt file."""
    if not requirements_path.exists():
        return set()

    resolved_requirements_path = requirements_path.resolve()
    requirements_root = requirements_root or resolved_requirements_path.parent
    seen = seen or set()
    if resolved_requirements_path in seen:
        return set()
    seen.add(resolved_requirements_path)

    packages: set[str] = set()
    for line in requirements_path.read_text(encoding="utf-8").splitlines():
        stripped = _strip_inline_comment(line.strip()).strip()
        if not stripped or stripped.startswith("#"):
            continue

        include_path = _requirement_include_value(stripped)
        if include_path is not None:
            packages.update(
                declared_requirements(
                    _requirement_include_path(requirements_path, include_path, requirements_root),
                    seen,
                    requirements_root,
                )
            )
            continue

        editable_path = _editable_requirement_value(stripped)
        if editable_path is not None:
            raise RequirementParseError(f"editable requirements are not supported: {editable_path}")

        if stripped.startswith("-"):
            continue

        if ";" in stripped:
            _, marker_text = stripped.split(";", 1)
            if not marker_text.strip():
                raise RequirementParseError(f"empty environment marker: {stripped}")
            # Script imports are unconditional, so marker-gated declarations do
            # not prove the package will be available at runtime.
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


def _assigned_expressions(tree: ast.AST) -> dict[str, list[ast.AST]]:
    assignments: dict[str, list[ast.AST]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments.setdefault(target.id, []).append(node.value)
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
        ):
            assignments.setdefault(node.target.id, []).append(node.value)
        elif isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
            assignments.setdefault(node.target.id, []).append(node.value)
    return assignments


def _string_literal_requires_lxml(
    node: ast.AST,
    assignments: dict[str, list[ast.AST]],
    seen_names: set[str] | None = None,
) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value in {"lxml", "lxml-xml", "xml"}
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return any(
            _string_literal_requires_lxml(item, assignments, seen_names) for item in node.elts
        )
    if isinstance(node, ast.Name):
        seen_names = seen_names or set()
        if node.id in seen_names:
            return False
        return any(
            _string_literal_requires_lxml(value, assignments, seen_names | {node.id})
            for value in assignments.get(node.id, [])
        )
    if isinstance(node, ast.IfExp):
        return _string_literal_requires_lxml(
            node.body, assignments, seen_names
        ) or _string_literal_requires_lxml(node.orelse, assignments, seen_names)
    return False


def beautifulsoup_lxml_dependencies(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()

    assignments = _assigned_expressions(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_beautifulsoup_call(node):
            continue
        if any(_string_literal_requires_lxml(arg, assignments) for arg in node.args[1:]):
            return {"lxml"}
        for keyword in node.keywords:
            if keyword.arg in {"features", "builder"} and _string_literal_requires_lxml(
                keyword.value,
                assignments,
            ):
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
