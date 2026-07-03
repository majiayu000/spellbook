#!/usr/bin/env python3
"""Extract recent Claude Code session summaries from ~/.claude/projects.

Usage: python3 extract_sessions.py [--days N] [--json] [--max-msgs M]

Sessions are selected by file mtime, but message counts, tool-call counts
and sampled user messages only include events whose timestamp falls inside
the requested window. A session that started before the window (resumed
recently) is flagged as "resumed" so old prompts don't pollute the recap.
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys


def parse_session(path, limit, cutoff_iso):
    """Return session stats restricted to events at or after cutoff_iso.

    Returns (full_start, window_start, window_end, n_user, texts, n_tools).
    full_start is the first timestamp in the transcript regardless of window.
    """
    n_user = 0
    n_tools = 0
    texts = []
    full_start = None
    win_start = win_end = None
    last_ts = None
    with open(path) as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = d.get("timestamp")
            if ts:
                last_ts = ts
                if not full_start:
                    full_start = ts
            # events without their own timestamp inherit the last seen one
            if last_ts is None or last_ts < cutoff_iso:
                continue
            if ts:
                win_end = ts
                if not win_start:
                    win_start = ts
            if d.get("type") == "assistant":
                c = d.get("message", {}).get("content")
                if isinstance(c, list):
                    n_tools += sum(1 for p in c if isinstance(p, dict) and p.get("type") == "tool_use")
            if d.get("type") == "user" and not d.get("isMeta"):
                c = d.get("message", {}).get("content")
                txt = None
                if isinstance(c, str):
                    txt = c
                elif isinstance(c, list):
                    for part in c:
                        if isinstance(part, dict) and part.get("type") == "text":
                            txt = part["text"]
                            break
                if txt and not txt.lstrip().startswith("<"):
                    n_user += 1
                    if len(texts) < limit:
                        texts.append(" ".join(txt.split())[:200])
    return full_start, win_start, win_end, n_user, texts, n_tools


def clean_project_name(slug):
    """Strip the flattened home-dir prefix from a project dir name.

    Works for any user's home (local or synced remote), e.g.
    "-Users-lifcc-Desktop-code-AI-foo" -> "AI-foo".
    """
    m = re.match(r"^-(?:Users|home)-[^-]+-(?:Desktop-code-)?", slug)
    return slug[m.end():] if m else slug


def discover_roots(extra_roots):
    """Return [(host_label, projects_dir)] to scan.

    Always includes the local ~/.claude/projects, then any synced remote
    hosts under ~/.claude/remote-sessions/<host>/projects, then explicit
    --extra-root values ("label=path" or bare path).
    """
    roots = [("local", os.path.expanduser("~/.claude/projects"))]
    for d in sorted(glob.glob(os.path.expanduser("~/.claude/remote-sessions/*/projects"))):
        roots.append((os.path.basename(os.path.dirname(d)), d))
    for spec in extra_roots:
        label, _, path = spec.rpartition("=")
        path = os.path.expanduser(path)
        roots.append((label or os.path.basename(path.rstrip("/")), path))
    return [(label, d) for label, d in roots if os.path.isdir(d)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=2)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-msgs", type=int, default=3)
    ap.add_argument("--extra-root", action="append", default=[],
                    help="extra projects dir to scan, as 'label=path' or bare path; repeatable")
    args = ap.parse_args()

    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff_dt = now - datetime.timedelta(days=args.days)
    cutoff_epoch = cutoff_dt.timestamp()
    # transcript timestamps are ISO-8601 UTC ("...Z"); compare lexicographically
    cutoff_iso = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%S")

    roots = discover_roots(args.extra_root)
    files = []
    for host, root in roots:
        files.extend(
            (host, f) for f in glob.glob(os.path.join(root, "*", "*.jsonl"))
            if "/subagents/" not in f and os.path.getmtime(f) > cutoff_epoch
        )

    sessions = []
    for host, f in sorted(files, key=lambda p: os.path.getmtime(p[1])):
        proj = clean_project_name(os.path.basename(os.path.dirname(f)))
        full_start, win_start, win_end, n_user, texts, n_tools = parse_session(
            f, args.max_msgs, cutoff_iso)
        if not win_start and n_user == 0 and n_tools == 0:
            continue  # mtime bumped but no in-window activity
        sub_dir = f[:-6] + "/subagents"
        n_sub = len(glob.glob(sub_dir + "/*.jsonl")) if os.path.isdir(sub_dir) else 0
        sessions.append({
            "host": host,
            "project": proj,
            "session": os.path.basename(f)[:8],
            "start": win_start,
            "end": win_end,
            "resumed": bool(full_start and full_start < cutoff_iso),
            "full_start": full_start,
            "user_msgs": n_user,
            "tool_calls": n_tools,
            "subagents": n_sub,
            "size_mb": round(os.path.getsize(f) / 1e6, 1),
            "first_messages": texts,
        })

    if args.json:
        json.dump(sessions, sys.stdout, ensure_ascii=False, indent=1)
        return

    hosts = ", ".join(label for label, _ in roots)
    print(f"# {len(sessions)} sessions with activity in last {args.days:g} days, "
          f"{len({s['project'] for s in sessions})} projects, hosts: {hosts}\n")
    for s in sessions:
        t0 = (s["start"] or "?")[:16]
        t1 = (s["end"] or "?")[11:16]
        tag = f" [resumed, started {s['full_start'][:10]}]" if s["resumed"] else ""
        where = "" if s["host"] == "local" else f" @{s['host']}"
        print(f"### {s['project']}{where} | {s['session']} | {t0} → {t1}{tag} | "
              f"user:{s['user_msgs']} tools:{s['tool_calls']} sub:{s['subagents']} {s['size_mb']}MB")
        for m in s["first_messages"]:
            print(f"   - {m}")
        print()


if __name__ == "__main__":
    main()
