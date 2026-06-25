#!/usr/bin/env python3
"""Skill usage report for the local machine.

Scans Claude Code and Codex session logs and reports skill **usage evidence**,
not an authoritative call count. Claude numbers are exact (structured Skill
tool_use). Codex numbers are implicit evidence only (sed/cat reads of SKILL.md):
on most machines `$skill` mentions and skill-script runs are ~0, and Codex's
authoritative skill_invocation analytics are POSTed to a backend, never stored
locally. So "no local evidence" means exactly that — not "never used".

Outputs a terminal table and a Markdown report (CSV/JSON optional).

Data sources (read-only):
  * Claude Code  — ~/.claude/projects/*/*.jsonl (structured tool_use, 100%).
  * Codex        — ~/.codex/sessions/**/rollout-*.jsonl (path regex on
    skills/<name>/SKILL.md inside function_call lines, ~95%).

Performance: ripgrep (rg --json) pre-filters the multi-gigabyte Codex corpus;
a pure-Python glob+scan fallback runs when rg is unavailable.

Output language: --lang (zh default, en available).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator

CLAUDE_DIR_DEFAULT = Path.home() / ".claude"
CODEX_DIR_DEFAULT = Path.home() / ".codex"
INSTALLED_DIRS_DEFAULT = [Path.home() / ".claude" / "skills", Path.home() / ".codex" / "skills"]

CLAUDE_PRE_GREP = '"name":"Skill"'
CODEX_GREP_PATTERN = r"skills/[a-z0-9_-]+/SKILL\.md"
CODEX_SKILL_RE = re.compile(r"skills/([a-z0-9_-]+)/SKILL\.md")
CODEX_FUNC_MARKER = '"type":"function_call"'
CODEX_FNAME_UUID_RE = re.compile(
    r"rollout-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl$",
    re.I,
)

TOP_DEFAULT = 20
SAMPLE_LIMIT = 5
SAMPLE_WIDTH = 200
ZOMBIE_TABLE_LIMIT = 50

# Terminal table headers stay English (fixed-width alignment). Titles and the
# Markdown report are localized. "zombie" wording is avoided: a skill with no
# local trace is "no_local_evidence", not "never used".
LABELS: dict[str, dict[str, str]] = {
    "en": {
        "table_top": "Top skills by total evidence:",
        "table_zombie": "Installed skills with no local evidence — {n} total:",
        "table_zombie_more": "...and {n} more (see Markdown report for the full list).",
        "report_title": "# Skill Usage Evidence Report",
        "generated_range": "Generated: {gen} | Range: {rng}",
        "sources": "Sources: Claude ({cdir}, {cf} files) + Codex ({xdir}, {xf} files)",
        "summary": "Installed: {inst} | With evidence: {used} | No local evidence: {none}",
        "codex_mode_line": "Codex counting: {mode} | Parse failures: {fail}",
        "overview": "## Overview",
        "metric": "Metric", "skill_calls": "Skill evidence",
        "distinct": "Distinct skills", "files_scanned": "Files scanned",
        "top": "## Top Skills by Total Evidence",
        "md_th": "| Skill | Claude | Codex (implicit) | Total | Last seen | Projects | Runtime |",
        "zombie_h": "## Skills with No Local Evidence — {n}",
        "zombie_none": "_None — every installed skill has local evidence._",
        "trend": "## Monthly Trend",
        "trend_th": "| Month | Evidence | Distinct skills |",
        "projects": "## Top Projects",
        "projects_th": "| Project | Evidence |",
        "caveats": "## Caveats",
        "caveat_codex": "- Codex detection is a path-regex heuristic (~95% precision). Non-skill "
                        "`sed`/`cat` calls that read `SKILL.md` are counted; any true native Codex "
                        "skill calls are invisible. Claude numbers are exact (structured tool_use).",
        "caveat_evidence": "- Codex counts are **implicit evidence only** (sed/cat reads of `SKILL.md`). "
                           "On this machine `$skill` mentions and skill-script runs are ~0, so they are "
                           "not a separate column. This is NOT an authoritative call count — Codex's "
                           "`skill_invocation` analytics are POSTed to a backend and never stored locally.",
        "caveat_mode_call": "- Codex numbers reflect SKILL.md reads. In `call` mode each read counts; "
                            "a skill re-read many times in one session inflates the count.",
        "caveat_mode_session": "- Codex numbers reflect SKILL.md reads. In `session` mode each "
                               "(skill, session) pair counts once, so a skill loaded repeatedly in one "
                               "session is not inflated.",
        "caveat_installed": "- Installed skill set defaults to `~/.claude/skills` and `~/.codex/skills`.",
        "caveat_readonly": "- 'No local evidence' means no local trace, NOT 'never used'. This tool is "
                           "read-only and never modifies logs, skills, or config.",
        "parse_failures_h": "## Parse Failures (samples)",
    },
    "zh": {
        "table_top": "按总证据数排序的 skill：",
        "table_zombie": "无本地证据的 skill（已安装但本机日志无调用证据）— 共 {n} 个：",
        "table_zombie_more": "……还有 {n} 个（完整列表见 Markdown 报告）。",
        "report_title": "# Skill 使用证据报告",
        "generated_range": "生成时间：{gen} | 范围：{rng}",
        "sources": "数据来源：Claude（{cdir}，{cf} 个文件）+ Codex（{xdir}，{xf} 个文件）",
        "summary": "已安装：{inst} | 有证据：{used} | 无本地证据：{none}",
        "codex_mode_line": "Codex 口径：{mode} | 解析失败：{fail}",
        "overview": "## 概览",
        "metric": "指标", "skill_calls": "skill 证据数",
        "distinct": "不同 skill 数", "files_scanned": "扫描文件数",
        "top": "## 按总证据数排序的 skill",
        "md_th": "| Skill | Claude | Codex（implicit） | 合计 | 最近出现 | 项目数 | Runtime |",
        "zombie_h": "## 无本地证据的 skill — {n}",
        "zombie_none": "_无 —— 所有已安装 skill 本机都有调用证据。_",
        "trend": "## 月度趋势",
        "trend_th": "| 月份 | 证据数 | 不同 skill 数 |",
        "projects": "## 项目分布（Top 10）",
        "projects_th": "| 项目 | 证据数 |",
        "caveats": "## 注意事项",
        "caveat_codex": "- Codex 识别是路径正则启发式（约 95% 精度）。非 skill 的 "
                        "`sed`/`cat` 读取 `SKILL.md` 也会被计入；Codex 原生 skill 调用（若存在）不可见。"
                        "Claude 数字精确（结构化 tool_use）。",
        "caveat_evidence": "- Codex 计数**只是 implicit 证据**（sed/cat 读 `SKILL.md`）。本机上 "
                           "`$skill` mention 和 skill 脚本运行约为 0，故未单列。这**不是权威调用计数**"
                           "——Codex 的 `skill_invocation` analytics 直接 POST 到后端，不存本机。",
        "caveat_mode_call": "- Codex 数字反映 SKILL.md 的读取。`call` 口径下每次读取都计数，"
                            "同一会话内反复读取会抬高计数。",
        "caveat_mode_session": "- Codex 数字反映 SKILL.md 的读取。`session` 口径下每个 "
                               "(skill, 会话) 只计一次，同一会话内反复加载不重复计数。",
        "caveat_installed": "- 已安装 skill 集合默认取 `~/.claude/skills` 与 `~/.codex/skills`。",
        "caveat_readonly": "- “无本地证据”只表示本机没有痕迹，**不等同“从未使用”**。本工具只读，"
                           "绝不修改日志、skill 或配置。",
        "parse_failures_h": "## 解析失败（样本）",
    },
}


@dataclass(frozen=True)
class ClaudeHit:
    skill: str
    ts: str
    cwd: str
    session_id: str


@dataclass(frozen=True)
class CodexHit:
    skill: str
    ts: str
    cwd: str
    session_id: str


@dataclass
class SkillStat:
    name: str
    claude_calls: int = 0
    codex_calls: int = 0
    first_used: str | None = None
    last_used: str | None = None
    last_runtime: str | None = None
    projects: Counter = field(default_factory=Counter)
    runtimes: set[str] = field(default_factory=set)

    @property
    def total(self) -> int:
        return self.claude_calls + self.codex_calls


@dataclass
class AggResult:
    stats: dict[str, SkillStat]
    installed: set[str]
    generated_at: str
    claude_files_scanned: int
    codex_files_scanned: int
    parse_failures: int
    parse_failure_samples: list[str]
    codex_mode: str
    earliest: str | None
    latest: str | None
    by_month: Counter
    by_month_skill: dict[str, Counter]


def _record_sample(samples: list[str], text: str) -> None:
    if len(samples) >= SAMPLE_LIMIT:
        return
    samples.append(text[:SAMPLE_WIDTH])


def _is_func_call_line(text: str) -> bool:
    return CODEX_FUNC_MARKER in text


def _parse_claude_line(text: str) -> list[ClaudeHit]:
    try:
        d = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(d, dict):
        return []
    msg = d.get("message")
    if not isinstance(msg, dict):
        return []
    content = msg.get("content")
    if not isinstance(content, list):
        return []
    ts = d.get("timestamp") or ""
    cwd = d.get("cwd") or ""
    session_id = d.get("sessionId") or ""
    hits: list[ClaudeHit] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "tool_use" or item.get("name") != "Skill":
            continue
        raw_input = item.get("input")
        if not isinstance(raw_input, dict):
            continue
        skill = raw_input.get("skill")
        if isinstance(skill, str) and skill.strip():
            hits.append(ClaudeHit(skill=skill.strip(), ts=ts, cwd=cwd, session_id=session_id))
    return hits


def _codex_workdir(payload: dict, meta_fallback: dict | None) -> str:
    args_raw = payload.get("arguments")
    if isinstance(args_raw, str):
        try:
            args = json.loads(args_raw)
        except (json.JSONDecodeError, ValueError):
            args = None
        if isinstance(args, dict) and isinstance(args.get("workdir"), str):
            return args["workdir"]
    if isinstance(meta_fallback, dict) and isinstance(meta_fallback.get("cwd"), str):
        return meta_fallback["cwd"]
    return ""


def _codex_session_id(payload: dict, meta_fallback: dict | None, file_path: Path) -> str:
    if isinstance(meta_fallback, dict) and isinstance(meta_fallback.get("id"), str):
        return meta_fallback["id"]
    match = CODEX_FNAME_UUID_RE.search(file_path.name)
    return match.group(1) if match else ""


def _parse_codex_line(text: str, file_path: Path, meta_fallback: dict | None = None) -> CodexHit | None:
    if not _is_func_call_line(text):
        return None
    try:
        d = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(d, dict):
        return None
    payload = d.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "function_call":
        return None
    match = CODEX_SKILL_RE.search(text)
    if not match:
        return None
    return CodexHit(
        skill=match.group(1),
        ts=d.get("timestamp") or "",
        cwd=_codex_workdir(payload, meta_fallback),
        session_id=_codex_session_id(payload, meta_fallback, file_path),
    )


def _python_fallback(pattern: str, root: Path) -> Iterator[tuple[Path, str]]:
    regex = re.compile(pattern)
    for path in root.rglob("*.jsonl"):
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if regex.search(line):
                        yield path, line.rstrip("\n")
        except OSError:
            continue


def _run_rg(pattern: str, root: Path, *, no_rg: bool = False) -> Iterator[tuple[Path, str]]:
    if no_rg or shutil.which("rg") is None:
        yield from _python_fallback(pattern, root)
        return
    cmd = ["rg", "--json", "--no-heading", "-n", "--", pattern, str(root)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError:
        yield from _python_fallback(pattern, root)
        return
    if proc.returncode not in (0, 1):
        sys.stderr.write(f"[warn] rg failed (rc={proc.returncode}); using Python scan\n")
        yield from _python_fallback(pattern, root)
        return
    for raw in proc.stdout.splitlines():
        try:
            event = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue
        if event.get("type") != "match":
            continue
        data = event.get("data") or {}
        path_text = (data.get("path") or {}).get("text")
        line_text = (data.get("lines") or {}).get("text")
        if path_text and line_text is not None:
            yield Path(path_text), line_text.rstrip("\n")


def _count_scanned_files(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for _ in root.rglob("*.jsonl"))


def discover_installed_skills(dirs: list[Path]) -> set[str]:
    names: set[str] = set()
    for directory in dirs:
        if not directory.is_dir():
            continue
        for child in directory.iterdir():
            if child.is_dir() and not child.name.startswith("."):
                names.add(child.name)
    return names


def collect_claude(
    claude_dir: Path, *, since: str | None = None, no_rg: bool = False
) -> tuple[list[ClaudeHit], int, list[str]]:
    projects = claude_dir / "projects"
    hits: list[ClaudeHit] = []
    failures = 0
    samples: list[str] = []
    if not projects.is_dir():
        return hits, failures, samples
    for _path, text in _run_rg(CLAUDE_PRE_GREP, projects, no_rg=no_rg):
        if CLAUDE_PRE_GREP not in text:
            continue
        parsed = _parse_claude_line(text)
        if not parsed:
            failures += 1
            _record_sample(samples, text)
            continue
        for hit in parsed:
            if since and hit.ts[:7] < since:
                continue
            hits.append(hit)
    return hits, failures, samples


def _codex_roots_for_since(sessions: Path, since: str | None) -> list[Path]:
    if not since:
        return [sessions]
    roots: list[Path] = []
    for year_dir in sorted(sessions.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir() or not month_dir.name.isdigit():
                continue
            ym = f"{year_dir.name}-{int(month_dir.name):02d}"
            if ym >= since:
                roots.append(month_dir)
    return roots


def collect_codex(
    codex_dir: Path,
    *,
    since: str | None = None,
    dedup_mode: str = "session",
    no_rg: bool = False,
) -> tuple[list[CodexHit], int, list[str]]:
    sessions = codex_dir / "sessions"
    hits: list[CodexHit] = []
    failures = 0
    samples: list[str] = []
    if not sessions.is_dir():
        return hits, failures, samples
    seen: set[tuple[str, str]] = set()
    for root in _codex_roots_for_since(sessions, since):
        for path, text in _run_rg(CODEX_GREP_PATTERN, root, no_rg=no_rg):
            hit = _parse_codex_line(text, path)
            if hit is not None:
                if dedup_mode == "session":
                    key = (hit.skill, hit.session_id)
                    if key in seen:
                        continue
                    seen.add(key)
                hits.append(hit)
            elif _is_func_call_line(text):
                failures += 1
                _record_sample(samples, text)
    return hits, failures, samples


def _bump(stat: SkillStat, runtime: str, ts: str, cwd: str, calls: int) -> None:
    if runtime == "claude":
        stat.claude_calls += calls
    else:
        stat.codex_calls += calls
    stat.runtimes.add(runtime)
    if ts:
        if stat.first_used is None or ts < stat.first_used:
            stat.first_used = ts
        if stat.last_used is None or ts > stat.last_used:
            stat.last_used = ts
            stat.last_runtime = runtime
    if cwd:
        stat.projects[cwd] += calls


def aggregate(
    claude_hits: list[ClaudeHit],
    codex_hits: list[CodexHit],
    installed: set[str],
    *,
    claude_files_scanned: int = 0,
    codex_files_scanned: int = 0,
    parse_failures: int = 0,
    parse_failure_samples: list[str] | None = None,
    codex_mode: str = "session",
) -> AggResult:
    stats: dict[str, SkillStat] = {}
    by_month: Counter = Counter()
    by_month_skill: dict[str, Counter] = defaultdict(Counter)

    def record(hit: CodexHit | ClaudeHit, runtime: str) -> None:
        stat = stats.setdefault(hit.skill, SkillStat(name=hit.skill))
        _bump(stat, runtime, hit.ts, hit.cwd, 1)
        month = hit.ts[:7]
        if len(month) == 7:
            by_month[month] += 1
            by_month_skill[month][hit.skill] += 1

    for hit in claude_hits:
        record(hit, "claude")
    for hit in codex_hits:
        record(hit, "codex")

    timestamps = [h.ts for h in claude_hits + codex_hits if h.ts]
    return AggResult(
        stats=stats,
        installed=installed,
        generated_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        claude_files_scanned=claude_files_scanned,
        codex_files_scanned=codex_files_scanned,
        parse_failures=parse_failures,
        parse_failure_samples=parse_failure_samples or [],
        codex_mode=codex_mode,
        earliest=min(timestamps) if timestamps else None,
        latest=max(timestamps) if timestamps else None,
        by_month=by_month,
        by_month_skill=by_month_skill,
    )


def _runtime_label(runtimes: set[str]) -> str:
    if {"claude", "codex"} <= runtimes:
        return "both"
    if "codex" in runtimes:
        return "codex"
    if "claude" in runtimes:
        return "claude"
    return "-"


def _format_table(headers: list[str], rows: list[list[str]], widths: list[int]) -> str:
    sep = "  "
    header_line = sep.join(h.ljust(widths[i]) for i, h in enumerate(headers))
    divider = sep.join("-" * widths[i] for i in range(len(headers)))
    body_lines = [
        sep.join(str(c[i]).ljust(widths[i])[: widths[i]] for i in range(len(c))) for c in rows
    ]
    return "\n".join([header_line, divider, *body_lines])


def render_table(agg: AggResult, top: int, lang: str = "zh") -> str:
    L = LABELS[lang]
    ranked = sorted(agg.stats.values(), key=lambda s: s.total, reverse=True)
    headers = ["SKILL", "CLAUDE", "CODEX", "TOTAL", "LAST", "PROJECTS", "RUNTIME"]
    widths = [30, 7, 7, 7, 12, 9, 8]
    rows = [
        [
            s.name, str(s.claude_calls), str(s.codex_calls), str(s.total),
            (s.last_used or "")[:10], str(len(s.projects)), _runtime_label(s.runtimes),
        ]
        for s in ranked[:top]
    ]
    out = [L["table_top"], _format_table(headers, rows, widths)]
    no_evidence = sorted(agg.installed - set(agg.stats))
    if no_evidence:
        shown = no_evidence[:ZOMBIE_TABLE_LIMIT]
        more = len(no_evidence) - len(shown)
        z_rows = [[z, "-", "-", "0", "-", "0", "-"] for z in shown]
        out.append("")
        out.append(L["table_zombie"].format(n=len(no_evidence)))
        out.append(_format_table(headers, z_rows, [40, 7, 7, 7, 12, 9, 8]))
        if more > 0:
            out.append(L["table_zombie_more"].format(n=more))
    return "\n".join(out)


def _range_str(agg: AggResult) -> str:
    if not agg.earliest:
        return "n/a"
    return f"{agg.earliest[:10]} → {agg.latest[:10]}" if agg.latest else agg.earliest[:10]


def render_markdown(agg: AggResult, top: int, lang: str = "zh") -> str:
    L = LABELS[lang]
    distinct = len(agg.stats)
    no_evidence = sorted(agg.installed - set(agg.stats))
    total_claude = sum(s.claude_calls for s in agg.stats.values())
    total_codex = sum(s.codex_calls for s in agg.stats.values())
    distinct_claude = sum(1 for s in agg.stats.values() if s.claude_calls)
    distinct_codex = sum(1 for s in agg.stats.values() if s.codex_calls)
    lines = [
        L["report_title"], "",
        L["generated_range"].format(gen=agg.generated_at, rng=_range_str(agg)),
        L["sources"].format(cdir=CLAUDE_DIR_DEFAULT, cf=agg.claude_files_scanned,
                            xdir=CODEX_DIR_DEFAULT, xf=agg.codex_files_scanned),
        L["summary"].format(inst=len(agg.installed), used=distinct, none=len(no_evidence)),
        L["codex_mode_line"].format(mode=agg.codex_mode, fail=agg.parse_failures),
        "",
        L["overview"], "",
        f"| {L['metric']} | Claude | Codex | Total |",
        "|---|---|---|---|",
        f"| {L['skill_calls']} | {total_claude} | {total_codex} | {total_claude + total_codex} |",
        f"| {L['distinct']} | {distinct_claude} | {distinct_codex} | {distinct} |",
        f"| {L['files_scanned']} | {agg.claude_files_scanned} | {agg.codex_files_scanned} | "
        f"{agg.claude_files_scanned + agg.codex_files_scanned} |",
        "",
        L["top"], "",
        L["md_th"],
        "|---|---|---|---|---|---|---|",
    ]
    for s in sorted(agg.stats.values(), key=lambda x: x.total, reverse=True)[:top]:
        lines.append(
            f"| `{s.name}` | {s.claude_calls} | {s.codex_calls} | {s.total} | "
            f"{(s.last_used or '')[:10]} | {len(s.projects)} | {_runtime_label(s.runtimes)} |"
        )
    lines += ["", L["zombie_h"].format(n=len(no_evidence)), ""]
    if no_evidence:
        for z in no_evidence:
            lines.append(f"- `{z}`")
    else:
        lines.append(L["zombie_none"])
    lines += ["", L["trend"], "", L["trend_th"], "|---|---|---|"]
    for month in sorted(agg.by_month):
        lines.append(f"| {month} | {agg.by_month[month]} | {len(agg.by_month_skill[month])} |")
    project_counter: Counter = Counter()
    for stat in agg.stats.values():
        project_counter.update(stat.projects)
    lines += ["", L["projects"], "", L["projects_th"], "|---|---|"]
    for project, count in project_counter.most_common(10):
        label = Path(project).name or project
        lines.append(f"| `{label}` ({project}) | {count} |")
    lines += ["", L["caveats"], "",
              L["caveat_codex"],
              L["caveat_evidence"],
              L["caveat_mode_call"] if agg.codex_mode == "call" else L["caveat_mode_session"],
              L["caveat_installed"],
              L["caveat_readonly"]]
    if agg.parse_failure_samples:
        lines += ["", L["parse_failures_h"], ""]
        for sample in agg.parse_failure_samples:
            lines.append(f"- `{sample}`")
    return "\n".join(lines) + "\n"


def _stat_to_dict(stat: SkillStat) -> dict:
    return {
        "name": stat.name,
        "claude_calls": stat.claude_calls,
        "codex_calls": stat.codex_calls,
        "total": stat.total,
        "first_used": stat.first_used,
        "last_used": stat.last_used,
        "last_runtime": stat.last_runtime,
        "projects": dict(stat.projects),
        "runtimes": sorted(stat.runtimes),
    }


def render_json(agg: AggResult) -> str:
    payload = {
        "generated_at": agg.generated_at,
        "range": {"earliest": agg.earliest, "latest": agg.latest},
        "installed_count": len(agg.installed),
        "installed": sorted(agg.installed),
        "total_claude_calls": sum(s.claude_calls for s in agg.stats.values()),
        "total_codex_calls": sum(s.codex_calls for s in agg.stats.values()),
        "codex_mode": agg.codex_mode,
        "parse_failures": agg.parse_failures,
        "claude_files_scanned": agg.claude_files_scanned,
        "codex_files_scanned": agg.codex_files_scanned,
        "by_month": dict(sorted(agg.by_month.items())),
        "stats": [_stat_to_dict(s) for s in sorted(agg.stats.values(), key=lambda x: x.total, reverse=True)],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def render_csv(agg: AggResult) -> str:
    """Per-skill CSV. Column names stay English (stable data interface).

    status: used (installed + has local evidence), no_local_evidence (installed,
    no local trace — NOT 'never used'), uninstalled (evidence in logs but not in
    the installed set).
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["skill", "claude_calls", "codex_calls", "total", "first_used",
         "last_used", "last_runtime", "projects", "runtimes", "status"]
    )
    for name in sorted(set(agg.stats) | agg.installed):
        stat = agg.stats.get(name)
        if stat is None:
            writer.writerow([name, 0, 0, 0, "", "", "", 0, "-", "no_local_evidence"])
            continue
        status = "used" if name in agg.installed else "uninstalled"
        writer.writerow(
            [name, stat.claude_calls, stat.codex_calls, stat.total,
             stat.first_used or "", stat.last_used or "", stat.last_runtime or "",
             len(stat.projects), _runtime_label(stat.runtimes), status]
        )
    return buf.getvalue()


def _eprint(msg: str, quiet: bool) -> None:
    if not quiet:
        sys.stderr.write(msg + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--claude-dir", type=Path, default=CLAUDE_DIR_DEFAULT)
    parser.add_argument("--codex-dir", type=Path, default=CODEX_DIR_DEFAULT)
    parser.add_argument("--top", type=int, default=TOP_DEFAULT)
    parser.add_argument("--since", help="Only count calls in YYYY-MM or later")
    parser.add_argument("--out", help="Markdown output path (- for stdout)")
    parser.add_argument("--json", dest="json_path", help="Also write aggregate JSON to this path")
    parser.add_argument("--csv", dest="csv_path", help="Also write a per-skill CSV to this path")
    parser.add_argument("--no-claude", action="store_true")
    parser.add_argument("--no-codex", action="store_true")
    parser.add_argument("--codex-mode", choices=["call", "session"], default="session")
    parser.add_argument("--installed-dirs", nargs="+", type=Path, default=INSTALLED_DIRS_DEFAULT)
    parser.add_argument("--lang", choices=["zh", "en"], default="zh", help="Output language for the report")
    parser.add_argument("--no-rg", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    installed = discover_installed_skills(args.installed_dirs)
    claude_hits: list[ClaudeHit] = []
    codex_hits: list[CodexHit] = []
    failures = 0
    samples: list[str] = []
    claude_files = 0
    codex_files = 0

    if not args.no_claude:
        claude_projects = args.claude_dir / "projects"
        if claude_projects.is_dir():
            _eprint(f"[info] scanning Claude logs in {claude_projects} ...", args.quiet)
            claude_hits, c_fail, c_samples = collect_claude(
                args.claude_dir, since=args.since, no_rg=args.no_rg
            )
            claude_files = _count_scanned_files(claude_projects)
            failures += c_fail
            samples += c_samples
            _eprint(f"[info] Claude: {len(claude_hits)} calls in {claude_files} files", args.quiet)
        else:
            _eprint(f"[info] Claude dir missing: {claude_projects}, skipping", args.quiet)

    if not args.no_codex:
        codex_sessions = args.codex_dir / "sessions"
        if codex_sessions.is_dir():
            _eprint(f"[info] scanning Codex logs in {codex_sessions} ...", args.quiet)
            codex_hits, x_fail, x_samples = collect_codex(
                args.codex_dir, since=args.since, dedup_mode=args.codex_mode, no_rg=args.no_rg
            )
            codex_files = _count_scanned_files(codex_sessions)
            failures += x_fail
            samples += x_samples
            _eprint(f"[info] Codex: {len(codex_hits)} implicit-evidence hits ({args.codex_mode} mode)", args.quiet)
        else:
            _eprint(f"[info] Codex dir missing: {codex_sessions}, skipping", args.quiet)

    agg = aggregate(
        claude_hits,
        codex_hits,
        installed,
        claude_files_scanned=claude_files,
        codex_files_scanned=codex_files,
        parse_failures=failures,
        parse_failure_samples=samples,
        codex_mode=args.codex_mode,
    )

    table = render_table(agg, args.top, args.lang)
    markdown = render_markdown(agg, args.top, args.lang)

    out_to_stdout = args.out == "-"
    if out_to_stdout:
        sys.stdout.write(markdown)
    else:
        table_dest = sys.stderr if args.out else sys.stdout
        table_dest.write(table + "\n")
        out_path = Path(args.out) if args.out else Path.home() / f"skill-usage-report-{datetime.now().strftime('%Y%m%d')}.md"
        out_path.write_text(markdown, encoding="utf-8")
        _eprint(f"[info] Markdown report written to {out_path}", args.quiet)

    if args.json_path:
        Path(args.json_path).write_text(render_json(agg), encoding="utf-8")
        _eprint(f"[info] JSON written to {args.json_path}", args.quiet)
    if args.csv_path:
        Path(args.csv_path).write_text(render_csv(agg), encoding="utf-8")
        _eprint(f"[info] CSV written to {args.csv_path}", args.quiet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
