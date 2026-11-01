"""Render stills through the offline path and tile them into contact sheets.
Usage: uv run --with playwright --python 3.12 python -I stills.py <film.html> <outdir> <t1,t2,...> [samples=8]
"""
import base64
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SKILL = Path(__file__).resolve().parent.parent
ARGS = ["--ignore-gpu-blocklist"] + (["--use-angle=metal"] if sys.platform == "darwin" else [])


def sheets(out):
    frames = sorted(out.glob("t*.jpg"))
    for i in range(0, len(frames), 12):
        part = frames[i:i + 12]
        inputs = [a for f in part for a in ("-i", str(f))]
        scaled = ";".join(f"[{k}:v]scale=640:360[v{k}]" for k in range(len(part)))
        if len(part) == 1:
            graph = f"[0:v]scale=640:360"
        else:
            layout = "|".join(f"{(j % 3) * 640}_{(j // 3) * 360}" for j in range(len(part)))
            graph = scaled + ";" + "".join(f"[v{k}]" for k in range(len(part))) + f"xstack=inputs={len(part)}:layout={layout}:fill=black"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-frames:v", "1", "-q:v", "3", str(out / f"sheet{i // 12}.jpg")], check=True)


def main():
    html, out, times = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), [float(x) for x in sys.argv[3].split(",")]
    samples = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.jpg"):
        old.unlink()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True, args=ARGS)
        page = browser.new_page(viewport={"width": 1320, "height": 800})
        logs = []
        page.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
        page.on("console", lambda m: logs.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        page.route("**/three.min.js", lambda r: r.fulfill(path=str(SKILL / "assets/vendor/three.min.js"), content_type="application/javascript"))
        page.goto(f"file://{html}?render=1")
        try:
            page.wait_for_function("window.__ready===true", timeout=60000)
        except Exception:
            sys.exit("Film did not start:\n" + "\n".join(logs[:10]))
        for t in times:
            data = page.evaluate("([t, n]) => { window.renderFrame(t * 60, n, 60); return document.querySelector('canvas').toDataURL('image/jpeg', .92); }", [t, samples])
            (out / f"t{t:06.2f}.jpg").write_bytes(base64.b64decode(data.split(",")[1]))
        browser.close()
    sheets(out)
    print("sheets:", *sorted(str(p) for p in out.glob("sheet*.jpg")))
    for line in sorted(set(logs))[:10]:
        print(line[:300])


main()
