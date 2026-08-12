#!/usr/bin/env python3
"""Summarize Luna run telemetry into reliability, quality, and efficiency evidence."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
import sys

from run_luna_worker import default_run_log_path


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _integer(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _number(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
        return float(value)
    return None


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * percentile + 0.5)))
    return round(ordered[index], 3)


def read_records(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    records: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"{path}:{line_number}: invalid JSONL: {error.msg}"
                ) from error
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: record must be an object")
            records.append(record)
    return records


def summarize(path: Path) -> dict[str, object]:
    records = read_records(path)
    runs: dict[str, dict[str, object]] = {}
    latest_evaluations: dict[str, dict[str, object]] = {}
    evaluation_overwrites = 0
    orphan_evaluations = 0

    for record in records:
        record_type = record.get("record_type", "run")
        run_id = record.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            continue
        if record_type == "run":
            runs[run_id] = record
        elif record_type == "evaluation":
            if run_id in latest_evaluations:
                evaluation_overwrites += 1
            latest_evaluations[run_id] = record

    for run_id in latest_evaluations:
        if run_id not in runs:
            orphan_evaluations += 1

    run_values = list(runs.values())
    successful = [record for record in run_values if record.get("status") == "success"]
    failed = [record for record in run_values if record.get("status") == "failed"]
    evaluated = {
        run_id: evaluation
        for run_id, evaluation in latest_evaluations.items()
        if run_id in runs
    }
    evaluated_successes = {
        run_id: evaluation
        for run_id, evaluation in evaluated.items()
        if runs[run_id].get("status") == "success"
    }
    verified = {
        run_id: evaluation
        for run_id, evaluation in evaluated_successes.items()
        if evaluation.get("outcome") == "verified"
    }
    verified_with_checks = {
        run_id: evaluation
        for run_id, evaluation in verified.items()
        if _integer(evaluation.get("checks_passed")) > 0
        and _integer(evaluation.get("checks_failed")) == 0
    }
    initial_evaluated = {
        run_id: evaluation
        for run_id, evaluation in evaluated_successes.items()
        if runs[run_id].get("command") == "run"
    }
    first_pass_verified = {
        run_id: evaluation
        for run_id, evaluation in initial_evaluated.items()
        if evaluation.get("outcome") == "verified"
    }

    outcomes = Counter(
        str(evaluation.get("outcome"))
        for evaluation in evaluated.values()
        if isinstance(evaluation.get("outcome"), str)
    )
    failures = Counter(
        str(record.get("failure_code"))
        for record in failed
        if isinstance(record.get("failure_code"), str)
    )
    usage_totals: Counter[str] = Counter()
    for record in successful:
        usage = record.get("usage")
        if not isinstance(usage, dict):
            continue
        for name, value in usage.items():
            if isinstance(name, str):
                usage_totals[name] += _integer(value)

    durations = [
        duration
        for record in run_values
        if (duration := _number(record.get("duration_seconds"))) is not None
    ]
    checks_passed = sum(_integer(evaluation.get("checks_passed")) for evaluation in evaluated.values())
    checks_failed = sum(_integer(evaluation.get("checks_failed")) for evaluation in evaluated.values())
    warning_runs = sum(_integer(record.get("warning_count")) > 0 for record in successful)

    return {
        "schema_version": 1,
        "source": str(path),
        "source_exists": path.is_file(),
        "records_total": len(records),
        "runs_total": len(run_values),
        "reliability": {
            "successful_runs": len(successful),
            "failed_runs": len(failed),
            "success_rate": _ratio(len(successful), len(run_values)),
            "warning_runs": warning_runs,
            "failure_codes": dict(sorted(failures.items())),
        },
        "quality": {
            "evaluated_runs": len(evaluated),
            "evaluation_coverage": _ratio(len(evaluated), len(run_values)),
            "evaluated_successful_runs": len(evaluated_successes),
            "successful_evaluation_coverage": _ratio(
                len(evaluated_successes), len(successful)
            ),
            "verified_runs": len(verified),
            "verified_rate_among_evaluated_successes": _ratio(
                len(verified), len(evaluated_successes)
            ),
            "verified_with_check_evidence": len(verified_with_checks),
            "verified_check_evidence_coverage": _ratio(
                len(verified_with_checks), len(verified)
            ),
            "initial_runs_evaluated": len(initial_evaluated),
            "first_pass_verified_runs": len(first_pass_verified),
            "first_pass_verified_rate": _ratio(
                len(first_pass_verified), len(initial_evaluated)
            ),
            "outcomes": dict(sorted(outcomes.items())),
            "checks_passed": checks_passed,
            "checks_failed": checks_failed,
        },
        "efficiency": {
            "token_scope": "luna_worker_only",
            "resume_runs": sum(record.get("command") == "resume" for record in run_values),
            "token_totals": dict(sorted(usage_totals.items())),
            "average_input_tokens_per_success": (
                round(usage_totals.get("input_tokens", 0) / len(successful), 2)
                if successful
                else None
            ),
            "average_output_tokens_per_success": (
                round(usage_totals.get("output_tokens", 0) / len(successful), 2)
                if successful
                else None
            ),
            "median_duration_seconds": (
                round(statistics.median(durations), 3) if durations else None
            ),
            "p95_duration_seconds": _percentile(durations, 0.95),
        },
        "integrity": {
            "evaluation_overwrites": evaluation_overwrites,
            "orphan_evaluations": orphan_evaluations,
        },
        "claim_boundary": (
            "observational evidence only; compare similar task cohorts or controlled benchmarks "
            "before claiming causal improvement"
        ),
    }


def to_text(summary: dict[str, object]) -> str:
    reliability = summary["reliability"]
    quality = summary["quality"]
    efficiency = summary["efficiency"]
    assert isinstance(reliability, dict)
    assert isinstance(quality, dict)
    assert isinstance(efficiency, dict)
    return "\n".join(
        [
            "Sol-Luna evidence summary",
            f"runs: {summary['runs_total']}",
            f"success_rate: {reliability['success_rate']}",
            f"evaluated_runs: {quality['evaluated_runs']}",
            f"evaluation_coverage: {quality['evaluation_coverage']}",
            f"verified_rate_among_evaluated_successes: {quality['verified_rate_among_evaluated_successes']}",
            f"first_pass_verified_rate: {quality['first_pass_verified_rate']}",
            f"verified_check_evidence_coverage: {quality['verified_check_evidence_coverage']}",
            f"resume_runs: {efficiency['resume_runs']}",
            f"median_duration_seconds: {efficiency['median_duration_seconds']}",
            f"p95_duration_seconds: {efficiency['p95_duration_seconds']}",
            f"claim_boundary: {summary['claim_boundary']}",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-log", type=Path, help="JSONL ledger; defaults to the Luna run log.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    path = args.run_log.expanduser() if args.run_log else default_run_log_path()
    if not path.is_absolute():
        print(f"analyze_run_log.py: --run-log must be absolute: {path}", file=sys.stderr)
        return 1
    try:
        summary = summarize(path.resolve())
    except (OSError, ValueError) as error:
        print(f"analyze_run_log.py: {error}", file=sys.stderr)
        return 1
    if args.format == "json":
        json.dump(summary, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(to_text(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
