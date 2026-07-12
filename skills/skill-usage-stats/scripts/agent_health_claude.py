"""Claude Code evidence collectors for the cross-tool health scanner."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from agent_health_core import (
    Check,
    ObjectResult,
    ParseIssue,
    candidate_rules,
    msg,
    object_value,
    read_frontmatter,
    read_json_object,
    read_jsonl_objects,
    safe_readonly_rule,
    string_value,
)


_CLAUDE_DENIAL_KINDS = {
    "user-rejected",
    "permission-rule",
    "automode-blocked",
    "automode-unavailable",
    "automode-parsing-error",
}


def _existing_json(path: Path) -> ObjectResult:
    return read_json_object(path) if path.exists() else ObjectResult(None, [])


def check_install(lang: str, *, home: Path, claude_dir: Path, claude_json: Path) -> Check:
    check = Check(
        "claude_install",
        msg(lang, "Claude Code installation", "Claude Code 安装"),
    )
    executable = shutil.which("claude")
    version = ""
    if executable is not None:
        try:
            result = subprocess.run(
                ["claude", "--version"], capture_output=True, text=True, timeout=15, check=False
            )
            if result.returncode == 0:
                version = result.stdout.strip().split()[0] if result.stdout.strip() else ""
            else:
                check.status = "warn"
                check.add(msg(
                    lang,
                    f"`claude --version` exited with status {result.returncode}.",
                    f"`claude --version` 退出码为 {result.returncode}。",
                ))
        except (OSError, subprocess.SubprocessError) as exc:
            check.status = "warn"
            check.add(msg(
                lang,
                f"Could not run `claude --version`: {exc}",
                f"无法运行 `claude --version`: {exc}",
            ))
    else:
        check.status = "info"
        check.add(msg(lang, "Claude CLI was not found on PATH.", "PATH 中未找到 Claude CLI。"))

    config_result = _existing_json(claude_json)
    config = config_result.data or {}
    check.add_errors(config_result.errors)
    install_method = string_value(config.get("installMethod"))
    local_install = claude_dir / "local"
    native_versions = home / ".local" / "share" / "claude" / "versions"
    try:
        native_evidence = native_versions.is_dir() and any(native_versions.iterdir())
    except OSError as exc:
        native_evidence = False
        check.add_errors([_path_issue(native_versions, "read_error", str(exc))])
    executable_outside_local = executable is not None and not _is_within(
        Path(executable).expanduser(), local_install
    )
    cleanup_eligible = (
        local_install.is_dir()
        and native_evidence
        and install_method == "native"
        and executable_outside_local
    )
    check.data.update({
        "version": version,
        "install_method": install_method,
        "executable": executable,
        "legacy_local_present": local_install.is_dir(),
        "native_version_evidence": native_evidence,
        "cleanup_eligible": cleanup_eligible,
    })
    if executable is not None:
        check.add(msg(
            lang,
            f"Version {version or 'unknown'}; executable `{executable}`.",
            f"版本 {version or '未知'}；可执行文件 `{executable}`。",
        ))
    if cleanup_eligible:
        check.status = "fail" if check.errors else "warn"
        check.add(msg(
            lang,
            "Evidence supports quarantining the legacy install: move `~/.claude/local` to "
            "`~/.claude/local.quarantine-YYYYMMDD-HHMMSS`, verify Claude still works, then "
            "request a separate confirmation before deletion.",
            "证据支持隔离旧安装：将 `~/.claude/local` 移到 "
            "`~/.claude/local.quarantine-YYYYMMDD-HHMMSS`，验证 Claude 正常后，再单独确认删除。",
        ))
    elif local_install.is_dir():
        if not check.errors:
            check.status = "warn"
        check.add(msg(
            lang,
            "A legacy local directory exists, but cleanup evidence is incomplete; no cleanup is recommended.",
            "发现旧本地目录，但清理证据不完整；不建议清理。",
        ))
    return check


def _path_issue(path: Path, kind: str, message: str) -> ParseIssue:
    return ParseIssue(str(path), kind, message)


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
    except ValueError:
        return False
    return True


def check_settings(
    lang: str, *, claude_dir: Path, claude_json: Path, project_dir: Path
) -> Check:
    check = Check(
        "claude_settings",
        msg(lang, "Claude settings parse health", "Claude settings 解析健康度"),
    )
    paths = [
        claude_dir / "settings.json",
        project_dir / ".claude" / "settings.json",
        project_dir / ".claude" / "settings.local.json",
        claude_json,
    ]
    parsed: dict[Path, dict[str, object]] = {}
    files_found = sum(1 for path in paths if path.exists())
    for path in paths:
        if not path.exists():
            continue
        result = read_json_object(path)
        check.add_errors(result.errors)
        if result.data is not None:
            parsed[path] = result.data
    user = parsed.get(claude_dir / "settings.json", {})
    raw_permissions = user.get("permissions")
    permissions = object_value(raw_permissions) or {}
    if raw_permissions is not None and object_value(raw_permissions) is None:
        check.add_errors([ParseIssue(
            str(claude_dir / "settings.json"),
            "invalid_field_type",
            "permissions must be a JSON object",
        )])
    default_mode = string_value(permissions.get("defaultMode"))
    check.data.update({
        "files_found": files_found,
        "parse_error_count": len(check.errors),
        "default_mode": default_mode,
    })
    if check.errors:
        check.add(msg(
            lang,
            f"{len(check.errors)} settings file(s) could not be parsed safely.",
            f"{len(check.errors)} 个 settings 文件无法安全解析。",
        ))
    elif parsed:
        check.add(msg(lang, "All discovered settings files are valid JSON objects.", "发现的 settings 文件均为有效 JSON 对象。"))
    else:
        check.status = "info"
        check.add(msg(lang, "No Claude settings files were found.", "未发现 Claude settings 文件。"))
    return check


def check_agents(lang: str, *, roots: Iterable[Path]) -> Check:
    check = Check("claude_agents", msg(lang, "Claude agent definitions", "Claude agent 定义"))
    names: dict[str, list[str]] = {}
    invalid: list[str] = []
    definition_count = 0
    existing_roots = [root for root in roots if root.is_dir()]
    for root in existing_roots:
        for path in root.rglob("*.md"):
            result = read_frontmatter(path)
            check.add_errors(result.errors)
            fields = result.data or {}
            name = string_value(fields.get("name"))
            definition_count += 1
            if not name or not string_value(fields.get("description")):
                invalid.append(str(path))
            if not name:
                continue
            names.setdefault(name, []).append(str(path))
    collisions = {name: paths for name, paths in names.items() if len(paths) > 1}
    check.data.update({
        "supported": bool(existing_roots),
        "definition_count": definition_count,
        "invalid": invalid,
        "collisions": collisions,
        "parse_error_count": len(check.errors),
    })
    if not check.errors:
        if invalid or collisions:
            check.status = "warn"
        elif not existing_roots:
            check.status = "info"
    check.add(msg(
        lang,
        f"Found {definition_count} agent definition(s); {len(invalid)} invalid and {len(collisions)} collision(s).",
        f"发现 {definition_count} 个 agent 定义；{len(invalid)} 个无效，{len(collisions)} 个重名。",
    ))
    return check


def check_sessions(lang: str, *, paths: Iterable[Path]) -> Check:
    selected = list(paths)
    check = Check("claude_sessions", msg(lang, "Claude session parse health", "Claude 会话解析健康度"))
    records, errors = read_jsonl_objects(selected)
    check.add_errors(errors)
    check.data.update({
        "supported": bool(selected),
        "transcript_count": len(selected),
        "record_count": len(records),
        "parse_error_count": len(errors),
    })
    if errors:
        check.add(msg(lang, f"Found {len(errors)} transcript parse error(s).", f"发现 {len(errors)} 个会话解析错误。"))
    elif selected:
        check.add(msg(lang, f"Parsed {len(records)} record(s) from {len(selected)} transcript(s).", f"从 {len(selected)} 个会话解析了 {len(records)} 条记录。"))
    else:
        check.status = "info"
        check.add(msg(lang, "No local Claude transcripts were available; this surface is unsupported.", "没有可用的本地 Claude 会话；此检查面不受支持。"))
    return check


def check_hooks(lang: str, *, paths: Iterable[Path]) -> Check:
    selected = list(paths)
    check = Check("claude_hooks", msg(lang, "Claude hook timing", "Claude hook 耗时"))
    records, errors = read_jsonl_objects(selected)
    aggregate: dict[str, dict[str, int]] = {}
    for record in records:
        attachment = object_value(record.data.get("attachment")) or {}
        name = string_value(attachment.get("hookName"))
        duration = attachment.get("durationMs")
        if name is None or isinstance(duration, bool) or not isinstance(duration, (int, float)):
            continue
        stats = aggregate.setdefault(name, {"runs": 0, "sum_ms": 0, "max_ms": 0})
        millis = int(duration)
        stats["runs"] += 1
        stats["sum_ms"] += millis
        stats["max_ms"] = max(stats["max_ms"], millis)
    slow: list[str] = []
    for name, stats in sorted(aggregate.items(), key=lambda item: item[1]["max_ms"], reverse=True):
        average = stats["sum_ms"] // stats["runs"]
        threshold = 2000 if name.startswith(("PreToolUse", "PostToolUse", "UserPromptSubmit")) else 10000
        if average > threshold:
            slow.append(name)
        check.add(f"{name}: avg={average}ms max={stats['max_ms']}ms runs={stats['runs']}")
    check.add_errors(errors)
    check.data.update({"timings": aggregate, "slow": slow, "parse_error_count": len(errors)})
    if not errors:
        if slow:
            check.status = "warn"
        elif not aggregate:
            check.status = "info"
            check.add(msg(lang, "No hook timing evidence was present in the selected transcripts.", "所选会话中没有 hook 计时证据。"))
    return check


def check_denials(lang: str, *, paths: Iterable[Path]) -> Check:
    selected = list(paths)
    check = Check("claude_denials", msg(lang, "Claude denied read-only commands", "Claude 被拒只读命令"))
    records, errors = read_jsonl_objects(selected)
    calls: dict[tuple[Path, str], str | None] = {}
    denied_commands: list[str] = []
    denial_count = 0
    unpaired_denial_count = 0
    unmatched_result_count = 0
    duplicate_call_count = 0
    for record in records:
        message = object_value(record.data.get("message")) or {}
        content = message.get("content")
        denial_field_present = "toolDenialKind" in record.data
        denial_kind = string_value(record.data.get("toolDenialKind"))
        denial_marked = denial_kind in _CLAUDE_DENIAL_KINDS
        if denial_field_present and not denial_marked:
            errors.append(ParseIssue(
                str(record.path), "invalid_record_schema",
                "toolDenialKind has an unsupported value", record.line,
            ))
        if not isinstance(content, list):
            if denial_marked:
                errors.append(ParseIssue(
                    str(record.path), "invalid_record_schema",
                    "toolDenialKind requires exactly one typed tool_result block", record.line,
                ))
            continue
        blocks = [block for raw in content if (block := object_value(raw)) is not None]
        result_count = sum(block.get("type") == "tool_result" for block in blocks)
        if denial_marked and result_count != 1:
            errors.append(ParseIssue(
                str(record.path), "invalid_record_schema",
                "toolDenialKind requires exactly one typed tool_result block", record.line,
            ))
            denial_marked = False
        for block in blocks:
            block_type = block.get("type")
            if block_type == "tool_use":
                call_id = string_value(block.get("id"))
                if not call_id:
                    errors.append(ParseIssue(
                        str(record.path), "invalid_record_schema",
                        "tool_use is missing string id", record.line,
                    ))
                    continue
                command = None
                if block.get("name") == "Bash":
                    inputs = object_value(block.get("input")) or {}
                    command = string_value(inputs.get("command"))
                    if not command:
                        errors.append(ParseIssue(
                            str(record.path), "invalid_record_schema",
                            "Bash tool_use is missing string command", record.line,
                        ))
                call_key = (record.path, call_id)
                if call_key in calls:
                    duplicate_call_count += 1
                    calls[call_key] = None
                else:
                    calls[call_key] = command
            if block_type != "tool_result":
                continue
            result_id = string_value(block.get("tool_use_id"))
            if not result_id:
                errors.append(ParseIssue(
                    str(record.path), "invalid_record_schema",
                    "tool_result is missing string tool_use_id", record.line,
                ))
                continue
            call_key = (record.path, result_id)
            if call_key in calls:
                command = calls.pop(call_key)
            else:
                command = None
                unmatched_result_count += 1
            if denial_marked:
                denial_count += 1
                if command is None:
                    unpaired_denial_count += 1
                else:
                    denied_commands.append(command)
    safe_denials = sum(1 for command in denied_commands if safe_readonly_rule(command) is not None)
    incomplete_call_count = len(calls)
    evidence_incomplete = bool(
        incomplete_call_count or unmatched_result_count or duplicate_call_count
    )
    candidates = [] if errors or evidence_incomplete else candidate_rules(denied_commands)
    check.add_errors(errors)
    check.data.update({
        "supported": bool(selected),
        "denial_count": denial_count,
        "unpaired_denial_count": unpaired_denial_count,
        "incomplete_call_count": incomplete_call_count,
        "unmatched_result_count": unmatched_result_count,
        "duplicate_call_count": duplicate_call_count,
        "safe_denial_count": safe_denials,
        "candidates": candidates,
        "parse_error_count": len(errors),
    })
    if errors:
        check.add(msg(
            lang,
            f"Found {len(errors)} transcript parse or schema error(s).",
            f"发现 {len(errors)} 个会话解析或结构错误。",
        ))
    else:
        if evidence_incomplete:
            check.status = "warn"
            check.add(msg(
                lang,
                f"Denial evidence is incomplete: {incomplete_call_count} tool call(s) lack a result, "
                f"{unmatched_result_count} result(s) lack a prior call, and "
                f"{duplicate_call_count} pending call ID(s) were duplicated.",
                f"拒绝证据不完整：{incomplete_call_count} 个工具调用缺少结果，"
                f"{unmatched_result_count} 个结果缺少先前调用，"
                f"{duplicate_call_count} 个待处理调用 ID 重复。",
            ))
        elif denial_count:
            check.status = "warn"
        elif not selected:
            check.status = "info"
    if errors or evidence_incomplete:
        check.add(msg(
            lang,
            f"Among complete call/result pairs, observed {denial_count} denial(s); "
            f"{len(candidates)} exact repeated read-only candidate(s).",
            f"在完整的调用/结果配对中观察到 {denial_count} 次拒绝；"
            f"{len(candidates)} 个重复且精确的只读候选。",
        ))
    else:
        check.add(msg(
            lang,
            f"Observed {denial_count} denial(s); {len(candidates)} exact repeated read-only candidate(s).",
            f"观察到 {denial_count} 次拒绝；{len(candidates)} 个重复且精确的只读候选。",
        ))
    for candidate in candidates:
        check.add(candidate)
    return check


def check_context(lang: str, *, claude_dir: Path) -> Check:
    check = Check("claude_context", msg(lang, "Claude context surfaces", "Claude 上下文检查面"))
    context_path = claude_dir / "CLAUDE.md"
    tokens = 0
    lines = 0
    if context_path.exists():
        try:
            text = context_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            check.add_errors([_path_issue(context_path, "read_error", str(exc))])
        else:
            tokens = len(text) // 4
            lines = text.count("\n") + 1
    skills_dir = claude_dir / "skills"
    skill_count = 0
    if skills_dir.is_dir():
        try:
            skill_count = sum(1 for path in skills_dir.iterdir() if path.is_dir())
        except OSError as exc:
            check.add_errors([_path_issue(skills_dir, "read_error", str(exc))])
    check.data.update({"context_lines": lines, "context_tokens": tokens, "skill_count": skill_count})
    check.add(msg(lang, f"CLAUDE.md: {lines} line(s), about {tokens} token(s); {skill_count} skill directory(s).", f"CLAUDE.md：{lines} 行，约 {tokens} tokens；{skill_count} 个技能目录。"))
    if not context_path.exists() and not skills_dir.is_dir():
        check.status = "info"
    return check


def check_mcp_plugins(lang: str, *, claude_json: Path) -> Check:
    check = Check("claude_mcp_plugins", msg(lang, "Claude MCP and plugins", "Claude MCP 与插件"))
    if not claude_json.exists():
        check.status = "info"
        check.data = {"supported": False, "mcp": [], "plugin_count": 0, "parse_error_count": 0}
        check.add(msg(lang, "No Claude configuration evidence was available; this surface is unsupported.", "没有可用的 Claude 配置证据；此检查面不受支持。"))
        return check
    result = read_json_object(claude_json)
    check.add_errors(result.errors)
    config = result.data or {}
    raw_mcp = config.get("mcpServers")
    raw_plugins = config.get("pluginUsage")
    mcp = object_value(raw_mcp) or {}
    plugins = object_value(raw_plugins) or {}
    schema_errors: list[ParseIssue] = []
    if raw_mcp is not None and object_value(raw_mcp) is None:
        schema_errors.append(ParseIssue(str(claude_json), "invalid_field_type", "mcpServers must be a JSON object"))
    if raw_plugins is not None and object_value(raw_plugins) is None:
        schema_errors.append(ParseIssue(str(claude_json), "invalid_field_type", "pluginUsage must be a JSON object"))
    check.add_errors(schema_errors)
    check.data.update({
        "supported": result.data is not None,
        "mcp": sorted(mcp),
        "plugin_count": len(plugins),
        "parse_error_count": len(check.errors),
    })
    check.add(msg(lang, f"Found {len(mcp)} MCP server declaration(s) and {len(plugins)} plugin usage record(s).", f"发现 {len(mcp)} 个 MCP 服务声明和 {len(plugins)} 条插件使用记录。"))
    return check
