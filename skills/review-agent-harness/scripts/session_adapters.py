#!/usr/bin/env python3
"""Privacy-safe Codex and Claude Code JSONL session adapters."""

from __future__ import annotations

import json
import re
from pathlib import Path

from harness_common import sanitize_text


SUPPORTED_PROVIDERS = ("codex", "claude")
_EDIT_TOOL_RE = re.compile(r"(?:apply_patch|edit|write|create_file|replace|str_replace)", re.IGNORECASE)
_VALIDATION_RE = re.compile(
    r"(?:^|\b)(?:pytest|cargo\s+(?:check|test)|go\s+(?:build|test)|npm\s+(?:test|run)|pnpm\s+(?:test|run)|yarn\s+(?:test|run)|tsc|lint|check|test|build)(?:\b|$)",
    re.IGNORECASE,
)
_FAILURE_RE = re.compile(
    r"(?:exit(?:ed with)?(?:_code| code)?[\s\"':=]+[1-9]\d*|\bfailed\b|\berror\b)",
    re.IGNORECASE,
)


def discover_jsonl_files(roots: list[Path], *, limit: int) -> tuple[list[Path], int]:
    """Discover JSONL only below explicitly supplied roots."""

    discovered: list[Path] = []
    outside_scope = 0
    for root in roots:
        resolved = root.expanduser().resolve()
        if not resolved.is_dir():
            raise ValueError(f"session root is not a directory: {root}")
        for path in resolved.rglob("*.jsonl"):
            candidate = path.resolve()
            try:
                candidate.relative_to(resolved)
            except ValueError:
                outside_scope += 1
                continue
            if candidate.is_file():
                discovered.append(candidate)
    ordered = sorted(set(discovered), key=lambda path: (-path.stat().st_mtime_ns, str(path)))
    return ordered[:limit], outside_scope + max(0, len(ordered) - limit)


def _content_text(content: object) -> list[str]:
    if isinstance(content, str):
        return [content]
    if not isinstance(content, list):
        return []
    values: list[str] = []
    for item in content:
        if isinstance(item, str):
            values.append(item)
        elif isinstance(item, dict):
            for key in ("text", "input_text", "content"):
                if isinstance(item.get(key), str):
                    values.append(str(item[key]))
                    break
    return values


def _command_text(tool_input: object) -> str:
    if isinstance(tool_input, str):
        try:
            decoded = json.loads(tool_input)
        except json.JSONDecodeError:
            return tool_input
        return _command_text(decoded)
    if isinstance(tool_input, dict):
        for key in ("cmd", "command", "args"):
            value = tool_input.get(key)
            if isinstance(value, str):
                return value
    return ""


def _tool_counts(name: str, tool_input: object) -> tuple[int, int]:
    command = _command_text(tool_input)
    edit = int(bool(_EDIT_TOOL_RE.search(name)))
    validation = int(bool(_VALIDATION_RE.search(command) or _VALIDATION_RE.search(name)))
    return edit, validation


def _empty_session(alias: str) -> dict[str, object]:
    return {
        "alias": alias,
        "user_turns": 0,
        "request_summary": None,
        "tool_calls": 0,
        "edit_calls": 0,
        "validation_calls": 0,
        "tool_failures": 0,
        "malformed_lines": 0,
        "unsupported_lines": 0,
        "evidence_state": "present",
    }


def _parse_codex_event(event: dict[str, object], session: dict[str, object], requests: list[str]) -> bool:
    payload = event.get("payload")
    if event.get("type") != "response_item" or not isinstance(payload, dict):
        return False
    item_type = payload.get("type")
    if item_type == "message" and payload.get("role") == "user":
        content_values = _content_text(payload.get("content"))
        recognized = False
        for text in content_values:
            if text.strip():
                requests.append(text)
                session["user_turns"] = int(session["user_turns"]) + 1
                recognized = True
        return recognized
    if item_type in {"function_call", "custom_tool_call"}:
        raw_name = payload.get("name") or payload.get("tool_name")
        tool_input = payload.get("arguments") if "arguments" in payload else payload.get("input")
        if not isinstance(raw_name, str) or not raw_name.strip() or tool_input is None:
            return False
        name = raw_name
        edit, validation = _tool_counts(name, tool_input)
        session["tool_calls"] = int(session["tool_calls"]) + 1
        session["edit_calls"] = int(session["edit_calls"]) + edit
        session["validation_calls"] = int(session["validation_calls"]) + validation
        return True
    if item_type in {"function_call_output", "custom_tool_call_output"}:
        output = str(payload.get("output") or payload.get("content") or "")
        if _FAILURE_RE.search(output):
            session["tool_failures"] = int(session["tool_failures"]) + 1
        return True
    return False


def _parse_claude_event(event: dict[str, object], session: dict[str, object], requests: list[str]) -> bool:
    event_type = event.get("type")
    message = event.get("message")
    if not isinstance(message, dict):
        return False
    content = message.get("content")
    if event_type == "user":
        request_content = content
        if isinstance(content, list):
            request_content = [
                item
                for item in content
                if not (isinstance(item, dict) and item.get("type") == "tool_result")
            ]
        recognized = False
        for text in _content_text(request_content):
            if text.strip():
                requests.append(text)
                session["user_turns"] = int(session["user_turns"]) + 1
                recognized = True
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "tool_result" and item.get("is_error") is True:
                    session["tool_failures"] = int(session["tool_failures"]) + 1
                    recognized = True
                elif isinstance(item, dict) and item.get("type") == "tool_result":
                    recognized = True
        return recognized
    if event_type != "assistant" or not isinstance(content, list):
        return False
    recognized = False
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") in {"text", "thinking"} and isinstance(item.get("text"), str):
            recognized = True
            continue
        if item.get("type") != "tool_use":
            continue
        raw_name = item.get("name")
        tool_input = item.get("input")
        if not isinstance(raw_name, str) or not raw_name.strip() or tool_input is None:
            continue
        name = raw_name
        edit, validation = _tool_counts(name, tool_input)
        session["tool_calls"] = int(session["tool_calls"]) + 1
        session["edit_calls"] = int(session["edit_calls"]) + edit
        session["validation_calls"] = int(session["validation_calls"]) + validation
        recognized = True
    return recognized


def parse_sessions(
    provider: str,
    paths: list[Path],
    *,
    include_request_summaries: bool = False,
) -> dict[str, object]:
    """Parse bounded explicit session files into a sanitized facts envelope."""

    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"unsupported provider: {provider}")
    sessions: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    for index, path in enumerate(paths, start=1):
        resolved = path.expanduser().resolve()
        if not resolved.is_file():
            raise ValueError(f"session file is not a file: {path}")
        session = _empty_session(f"session-{index}")
        requests: list[str] = []
        recognized_lines = 0
        with resolved.open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    session["malformed_lines"] = int(session["malformed_lines"]) + 1
                    warnings.append({
                        "code": "malformed-jsonl",
                        "source": session["alias"],
                        "line": line_number,
                    })
                    continue
                if not isinstance(event, dict):
                    session["unsupported_lines"] = int(session["unsupported_lines"]) + 1
                    warnings.append({
                        "code": "unsupported-event-shape",
                        "source": session["alias"],
                        "line": line_number,
                    })
                    continue
                if provider == "codex":
                    recognized = _parse_codex_event(event, session, requests)
                else:
                    recognized = _parse_claude_event(event, session, requests)
                if recognized:
                    recognized_lines += 1
                else:
                    session["unsupported_lines"] = int(session["unsupported_lines"]) + 1
                    warnings.append({
                        "code": "unsupported-event-shape",
                        "source": session["alias"],
                        "line": line_number,
                    })
        if include_request_summaries and requests:
            session["request_summary"] = sanitize_text(requests[0], limit=220)
        if recognized_lines == 0:
            session["evidence_state"] = "unobserved"
            if int(session["malformed_lines"]) == 0 and int(session["unsupported_lines"]) == 0:
                warnings.append({
                    "code": "no-recognized-events",
                    "source": session["alias"],
                    "line": 0,
                })
        else:
            session["evidence_state"] = "exercised" if int(session["tool_calls"]) > 0 else "present"
        sessions.append(session)

    totals = {
        key: sum(int(session[key]) for session in sessions)
        for key in (
            "user_turns",
            "tool_calls",
            "edit_calls",
            "validation_calls",
            "tool_failures",
            "malformed_lines",
            "unsupported_lines",
        )
    }
    return {
        "status": (
            "unavailable"
            if not sessions
            else "unobserved"
            if all(session["evidence_state"] == "unobserved" for session in sessions)
            else "available"
        ),
        "provider": provider,
        "sessions": sessions,
        "summary": {"session_count": len(sessions), **totals},
        "warnings": warnings,
        "privacy": {
            "source_paths_emitted": False,
            "stable_session_ids_emitted": False,
            "raw_transcripts_emitted": False,
            "request_summaries": "sanitized-first-request" if include_request_summaries else "omitted",
        },
    }
