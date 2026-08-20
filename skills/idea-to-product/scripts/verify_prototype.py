#!/usr/bin/env python3
"""Verify an idea-to-product HTML prototype is bounded and offline-safe."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import urlparse


MAX_BYTES = 80 * 1024
URL_ATTRS = {"action", "formaction", "href", "poster", "src"}
REMOTE_SCHEMES = {"http", "https", "ws", "wss"}


def is_remote(value: str) -> bool:
    stripped = value.strip()
    if stripped.startswith("//"):
        return True
    return urlparse(stripped).scheme.lower() in REMOTE_SCHEMES


class PrototypeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.errors: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        normalized = {key.lower(): (value or "") for key, value in attrs}
        if tag.lower() == "script" and "src" in normalized:
            self.errors.append("external script src is forbidden")
        if tag.lower() == "link" and "href" in normalized:
            self.errors.append("link href is forbidden in a single-file prototype")
        for name, value in normalized.items():
            if name.startswith("on"):
                self.errors.append(f"inline event handler is forbidden: {name}")
            if name in URL_ATTRS and value.strip().lower().startswith("javascript:"):
                self.errors.append(f"javascript URL is forbidden: {name}")
            if name in URL_ATTRS and is_remote(value):
                self.errors.append(f"remote {name} URL is forbidden: {value}")


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

    checks = {
        "unresolved template placeholder": r"\{\{[^}]+\}\}",
        "remote CSS @import": r"@import\s+(?:url\()?\s*['\"]?(?:https?:)?//",
        "remote CSS url()": r"url\(\s*['\"]?(?:https?:)?//",
        "remote fetch": r"\bfetch\s*\(\s*['\"](?:https?:)?//",
        "remote XMLHttpRequest.open": r"\.open\s*\([^,]+,\s*['\"](?:https?:)?//",
        "remote WebSocket/EventSource": r"\b(?:WebSocket|EventSource)\s*\(\s*['\"](?:wss?:|https?:)?//",
    }
    for label, pattern in checks.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            errors.append(label)

    required = {
        "dark mode media query": "@media (prefers-color-scheme: dark)",
        "mobile media query": "@media (max-width: 640px)",
        "interactive event listener": "addEventListener",
        "initial progress state": "showStep(1)",
    }
    for label, needle in required.items():
        if needle not in text:
            errors.append(f"missing {label}")
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
