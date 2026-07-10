#!/usr/bin/env python3
"""Cross-tool agent health scan (Claude Code + Codex).

Read-only. Gathers the same diagnostics as the built-in `/doctor` for Claude Code
AND the equivalent surfaces for Codex, then prints a structured Markdown report
(optionally JSON). It NEVER writes settings, disables anything, or updates:
those actions are performed by the SKILL orchestrator after user confirmation.

Secrets safety: only reads key names / enabled flags / durations. Never reads or
prints `env` / `headers` / `auth.json` values, and never dumps whole config files.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path

try:
    import tomllib  # py3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"
CODEX_DIR = HOME / ".codex"
CLAUDE_JSON = HOME / ".claude.json"
SCAN_TRANSCRIPTS = 50  # most-recent sessions to scan for hooks/denials

# read-only Bash subcommands we are willing to suggest allow-rules for
READONLY_GIT = {"status", "log", "diff", "show", "branch", "stash"}
READONLY_CMDS = {"ls", "cat", "pwd", "which", "wc", "head", "tail", "tree", "gh"}


@dataclass
class Check:
    key: str
    title: str
    status: str = "ok"           # ok | warn | fail | info
    lines: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)

    def add(self, line: str) -> None:
        self.lines.append(line)


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _semver(v: str) -> tuple:
    v = v.split("+")[0].strip()
    parts = re.findall(r"\d+", v)
    return tuple(int(p) for p in parts[:3]) or (0,)


def _recent_transcripts(limit: int) -> list[Path]:
    proj = CLAUDE_DIR / "projects"
    if not proj.is_dir():
        return []
    files = [p for p in proj.rglob("*.jsonl") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:limit]


# ---------------------------------------------------------------- Claude checks
def check_claude_install() -> Check:
    c = Check("claude_install", "Claude Code 安装 / 版本")
    ver = ""
    exe = shutil.which("claude")
    try:
        out = subprocess.run(["claude", "--version"], capture_output=True,
                             text=True, timeout=15)
        ver = out.stdout.strip().split()[0] if out.stdout.strip() else ""
    except Exception as e:
        c.status = "warn"
        c.add(f"无法运行 `claude --version`: {e}")
    cfg = _read_json(CLAUDE_JSON) or {}
    method = cfg.get("installMethod", "?")
    native = HOME / ".local/share/claude/versions"
    npm_leftover = (CLAUDE_DIR / "local").is_dir()
    c.data = {"version": ver, "installMethod": method, "exe": exe,
              "npm_leftover": npm_leftover,
              "autoUpdates": cfg.get("autoUpdates"),
              "numStartups": cfg.get("numStartups")}
    c.add(f"版本 {ver or '?'}  ·  installMethod={method}  ·  解析到 {exe or '未找到'}")
    if npm_leftover:
        c.status = "warn"
        c.add("发现 `~/.claude/local`(npm 残留),native 安装下可删除")
    if cfg.get("autoUpdates") is False:
        c.add("autoUpdates=false(后台自动更新已关,需手动 `claude update`)")
    return c


def check_claude_settings() -> Check:
    c = Check("claude_settings", "Claude settings 解析")
    files = [CLAUDE_DIR / "settings.json",
             Path(".claude/settings.json"),
             Path(".claude/settings.local.json"), CLAUDE_JSON]
    broken = []
    for f in files:
        if f.exists() and _read_json(f) is None:
            broken.append(str(f))
    if broken:
        c.status = "fail"
        for b in broken:
            c.add(f"解析失败(会被整体忽略): {b}")
    else:
        c.add("所有存在的 settings 文件解析正常")
    # default permission mode
    user = _read_json(CLAUDE_DIR / "settings.json") or {}
    mode = (user.get("permissions") or {}).get("defaultMode", "unset")
    c.data["defaultMode"] = mode
    c.add(f"permissions.defaultMode = {mode}"
          + (" (建议设为 auto)" if mode in ("unset", "default") else ""))
    return c


def _frontmatter(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    fm = {}
    for line in text[3:end if end > 0 else 0].splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


def check_claude_agents() -> Check:
    c = Check("claude_agents", "Claude agent 定义")
    dirs = [Path(".claude/agents"), CLAUDE_DIR / "agents"]
    names: dict[str, list[str]] = {}
    invalid = []
    total = 0
    for d in dirs:
        if not d.is_dir():
            continue
        for f in d.rglob("*.md"):
            fm = _frontmatter(f)
            if "name" not in fm:
                continue  # co-located doc, skip
            total += 1
            if not fm.get("description"):
                invalid.append(str(f))
            names.setdefault((str(d), fm["name"]).__str__(), []).append(str(f))
    # collisions within same dir
    coll = {k: v for k, v in names.items() if len(v) > 1}
    c.data = {"total": total, "invalid": invalid, "collisions": coll}
    c.add(f"共 {total} 个 agent 定义")
    if invalid:
        c.status = "warn"
        c.add(f"缺 description(不会加载): {', '.join(invalid)}")
    if coll:
        c.status = "warn"
        c.add(f"同目录重名冲突: {list(coll)}")
    if not invalid and not coll:
        c.add("全部有效,无重名冲突")
    return c


def check_claude_hooks() -> Check:
    c = Check("claude_hooks", "Claude hook 耗时")
    agg: dict[str, dict] = {}
    for f in _recent_transcripts(SCAN_TRANSCRIPTS):
        try:
            for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                if '"hook_success"' not in line and '"hook_cancelled"' not in line:
                    continue
                obj = json.loads(line)
                att = obj.get("attachment") or {}
                name = att.get("hookName")
                dur = att.get("durationMs")
                if not name or dur is None:
                    continue
                s = agg.setdefault(name, {"runs": 0, "sum": 0, "max": 0})
                s["runs"] += 1
                s["sum"] += dur
                s["max"] = max(s["max"], dur)
        except Exception:
            continue
    slow = []
    for name, s in sorted(agg.items(), key=lambda kv: kv[1]["max"], reverse=True):
        avg = s["sum"] // s["runs"]
        per_call = name.startswith(("PreToolUse", "PostToolUse", "UserPromptSubmit"))
        thresh = 2000 if per_call else 10000
        mark = "  ⚠️慢" if avg > thresh else ""
        c.add(f"{name}: avg={avg}ms max={s['max']}ms runs={s['runs']}{mark}")
        if avg > thresh:
            slow.append(name)
    c.data = {"agg": agg, "slow": slow}
    if slow:
        c.status = "warn"
    elif not agg:
        c.status = "info"
        c.add("窗口内无 hook 计时记录(静默成功不落盘属正常)")
    return c


def check_claude_denials() -> Check:
    c = Check("claude_denials", "Claude 被拒的只读命令")
    counts: dict[str, dict] = {}
    for f in _recent_transcripts(SCAN_TRANSCRIPTS):
        try:
            lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        tool_by_id = {}
        for line in lines:
            if '"tool_use"' not in line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            for blk in (obj.get("message", {}).get("content") or []):
                if isinstance(blk, dict) and blk.get("type") == "tool_use":
                    tool_by_id[blk.get("id")] = blk
        for line in lines:
            if '"toolDenialKind"' not in line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            kind = obj.get("toolDenialKind")
            tid = None
            for blk in (obj.get("message", {}).get("content") or []):
                if isinstance(blk, dict) and blk.get("tool_use_id"):
                    tid = blk["tool_use_id"]
            call = tool_by_id.get(tid)
            if not call:
                continue
            name = call.get("name", "")
            inp = call.get("input", {})
            if name == "Bash":
                cmd = (inp.get("command") or "").strip()
                first = " ".join(cmd.split()[:2])
                sub = cmd.split()[0] if cmd.split() else ""
                sub1 = cmd.split()[1] if len(cmd.split()) > 1 else ""
                readonly = (sub in READONLY_CMDS or
                            (sub == "git" and sub1 in READONLY_GIT))
                key = f"Bash:{first}"
            elif name.startswith("mcp__"):
                readonly = bool(re.search(r"__(get|list|read|search|show)_", name))
                key = name
            else:
                continue
            s = counts.setdefault(key, {"n": 0, "kinds": {}, "readonly": readonly})
            s["n"] += 1
            s["kinds"][kind] = s["kinds"].get(kind, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: kv[1]["n"], reverse=True)
    cand = [(k, v) for k, v in ranked if v["readonly"] and v["n"] >= 2]
    c.data = {"all": counts, "candidates": [k for k, _ in cand]}
    if not counts:
        c.add("窗口内无被拒命令")
    else:
        for k, v in ranked[:10]:
            c.add(f"{k}  ×{v['n']}  {v['kinds']}"
                  + ("  → 可预批准(只读)" if (k, v) in cand else ""))
    return c


def check_claude_context() -> Check:
    c = Check("claude_context", "Claude 上下文占用(估算)")
    md = CLAUDE_DIR / "CLAUDE.md"
    md_tokens = 0
    if md.exists():
        md_tokens = len(md.read_text(errors="ignore")) // 4
        c.add(f"~/.claude/CLAUDE.md: ~{md_tokens} tokens ({sum(1 for _ in md.open())} 行)")
    skills_dir = CLAUDE_DIR / "skills"
    nskills = len(list(skills_dir.glob("*/"))) if skills_dir.is_dir() else 0
    listing_chars = 0
    for sk in (skills_dir.glob("*/SKILL.md") if skills_dir.is_dir() else []):
        try:
            fm = _frontmatter(sk)
            listing_chars += len(fm.get("name", "")) + len(fm.get("description", ""))
        except Exception:
            pass
    c.data = {"claudemd_tokens": md_tokens, "n_skills": nskills,
              "listing_tokens": listing_chars // 4}
    c.add(f"技能 {nskills} 个,列表常驻 ~{listing_chars // 4} tokens"
          "(接近 ~1% 预算即触发路由截断)")
    if nskills > 150:
        c.status = "warn"
    return c


def check_claude_mcp_plugins() -> Check:
    c = Check("claude_mcp_plugins", "Claude MCP / 插件")
    cfg = _read_json(CLAUDE_JSON) or {}
    servers = list((cfg.get("mcpServers") or {}).keys())
    plugins = cfg.get("pluginUsage") or {}
    c.data = {"mcp": servers, "plugins": plugins}
    c.add(f"MCP 服务器: {servers or '无'}")
    if plugins:
        for name, u in plugins.items():
            c.add(f"插件 {name}: usageCount={u.get('usageCount')}")
    else:
        c.add("无已启用插件")
    return c


# ---------------------------------------------------------------- Codex checks
def check_codex_install() -> Check:
    c = Check("codex_install", "Codex 安装 / 版本")
    ver = ""
    exe = shutil.which("codex")
    try:
        out = subprocess.run(["codex", "--version"], capture_output=True,
                             text=True, timeout=15)
        ver = out.stdout.strip()
    except Exception as e:
        c.status = "warn"
        c.add(f"无法运行 `codex --version`: {e}")
    c.data = {"version": ver, "exe": exe}
    c.add(f"版本 {ver or '?'}  ·  解析到 {exe or '未找到'}")
    if not exe:
        c.status = "info"
        c.add("Codex CLI 未安装或不在 PATH,跳过 Codex 检查")
    return c


def check_codex_config() -> Check:
    c = Check("codex_config", "Codex config.toml")
    path = CODEX_DIR / "config.toml"
    if not path.exists():
        c.status = "info"
        c.add("未找到 ~/.codex/config.toml")
        return c
    if tomllib is None:
        c.status = "warn"
        c.add("当前 Python 无 tomllib(<3.11),无法解析 config.toml")
        return c
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        c.status = "fail"
        c.add(f"config.toml 解析失败(会被忽略): {e}")
        return c
    mcp = data.get("mcp_servers") or {}
    mcp_state = {k: (v.get("enabled", True) if isinstance(v, dict) else True)
                 for k, v in mcp.items()}
    c.data = {"model": data.get("model"),
              "reasoning": data.get("model_reasoning_effort"),
              "mcp": mcp_state,
              "hooks": bool(data.get("hooks"))}
    c.add(f"model={data.get('model', '?')}  reasoning={data.get('model_reasoning_effort', '?')}")
    c.add(f"MCP 服务器: {mcp_state or '无'}")
    return c


def check_codex_agents_md() -> Check:
    c = Check("codex_agents_md", "Codex AGENTS.md")
    path = CODEX_DIR / "AGENTS.md"
    if not path.exists():
        c.status = "info"
        c.add("无 ~/.codex/AGENTS.md")
        return c
    text = path.read_text(errors="ignore")
    nlines = text.count("\n") + 1
    c.data = {"lines": nlines, "tokens": len(text) // 4}
    c.add(f"~/.codex/AGENTS.md: {nlines} 行, ~{len(text) // 4} tokens")
    if nlines > 200:
        c.status = "warn"
        c.add("超过 200 行(W-19: 指令文档过大会降低遵循度)")
    return c


# ---------------------------------------------------------------- version net
def check_updates(installed_claude: str) -> Check:
    c = Check("updates", "版本时效(联网)")
    if os.environ.get("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"):
        c.status = "info"
        c.add("非必要流量已禁用,跳过版本查询")
        return c
    try:
        req = urllib.request.Request(
            "https://downloads.claude.ai/claude-code-releases/latest")
        latest = urllib.request.urlopen(req, timeout=10).read().decode().strip()
        if _semver(installed_claude) >= _semver(latest):
            c.add(f"Claude Code {installed_claude} 已是最新({latest})")
        else:
            c.status = "warn"
            c.add(f"Claude Code {installed_claude} 落后于 {latest} → `claude update`")
        c.data["claude_latest"] = latest
    except Exception as e:
        c.status = "info"
        c.add(f"无法查询 Claude 最新版: {e}")
    return c


# ---------------------------------------------------------------- usage reuse
def check_usage(lang: str) -> Check:
    c = Check("usage", "Skill 用量 / 僵尸(复用 skill_usage_report.py)")
    # canonical reporter lives alongside this file (loom single source of truth).
    script = Path(__file__).parent / "skill_usage_report.py"
    if not script.exists():
        script = CLAUDE_DIR / "skills/skill-usage-stats/scripts/skill_usage_report.py"
    if not script.exists():
        c.status = "info"
        c.add("未找到 skill_usage_report.py,跳过用量检查")
        return c
    c.data = {"cmd": f"python3 {script} --lang {lang}"}
    c.add("用量/僵尸清单请运行以下脚本(跨 Claude+Codex,只读):")
    c.add(f"  python3 {script} --lang {lang}")
    return c


# ---------------------------------------------------------------- render
STATUS_ICON = {"ok": "✅", "warn": "⚠️", "fail": "❌", "info": "ℹ️"}


def render_markdown(checks: list[Check]) -> str:
    warns = [c for c in checks if c.status in ("warn", "fail")]
    out = ["# Agent 健康体检 (Claude Code + Codex)\n"]
    out.append(f"体检项 {len(checks)} 个,其中需关注 {len(warns)} 个。\n")
    for c in checks:
        out.append(f"## {STATUS_ICON.get(c.status, '·')} {c.title}")
        for ln in c.lines:
            out.append(f"- {ln}")
        out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Cross-tool agent health scan (read-only)")
    p.add_argument("--lang", choices=["zh", "en"], default="zh")
    p.add_argument("--check-updates", action="store_true",
                   help="联网查询最新版本(默认关闭)")
    p.add_argument("--no-codex", action="store_true")
    p.add_argument("--json", dest="json_path", help="额外写出结构化 JSON")
    p.add_argument("--out", help="Markdown 写出路径(- 为 stdout)", default="-")
    args = p.parse_args(argv)

    checks: list[Check] = []
    ci = check_claude_install()
    checks += [ci, check_claude_settings(), check_claude_agents(),
               check_claude_hooks(), check_claude_denials(),
               check_claude_context(), check_claude_mcp_plugins()]
    if not args.no_codex:
        cx = check_codex_install()
        checks.append(cx)
        if cx.data.get("exe"):
            checks += [check_codex_config(), check_codex_agents_md()]
    if args.check_updates:
        checks.append(check_updates(ci.data.get("version", "")))
    checks.append(check_usage(args.lang))

    md = render_markdown(checks)
    if args.out == "-":
        print(md)
    else:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"报告已写入 {args.out}")
    if args.json_path:
        Path(args.json_path).write_text(
            json.dumps([asdict(c) for c in checks], ensure_ascii=False, indent=2),
            encoding="utf-8")
        print(f"JSON 已写入 {args.json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
