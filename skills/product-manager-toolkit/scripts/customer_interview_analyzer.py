#!/usr/bin/env python3
"""Extract lightweight product insights from customer interview notes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


PAIN_PATTERNS = (
    r"\b(frustrat(?:ed|ing)|annoy(?:ed|ing)|pain|problem|hard|difficult|slow|confusing|blocked)\b",
    r"\b(can't|cannot|unable|struggle|waste|manual|too many steps)\b",
)

REQUEST_PATTERNS = (
    r"\b(i want|i need|would like|wish|could you|feature request|it should)\b",
    r"\b(automate|export|import|integrate|notify|filter|search|dashboard)\b",
)

JOB_PATTERNS = (
    r"\bwhen i\b.*\bi want to\b",
    r"\bso i can\b",
    r"\bmy goal is\b",
)

POSITIVE = {"love", "great", "easy", "fast", "helpful", "clear", "useful"}
NEGATIVE = {
    "annoyed",
    "annoying",
    "blocked",
    "broken",
    "confusing",
    "frustrated",
    "frustrating",
    "hard",
    "hate",
    "manual",
    "slow",
}


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。！？])\s+|\n+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def matching_sentences(items: list[str], patterns: tuple[str, ...]) -> list[str]:
    matches = []
    for item in items:
        if any(re.search(pattern, item, flags=re.IGNORECASE) for pattern in patterns):
            matches.append(item)
    return matches


def sentiment(text: str) -> dict[str, object]:
    words = re.findall(r"[A-Za-z']+", text.lower())
    positive = sum(word in POSITIVE for word in words)
    negative = sum(word in NEGATIVE for word in words)
    if positive > negative:
        label = "positive"
    elif negative > positive:
        label = "negative"
    else:
        label = "mixed"
    return {"label": label, "positive_terms": positive, "negative_terms": negative}


def themes(items: list[str]) -> list[dict[str, object]]:
    stop = {"the", "and", "that", "with", "this", "from", "have", "when", "they", "need", "want"}
    counts: dict[str, int] = {}
    for item in items:
        for word in re.findall(r"[A-Za-z][A-Za-z-]{3,}", item.lower()):
            if word not in stop:
                counts[word] = counts.get(word, 0) + 1
    return [
        {"theme": word, "mentions": count}
        for word, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:10]
    ]


def analyze_interview(text: str) -> dict[str, object]:
    items = sentences(text)
    pain_points = matching_sentences(items, PAIN_PATTERNS)
    requests = matching_sentences(items, REQUEST_PATTERNS)
    jobs = matching_sentences(items, JOB_PATTERNS)
    quotes = sorted(dict.fromkeys(pain_points + requests), key=len, reverse=True)[:5]
    return {
        "summary": {
            "sentence_count": len(items),
            "pain_point_count": len(pain_points),
            "feature_request_count": len(requests),
            "job_statement_count": len(jobs),
            "sentiment": sentiment(text),
        },
        "pain_points": pain_points,
        "feature_requests": requests,
        "jobs_to_be_done": jobs,
        "themes": themes(items),
        "key_quotes": quotes,
    }


def render_markdown(report: dict[str, object]) -> str:
    lines = ["## Interview Analysis", ""]
    summary = report["summary"]
    lines.append(f"- Sentences: {summary['sentence_count']}")
    lines.append(f"- Pain points: {summary['pain_point_count']}")
    lines.append(f"- Feature requests: {summary['feature_request_count']}")
    lines.append(f"- Sentiment: {summary['sentiment']['label']}")
    for section in ["pain_points", "feature_requests", "jobs_to_be_done", "key_quotes"]:
        lines.extend(["", f"### {section.replace('_', ' ').title()}"])
        values = report[section]
        if values:
            lines.extend(f"- {value}" for value in values)
        else:
            lines.append("- None detected")
    lines.extend(["", "### Themes"])
    lines.extend(f"- {item['theme']}: {item['mentions']}" for item in report["themes"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript")
    parser.add_argument("format", nargs="?", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()

    try:
        text = Path(args.transcript).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    report = analyze_interview(text)
    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
