#!/usr/bin/env python3
"""Verify an idea-to-product HTML prototype is bounded and offline-safe."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import sys


MAX_BYTES = 80 * 1024
URL_ATTRS = {"action", "formaction", "href", "poster", "src"}
JS_NOISE = re.compile(
    r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`|//[^\n]*|/\*.*?\*/',
    flags=re.DOTALL,
)
IIFE = re.compile(
    r"^\s*\(\s*function\s*\([^)]*\)\s*\{(?P<body>.*)\}\s*\)\s*\(\s*\)\s*;?\s*$",
    flags=re.DOTALL,
)


class PrototypeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.errors: list[str] = []
        self.script_count = 0
        self.script_depth = 0
        self.script_chunks: list[str] = []
        self.action_count = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        normalized = {key.lower(): (value or "") for key, value in attrs}
        normalized_tag = tag.lower()
        if normalized_tag == "script":
            self.script_count += 1
            self.script_depth += 1
            if "src" in normalized:
                self.errors.append("external script src is forbidden")
        if normalized_tag == "link" and "href" in normalized:
            self.errors.append("link href is forbidden in a single-file prototype")
        if normalized.get("http-equiv", "").lower() == "refresh":
            self.errors.append("meta refresh is forbidden")
        if "data-action" in normalized:
            self.action_count += 1
        for name, value in normalized.items():
            if name.startswith("on"):
                self.errors.append(f"inline event handler is forbidden: {name}")
            if name in URL_ATTRS and value.strip().lower().startswith("javascript:"):
                self.errors.append(f"javascript URL is forbidden: {name}")
            if name in URL_ATTRS:
                target = value.strip().lower()
                if target and not target.startswith(("#", "data:")):
                    self.errors.append(
                        f"non-embedded {name} target is forbidden: {value}"
                    )

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self.script_depth:
            self.script_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.script_depth:
            self.script_chunks.append(data)


def executable_js(source: str) -> str:
    """Remove comments and string bodies before checking executable calls."""
    return JS_NOISE.sub(" ", source)


def top_level_js(source: str) -> str:
    """Keep only statements outside brace-delimited callbacks/functions."""
    depth = 0
    result: list[str] = []
    for char in source:
        if char == "{":
            depth += 1
            result.append(" ")
        elif char == "}":
            depth = max(0, depth - 1)
            # A completed top-level block is also a safe statement boundary.
            result.append(";\n" if depth == 0 else " ")
        elif depth == 0:
            result.append(char)
        else:
            # Preserve line boundaries so diagnostics and anchored checks stay stable.
            result.append("\n" if char == "\n" else " ")
    return "".join(result)


def entrypoint_js(source: str) -> str:
    """Return statements executed at script load, including a whole-script IIFE."""
    match = IIFE.fullmatch(source)
    return top_level_js(match.group("body") if match else source)


def verify(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"prototype does not exist: {path}"]
    size = path.stat().st_size
    if size > MAX_BYTES:
        errors.append(f"prototype is {size} bytes; limit is {MAX_BYTES}")
    text = path.read_text(encoding="utf-8")

    parser = PrototypeParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:  # HTMLParser can reject malformed entities/state.
        errors.append(f"HTML parse failed: {exc}")
    errors.extend(parser.errors)

    if parser.script_count != 1:
        errors.append(f"expected exactly one inline script; found {parser.script_count}")
    if parser.action_count < 1:
        errors.append("missing data-action control")

    checks = {
        "unresolved template placeholder": r"\{\{[^}]+\}\}",
        "external URL literal": r"(?:https?|wss?)://|(?<!:)//[a-z0-9]",
        "CSS @import": r"@import\b",
        "CSS url() dependency": r"url\s*\(",
    }
    for label, pattern in checks.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            errors.append(label)

    required_text = {
        "dark mode media query": "@media (prefers-color-scheme: dark)",
        "mobile media query": "@media (max-width: 640px)",
    }
    for label, needle in required_text.items():
        if needle not in text:
            errors.append(f"missing {label}")

    script_source = "\n".join(parser.script_chunks)
    js = executable_js(script_source)
    entrypoint = entrypoint_js(js)
    required_js = {
        "interactive event listener": (
            r"(?:^|;)\s*document\s*\.\s*addEventListener\s*\("
        ),
        "initial progress state": r"(?:^|;)\s*showStep\s*\(\s*1\s*\)\s*;",
    }
    for label, pattern in required_js.items():
        if not re.search(pattern, entrypoint, flags=re.MULTILINE):
            errors.append(f"missing {label}")

    dangerous_js = {
        "eval() is forbidden": r"\beval\b",
        "Function() constructor is forbidden": r"\bFunction\b",
        "document.write is forbidden": r"\bdocument\s*\.\s*write\s*\(",
        "innerHTML assignment is forbidden": r"\binnerHTML\b",
        "insertAdjacentHTML is forbidden": r"\binsertAdjacentHTML\b",
        "fetch() is forbidden": r"\bfetch\b",
        "XMLHttpRequest is forbidden": r"\bXMLHttpRequest\b",
        "WebSocket is forbidden": r"\bWebSocket\b",
        "EventSource is forbidden": r"\bEventSource\b",
        "sendBeacon is forbidden": r"\bsendBeacon\b",
        "dynamic import() is forbidden": r"\bimport\s*\(",
    }
    for label, pattern in dangerous_js.items():
        if re.search(pattern, script_source):
            errors.append(label)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prototype", type=Path)
    args = parser.parse_args()
    errors = verify(args.prototype)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OK: {args.prototype}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
