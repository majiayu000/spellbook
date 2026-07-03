#!/usr/bin/env python3
"""Extract recent Claude Code session summaries from ~/.claude/projects.

Usage: python3 extract_sessions.py [--days N] [--json] [--max-msgs M]
"""
import argparse
import datetime
import glob
import json
import os
import sys


def first_user_texts(path, limit):
    """Return (start_ts, end_ts, n_user_msgs, first_texts, n_tool_calls)."""
    n_user = 0
    n_tools = 0
    texts = []
    start = end = None
    with open(path) as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = d.get("timestamp")
            if ts:
                end = ts
                if not start:
                    start = ts
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
    return start, end, n_user, texts, n_tools


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=2)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-msgs", type=int, default=3)
    args = ap.parse_args()

    cutoff = datetime.datetime.now().timestamp() - args.days * 86400
    root = os.path.expanduser("~/.claude/projects")
    files = [
        f for f in glob.glob(os.path.join(root, "*", "*.jsonl"))
        if "/subagents/" not in f and os.path.getmtime(f) > cutoff
    ]

    sessions = []
    for f in sorted(files, key=os.path.getmtime):
        proj = os.path.basename(os.path.dirname(f))
        # strip common home-path prefix noise for readability
        for prefix in ("-Users-apple-Desktop-code-", "-Users-apple-"):
            if proj.startswith(prefix):
                proj = proj[len(prefix):]
                break
        start, end, n_user, texts, n_tools = first_user_texts(f, args.max_msgs)
        sub_dir = f[:-6] + "/subagents"
        n_sub = len(glob.glob(sub_dir + "/*.jsonl")) if os.path.isdir(sub_dir) else 0
        sessions.append({
            "project": proj,
            "session": os.path.basename(f)[:8],
            "start": start,
            "end": end,
            "user_msgs": n_user,
            "tool_calls": n_tools,
            "subagents": n_sub,
            "size_mb": round(os.path.getsize(f) / 1e6, 1),
            "first_messages": texts,
        })

    if args.json:
        json.dump(sessions, sys.stdout, ensure_ascii=False, indent=1)
        return

    print(f"# {len(sessions)} sessions in last {args.days:g} days, "
          f"{len({s['project'] for s in sessions})} projects\n")
    for s in sessions:
        t0 = (s["start"] or "?")[:16]
        t1 = (s["end"] or "?")[11:16]
        print(f"### {s['project']} | {s['session']} | {t0} → {t1} | "
              f"user:{s['user_msgs']} tools:{s['tool_calls']} sub:{s['subagents']} {s['size_mb']}MB")
        for m in s["first_messages"]:
            print(f"   - {m}")
        print()


if __name__ == "__main__":
    main()
