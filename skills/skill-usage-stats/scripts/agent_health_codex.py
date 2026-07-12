"""Codex evidence collectors for the cross-tool health scanner."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from agent_health_core import (
    Check,
    ParseIssue,
    candidate_rules,
    contains_denial,
    msg,
    object_value,
    read_frontmatter,
    read_json_object,
    read_jsonl_objects,
    read_toml_object,
    safe_readonly_rule,
    string_value,
)


def check_install(lang: str) -> Check:
    check = Check("codex_install", msg(lang, "Codex installation", "Codex 安装"))
    executable = shutil.which("codex")
    version = ""
    if executable is None:
        check.status = "info"
        check.data = {"supported": False, "version": "", "executable": None}
        check.add(msg(lang, "Codex CLI was not found on PATH; filesystem checks remain available.", "PATH 中未找到 Codex CLI；仍会执行文件系统检查。"))
        return check
    try:
        result = subprocess.run(
            ["codex", "--version"], capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        check.status = "warn"
        check.add(msg(lang, f"Could not run `codex --version`: {exc}", f"无法运行 `codex --version`: {exc}"))
    else:
        if result.returncode == 0:
            version = result.stdout.strip()
        else:
            check.status = "warn"
            check.add(msg(lang, f"`codex --version` exited with status {result.returncode}.", f"`codex --version` 退出码为 {result.returncode}。"))
    check.data = {"supported": True, "version": version, "executable": executable}
    check.add(msg(lang, f"Version {version or 'unknown'}; executable `{executable}`.", f"版本 {version or '未知'}；可执行文件 `{executable}`。"))
    return check


def check_config(lang: str, *, path: Path) -> Check:
    check = Check("codex_config", msg(lang, "Codex config.toml", "Codex config.toml"))
    if not path.exists():
        check.status = "info"
        check.data = {"supported": False, "mcp": {}, "parse_error_count": 0}
        check.add(msg(lang, "No config.toml evidence was available; this surface is unsupported.", "没有可用的 config.toml 证据；此检查面不受支持。"))
        return check
    result = read_toml_object(path)
    check.add_errors(result.errors)
    config = result.data or {}
    raw_mcp_value = config.get("mcp_servers")
    raw_mcp = object_value(raw_mcp_value) or {}
    if raw_mcp_value is not None and object_value(raw_mcp_value) is None:
        check.add_errors([ParseIssue(
            str(path), "invalid_field_type", "mcp_servers must be a TOML table"
        )])
    mcp: dict[str, bool] = {}
    for name, raw_server in raw_mcp.items():
        server = object_value(raw_server)
        if server is None:
            check.add_errors([ParseIssue(
                str(path), "invalid_field_type", f"mcp_servers.{name} must be a TOML table"
            )])
            continue
        enabled = server.get("enabled", True) if server is not None else True
        if not isinstance(enabled, bool):
            check.add_errors([ParseIssue(
                str(path), "invalid_field_type", f"mcp_servers.{name}.enabled must be boolean"
            )])
            continue
        mcp[name] = enabled
    check.data.update({
        "supported": result.data is not None,
        "model": string_value(config.get("model")),
        "reasoning": string_value(config.get("model_reasoning_effort")),
        "mcp": mcp,
        "parse_error_count": len(check.errors),
    })
    if check.errors:
        check.add(msg(lang, f"config.toml has {len(check.errors)} parse or schema error(s).", f"config.toml 有 {len(check.errors)} 个解析或结构错误。"))
    else:
        check.add(msg(lang, f"Parsed {len(mcp)} MCP server declaration(s).", f"解析到 {len(mcp)} 个 MCP 服务声明。"))
    return check


def check_skills(lang: str, *, roots: Iterable[Path]) -> Check:
    check = Check("codex_skills", msg(lang, "Codex skill definitions", "Codex 技能定义"))
    existing_roots = [root for root in roots if root.is_dir()]
    definitions: dict[str, list[str]] = {}
    invalid: list[str] = []
    definition_count = 0
    for root in existing_roots:
        for path in root.rglob("SKILL.md"):
            result = read_frontmatter(path)
            check.add_errors(result.errors)
            fields = result.data or {}
            name = string_value(fields.get("name"))
            description = string_value(fields.get("description"))
            definition_count += 1
            if not name or not description:
                invalid.append(str(path))
                continue
            definitions.setdefault(name, []).append(str(path))
    collisions = {name: paths for name, paths in definitions.items() if len(paths) > 1}
    check.data.update({
        "supported": bool(existing_roots),
        "definition_count": definition_count,
        "invalid": invalid,
        "collisions": collisions,
        "parse_error_count": len(check.errors),
    })
    if check.errors:
        check.add(msg(lang, f"Found {len(check.errors)} skill parse error(s).", f"发现 {len(check.errors)} 个技能解析错误。"))
    elif invalid or collisions:
        check.status = "warn"
    elif not existing_roots:
        check.status = "info"
    check.add(msg(lang, f"Found {definition_count} definition(s), {len(invalid)} invalid file(s), and {len(collisions)} declared-name collision(s).", f"发现 {definition_count} 个定义、{len(invalid)} 个无效文件和 {len(collisions)} 个声明名冲突。"))
    if not existing_roots:
        check.add(msg(lang, "No current or legacy skill root was available; this surface is unsupported.", "当前和旧版技能根目录均不可用；此检查面不受支持。"))
    return check


def _parse_exec_command(record_path: Path, line: int, arguments: object) -> tuple[str | None, ParseIssue | None]:
    if not isinstance(arguments, str):
        return None, ParseIssue(str(record_path), "invalid_tool_arguments", "exec_command arguments must be a JSON string", line)
    try:
        raw = json.loads(arguments)
    except json.JSONDecodeError as exc:
        return None, ParseIssue(str(record_path), "invalid_tool_arguments", str(exc), line)
    parsed = object_value(raw)
    if parsed is None:
        return None, ParseIssue(str(record_path), "invalid_tool_arguments", "exec_command arguments must contain an object", line)
    command = string_value(parsed.get("cmd"))
    if command is None:
        return None, ParseIssue(str(record_path), "invalid_tool_arguments", "exec_command arguments are missing string field `cmd`", line)
    return command, None


def check_sessions(lang: str, *, paths: Iterable[Path]) -> Check:
    selected = list(paths)
    check = Check("codex_sessions", msg(lang, "Codex local session health", "Codex 本地会话健康度"))
    records, errors = read_jsonl_objects(selected)
    calls: dict[tuple[Path, str], str | None] = {}
    denied_commands: list[str] = []
    denial_count = 0
    unpaired_denials = 0
    schema_supported = False
    for record in records:
        event_type = string_value(record.data.get("type"))
        raw_payload = record.data.get("payload")
        payload_object = object_value(raw_payload)
        payload = payload_object or {}
        payload_type = string_value(payload.get("type"))
        if event_type == "session_meta":
            schema_supported = True
            if payload_object is None:
                errors.append(ParseIssue(
                    str(record.path), "invalid_record_schema", "session_meta payload must be an object", record.line
                ))
            continue
        if event_type != "response_item":
            continue
        if payload_object is None:
            schema_supported = True
            errors.append(ParseIssue(
                str(record.path), "invalid_record_schema", "response_item payload must be an object", record.line
            ))
            continue
        if payload_type is None:
            schema_supported = True
            errors.append(ParseIssue(
                str(record.path),
                "invalid_record_schema",
                "response_item payload is missing string type",
                record.line,
            ))
            continue
        if payload_type == "function_call":
            schema_supported = True
            call_id = string_value(payload.get("call_id"))
            if not call_id:
                errors.append(ParseIssue(
                    str(record.path), "invalid_record_schema", "function_call is missing string call_id", record.line
                ))
                continue
            function_name = string_value(payload.get("name"))
            if function_name is None:
                errors.append(ParseIssue(
                    str(record.path), "invalid_record_schema", "function_call is missing string name", record.line
                ))
                continue
            if function_name == "exec_command":
                command, issue = _parse_exec_command(record.path, record.line, payload.get("arguments"))
                if issue is not None:
                    errors.append(issue)
                calls[(record.path, call_id)] = command
            else:
                calls[(record.path, call_id)] = None
        elif payload_type == "function_call_output":
            schema_supported = True
            call_id = string_value(payload.get("call_id"))
            if call_id is None:
                errors.append(ParseIssue(
                    str(record.path), "invalid_record_schema", "function_call_output is missing string call_id", record.line
                ))
                continue
            if "output" not in payload:
                errors.append(ParseIssue(
                    str(record.path), "invalid_record_schema", "function_call_output is missing output", record.line
                ))
                continue
            command = calls.pop((record.path, call_id), None)
            if call_id and contains_denial(payload.get("output")):
                denial_count += 1
                if command is None:
                    unpaired_denials += 1
                else:
                    denied_commands.append(command)
        elif payload_type in {"custom_tool_call", "custom_tool_call_output"}:
            schema_supported = True
            call_id = string_value(payload.get("call_id"))
            if payload_type == "custom_tool_call":
                if call_id:
                    calls[(record.path, call_id)] = None
            elif call_id:
                command = calls.pop((record.path, call_id), None)
                if contains_denial(payload.get("output")):
                    denial_count += 1
                    if command is None:
                        unpaired_denials += 1
                    else:
                        denied_commands.append(command)

    candidates = candidate_rules(denied_commands)
    unsafe_denials = sum(
        1
        for command in denied_commands
        if safe_readonly_rule(command) is None
    )
    check.add_errors(errors)
    check.data.update({
        "supported": bool(selected),
        "schema_supported": schema_supported,
        "transcript_count": len(selected),
        "record_count": len(records),
        "parse_error_count": len(errors),
        "denial_count": denial_count,
        "unpaired_denial_count": unpaired_denials,
        "unsafe_denial_count": unsafe_denials,
        "candidates": candidates,
    })
    if errors:
        check.add(msg(lang, f"Found {len(errors)} transcript parse or schema error(s).", f"发现 {len(errors)} 个会话解析或结构错误。"))
    elif not selected or not schema_supported:
        check.status = "info"
        check.add(msg(lang, "No verifiable local Codex session schema was available; this surface is unsupported.", "没有可验证的本地 Codex 会话结构；此检查面不受支持。"))
    elif denial_count:
        check.status = "warn"
        check.add(msg(lang, f"Observed {denial_count} denial(s); {len(candidates)} exact repeated read-only candidate(s).", f"观察到 {denial_count} 次拒绝；{len(candidates)} 个重复且精确的只读候选。"))
    else:
        check.add(msg(lang, f"Parsed {len(records)} record(s) using the verified local schema; no denials were observed.", f"使用已验证的本地结构解析了 {len(records)} 条记录；未观察到拒绝。"))
    for candidate in candidates:
        check.add(candidate)
    return check


def check_context(lang: str, *, paths: Iterable[Path]) -> Check:
    selected = [path for path in paths if path.exists()]
    check = Check("codex_context", msg(lang, "Codex AGENTS.md context", "Codex AGENTS.md 上下文"))
    documents: list[dict[str, object]] = []
    for path in selected:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            check.add_errors([ParseIssue(str(path), "read_error", str(exc))])
            continue
        documents.append({"path": str(path), "lines": text.count("\n") + 1, "tokens": len(text) // 4})
    check.data.update({"supported": bool(selected), "documents": documents, "parse_error_count": len(check.errors)})
    if not selected:
        check.status = "info"
        check.add(msg(lang, "No AGENTS.md evidence was available; this surface is unsupported.", "没有可用的 AGENTS.md 证据；此检查面不受支持。"))
    else:
        check.add(msg(lang, f"Read {len(documents)} AGENTS.md context file(s).", f"读取了 {len(documents)} 个 AGENTS.md 上下文文件。"))
    return check


def check_plugins(lang: str, *, plugins_dir: Path) -> Check:
    check = Check("codex_plugins", msg(lang, "Codex plugin surfaces", "Codex 插件检查面"))
    if not plugins_dir.is_dir():
        check.status = "info"
        check.data = {"supported": False, "plugin_count": 0, "skill_plugin_count": 0, "mcp_plugin_count": 0, "invalid": [], "parse_error_count": 0}
        check.add(msg(lang, "No plugin cache evidence was available; this surface is unsupported.", "没有可用的插件缓存证据；此检查面不受支持。"))
        return check
    manifests = list(plugins_dir.rglob(".codex-plugin/plugin.json"))
    invalid: list[str] = []
    plugin_count = 0
    skill_plugin_count = 0
    mcp_plugin_count = 0
    for manifest in manifests:
        result = read_json_object(manifest)
        check.add_errors(result.errors)
        data = result.data
        if data is None:
            invalid.append(str(manifest))
            continue
        name = string_value(data.get("name"))
        version = string_value(data.get("version"))
        if not name or not version:
            invalid.append(str(manifest))
        plugin_count += 1
        skills = data.get("skills")
        if skills is not None:
            if isinstance(skills, list):
                if skills:
                    skill_plugin_count += 1
            else:
                check.add_errors([ParseIssue(
                    str(manifest), "invalid_field_type", "skills must be a JSON array"
                )])
        mcp = data.get("mcpServers")
        if mcp is not None:
            if isinstance(mcp, (dict, list)):
                if mcp:
                    mcp_plugin_count += 1
            else:
                check.add_errors([ParseIssue(
                    str(manifest), "invalid_field_type", "mcpServers must be a JSON object or array"
                )])
    check.data.update({
        "supported": True,
        "plugin_count": plugin_count,
        "skill_plugin_count": skill_plugin_count,
        "mcp_plugin_count": mcp_plugin_count,
        "invalid": invalid,
        "parse_error_count": len(check.errors),
    })
    if check.errors:
        check.add(msg(lang, f"Found {len(check.errors)} plugin manifest parse error(s).", f"发现 {len(check.errors)} 个插件清单解析错误。"))
    elif invalid:
        check.status = "warn"
    elif not manifests:
        check.status = "info"
    check.add(msg(lang, f"Found {plugin_count} plugin manifest(s), including {skill_plugin_count} with skills and {mcp_plugin_count} with MCP declarations.", f"发现 {plugin_count} 个插件清单，其中 {skill_plugin_count} 个声明技能，{mcp_plugin_count} 个声明 MCP。"))
    return check
