#!/usr/bin/env python3
"""Read a repo's commits in a time window and lay them out as lanes: the main line in lane 0,
every side branch on its own lane while it is open, forks and merges kept as edges.

usage: lanes.py <repo> --since "2026-11-01 20:00" --until "2026-11-02 06:00" [--branch main] [--max 400] > night.json
Read-only git. Output is JSON: commits (x order, lane, parents as x indexes, labels) and segments.
"""
import argparse, json, os, re, subprocess, sys
from datetime import datetime

def git(repo, *args):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    return subprocess.run(['git', '-C', repo, *args], capture_output=True, text=True, check=True, env=env).stdout

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repo'); ap.add_argument('--since', required=True); ap.add_argument('--until', required=True)
    ap.add_argument('--branch', default=None, help='main line (default: current branch)')
    ap.add_argument('--max', type=int, default=400, help='keep at most this many commits (newest)')
    a = ap.parse_args()
    branch = a.branch or git(a.repo, 'rev-parse', '--abbrev-ref', 'HEAD').strip()
    raw = git(a.repo, 'log', '--all', f'--since={a.since}', f'--until={a.until}', '--topo-order', '--reverse',
              '--format=%H%x09%P%x09%ct%x09%s')
    rows = [l.split('\t', 3) for l in raw.splitlines() if l.strip()]
    if not rows:
        sys.exit(f'no commits between {a.since} and {a.until}')
    rows = rows[-a.max:]
    fp = set(git(a.repo, 'rev-list', '--first-parent', branch, f'--since={a.since}').split())
    topo = {r[0]: i for i, r in enumerate(rows)}
    cs = [{'h': h, 'p': p.split(), 'ts': int(ts), 's': s, 'main': h in fp} for h, p, ts, s in rows]
    if not any(c['main'] for c in cs):      # window is all side work: treat the longest first-parent chain as main
        for c in cs: c['main'] = True
    cs.sort(key=lambda c: (c['ts'], topo[c['h']]))
    X = {c['h']: i for i, c in enumerate(cs)}
    # side segments: chains of non-main commits along first parents
    seg, segs = {}, []
    for c in sorted(cs, key=lambda c: topo[c['h']]):
        if c['main']: continue
        p0 = c['p'][0] if c['p'] else None
        if p0 in seg and segs[seg[p0]]['last'] == p0: sid = seg[p0]
        else: sid = len(segs); segs.append({'commits': [], 'fork': p0, 'last': None, 'name': None})
        seg[c['h']] = sid; segs[sid]['commits'].append(c['h']); segs[sid]['last'] = c['h']
    for sg in segs:
        xs = [X[h] for h in sg['commits']]
        start = X[sg['fork']] if sg['fork'] in X else min(xs) - 1
        end = max(xs)
        for c in cs:
            if sg['last'] in c['p'][1:]: end = max(end, X[c['h']])
        sg['span'] = (start, end)
    occupied = {}
    for i in sorted(range(len(segs)), key=lambda i: segs[i]['span'][0]):
        s0, s1 = segs[i]['span']
        L, n = None, 1
        while L is None:
            for cand in (n, -n):
                if all(not (s0 <= e and s <= s1) for s, e in occupied.get(cand, [])): L = cand; break
            n += 1
        occupied.setdefault(L, []).append((s0, s1)); segs[i]['lane'] = L
    for c in cs:
        m = re.match(r"Merge (?:remote-tracking )?branch '([^']+)'(?: into (\S+))?", c['s'])
        if not m: continue
        src, dst = m.group(1), m.group(2)
        if c['h'] in seg and dst: segs[seg[c['h']]]['name'] = dst
        elif not dst and len(c['p']) > 1 and c['p'][1] in seg: segs[seg[c['p'][1]]]['name'] = src
    span_h = (cs[-1]['ts'] - cs[0]['ts']) / 3600
    fmt = '%H:%M' if span_h < 20 else '%m-%d %H:%M'
    out = []
    for c in cs:
        s, merge = c['s'], len(c['p']) > 1
        typ = 'merge' if merge else ((re.match(r'^(\w+)(\(|:)', s) or [None, 'commit'])[1])
        label = '合并' if merge else re.sub(r'^\w+(\([^)]*\))?!?:\s*', '', s)
        label = re.split(r'[：，。;；]', label)[0][:40]
        out.append({'h': c['h'][:8], 't': datetime.fromtimestamp(c['ts']).strftime(fmt), 'x': X[c['h']],
                    'lane': 0 if c['main'] else segs[seg[c['h']]]['lane'], 'merge': merge, 'type': typ,
                    'label': label, 'p': [X[q] for q in c['p'] if q in X]})
    t0 = datetime.fromtimestamp(cs[0]['ts']); t1 = datetime.fromtimestamp(cs[-1]['ts'])
    try: url = git(a.repo, 'remote', 'get-url', 'origin').strip()
    except subprocess.CalledProcessError: url = ''
    repo_name = re.sub(r'\.git$', '', url.rstrip('/').split('/')[-1]) if url else os.path.basename(git(a.repo, 'rev-parse', '--show-toplevel').strip())
    json.dump({'repo': repo_name, 'branch': branch,
               'from': t0.strftime('%m-%d %H:%M'), 'to': t1.strftime('%m-%d %H:%M'), 'hours': round(span_h, 1),
               'commits': out, 'merges': sum(c['merge'] for c in out),
               'segments': [{'lane': sg['lane'], 'span': sg['span'], 'n': len(sg['commits']), 'name': sg['name']} for sg in segs]},
              sys.stdout, ensure_ascii=False)

if __name__ == '__main__':
    main()
