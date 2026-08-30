#!/usr/bin/env python3
"""Validate the sanitized 2026-08-12 Sol-Luna benchmark evidence."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from typing import cast
from unittest import mock


SKILL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_DIR.parents[1]
EVIDENCE_PATH = SKILL_DIR / "evals" / "transport-warning-benchmark-2026-08-12.json"
TASK_PATH = SKILL_DIR / "evals" / "transport-warning-benchmark-2026-08-12-task.md"
RATE_CARD_PATH = SKILL_DIR / "references" / "rate-card-2026-08-05.json"
REFERENCE_PATH = SKILL_DIR / "references" / "transport-warning-benchmark-2026-08-12.md"
PUBLISHED_SOURCE = {
    "baseline_commit": "f3a68b17159ccf14b75d1c074380971a93c55901",
    "baseline_tree": "21735b7bb4fd982dc8919269dda9209c5caf3014",
    "implementation_commit": "3aef0df62c7739ae3c568b594f37c7bbcda36117",
    "implementation_tree": "5ed15a2cc66859547c1334e6dc3b708da04d9f53",
}
REPOSITORY_MARKERS = (
    "scripts/validate_skills.py",
    "skills/sol-luna-router/scripts/test_benchmark_evidence.py",
)

SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
WINDOWS_PATH_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")
KNOWN_POSIX_ROOT_RE = re.compile(
    r"(?<![A-Za-z0-9])/(?:Users|home|private|var|tmp|opt|Volumes|mnt|root)(?:/|$)"
)
CONCRETE_LOCAL_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:~[\\/][^\s`<>\"']+|"
    r"/(?:Users|home|private|var|tmp|opt|Volumes|mnt|root)/[^\s`<>\"']+|"
    r"/[A-Za-z0-9_.-]+/(?:[^\s`<>\"']+/)+[^\s`<>\"']+|"
    r"[A-Za-z]:[\\/](?:Users|home|private|var|tmp|opt|Volumes|mnt|root)[\\/][^\s`<>\"']+)"
)
AUTH_MATERIAL_RE = re.compile(
    r"(?ix)(?:"
    r"(?:authorization\s*:\s*)?bearer\s+[A-Za-z0-9._~+/=-]{20,}|"
    r"(?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|password|secret|credential)"
    r"\s*[:=]\s*[^\s`<>\"']{8,}|"
    r"(?:sk|pk)-[A-Za-z0-9_-]{16,}|"
    r"-----BEGIN\s+(?:RSA\s+|EC\s+|OPENSSH\s+)?PRIVATE\s+KEY-----"
    r")"
)
UUID_RE = re.compile(
    r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
)
RAW_EXECUTION_MARKER_RE = re.compile(
    r"(?ix)(?:"
    r"[\"']?(?:session|thread|run)[_-]id[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9][A-Za-z0-9_-]{7,}"
    r"|(?:session|thread|run)[_-]id\s*=\s*[^\s]+"
    r"|(?:session_meta|thread_meta|run_meta)\b"
    r")"
)
RAW_TRANSCRIPT_MARKER_RE = re.compile(
    r"(?ix)(?:"
    r"(?:begin|end|start|stop)\s+(?:raw\s+)?transcript"
    r"|(?:raw\s+)?transcript\s*(?:\[|\{|:|=)"
    r"|<\/?(?:session|transcript)(?:\s|>)"
    r")"
)
SENSITIVE_KEY_PARTS = (
    "username",
    "user_name",
    "session",
    "thread",
    "run_id",
    "prompt",
    "response",
    "transcript",
    "credential",
    "password",
    "secret",
    "api_key",
    "access_token",
    "refresh_token",
    "private_key",
    "ledger",
    "cwd",
    "absolute_path",
    "local_path",
    "machine_path",
)


class EvidenceValidationError(ValueError):
    """Raised when the checked-in benchmark evidence drifts or is unsafe."""


def _reject_constant(value: str) -> None:
    raise EvidenceValidationError(f"non-finite JSON number: {value}")


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> dict[str, object]:
    try:
        raw = path.read_text(encoding="utf-8")
        loaded = json.loads(
            raw,
            object_pairs_hook=_unique_pairs,
            parse_constant=_reject_constant,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceValidationError(f"unable to load {path.name}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise EvidenceValidationError(f"{path.name} must contain a JSON object")
    return cast(dict[str, object], loaded)


def _mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise EvidenceValidationError(f"{context} must be an object")
    if not all(isinstance(key, str) for key in value):
        raise EvidenceValidationError(f"{context} has a non-string key")
    return cast(dict[str, object], value)


def _sequence(value: object, context: str) -> list[object]:
    if not isinstance(value, list):
        raise EvidenceValidationError(f"{context} must be an array")
    return value


def _keys(
    value: dict[str, object],
    expected: set[str],
    context: str,
    *,
    optional: set[str] | None = None,
) -> None:
    allowed = expected | (optional or set())
    actual = set(value)
    missing = expected - actual
    extra = actual - allowed
    if missing or extra:
        raise EvidenceValidationError(
            f"{context} keys drifted; missing={sorted(missing)}, extra={sorted(extra)}"
        )


def _equal(actual: object, expected: object, context: str) -> None:
    if actual != expected:
        raise EvidenceValidationError(f"{context}: expected {expected!r}, got {actual!r}")


def _integer(value: object, context: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise EvidenceValidationError(f"{context} must be a non-negative integer")
    return value


def _decimal(value: object, context: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise EvidenceValidationError(f"{context} must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise EvidenceValidationError(f"{context} must be numeric") from exc
    if not result.is_finite() or result < 0:
        raise EvidenceValidationError(f"{context} must be finite and non-negative")
    return result


def _string(value: object, context: str) -> str:
    if not isinstance(value, str):
        raise EvidenceValidationError(f"{context} must be a string")
    return value


def _check_hash(value: object, pattern: re.Pattern[str], context: str) -> None:
    candidate = _string(value, context)
    if pattern.fullmatch(candidate) is None:
        raise EvidenceValidationError(f"{context} is not a lowercase hexadecimal hash")


def _read_utf8(path: Path, context: str) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise EvidenceValidationError(f"unable to read {context}: {exc}") from exc


def _check_markdown_privacy_text(text: str, context: str) -> None:
    """Reject concrete leaks while allowing generic privacy documentation."""
    checks = (
        (CONCRETE_LOCAL_PATH_RE, "absolute local path"),
        (AUTH_MATERIAL_RE, "auth or credential material"),
        (UUID_RE, "UUID-like execution id"),
        (RAW_EXECUTION_MARKER_RE, "raw execution/session marker"),
        (RAW_TRANSCRIPT_MARKER_RE, "raw transcript marker"),
    )
    for pattern, label in checks:
        if pattern.search(text) is not None:
            raise EvidenceValidationError(f"{label} in {context}")


def _check_markdown_privacy(path: Path) -> None:
    _check_markdown_privacy_text(_read_utf8(path, path.name), path.name)


def _check_privacy(value: object, context: str = "evidence") -> None:
    """Reject sensitive field names and absolute machine-local paths."""
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = _string(key, f"{context} key")
            normalized = re.sub(r"[^a-z0-9]+", "_", key_text.lower()).strip("_")
            if any(part in normalized for part in SENSITIVE_KEY_PARTS):
                raise EvidenceValidationError(f"privacy-sensitive key: {context}.{key_text}")
            _check_privacy(child, f"{context}.{key_text}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _check_privacy(child, f"{context}[{index}]")
        return
    if isinstance(value, str):
        stripped = value.strip()
        if (
            (stripped.startswith("/") and not stripped.startswith("//"))
            or WINDOWS_PATH_RE.search(value) is not None
            or KNOWN_POSIX_ROOT_RE.search(value) is not None
            or CONCRETE_LOCAL_PATH_RE.search(value) is not None
        ):
            raise EvidenceValidationError(f"absolute local path: {context}")
        for pattern, label in (
            (AUTH_MATERIAL_RE, "auth or credential material"),
            (UUID_RE, "UUID-like execution id"),
            (RAW_EXECUTION_MARKER_RE, "raw execution/session marker"),
            (RAW_TRANSCRIPT_MARKER_RE, "raw transcript marker"),
        ):
            if pattern.search(value) is not None:
                raise EvidenceValidationError(f"{label}: {context}")


def _git_output(*args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "--no-replace-objects", "-C", str(REPO_ROOT), *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise EvidenceValidationError(f"unable to run git: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown git error"
        raise EvidenceValidationError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout.strip()


def _repository_git_context_available() -> bool:
    return shutil.which("git") is not None and all(
        (REPO_ROOT / marker).is_file() for marker in REPOSITORY_MARKERS
    )


def _check_published_source_metadata(value: object) -> dict[str, object]:
    source = _mapping(value, "published_source")
    _keys(
        source,
        {"baseline_commit", "baseline_tree", "implementation_commit", "implementation_tree"},
        "published_source",
    )
    for name in ("baseline_commit", "baseline_tree", "implementation_commit", "implementation_tree"):
        _check_hash(source[name], SHA1_RE, f"published_source.{name}")
        _equal(
            source[name],
            PUBLISHED_SOURCE[name],
            f"published source {name.replace('_', ' ')} (published_source.{name})",
        )
    return source


def _check_published_source(value: object, implementation_paths: list[object]) -> None:
    source = _check_published_source_metadata(value)
    if not _repository_git_context_available():
        raise EvidenceValidationError(
            "published-source provenance requires a Git checkout"
        )

    baseline_commit = _string(source["baseline_commit"], "published_source.baseline_commit")
    implementation_commit = _string(
        source["implementation_commit"], "published_source.implementation_commit"
    )
    _equal(
        _git_output("show", "-s", "--format=%T", baseline_commit),
        source["baseline_tree"],
        "published source baseline tree",
    )
    _equal(
        _git_output("show", "-s", "--format=%T", implementation_commit),
        source["implementation_tree"],
        "published source implementation tree",
    )
    _equal(
        _git_output("show", "-s", "--format=%P", implementation_commit).split(),
        [baseline_commit],
        "published source implementation parent",
    )
    _equal(
        _git_output("diff", "--name-only", baseline_commit, implementation_commit, "--").splitlines(),
        implementation_paths,
        "published source changed paths",
    )


def _check_rate_card(card: dict[str, object]) -> None:
    _keys(
        card,
        {"schema_version", "id", "as_of", "label", "not_current_pricing", "units", "model_mapping", "rates"},
        "rate card",
    )
    _equal(card["schema_version"], 1, "rate card schema_version")
    _equal(card["id"], "sol-luna-credits-2026-08-05", "rate card id")
    _equal(card["as_of"], "2026-08-05", "rate card as_of")
    _equal(card["label"], "historical benchmark estimate", "rate card label")
    _equal(card["not_current_pricing"], True, "rate card not_current_pricing")

    units = _mapping(card["units"], "rate card units")
    _keys(units, {"currency", "token_basis"}, "rate card units")
    _equal(units["currency"], "credits", "rate card currency")
    _equal(units["token_basis"], "per_1m_tokens", "rate card token basis")

    model_mapping = _mapping(card["model_mapping"], "rate card model_mapping")
    _keys(model_mapping, {"sol", "luna"}, "rate card model_mapping")
    _equal(model_mapping["sol"], "gpt-5.6-sol", "rate card Sol model")
    _equal(model_mapping["luna"], "gpt-5.6-luna", "rate card Luna model")

    rates = _mapping(card["rates"], "rate card rates")
    _keys(rates, {"gpt-5.6-sol", "gpt-5.6-luna"}, "rate card rates")
    expected_rates = {
        "gpt-5.6-sol": {"uncached_input": 125, "cached_input": 12.5, "output": 750},
        "gpt-5.6-luna": {"uncached_input": 5, "cached_input": 0.5, "output": 30},
    }
    for model, expected in expected_rates.items():
        model_rates = _mapping(rates[model], f"rate card rates.{model}")
        _keys(model_rates, set(expected), f"rate card rates.{model}")
        for name, rate in expected.items():
            _equal(model_rates[name], rate, f"rate card rates.{model}.{name}")


def _stage_credits(stage: dict[str, object], card: dict[str, object]) -> Decimal:
    model = _string(stage["model"], "stage model")
    rates = _mapping(_mapping(card["rates"], "rate card rates")[model], f"rates.{model}")
    usage = _mapping(stage["usage"], f"{model} usage")
    uncached = _integer(usage["uncached_input_tokens"], f"{model} uncached input")
    cached = _integer(usage["cached_input_tokens"], f"{model} cached input")
    output = _integer(usage["output_tokens"], f"{model} output")
    return (
        Decimal(uncached) * _decimal(rates["uncached_input"], f"rates.{model}.uncached_input")
        + Decimal(cached) * _decimal(rates["cached_input"], f"rates.{model}.cached_input")
        + Decimal(output) * _decimal(rates["output"], f"rates.{model}.output")
    ) / Decimal(1_000_000)


def _check_usage(stage: dict[str, object], expected: dict[str, int], context: str) -> None:
    usage = _mapping(stage["usage"], f"{context}.usage")
    _keys(
        usage,
        {"input_tokens", "cached_input_tokens", "uncached_input_tokens", "output_tokens", "reasoning_output_tokens"},
        f"{context}.usage",
    )
    for name, expected_value in expected.items():
        _equal(_integer(usage[name], f"{context}.usage.{name}"), expected_value, f"{context}.usage.{name}")
    input_tokens = _integer(usage["input_tokens"], f"{context}.usage.input_tokens")
    cached_tokens = _integer(usage["cached_input_tokens"], f"{context}.usage.cached_input_tokens")
    uncached_tokens = _integer(usage["uncached_input_tokens"], f"{context}.usage.uncached_input_tokens")
    if cached_tokens > input_tokens:
        raise EvidenceValidationError(f"{context}: cached input exceeds input")
    _equal(uncached_tokens, input_tokens - cached_tokens, f"{context}.usage uncached recomputation")
    if _integer(usage["reasoning_output_tokens"], f"{context}.usage.reasoning_output_tokens") > _integer(
        usage["output_tokens"], f"{context}.usage.output_tokens"
    ):
        raise EvidenceValidationError(f"{context}: reasoning output exceeds output")


def _check_test_gate(value: object, context: str, expected_passed: int, expected_total: int) -> None:
    gate = _mapping(value, context)
    _keys(gate, {"passed", "total"}, context)
    _equal(_integer(gate["passed"], f"{context}.passed"), expected_passed, f"{context}.passed")
    _equal(_integer(gate["total"], f"{context}.total"), expected_total, f"{context}.total")
    if _integer(gate["passed"], f"{context}.passed") != _integer(gate["total"], f"{context}.total"):
        raise EvidenceValidationError(f"{context}: quality gate is incomplete")


def _check_comparator_arithmetic(
    comparator: dict[str, object], measured: dict[str, object], context: str
) -> None:
    if "arithmetic" not in comparator:
        return
    arithmetic = _mapping(comparator["arithmetic"], f"{context}.arithmetic")
    _keys(
        arithmetic,
        {"credit_delta_vs_measured_total", "duration_delta_vs_measured_total_seconds"},
        f"{context}.arithmetic",
    )
    expected_credit_delta = _decimal(comparator["estimated_credits"], f"{context}.estimated_credits") - _decimal(
        measured["estimated_credits"], "measured estimated_credits"
    )
    expected_duration_delta = _decimal(comparator["duration_seconds"], f"{context}.duration_seconds") - _decimal(
        measured["duration_seconds"], "measured duration_seconds"
    )
    _equal(
        _decimal(arithmetic["credit_delta_vs_measured_total"], f"{context}.arithmetic credit delta"),
        expected_credit_delta,
        f"{context}.arithmetic credit delta",
    )
    _equal(
        _decimal(
            arithmetic["duration_delta_vs_measured_total_seconds"],
            f"{context}.arithmetic duration delta",
        ),
        expected_duration_delta,
        f"{context}.arithmetic duration delta",
    )


def validate_evidence(
    evidence_path: Path = EVIDENCE_PATH,
    rate_card_path: Path = RATE_CARD_PATH,
    task_path: Path = TASK_PATH,
    reference_path: Path = REFERENCE_PATH,
    include_repository_provenance: bool = True,
) -> None:
    evidence = _load_json(evidence_path)
    rate_card = _load_json(rate_card_path)
    _check_privacy(evidence)
    _check_rate_card(rate_card)
    _check_markdown_privacy(task_path)
    _check_markdown_privacy(reference_path)

    _keys(
        evidence,
        {"schema_version", "benchmark", "provenance", "scope", "invalid_attempts", "quality", "historical_comparators", "claim_boundaries"},
        "evidence",
    )
    _equal(evidence["schema_version"], 1, "evidence schema_version")

    benchmark = _mapping(evidence["benchmark"], "benchmark")
    _keys(benchmark, {"id", "date", "rate_card", "rate_card_status", "implementation_paths"}, "benchmark")
    _equal(benchmark["id"], "luna-max-transport-warning-2026-08-12", "benchmark id")
    _equal(benchmark["date"], "2026-08-12", "benchmark date")
    _equal(benchmark["rate_card"], "references/rate-card-2026-08-05.json", "benchmark rate_card")
    _equal(benchmark["rate_card_status"], "historical estimate; not current pricing", "benchmark rate_card_status")
    paths = _sequence(benchmark["implementation_paths"], "benchmark implementation_paths")
    _equal(
        paths,
        [
            "skills/sol-luna-router/SKILL.md",
            "skills/sol-luna-router/scripts/run_luna_worker.py",
            "skills/sol-luna-router/scripts/test_run_luna_worker.py",
        ],
        "benchmark implementation_paths",
    )

    provenance = _mapping(evidence["provenance"], "provenance")
    _keys(
        provenance,
        {
            "published_source",
            "isolated_snapshot",
            "task_artifact_sha256",
            "held_out_evaluator_sha256",
            "held_out_evaluator_source_included",
        },
        "provenance",
    )
    if include_repository_provenance:
        _check_published_source(provenance["published_source"], paths)
    else:
        _check_published_source_metadata(provenance["published_source"])
    isolated = _mapping(provenance["isolated_snapshot"], "isolated_snapshot")
    _keys(isolated, {"baseline_commit", "baseline_tree", "git_objects_included"}, "isolated_snapshot")
    _equal(isolated["baseline_commit"], "bc9e6fb2dfa7e035a1dabcce0d347a1c121b1237", "isolated baseline commit")
    _equal(isolated["baseline_tree"], "80a082fa823225fd9d50ac60f2d74d9757242b13", "isolated baseline tree")
    _check_hash(isolated["baseline_commit"], SHA1_RE, "isolated baseline commit")
    _check_hash(isolated["baseline_tree"], SHA1_RE, "isolated baseline tree")
    _equal(isolated["git_objects_included"], False, "isolated Git object inclusion")
    _equal(provenance["task_artifact_sha256"], "9f18469a288f95bde73705c307051e8be051619904674cfd8c9403585b57a903", "task artifact SHA-256")
    _equal(provenance["held_out_evaluator_sha256"], "837ffa015b88d70d9f591711e61e81226ee0aad64debd7cb2c8326808c52dd9c", "held-out evaluator SHA-256")
    _check_hash(provenance["task_artifact_sha256"], SHA256_RE, "task artifact SHA-256")
    actual_task_hash = hashlib.sha256(task_path.read_bytes()).hexdigest()
    _equal(actual_task_hash, provenance["task_artifact_sha256"], "task artifact SHA-256")
    _check_hash(provenance["held_out_evaluator_sha256"], SHA256_RE, "held-out evaluator SHA-256")
    _equal(provenance["held_out_evaluator_source_included"], False, "held-out evaluator source inclusion")

    scope = _mapping(evidence["scope"], "scope")
    _keys(scope, {"included", "complete_routed_task_cost", "excluded", "stages", "measured_sequential"}, "scope")
    _equal(scope["included"], ["Luna worker", "isolated Sol verification"], "scope included")
    _equal(scope["complete_routed_task_cost"], False, "complete_routed_task_cost")
    _equal(
        scope["excluded"],
        [
            "root-session preflight and dispatch",
            "two invalid nested-CLI transport failures",
            "one invalid read-only verification attempt",
        ],
        "scope exclusions",
    )
    stages = _sequence(scope["stages"], "scope stages")
    if len(stages) != 2:
        raise EvidenceValidationError(f"scope stages: expected 2, got {len(stages)}")
    expected_stages = [
        (
            "luna_worker",
            "gpt-5.6-luna",
            "max",
            Decimal("259.353"),
            Decimal("0.865120"),
            {"input_tokens": 371636, "cached_input_tokens": 302080, "uncached_input_tokens": 69556, "output_tokens": 12210, "reasoning_output_tokens": 7108},
        ),
        (
            "isolated_sol_verifier",
            "gpt-5.6-sol",
            "medium",
            Decimal("38.940"),
            Decimal("1.847600"),
            {"input_tokens": 39922, "cached_input_tokens": 30208, "uncached_input_tokens": 9714, "output_tokens": 341, "reasoning_output_tokens": 38},
        ),
    ]
    total_duration = Decimal(0)
    total_credits = Decimal(0)
    for index, (stage_value, expected) in enumerate(zip(stages, expected_stages, strict=True)):
        context = f"scope stages[{index}]"
        stage = _mapping(stage_value, context)
        _keys(stage, {"name", "model", "reasoning_effort", "duration_seconds", "usage", "estimated_credits"}, context)
        name, model, effort, duration, credits, usage = expected
        _equal(stage["name"], name, f"{context}.name")
        _equal(stage["model"], model, f"{context}.model")
        _equal(stage["reasoning_effort"], effort, f"{context}.reasoning_effort")
        _equal(_decimal(stage["duration_seconds"], f"{context}.duration_seconds"), duration, f"{context}.duration_seconds")
        _check_usage(stage, usage, context)
        computed_credits = _stage_credits(stage, rate_card)
        _equal(computed_credits, credits, f"{context} recomputed credits")
        _equal(_decimal(stage["estimated_credits"], f"{context}.estimated_credits"), credits, f"{context}.estimated_credits")
        total_duration += duration
        total_credits += credits

    measured = _mapping(scope["measured_sequential"], "measured_sequential")
    _keys(measured, {"duration_seconds", "estimated_credits"}, "measured_sequential")
    _equal(_decimal(measured["duration_seconds"], "measured duration_seconds"), Decimal("298.293"), "measured duration_seconds")
    _equal(_decimal(measured["estimated_credits"], "measured estimated_credits"), Decimal("2.712720"), "measured estimated_credits")
    _equal(total_duration, _decimal(measured["duration_seconds"], "measured duration_seconds"), "stage duration sum")
    _equal(total_credits, _decimal(measured["estimated_credits"], "measured estimated_credits"), "stage credit sum")

    invalid = _mapping(evidence["invalid_attempts"], "invalid_attempts")
    _keys(invalid, {"total", "classes"}, "invalid_attempts")
    _equal(_integer(invalid["total"], "invalid_attempts.total"), 3, "invalid_attempts.total")
    classes = _mapping(invalid["classes"], "invalid_attempts.classes")
    _keys(classes, {"nested_cli_transport_failure", "read_only_verification_attempt"}, "invalid_attempts.classes")
    _equal(_integer(classes["nested_cli_transport_failure"], "nested CLI failures"), 2, "nested CLI failure count")
    _equal(_integer(classes["read_only_verification_attempt"], "read-only attempts"), 1, "read-only attempt count")
    _equal(sum(_integer(value, f"invalid_attempts.classes.{key}") for key, value in classes.items()), 3, "invalid attempt class sum")

    quality = _mapping(evidence["quality"], "quality")
    _keys(quality, {"worker_tests", "held_out_tests", "python_compile", "git_diff_check", "scope_violations", "correction_cycles"}, "quality")
    _check_test_gate(quality["worker_tests"], "worker_tests", 10, 10)
    _check_test_gate(quality["held_out_tests"], "held_out_tests", 4, 4)
    _equal(quality["python_compile"], "pass", "python_compile")
    _equal(quality["git_diff_check"], "pass", "git_diff_check")
    _equal(_integer(quality["scope_violations"], "scope_violations"), 0, "scope_violations")
    _equal(_integer(quality["correction_cycles"], "correction_cycles"), 0, "correction_cycles")

    comparators = _sequence(evidence["historical_comparators"], "historical_comparators")
    if len(comparators) != 2:
        raise EvidenceValidationError(f"historical_comparators: expected 2, got {len(comparators)}")
    expected_comparators = [
        ("sol_only_2026-08-05", "Sol-only", Decimal("12.766250"), Decimal("147.01")),
        ("thin_sol_luna_high_2026-08-05", "thin Sol+Luna High", Decimal("4.534795"), Decimal("132.29")),
    ]
    for index, (value, expected) in enumerate(zip(comparators, expected_comparators, strict=True)):
        context = f"historical_comparators[{index}]"
        comparator = _mapping(value, context)
        _keys(
            comparator,
            {"name", "label", "variant", "date", "isolated_baseline_tree", "estimated_credits", "duration_seconds", "held_out_tests", "claim_boundary"},
            context,
            optional={"arithmetic"},
        )
        name, variant, credits, duration = expected
        _equal(comparator["name"], name, f"{context}.name")
        _equal(comparator["label"], "historical comparator; not current pricing", f"{context}.label")
        _equal(comparator["variant"], variant, f"{context}.variant")
        _equal(comparator["date"], "2026-08-05", f"{context}.date")
        _equal(comparator["isolated_baseline_tree"], "80a082fa823225fd9d50ac60f2d74d9757242b13", f"{context}.isolated_baseline_tree")
        _check_hash(comparator["isolated_baseline_tree"], SHA1_RE, f"{context}.isolated_baseline_tree")
        _equal(_decimal(comparator["estimated_credits"], f"{context}.estimated_credits"), credits, f"{context}.estimated_credits")
        _equal(_decimal(comparator["duration_seconds"], f"{context}.duration_seconds"), duration, f"{context}.duration_seconds")
        _check_test_gate(comparator["held_out_tests"], f"{context}.held_out_tests", 4, 4)
        _equal(
            comparator["claim_boundary"],
            "Historical comparator only; not proof that the scoped Max two-stage cost is a complete end-to-end result.",
            f"{context}.claim_boundary",
        )
        _check_comparator_arithmetic(comparator, measured, context)

    boundaries = _sequence(evidence["claim_boundaries"], "claim_boundaries")
    expected_boundaries = [
        "Measured scope is the Luna worker plus isolated Sol verification; complete_routed_task_cost is false.",
        "Root-session preflight and dispatch, two invalid nested-CLI transport failures, and one invalid read-only verification attempt are excluded from the measured sequential stages.",
        "Credits use references/rate-card-2026-08-05.json as a historical estimate, not current pricing.",
        "The held-out evaluator is represented only by its SHA-256; its source and contents are not included.",
        "The isolated snapshot commit and tree are historical run identifiers whose Git objects are not included; published_source is the repository-verifiable implementation provenance.",
        "The validator checks record integrity, arithmetic, published code provenance, and privacy; excluded raw ledgers and held-out evaluator contents prevent independent replay of the historical usage and quality results.",
        "The listed implementation paths are benchmark result metadata, not current PR changed files.",
        "The 2026-08-05 comparators are historical controlled comparators and do not establish global optimality or prove the scoped Max two-stage cost is a complete end-to-end result.",
    ]
    _equal(boundaries, expected_boundaries, "claim_boundaries")


class BenchmarkEvidenceTests(unittest.TestCase):
    def test_package_evidence_is_valid(self) -> None:
        validate_evidence(include_repository_provenance=False)

    def test_standalone_package_validation_does_not_invoke_git_provenance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="benchmark-evidence-standalone-") as directory:
            with (
                mock.patch.object(sys.modules[__name__], "REPO_ROOT", Path(directory)),
                mock.patch.object(
                    sys.modules[__name__],
                    "_git_output",
                    side_effect=AssertionError("Git provenance must be skipped"),
                ),
            ):
                validate_evidence(include_repository_provenance=False)

    @unittest.skipUnless(shutil.which("git"), "Git executable is required for this fixture")
    def test_unrelated_consumer_git_checkout_is_not_repository_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="benchmark-evidence-consumer-") as directory:
            consumer_root = Path(directory)
            subprocess.run(
                ["git", "init", "-q", str(consumer_root)],
                check=True,
                capture_output=True,
                text=True,
            )
            with mock.patch.object(sys.modules[__name__], "REPO_ROOT", consumer_root):
                self.assertFalse(_repository_git_context_available())

    @unittest.skipUnless(shutil.which("git"), "Git executable is required for this fixture")
    def test_shallow_spellbook_checkout_does_not_skip_provenance(self) -> None:
        evidence = _load_json(EVIDENCE_PATH)
        provenance = _mapping(evidence["provenance"], "provenance")
        with tempfile.TemporaryDirectory(prefix="benchmark-evidence-shallow-") as directory:
            checkout = Path(directory)
            marker_paths = (
                checkout / "scripts" / "validate_skills.py",
                checkout
                / "skills"
                / "sol-luna-router"
                / "scripts"
                / "test_benchmark_evidence.py",
            )
            for marker in marker_paths:
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.write_text("# repository marker\n", encoding="utf-8")
            subprocess.run(
                ["git", "init", "-q", str(checkout)],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "-C", str(checkout), "add", *(str(path) for path in marker_paths)],
                check=True,
                capture_output=True,
                text=True,
            )
            with mock.patch.object(sys.modules[__name__], "REPO_ROOT", checkout):
                self.assertTrue(_repository_git_context_available())
                with self.assertRaisesRegex(EvidenceValidationError, "git show"):
                    _check_published_source(provenance["published_source"], [])

    def test_source_checkout_detection_does_not_run_git(self) -> None:
        with tempfile.TemporaryDirectory(prefix="benchmark-evidence-owned-") as directory:
            checkout = Path(directory)
            for marker in REPOSITORY_MARKERS:
                path = checkout / marker
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# repository marker\n", encoding="utf-8")
            with (
                mock.patch.object(sys.modules[__name__], "REPO_ROOT", checkout),
                mock.patch.object(shutil, "which", return_value="/usr/bin/git"),
                mock.patch.object(
                    subprocess,
                    "run",
                    side_effect=AssertionError("source detection must not invoke Git"),
                ),
            ):
                self.assertTrue(_repository_git_context_available())

    def test_standalone_validation_rejects_arbitrary_published_source_hashes(self) -> None:
        evidence = _load_json(EVIDENCE_PATH)
        provenance = _mapping(evidence["provenance"], "provenance")
        source = _mapping(provenance["published_source"], "published_source")
        source["baseline_commit"] = "0" * 40
        with tempfile.TemporaryDirectory(prefix="benchmark-evidence-test-") as directory:
            drifted_evidence = Path(directory) / EVIDENCE_PATH.name
            drifted_evidence.write_text(json.dumps(evidence), encoding="utf-8")
            with self.assertRaisesRegex(
                EvidenceValidationError,
                "published_source.baseline_commit",
            ):
                validate_evidence(
                    evidence_path=drifted_evidence,
                    include_repository_provenance=False,
                )

    @unittest.skipUnless(
        _repository_git_context_available(),
        "published-source provenance requires the Spellbook Git checkout",
    )
    def test_published_source_check_rejects_missing_git_context(self) -> None:
        evidence = _load_json(EVIDENCE_PATH)
        provenance = _mapping(evidence["provenance"], "provenance")
        with tempfile.TemporaryDirectory(prefix="benchmark-evidence-no-git-") as directory:
            with mock.patch.object(sys.modules[__name__], "REPO_ROOT", Path(directory)):
                with self.assertRaisesRegex(
                    EvidenceValidationError,
                    "published-source provenance requires a Git checkout",
                ):
                    _check_published_source(provenance["published_source"], [])

    def test_task_hash_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="benchmark-evidence-test-") as directory:
            drifted_task = Path(directory) / TASK_PATH.name
            drifted_task.write_bytes(TASK_PATH.read_bytes() + b"\n")
            with self.assertRaisesRegex(EvidenceValidationError, "task artifact SHA-256"):
                validate_evidence(
                    task_path=drifted_task,
                    include_repository_provenance=False,
                )

    def test_markdown_privacy_leaks_are_rejected(self) -> None:
        leaks = (
            ("/Users/example/.codex", "absolute local path"),
            ("Authorization: Bearer " + "A" * 24, "auth or credential material"),
            ("run UUID 00000000-0000-0000-0000-000000000000", "UUID-like execution id"),
            ('"session_id": "abc12345"', "raw execution/session marker"),
            ("BEGIN RAW TRANSCRIPT", "raw transcript marker"),
        )
        with tempfile.TemporaryDirectory(prefix="benchmark-evidence-test-") as directory:
            for index, (content, message) in enumerate(leaks):
                path = Path(directory) / f"leak-{index}.md"
                path.write_text(content, encoding="utf-8")
                with self.subTest(message=message):
                    with self.assertRaisesRegex(EvidenceValidationError, message):
                        _check_markdown_privacy(path)

    def test_generic_privacy_terms_and_relative_paths_are_allowed(self) -> None:
        _check_markdown_privacy_text(
            "Do not include user names, session/thread/run IDs, credentials, or raw transcripts.\n"
            "Use skills/sol-luna-router/scripts/run_luna_worker.py.\n",
            "generic markdown fixture",
        )
        _check_privacy(
            {
                "note": "Credentials and raw transcripts are excluded.",
                "path": "skills/sol-luna-router/scripts/run_luna_worker.py",
            }
        )

    def test_json_string_privacy_leaks_are_rejected(self) -> None:
        leaks = (
            ("artifact at /custom/project/private/file.json", "absolute local path"),
            ("Authorization: Bearer " + "A" * 24, "auth or credential material"),
            ("run UUID 00000000-0000-0000-0000-000000000000", "UUID-like execution id"),
            ('"session_id": "abc12345"', "raw execution/session marker"),
            ("BEGIN RAW TRANSCRIPT", "raw transcript marker"),
        )
        for content, message in leaks:
            with self.subTest(message=message):
                with self.assertRaisesRegex(EvidenceValidationError, message):
                    _check_privacy({"note": content})

    @unittest.skipUnless(
        _repository_git_context_available(),
        "published-source provenance requires the Spellbook Git checkout",
    )
    def test_published_source_provenance_is_valid(self) -> None:
        validate_evidence()

    @unittest.skipUnless(
        _repository_git_context_available(),
        "published-source provenance requires the Spellbook Git checkout",
    )
    def test_published_source_tree_drift_is_rejected(self) -> None:
        evidence = _load_json(EVIDENCE_PATH)
        provenance = _mapping(evidence["provenance"], "provenance")
        source = _mapping(provenance["published_source"], "published_source")
        def drifted_git_output(*args: str) -> str:
            if args == ("show", "-s", "--format=%T", PUBLISHED_SOURCE["baseline_commit"]):
                return PUBLISHED_SOURCE["baseline_tree"]
            if args == ("show", "-s", "--format=%T", PUBLISHED_SOURCE["implementation_commit"]):
                return "0" * 40
            raise AssertionError(f"unexpected Git command: {args}")

        with mock.patch.object(
            sys.modules[__name__], "_git_output", side_effect=drifted_git_output
        ):
            with self.assertRaisesRegex(EvidenceValidationError, "published source implementation tree"):
                _check_published_source(source, [])

    def test_privacy_sensitive_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(EvidenceValidationError, "privacy-sensitive key"):
            _check_privacy({"thread_id": "not included"})

    def test_absolute_local_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(EvidenceValidationError, "absolute local path"):
            _check_privacy({"path": "/" + "Users/example/private-file"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
