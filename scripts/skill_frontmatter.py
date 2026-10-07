"""Parse skill YAML frontmatter with a small fallback parser."""

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


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def strip_inline_comment(line: str) -> str:
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


def normalize_scalar(value: object) -> object:
    if not isinstance(value, str):
        return value
    return re.sub(r"\s+", " ", value).strip()


def fallback_parse_frontmatter(frontmatter_text: str, path: Path) -> tuple[dict[str, object], list[str]]:
    frontmatter: dict[str, object] = {}
    messages: list[str] = []
    current_key: str | None = None
    current_nested_key: str | None = None
    metadata_indent: int | None = None
    quoted_key: str | None = None
    quote_char: str | None = None
    quoted_parts: list[str] = []

    def finish_quoted_scalar() -> None:
        nonlocal quoted_key, quote_char, quoted_parts
        if quoted_key is not None:
            value = " ".join(part for part in quoted_parts if part)
            frontmatter[quoted_key] = value if quoted_key == "compatibility" else normalize_scalar(value)
        quoted_key = None
        quote_char = None
        quoted_parts = []

    for raw_line in frontmatter_text.splitlines():
        line = raw_line.rstrip()
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

        line = strip_inline_comment(line).rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        key_match = re.match(r"^([A-Za-z0-9_-]+):(?:\s*(.*))?$", line)
        if key_match:
            current_key = key_match.group(1)
            current_nested_key = None
            metadata_indent = None
            raw_value = key_match.group(2) or ""
            stripped_value = raw_value.strip()

            if stripped_value[:1] in {"'", '"'} and not stripped_value.endswith(stripped_value[0]):
                quoted_key = current_key
                quote_char = stripped_value[0]
                quoted_parts = [stripped_value[1:]]
                continue

            if current_key == "compatibility" and stripped_value[:1] in {"|", ">"}:
                return frontmatter, messages + [
                    error(f"{path.relative_to(ROOT)} compatibility block scalars require PyYAML")
                ]

            if current_key == "compatibility" and stripped_value.startswith("{"):
                flow_match = re.fullmatch(r"\{\s*runtimes\s*:\s*\[(.*)\]\s*\}", stripped_value)
                if flow_match is None:
                    messages.append(error(f"{path.relative_to(ROOT)} has unsupported compatibility mapping; use PyYAML"))
                else:
                    frontmatter[current_key] = {
                        "runtimes": [strip_quotes(item) for item in flow_match.group(1).split(",") if item.strip()]
                    }
                continue

            value = strip_quotes(stripped_value)
            frontmatter[current_key] = (value if current_key == "compatibility" else normalize_scalar(value)) if stripped_value else {}
            continue

        if current_key == "metadata" and line.startswith(" "):
            metadata = frontmatter.get("metadata")
            nested_match = re.fullmatch(r"( +)([A-Za-z0-9_-]+):(?:\s*(.*))?", line)
            if not isinstance(metadata, dict) or nested_match is None:
                messages.append(error(f"{path.relative_to(ROOT)} has unsupported metadata line; use PyYAML: {line}"))
                continue
            indent = len(nested_match.group(1))
            if metadata_indent is not None and indent != metadata_indent:
                messages.append(error(f"{path.relative_to(ROOT)} has unsupported metadata indentation; use PyYAML: {line}"))
                continue
            metadata_indent = indent
            nested_key = nested_match.group(2)
            raw_value = (nested_match.group(3) or "").strip()
            metadata[nested_key] = normalize_scalar(strip_quotes(raw_value)) if raw_value else {}
            continue

        if current_key == "compatibility" and line.startswith("  "):
            compatibility = frontmatter.get("compatibility")
            if not isinstance(compatibility, dict):
                compatibility = {}
                frontmatter["compatibility"] = compatibility

            nested_key_match = re.match(r"^  ([A-Za-z0-9_-]+):(?:\s*(.*))?$", line)
            if nested_key_match:
                current_nested_key = nested_key_match.group(1)
                stripped_nested = (nested_key_match.group(2) or "").strip()
                if current_nested_key == "runtimes":
                    if stripped_nested == "[]":
                        compatibility[current_nested_key] = []
                    elif stripped_nested.startswith("[") and stripped_nested.endswith("]"):
                        raw_runtimes = stripped_nested.removeprefix("[").removesuffix("]")
                        compatibility[current_nested_key] = [
                            strip_quotes(item.strip()) for item in raw_runtimes.split(",") if item.strip()
                        ]
                    else:
                        compatibility[current_nested_key] = (
                            normalize_scalar(strip_quotes(stripped_nested)) if stripped_nested else []
                        )
                else:
                    compatibility[current_nested_key] = (
                        normalize_scalar(strip_quotes(stripped_nested)) if stripped_nested else {}
                    )
                continue

            list_match = re.match(r"^    -\s*(.*)$", line)
            if list_match and current_nested_key:
                value = compatibility.get(current_nested_key)
                if not isinstance(value, list):
                    value = []
                    compatibility[current_nested_key] = value
                value.append(strip_quotes(list_match.group(1).strip()))
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
                continued = f"{value} {strip_quotes(line)}"
                frontmatter[current_key] = continued if current_key == "compatibility" else normalize_scalar(continued)
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
        return {str(key): value if key == "compatibility" else normalize_scalar(value)
                for key, value in parsed.items()}, []

    return fallback_parse_frontmatter(frontmatter_text, path)
