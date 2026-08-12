#!/usr/bin/env python3
"""Privacy-safe Codex and Claude Code JSONL session adapters."""

from __future__ import annotations

import json
import re
from pathlib import Path

from harness_common import sanitize_text


SUPPORTED_PROVIDERS = ("codex", "claude")
MAX_SESSION_BYTES = 16 * 1024 * 1024
MAX_SESSION_LINES = 100_000
MAX_SESSION_LINE_BYTES = 1024 * 1024
MAX_SESSION_WARNINGS = 200
_EDIT_TOOL_NAMES = {
    "apply_patch",
    "create_file",
    "edit",
    "edit_file",
    "multiedit",
    "notebookedit",
    "replace",
    "str_replace",
    "str_replace_editor",
    "write",
    "write_file",
}
_VALIDATION_RE = re.compile(
    r"(?:^|\b)(?:pytest|cargo\s+(?:check|test)|go\s+(?:build|test)|npm\s+(?:test|run)|pnpm\s+(?:test|run)|yarn\s+(?:test|run)|tsc|lint|check|test|build)(?:\b|$)",
    re.IGNORECASE,
)
_FAILURE_RE = re.compile(
    r"(?:exit(?:ed with)?(?:_code| code)?[\s\"':=]+[1-9]\d*|\bfailed\b|\bfailure\b|\berror\b|\btraceback\b|\bpanic\b)",
    re.IGNORECASE,
)
_BENIGN_FAILURE_RE = re.compile(
    r"\b(?:no\s+errors?(?:\s+detected)?|errors?\s*(?:count)?\s*[:=]\s*0|"
    r"failed\s+tests?\s*[:=]\s*0|0\s+(?:tests?\s+)?failed)\b",
    re.IGNORECASE,
)
_FAILED_STATUSES = {"cancelled", "error", "failed", "failure", "timed_out", "timeout"}
_PASSED_STATUSES = {"completed", "ok", "pass", "passed", "success", "succeeded"}


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
    tool_leaf = re.split(r"__|[.:/]", name.casefold())[-1].replace("-", "_")
    edit = int(tool_leaf in _EDIT_TOOL_NAMES)
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
        "bytes_observed": 0,
        "lines_observed": 0,
        "input_truncated": False,
        "truncation_reasons": [],
        "evidence_state": "present",
    }


def _structured_failure(value: object) -> bool | None:
    """Prefer explicit tool-result status fields over prose heuristics."""

    if isinstance(value, dict):
        decisions: list[bool] = []
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if normalized in {"exit_code", "return_code", "returncode"}:
                if isinstance(item, int) and not isinstance(item, bool):
                    decisions.append(item != 0)
                elif isinstance(item, str) and item.strip().lstrip("-").isdigit():
                    decisions.append(int(item.strip()) != 0)
            elif normalized in {"is_error", "failed"} and isinstance(item, bool):
                decisions.append(item)
            elif normalized == "success" and isinstance(item, bool):
                decisions.append(not item)
            elif normalized in {"status", "result"} and isinstance(item, str):
                status = item.strip().casefold().replace(" ", "_").replace("-", "_")
                if status in _FAILED_STATUSES:
                    decisions.append(True)
                elif status in _PASSED_STATUSES:
                    decisions.append(False)
        if any(decisions):
            return True
        if decisions:
            return False
        nested = [_structured_failure(item) for item in value.values()]
        if any(item is True for item in nested):
            return True
        if any(item is False for item in nested):
            return False
        return None
    if isinstance(value, list):
        nested = [_structured_failure(item) for item in value]
        if any(item is True for item in nested):
            return True
        if any(item is False for item in nested):
            return False
    return None


def _tool_result_failed(value: object) -> bool:
    structured = _structured_failure(value)
    if structured is not None:
        return structured
    text = " ".join(_content_text(value)) if isinstance(value, list) else str(value or "")
    return bool(_FAILURE_RE.search(_BENIGN_FAILURE_RE.sub(" ", text)))


def _append_warning(
    warnings: list[dict[str, object]],
    warning: dict[str, object],
    *,
    limit: int,
) -> bool:
    if len(warnings) >= limit:
        return False
    warnings.append(warning)
    return True


def _parse_codex_event(event: dict[str, object], session: dict[str, object], requests: list[str]) -> bool:
    payload = event.get("payload")
    if event.get("type") != "response_item" or not isinstance(payload, dict):
        return False
    item_type = payload.get("type")
    if item_type == "message" and payload.get("role") == "user":
        content_values = _content_text(payload.get("content"))
        nonempty = [text for text in content_values if text.strip()]
        recognized = bool(nonempty)
        if nonempty:
            if not requests:
                requests.append(nonempty[0])
            session["user_turns"] = int(session["user_turns"]) + 1
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
        output = payload.get("output") if "output" in payload else payload.get("content")
        if _tool_result_failed(output):
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
        nonempty = [text for text in _content_text(request_content) if text.strip()]
        recognized = bool(nonempty)
        if nonempty:
            if not requests:
                requests.append(nonempty[0])
            session["user_turns"] = int(session["user_turns"]) + 1
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "tool_result":
                    if _tool_result_failed(item):
                        session["tool_failures"] = int(session["tool_failures"]) + 1
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
    max_bytes: int = MAX_SESSION_BYTES,
    max_lines: int = MAX_SESSION_LINES,
    max_line_bytes: int = MAX_SESSION_LINE_BYTES,
    max_warnings: int = MAX_SESSION_WARNINGS,
) -> dict[str, object]:
    """Parse bounded explicit session files into a sanitized facts envelope."""

    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"unsupported provider: {provider}")
    if min(max_bytes, max_lines, max_line_bytes, max_warnings) < 1:
        raise ValueError("session parse bounds must be positive")
    sessions: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    warnings_omitted = 0
    for index, path in enumerate(paths, start=1):
        resolved = path.expanduser().resolve()
        if not resolved.is_file():
            raise ValueError(f"session file is not a file: {path}")
        session = _empty_session(f"session-{index}")
        requests: list[str] = []
        recognized_lines = 0
        file_size = resolved.stat().st_size
        with resolved.open("rb") as handle:
            while int(session["lines_observed"]) < max_lines and int(session["bytes_observed"]) < max_bytes:
                remaining = max_bytes - int(session["bytes_observed"])
                raw_line = handle.readline(min(max_line_bytes, remaining) + 1)
                if not raw_line:
                    break
                if len(raw_line) > max_line_bytes:
                    session["input_truncated"] = True
                    session["truncation_reasons"].append("line-byte-limit")
                    break
                if len(raw_line) > remaining:
                    session["input_truncated"] = True
                    session["truncation_reasons"].append("session-byte-limit")
                    break
                session["bytes_observed"] = int(session["bytes_observed"]) + len(raw_line)
                session["lines_observed"] = int(session["lines_observed"]) + 1
                line_number = int(session["lines_observed"])
                line = raw_line.decode("utf-8", errors="replace")
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    session["malformed_lines"] = int(session["malformed_lines"]) + 1
                    if not _append_warning(warnings, {
                        "code": "malformed-jsonl",
                        "source": session["alias"],
                        "line": line_number,
                    }, limit=max_warnings):
                        warnings_omitted += 1
                    continue
                if not isinstance(event, dict):
                    session["unsupported_lines"] = int(session["unsupported_lines"]) + 1
                    if not _append_warning(warnings, {
                        "code": "unsupported-event-shape",
                        "source": session["alias"],
                        "line": line_number,
                    }, limit=max_warnings):
                        warnings_omitted += 1
                    continue
                if provider == "codex":
                    recognized = _parse_codex_event(event, session, requests)
                else:
                    recognized = _parse_claude_event(event, session, requests)
                if recognized:
                    recognized_lines += 1
                else:
                    session["unsupported_lines"] = int(session["unsupported_lines"]) + 1
                    if not _append_warning(warnings, {
                        "code": "unsupported-event-shape",
                        "source": session["alias"],
                        "line": line_number,
                    }, limit=max_warnings):
                        warnings_omitted += 1
        if int(session["lines_observed"]) >= max_lines and int(session["bytes_observed"]) < file_size:
            session["input_truncated"] = True
            session["truncation_reasons"].append("session-line-limit")
        if int(session["bytes_observed"]) >= max_bytes and int(session["bytes_observed"]) < file_size:
            session["input_truncated"] = True
            session["truncation_reasons"].append("session-byte-limit")
        session["truncation_reasons"] = sorted(set(session["truncation_reasons"]))
        if include_request_summaries and requests:
            session["request_summary"] = sanitize_text(requests[0], limit=220)
        if recognized_lines == 0:
            session["evidence_state"] = "unobserved"
            if int(session["malformed_lines"]) == 0 and int(session["unsupported_lines"]) == 0:
                if not _append_warning(warnings, {
                    "code": "no-recognized-events",
                    "source": session["alias"],
                    "line": 0,
                }, limit=max_warnings):
                    warnings_omitted += 1
        else:
            session["evidence_state"] = (
                "constrained"
                if session["input_truncated"]
                else "exercised"
                if int(session["tool_calls"]) > 0
                else "present"
            )
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
            "bytes_observed",
            "lines_observed",
        )
    }
    totals["truncated_session_count"] = sum(bool(session["input_truncated"]) for session in sessions)
    return {
        "status": (
            "unavailable"
            if not sessions
            else "constrained"
            if any(session["input_truncated"] for session in sessions)
            else "unobserved"
            if all(session["evidence_state"] == "unobserved" for session in sessions)
            else "available"
        ),
        "provider": provider,
        "sessions": sessions,
        "summary": {"session_count": len(sessions), **totals},
        "warnings": warnings,
        "warnings_omitted": warnings_omitted,
        "bounds": {
            "max_bytes_per_session": max_bytes,
            "max_lines_per_session": max_lines,
            "max_line_bytes": max_line_bytes,
            "max_warnings": max_warnings,
        },
        "privacy": {
            "source_paths_emitted": False,
            "stable_session_ids_emitted": False,
            "raw_transcripts_emitted": False,
            "request_summaries": "sanitized-first-request" if include_request_summaries else "omitted",
        },
    }
