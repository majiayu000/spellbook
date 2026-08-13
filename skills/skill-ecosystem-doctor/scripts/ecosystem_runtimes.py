"""Resolve which runtimes a governance policy governs.

The supported runtime set and each runtime's home directory live in
``ecosystem_model.RUNTIME_HOME_DIRS``. This module turns that single source of
truth into the two runtime tuples the planner needs, without any second copy of
the runtime list.
"""

from __future__ import annotations

from pathlib import Path

from ecosystem_model import (
    DEFAULT_PROJECTION_RUNTIMES,
    RUNTIME_HOME_DIRS,
    SUPPORTED_RUNTIMES,
)


# runtime_mirrors.<runtime>_only keeps a skill projected into this runtime only.
MIRROR_RUNTIME = "claude"


class RuntimePolicyError(RuntimeError):
    """Raised when a policy names an unsupported or malformed runtime set."""


def parse_runtime_mirrors(policy: dict) -> tuple[Path | None, set[str]]:
    """Authoritative mirror root and the skills pinned to MIRROR_RUNTIME."""
    config = policy.get("runtime_mirrors", {})
    if not isinstance(config, dict):
        raise RuntimePolicyError("runtime_mirrors must be an object")
    names = config.get(f"{MIRROR_RUNTIME}_only", [])
    root = config.get("authoritative_root")
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        raise RuntimePolicyError(
            f"runtime_mirrors.{MIRROR_RUNTIME}_only must be a string array"
        )
    if names and not isinstance(root, str):
        raise RuntimePolicyError("runtime_mirrors.authoritative_root is required")
    return (Path(root).expanduser() if isinstance(root, str) else None, set(names))


def parse_managed_global_sources(policy: dict) -> dict[str, tuple[Path, frozenset[str]]]:
    """Managed global skills mapped to their source path and target runtimes."""
    configured = policy.get("managed_global_sources", {})
    if not isinstance(configured, dict):
        raise RuntimePolicyError("managed_global_sources must be an object")
    result: dict[str, tuple[Path, frozenset[str]]] = {}
    for name, raw in configured.items():
        if not isinstance(name, str) or not isinstance(raw, dict):
            raise RuntimePolicyError("managed_global_sources entries must be objects")
        source = raw.get("source")
        runtimes = raw.get("runtimes")
        if not isinstance(source, str) or not source:
            raise RuntimePolicyError(f"managed global source is missing for {name}")
        if (
            not isinstance(runtimes, list)
            or not runtimes
            or not all(runtime in SUPPORTED_RUNTIMES for runtime in runtimes)
        ):
            raise RuntimePolicyError(f"managed global runtimes are invalid for {name}")
        source_path = Path(source).expanduser()
        if not (source_path / "SKILL.md").is_file():
            raise RuntimePolicyError(f"managed global source is missing: {source_path}")
        result[name] = (source_path, frozenset(runtimes))
    return result


def _canonical_order(names: set[str]) -> tuple[str, ...]:
    return tuple(runtime for runtime in RUNTIME_HOME_DIRS if runtime in names)


def projection_runtimes(policy: dict) -> tuple[str, ...]:
    """Runtimes that automatically receive global and project projections.

    When the policy omits ``projection_runtimes`` this stays at the historical
    codex+claude pair, so existing policy files keep their exact behaviour.
    Naming the field opts a deployment into the wider runtime set.
    """
    configured = policy.get("projection_runtimes")
    if configured is None:
        return DEFAULT_PROJECTION_RUNTIMES
    if (
        not isinstance(configured, list)
        or not all(runtime in SUPPORTED_RUNTIMES for runtime in configured)
    ):
        raise RuntimePolicyError(
            "projection_runtimes must be an array of "
            f"{sorted(SUPPORTED_RUNTIMES)}"
        )
    if len(configured) != len(set(configured)):
        raise RuntimePolicyError("projection_runtimes contains duplicate runtimes")
    return _canonical_order(set(configured))


def governed_runtimes(
    policy_runtimes: tuple[str, ...],
    managed_globals: dict[str, tuple[Path, frozenset[str]]],
) -> tuple[str, ...]:
    """Every runtime the policy touches, in canonical order.

    Stale-link removal sweeps these homes, so a runtime named only by a managed
    global source is still cleaned up when that skill is retired or hidden.
    """
    named = set(policy_runtimes)
    for _, runtimes in managed_globals.values():
        named.update(runtimes)
    return _canonical_order(named)
