#!/usr/bin/env python3
"""Prioritize feature ideas with the RICE framework."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys


IMPACT = {
    "massive": 3.0,
    "high": 2.0,
    "medium": 1.0,
    "low": 0.5,
    "minimal": 0.25,
}

CONFIDENCE = {
    "high": 1.0,
    "medium": 0.8,
    "low": 0.5,
}

EFFORT = {
    "xs": 0.25,
    "s": 0.5,
    "m": 1.0,
    "l": 2.0,
    "xl": 4.0,
}

SAMPLE_ROWS = [
    {
        "name": "Self-serve onboarding checklist",
        "reach": "2400",
        "impact": "high",
        "confidence": "high",
        "effort": "m",
    },
    {
        "name": "Advanced admin analytics",
        "reach": "600",
        "impact": "massive",
        "confidence": "medium",
        "effort": "xl",
    },
    {
        "name": "CSV import error preview",
        "reach": "950",
        "impact": "medium",
        "confidence": "high",
        "effort": "s",
    },
]


def parse_number(value: str, mapping: dict[str, float], field: str) -> float:
    normalized = str(value).strip().lower()
    if normalized in mapping:
        return mapping[normalized]
    if normalized.endswith("%"):
        return float(normalized[:-1]) / 100
    try:
        return float(normalized)
    except ValueError as exc:
        allowed = ", ".join(sorted(mapping)) or "number"
        raise ValueError(f"{field} must be numeric or one of: {allowed}") from exc


def parse_confidence(value: str) -> float:
    normalized = str(value).strip().lower()
    if normalized in CONFIDENCE:
        return CONFIDENCE[normalized]
    try:
        if normalized.endswith("%"):
            confidence = float(normalized[:-1]) / 100
        else:
            confidence = float(normalized)
            if confidence > 1:
                confidence /= 100
    except ValueError as exc:
        raise ValueError("confidence must be numeric, a percentage, or one of: high, medium, low") from exc
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1, or between 0% and 100%")
    return confidence


def read_features(path: Path) -> list[dict[str, object]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"name", "reach", "impact", "confidence", "effort"}
    if not rows:
        raise ValueError("input CSV has no feature rows")
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"input CSV missing columns: {', '.join(sorted(missing))}")

    features = []
    for row in rows:
        reach = parse_number(row["reach"], {}, "reach")
        impact = parse_number(row["impact"], IMPACT, "impact")
        confidence = parse_confidence(row["confidence"])
        effort = parse_number(row["effort"], EFFORT, "effort")
        if effort <= 0:
            raise ValueError(f"effort must be positive for {row['name']}")
        score = (reach * impact * confidence) / effort
        features.append(
            {
                "name": row["name"].strip(),
                "reach": reach,
                "impact": impact,
                "confidence": confidence,
                "effort": effort,
                "rice_score": round(score, 2),
                "_rice_score_sort": score,
                "bucket": classify(score, effort),
            }
        )
    ranked = sorted(features, key=lambda item: float(item["_rice_score_sort"]), reverse=True)
    for feature in ranked:
        del feature["_rice_score_sort"]
    return ranked


def classify(score: float, effort: float) -> str:
    if score >= 1000 and effort <= 1:
        return "quick win"
    if score >= 1000:
        return "big bet"
    if effort <= 1:
        return "fill-in"
    return "time sink"


def roadmap(features: list[dict[str, object]], capacity: float) -> list[dict[str, object]]:
    selected = []
    used = 0.0
    for feature in features:
        effort = float(feature["effort"])
        if used + effort <= capacity:
            selected.append(feature)
            used += effort
    return selected


def features_with_selection(features: list[dict[str, object]], capacity: float) -> list[dict[str, object]]:
    selected_ids = {id(feature) for feature in roadmap(features, capacity)}
    rows = []
    for feature in features:
        row = dict(feature)
        row["selected"] = id(feature) in selected_ids
        rows.append(row)
    return rows


def write_sample(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["name", "reach", "impact", "confidence", "effort"])
        writer.writeheader()
        writer.writerows(SAMPLE_ROWS)
    print(f"Wrote sample feature CSV: {path}")


def render_text(features: list[dict[str, object]], capacity: float) -> str:
    ranked = features_with_selection(features, capacity)
    lines = [
        "Feature Prioritization",
        "",
        "| Rank | Feature | RICE | Bucket | Effort | Selected |",
        "|---:|---|---:|---|---:|---|",
    ]
    for index, feature in enumerate(ranked, 1):
        selected = "yes" if feature["selected"] else "no"
        lines.append(
            f"| {index} | {feature['name']} | {feature['rice_score']} | "
            f"{feature['bucket']} | {feature['effort']} | {selected} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Feature CSV path, or 'sample' to create sample_features.csv")
    parser.add_argument("--capacity", type=float, default=15.0, help="Team capacity in person-months")
    parser.add_argument("--output", choices=["text", "json", "csv"], default="text")
    parser.add_argument("--sample-output", default="sample_features.csv")
    args = parser.parse_args()

    if args.input == "sample":
        write_sample(Path(args.sample_output))
        return 0

    try:
        features = read_features(Path(args.input))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.output == "json":
        print(json.dumps({"features": features_with_selection(features, args.capacity), "roadmap": roadmap(features, args.capacity)}, indent=2))
    elif args.output == "csv":
        ranked = features_with_selection(features, args.capacity)
        writer = csv.DictWriter(sys.stdout, fieldnames=list(ranked[0]))
        writer.writeheader()
        writer.writerows(ranked)
    else:
        print(render_text(features, args.capacity))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
