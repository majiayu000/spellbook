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

REQUEST_INTENT_PATTERNS = (
    r"\b(i want|i need|we need|would like|wish|could you|please|feature request)\b",
    r"\b(it should|should be able to|need to|want to)\b",
)

REQUEST_TERM_PATTERNS = (
    r"\b(add|allow|automate|dashboard|enable|export|filter|fix|import|improve|integrate|notify|search|support)\b",
    r"\b(easier|faster|less manual|fewer steps)\b",
)

NEGATED_REQUEST_PATTERNS = (
    r"\b(don't|do not|dont|never|no longer)\s+(want|need|wish|request)\b",
    r"\b(not|isn't|is not|wasn't|was not)\s+(needed|required|a priority)\b",
)

INTERVIEWER_PROMPT_PATTERNS = (
    r"^\s*(could you|can you|would you)\s+(tell|describe|explain|share|walk)\b",
    r"^\s*(what|how|why|when|where|do you|are you|have you)\b",
)

JOB_PATTERNS = (
    r"\bwhen i\b.*\bi want to\b",
    r"\bso i can\b",
    r"\bmy goal is\b",
)

COMPETITOR_PATTERNS = (
    r"\b(competitor|alternative|instead of|compared to|switch(?:ed|ing)? from)\b",
    r"\b(vs\.?|versus)\b",
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


def request_sentences(items: list[str]) -> list[str]:
    matches = []
    for item in items:
        is_negated = any(re.search(pattern, item, flags=re.IGNORECASE) for pattern in NEGATED_REQUEST_PATTERNS)
        is_interviewer_prompt = any(
            re.search(pattern, item, flags=re.IGNORECASE) for pattern in INTERVIEWER_PROMPT_PATTERNS
        )
        has_intent = any(re.search(pattern, item, flags=re.IGNORECASE) for pattern in REQUEST_INTENT_PATTERNS)
        has_request_term = any(re.search(pattern, item, flags=re.IGNORECASE) for pattern in REQUEST_TERM_PATTERNS)
        if has_intent and has_request_term and not is_negated and not is_interviewer_prompt:
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


def pain_severity(text: str) -> str:
    if re.search(r"\b(blocked|broken|cannot|can't|unable|hate|waste|too many steps)\b", text, re.IGNORECASE):
        return "high"
    if re.search(r"\b(frustrat(?:ed|ing)|annoy(?:ed|ing)|confusing|difficult|hard|manual|slow)\b", text, re.IGNORECASE):
        return "medium"
    return "low"


def request_priority(text: str) -> str:
    if re.search(r"\b(urgent|critical|must|blocked|cannot|can't|need to|we need)\b", text, re.IGNORECASE):
        return "high"
    if re.search(r"\b(i need|i want|should be able to|please|fix|support|enable)\b", text, re.IGNORECASE):
        return "medium"
    return "low"


def pain_findings(items: list[str]) -> list[dict[str, str]]:
    return [{"text": item, "severity": pain_severity(item)} for item in items]


def request_findings(items: list[str]) -> list[dict[str, str]]:
    return [{"text": item, "priority": request_priority(item)} for item in items]


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
    requests = request_sentences(items)
    jobs = matching_sentences(items, JOB_PATTERNS)
    competitors = matching_sentences(items, COMPETITOR_PATTERNS)
    quotes = sorted(dict.fromkeys(pain_points + requests), key=len, reverse=True)[:5]
    return {
        "summary": {
            "sentence_count": len(items),
            "pain_point_count": len(pain_points),
            "feature_request_count": len(requests),
            "job_statement_count": len(jobs),
            "competitor_mention_count": len(competitors),
            "sentiment": sentiment(text),
        },
        "pain_points": pain_points,
        "pain_point_findings": pain_findings(pain_points),
        "feature_requests": requests,
        "feature_request_findings": request_findings(requests),
        "jobs_to_be_done": jobs,
        "competitor_mentions": competitors,
        "themes": themes(items),
        "key_quotes": quotes,
    }


def render_markdown(report: dict[str, object]) -> str:
    lines = ["## Interview Analysis", ""]
    summary = report["summary"]
    lines.append(f"- Sentences: {summary['sentence_count']}")
    lines.append(f"- Pain points: {summary['pain_point_count']}")
    lines.append(f"- Feature requests: {summary['feature_request_count']}")
    lines.append(f"- Competitor mentions: {summary['competitor_mention_count']}")
    lines.append(f"- Sentiment: {summary['sentiment']['label']}")

    lines.extend(["", "### Pain Point Findings"])
    if report["pain_point_findings"]:
        lines.extend(f"- [{item['severity']}] {item['text']}" for item in report["pain_point_findings"])
    else:
        lines.append("- None detected")

    lines.extend(["", "### Feature Request Findings"])
    if report["feature_request_findings"]:
        lines.extend(f"- [{item['priority']}] {item['text']}" for item in report["feature_request_findings"])
    else:
        lines.append("- None detected")

    for section in ["jobs_to_be_done", "competitor_mentions", "key_quotes"]:
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
