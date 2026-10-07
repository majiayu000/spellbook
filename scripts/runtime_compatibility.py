"""Runtime compatibility metadata validation and normalization."""

from __future__ import annotations

from collections.abc import Callable


COMPATIBILITY_KEYS = {"runtimes"}
RUNTIME_IDS = ("claude_code", "codex", "portable")
UNSPECIFIED_RUNTIME = "unspecified"
RUNTIME_METADATA_KEY = "spellbook-runtimes"


def validate_compatibility(
    frontmatter: dict[str, object],
    path: str,
    error: Callable[[str], str],
) -> list[str]:
    compatibility = frontmatter.get("compatibility")
    metadata = frontmatter.get("metadata", {})
    if not isinstance(metadata, dict):
        return [error(f"{path} metadata must be a YAML mapping (install PyYAML for flow-style metadata)")]
    declared = RUNTIME_METADATA_KEY in metadata
    messages: list[str] = []
    if isinstance(compatibility, dict):
        # Keep old checkout/custom-skill metadata readable during migration.
        if declared:
            messages.append(error(f"{path} declares runtimes in both compatibility and metadata"))
        unexpected = {str(key) for key in compatibility if key not in COMPATIBILITY_KEYS}
        if unexpected:
            messages.append(error(f"{path} has unsupported compatibility keys: {', '.join(sorted(unexpected))}"))
        runtimes = compatibility.get("runtimes")
        if not isinstance(runtimes, list) or not runtimes:
            return messages + [error(f"{path} compatibility.runtimes must be a non-empty list")]
    else:
        if "compatibility" in frontmatter and (
            not isinstance(compatibility, str) or not compatibility.strip() or len(compatibility) > 500
        ):
            messages.append(error(f"{path} compatibility must be a non-empty string of at most 500 characters"))
        if not declared:
            return messages
        value = metadata[RUNTIME_METADATA_KEY]
        if not isinstance(value, str) or not value.strip():
            return messages + [error(f"{path} metadata.{RUNTIME_METADATA_KEY} must be a non-empty string")]
        runtimes = value.split()
    seen: set[str] = set()
    for runtime in runtimes:
        if not isinstance(runtime, str) or runtime != runtime.strip() or not runtime:
            messages.append(error(f"{path} runtime entries must be non-empty strings"))
        elif runtime == UNSPECIFIED_RUNTIME:
            messages.append(error(f"{path} must not declare unspecified; omit runtime metadata instead"))
        elif runtime not in RUNTIME_IDS:
            messages.append(error(f"{path} has unsupported runtime {runtime}; allowed: {', '.join(RUNTIME_IDS)}"))
        elif runtime in seen:
            messages.append(error(f"{path} declares duplicate runtime {runtime}"))
        else:
            seen.add(runtime)
    return messages


def compatibility_object(frontmatter: dict[str, object]) -> dict[str, list[str]]:
    metadata = frontmatter.get("metadata", {})
    if isinstance(metadata, dict) and RUNTIME_METADATA_KEY in metadata:
        value = metadata[RUNTIME_METADATA_KEY]
        runtimes = value.split() if isinstance(value, str) else []
    else:
        compatibility = frontmatter.get("compatibility")
        runtimes = compatibility.get("runtimes") if isinstance(compatibility, dict) else []
    if not isinstance(runtimes, list):
        return {"runtimes": [UNSPECIFIED_RUNTIME]}
    normalized = [runtime for runtime in RUNTIME_IDS if runtime in runtimes]
    return {"runtimes": normalized or [UNSPECIFIED_RUNTIME]}
