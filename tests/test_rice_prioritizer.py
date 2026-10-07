from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/product-manager-toolkit/scripts/rice_prioritizer.py"
VALID_ROW = {"name": "Valid feature", "reach": "100", "impact": "high", "confidence": "80%", "effort": "m"}


def run_cli(tmp_path: Path, rows: list[dict[str, str]], output: str = "json") -> subprocess.CompletedProcess[str]:
    input_path = tmp_path / "features.csv"
    with input_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(VALID_ROW))
        writer.writeheader()
        writer.writerows(rows)
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(input_path), "--output", output, "--capacity", "1"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


def reject_nonfinite_constant(value: str) -> None:
    raise AssertionError(f"non-standard JSON constant: {value}")


def test_valid_features_keep_scores_order_and_selection(tmp_path: Path) -> None:
    result = run_cli(tmp_path, [VALID_ROW, {**VALID_ROW, "name": "Higher score", "reach": "200"}])

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    payload = json.loads(result.stdout, parse_constant=reject_nonfinite_constant)
    assert [feature["name"] for feature in payload["features"]] == ["Higher score", "Valid feature"]
    assert [feature["rice_score"] for feature in payload["features"]] == [320.0, 160.0]
    assert [feature["selected"] for feature in payload["features"]] == [True, False]
    assert [feature["name"] for feature in payload["roadmap"]] == ["Higher score"]


@pytest.mark.parametrize("output", ["json", "text", "csv"])
@pytest.mark.parametrize("field", ["reach", "impact", "effort"])
@pytest.mark.parametrize("value", ["NaN", "inf", "-inf", "NaN%", "inf%", "-inf%", "1e309"])
def test_nonfinite_inputs_fail_without_partial_output(tmp_path: Path, output: str, field: str, value: str) -> None:
    result = run_cli(tmp_path, [VALID_ROW, {**VALID_ROW, "name": "Invalid feature", field: value}], output)

    assert result.returncode == 1
    assert result.stdout == ""
    assert f"error: {field} must be finite" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("output", ["json", "text", "csv"])
@pytest.mark.parametrize(
    "overrides",
    [
        {"reach": "1e308", "impact": "2"},
        {"reach": "1e308", "impact": "-2"},
        {"reach": "1e308", "impact": "2", "confidence": "0"},
        {"reach": "1e308", "impact": "1", "confidence": "1", "effort": "0.1"},
    ],
)
def test_nonfinite_computed_scores_fail_without_partial_output(
    tmp_path: Path, output: str, overrides: dict[str, str]
) -> None:
    result = run_cli(tmp_path, [VALID_ROW, {**VALID_ROW, "name": "Overflow feature", **overrides}], output)

    assert result.returncode == 1
    assert result.stdout == ""
    assert "error: RICE score must be finite for Overflow feature" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("confidence", ["NaN", "inf", "-inf", "NaN%", "inf%", "-inf%"])
def test_confidence_still_rejects_nonfinite_values(tmp_path: Path, confidence: str) -> None:
    result = run_cli(tmp_path, [{**VALID_ROW, "confidence": confidence}])

    assert result.returncode == 1
    assert result.stdout == ""
    assert "error: confidence must be between" in result.stderr


def test_sample_workflow_remains_unchanged(tmp_path: Path) -> None:
    sample_path = tmp_path / "sample.csv"
    sample = subprocess.run(
        [sys.executable, str(SCRIPT), "sample", "--sample-output", str(sample_path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert sample.returncode == 0, sample.stderr
    with sample_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    result = run_cli(tmp_path, rows)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout, parse_constant=reject_nonfinite_constant)
    assert [feature["name"] for feature in payload["features"]] == [
        "Self-serve onboarding checklist", "CSV import error preview", "Advanced admin analytics"
    ]
    assert [feature["rice_score"] for feature in payload["features"]] == [4800.0, 1900.0, 360.0]
