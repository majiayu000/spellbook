"""Runtime compatibility metadata validation and normalization."""

from __future__ import annotations

from collections.abc import Callable


COMPATIBILITY_KEYS = {"runtimes"}
RUNTIME_IDS = ("claude_code", "codex", "portable")
UNSPECIFIED_RUNTIME = "unspecified"


def validate_compatibility(
    frontmatter: dict[str, object],
    path: str,
    error: Callable[[str], str],
) -> list[str]:
    if "compatibility" not in frontmatter:
        return []
    compatibility = frontmatter["compatibility"]
    if not isinstance(compatibility, dict):
        return [error(f"{path} compatibility must be a YAML mapping")]
    messages: list[str] = []
    unexpected = {str(key) for key in compatibility if key not in COMPATIBILITY_KEYS}
    if unexpected:
        messages.append(error(f"{path} has unsupported compatibility keys: {', '.join(sorted(unexpected))}"))
    runtimes = compatibility.get("runtimes")
    if not isinstance(runtimes, list) or not runtimes:
        return messages + [error(f"{path} compatibility.runtimes must be a non-empty list")]
    seen: set[str] = set()
    for runtime in runtimes:
        if not isinstance(runtime, str) or runtime != runtime.strip() or not runtime:
            messages.append(error(f"{path} compatibility.runtimes entries must be non-empty strings"))
        elif runtime == UNSPECIFIED_RUNTIME:
            messages.append(error(f"{path} must not declare unspecified; omit compatibility metadata instead"))
        elif runtime not in RUNTIME_IDS:
            messages.append(error(f"{path} has unsupported runtime {runtime}; allowed: {', '.join(RUNTIME_IDS)}"))
        elif runtime in seen:
            messages.append(error(f"{path} declares duplicate runtime {runtime}"))
        else:
            seen.add(runtime)
    return messages


def compatibility_object(frontmatter: dict[str, object]) -> dict[str, list[str]]:
    compatibility = frontmatter.get("compatibility")
    if not isinstance(compatibility, dict):
        return {"runtimes": [UNSPECIFIED_RUNTIME]}
    runtimes = compatibility.get("runtimes")
    if not isinstance(runtimes, list):
        return {"runtimes": [UNSPECIFIED_RUNTIME]}
    normalized = [runtime for runtime in RUNTIME_IDS if runtime in runtimes]
    return {"runtimes": normalized or [UNSPECIFIED_RUNTIME]}
