"""Parse skill YAML frontmatter using PyYAML."""

from __future__ import annotations

import re
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only on minimal user systems.
    yaml = None


ROOT = Path(__file__).resolve().parents[1]


def error(message: str) -> str:
    return f"ERROR: {message}"


def normalize_scalar(value: object) -> object:
    if not isinstance(value, str):
        return value
    return re.sub(r"\s+", " ", value).strip()


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
        return {str(key): value if key == "compatibility" else normalize_scalar(value)
                for key, value in parsed.items()}, []

    return {}, [error(f"{path.relative_to(ROOT)} YAML frontmatter requires PyYAML")]
