"""Plan exact, reversible Codex plugin enablement changes."""

from __future__ import annotations

import re
from pathlib import Path


PLUGIN_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+$")
SECTION_RE = re.compile(r'^\[plugins\."([A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+)"\]\s*$')
ENABLED_RE = re.compile(r"^(\s*enabled\s*=\s*)(true|false)(\s*(?:#.*)?)$")


class PluginPolicyError(ValueError):
    """Raised when plugin state cannot be changed without rewriting TOML."""


def plan_plugin_states(config_path: Path, policy: dict) -> tuple[tuple[tuple[str, bool, bool], ...], str | None]:
    configured = policy.get("plugin_states", {})
    if not isinstance(configured, dict):
        raise PluginPolicyError("plugin_states must be an object")
    for plugin_id, enabled in configured.items():
        if not isinstance(plugin_id, str) or not PLUGIN_ID_RE.fullmatch(plugin_id):
            raise PluginPolicyError(f"invalid plugin id: {plugin_id!r}")
        if not isinstance(enabled, bool):
            raise PluginPolicyError(f"plugin state must be boolean: {plugin_id}")
    if not configured:
        return (), None

    original = config_path.read_text(encoding="utf-8")
    lines = original.splitlines()
    found: dict[str, tuple[int, bool, re.Match[str]]] = {}
    current_section: str | None = None
    for index, line in enumerate(lines):
        section = SECTION_RE.fullmatch(line)
        if section:
            current_section = section.group(1)
            continue
        if line.startswith("["):
            current_section = None
            continue
        enabled_match = ENABLED_RE.fullmatch(line)
        if current_section in configured and enabled_match:
            if current_section in found:
                raise PluginPolicyError(f"duplicate enabled setting: {current_section}")
            found[current_section] = (
                index,
                enabled_match.group(2) == "true",
                enabled_match,
            )
    missing = set(configured) - set(found)
    if missing:
        raise PluginPolicyError(f"configured plugin section is missing: {sorted(missing)}")

    changes: list[tuple[str, bool, bool]] = []
    for plugin_id, desired in sorted(configured.items()):
        index, current, match = found[plugin_id]
        if current == desired:
            continue
        lines[index] = f"{match.group(1)}{'true' if desired else 'false'}{match.group(3)}"
        changes.append((plugin_id, current, desired))
    if not changes:
        return (), None
    updated = "\n".join(lines) + ("\n" if original.endswith("\n") else "")
    return tuple(changes), updated
