#!/usr/bin/env python3
"""Parse Codex JSONL worker events without storing prompt or answer text."""

from __future__ import annotations

import json


def normalize_usage(usage: object) -> dict[str, int]:
    if not isinstance(usage, dict):
        return {}
    return {
        str(key): value
        for key, value in usage.items()
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0
    }


def extract_error(event: dict[str, object]) -> str:
    error = event.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str):
            return message
        return json.dumps(error, ensure_ascii=False, sort_keys=True)
    if isinstance(error, str):
        return error
    message = event.get("message")
    if isinstance(message, str):
        return message
    return json.dumps(event, ensure_ascii=False, sort_keys=True)


def partial_event_summary(stdout: str) -> tuple[str | None, int, dict[str, int]]:
    thread_id: str | None = None
    event_count = 0
    usage: dict[str, int] = {}
    for raw_line in stdout.splitlines():
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        event_count += 1
        candidate = event.get("thread_id") if event.get("type") == "thread.started" else None
        if isinstance(candidate, str) and candidate:
            thread_id = candidate
        normalized = normalize_usage(event.get("usage"))
        if normalized:
            usage = normalized
    return thread_id, event_count, usage
