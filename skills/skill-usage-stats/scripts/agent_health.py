#!/usr/bin/env python3
"""Evidence-bounded local health scan for Claude Code and Codex.

The scanner reads local configuration and recent session records. It does not
modify configuration, grant permissions, clean up installations, or infer that
one tool exposes a diagnostic surface merely because the other tool does.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import agent_health_claude as claude_checks
import agent_health_codex as codex_checks
from agent_health_core import Check, STATUS_ICON, msg, recent_files, safe_readonly_rule, semver


HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"
CODEX_DIR = HOME / ".codex"
CLAUDE_JSON = HOME / ".claude.json"
SCAN_TRANSCRIPTS = 50


def _safe_readonly_rule(command: str) -> str | None:
    """Compatibility wrapper for the conservative exact-command classifier."""

    return safe_readonly_rule(command)


def _claude_transcripts() -> list[Path]:
    return recent_files(CLAUDE_DIR / "projects", "*.jsonl", SCAN_TRANSCRIPTS)


def _codex_transcripts() -> list[Path]:
    return recent_files(CODEX_DIR / "sessions", "rollout-*.jsonl", SCAN_TRANSCRIPTS)


def check_claude_install(
    lang: str = "zh",
    *,
    home: Path | None = None,
    claude_dir: Path | None = None,
    claude_json: Path | None = None,
) -> Check:
    return claude_checks.check_install(
        lang,
        home=home or HOME,
        claude_dir=claude_dir or CLAUDE_DIR,
        claude_json=claude_json or CLAUDE_JSON,
    )


def check_claude_settings(
    lang: str = "zh",
    *,
    claude_dir: Path | None = None,
    claude_json: Path | None = None,
    project_dir: Path | None = None,
) -> Check:
    return claude_checks.check_settings(
        lang,
        claude_dir=claude_dir or CLAUDE_DIR,
        claude_json=claude_json or CLAUDE_JSON,
        project_dir=project_dir or Path.cwd(),
    )


def check_claude_agents(
    lang: str = "zh", *, roots: Iterable[Path] | None = None
) -> Check:
    selected = list(roots) if roots is not None else [
        Path.cwd() / ".claude" / "agents",
        CLAUDE_DIR / "agents",
    ]
    return claude_checks.check_agents(lang, roots=selected)


def check_claude_sessions(
    lang: str = "zh", *, paths: Iterable[Path] | None = None
) -> Check:
    selected = list(paths) if paths is not None else _claude_transcripts()
    return claude_checks.check_sessions(lang, paths=selected)


def check_claude_hooks(
    lang: str = "zh", *, paths: Iterable[Path] | None = None
) -> Check:
    selected = list(paths) if paths is not None else _claude_transcripts()
    return claude_checks.check_hooks(lang, paths=selected)


def check_claude_denials(
    lang: str = "zh", *, paths: Iterable[Path] | None = None
) -> Check:
    selected = list(paths) if paths is not None else _claude_transcripts()
    return claude_checks.check_denials(lang, paths=selected)


def check_claude_context(lang: str = "zh", *, claude_dir: Path | None = None) -> Check:
    return claude_checks.check_context(lang, claude_dir=claude_dir or CLAUDE_DIR)


def check_claude_mcp_plugins(lang: str = "zh", *, claude_json: Path | None = None) -> Check:
    return claude_checks.check_mcp_plugins(lang, claude_json=claude_json or CLAUDE_JSON)


def check_codex_install(lang: str = "zh") -> Check:
    return codex_checks.check_install(lang)


def check_codex_config(lang: str = "zh", *, path: Path | None = None) -> Check:
    return codex_checks.check_config(lang, path=path or CODEX_DIR / "config.toml")


def check_codex_skills(
    lang: str = "zh", *, roots: Iterable[Path] | None = None
) -> Check:
    selected = list(roots) if roots is not None else [HOME / ".agents" / "skills", CODEX_DIR / "skills"]
    return codex_checks.check_skills(lang, roots=selected)


def check_codex_sessions(
    lang: str = "zh", *, paths: Iterable[Path] | None = None
) -> Check:
    selected = list(paths) if paths is not None else _codex_transcripts()
    return codex_checks.check_sessions(lang, paths=selected)


def check_codex_agents_md(
    lang: str = "zh", *, paths: Iterable[Path] | None = None
) -> Check:
    selected = list(paths) if paths is not None else [CODEX_DIR / "AGENTS.md", Path.cwd() / "AGENTS.md"]
    return codex_checks.check_context(lang, paths=selected)


def check_codex_plugins(lang: str = "zh", *, plugins_dir: Path | None = None) -> Check:
    return codex_checks.check_plugins(lang, plugins_dir=plugins_dir or CODEX_DIR / "plugins")


def check_updates(installed_claude: str, lang: str = "zh") -> Check:
    check = Check("updates", msg(lang, "Version freshness (network)", "版本时效（联网）"))
    if os.environ.get("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"):
        check.status = "info"
        check.add(msg(lang, "Nonessential traffic is disabled; skipped the version query.", "非必要流量已禁用；跳过版本查询。"))
        return check
    try:
        request = urllib.request.Request("https://downloads.claude.ai/claude-code-releases/latest")
        with urllib.request.urlopen(request, timeout=10) as response:
            latest = response.read().decode("utf-8").strip()
    except (OSError, UnicodeDecodeError) as exc:
        check.status = "info"
        check.add(msg(lang, f"Could not query the latest Claude release: {exc}", f"无法查询 Claude 最新版本：{exc}"))
        return check
    check.data["claude_latest"] = latest
    if installed_claude and semver(installed_claude) < semver(latest):
        check.status = "warn"
        check.add(msg(lang, f"Claude Code {installed_claude} is behind {latest}.", f"Claude Code {installed_claude} 落后于 {latest}。"))
    else:
        check.add(msg(lang, f"Claude Code {installed_claude or 'unknown'}; latest release {latest}.", f"Claude Code {installed_claude or '未知'}；最新版 {latest}。"))
    return check


def check_usage(lang: str = "zh") -> Check:
    check = Check("usage", msg(lang, "Skill usage and inactive skills", "技能用量与未活跃技能"))
    script = SCRIPT_DIR / "skill_usage_report.py"
    if not script.exists():
        check.status = "info"
        check.data = {"supported": False}
        check.add(msg(lang, "skill_usage_report.py was unavailable; this surface is unsupported.", "skill_usage_report.py 不可用；此检查面不受支持。"))
        return check
    command = f"python3 {script} --lang {lang}"
    check.data = {"supported": True, "command": command}
    check.add(msg(lang, f"Run the separate read-only usage report: `{command}`", f"运行单独的只读用量报告：`{command}`"))
    return check


def run_checks(lang: str, *, include_codex: bool = True, include_updates: bool = False) -> list[Check]:
    claude_install = check_claude_install(lang)
    checks = [
        claude_install,
        check_claude_settings(lang),
        check_claude_agents(lang),
        check_claude_sessions(lang),
        check_claude_hooks(lang),
        check_claude_denials(lang),
        check_claude_context(lang),
        check_claude_mcp_plugins(lang),
    ]
    if include_codex:
        checks.extend([
            check_codex_install(lang),
            check_codex_config(lang),
            check_codex_skills(lang),
            check_codex_sessions(lang),
            check_codex_agents_md(lang),
            check_codex_plugins(lang),
        ])
    if include_updates:
        version = claude_install.data.get("version")
        checks.append(check_updates(version if isinstance(version, str) else "", lang))
    checks.append(check_usage(lang))
    return checks


def summarize(checks: Iterable[Check]) -> dict[str, int]:
    counts = {"total": 0, "failures": 0, "warnings": 0, "info": 0}
    for check in checks:
        counts["total"] += 1
        if check.status == "fail":
            counts["failures"] += 1
        elif check.status == "warn":
            counts["warnings"] += 1
        elif check.status == "info":
            counts["info"] += 1
    return counts


def render_markdown(checks: list[Check], lang: str = "zh") -> str:
    summary = summarize(checks)
    output = [msg(lang, "# Agent Health Check", "# Agent 健康检查"), ""]
    output.append(msg(
        lang,
        f"{summary['total']} checks: {summary['failures']} failure(s), {summary['warnings']} warning(s), {summary['info']} unsupported/informational.",
        f"共 {summary['total']} 项：{summary['failures']} 项失败，{summary['warnings']} 项警告，{summary['info']} 项不支持或仅供参考。",
    ))
    output.append("")
    for check in checks:
        output.append(f"## {STATUS_ICON.get(check.status, '·')} {check.title}")
        output.append("")
        for line in check.lines:
            output.append(f"- {line}")
        for error in check.errors:
            location = f"{error.path}:{error.line}" if error.line is not None else error.path
            output.append(f"- {error.kind}: {location} — {error.message}")
        if not check.lines and not check.errors:
            output.append(f"- {msg(lang, 'No evidence.', '无证据。')}")
        output.append("")
    return "\n".join(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evidence-bounded local agent health scan")
    parser.add_argument("--lang", choices=["zh", "en"], default="zh")
    parser.add_argument("--check-updates", action="store_true", help="query the latest Claude version")
    parser.add_argument("--no-codex", action="store_true", help="skip Codex filesystem checks")
    parser.add_argument("--json", dest="json_path", help="write structured JSON to this path")
    parser.add_argument("--out", default="-", help="write Markdown to this path, or - for stdout")
    args = parser.parse_args(argv)

    checks = run_checks(
        args.lang,
        include_codex=not args.no_codex,
        include_updates=args.check_updates,
    )
    markdown = render_markdown(checks, args.lang)
    if args.out == "-":
        print(markdown)
    else:
        Path(args.out).write_text(markdown, encoding="utf-8")
        print(msg(args.lang, f"Report written to {args.out}", f"报告已写入 {args.out}"))
    if args.json_path:
        payload = {"summary": summarize(checks), "checks": [asdict(check) for check in checks]}
        Path(args.json_path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(msg(args.lang, f"JSON written to {args.json_path}", f"JSON 已写入 {args.json_path}"))
    return 1 if any(check.status == "fail" for check in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
