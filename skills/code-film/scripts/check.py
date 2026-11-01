"""Measure a finished film. Prints specs, loudness, section levels and, for loops, both seams.
Usage: uv run --with playwright --python 3.12 python -I check.py <film.html> <film.mp4> [--loop] [--level name:a-b ...]
A silent section reads as -inf. It expects the WAV that render.py leaves beside the MP4.
"""
import argparse
import array
import math
import subprocess
import sys
import wave
from pathlib import Path

from playwright.sync_api import sync_playwright

SKILL = Path(__file__).resolve().parent.parent
ARGS = ["--ignore-gpu-blocklist"] + (["--use-angle=metal"] if sys.platform == "darwin" else [])

ap = argparse.ArgumentParser()
ap.add_argument("html")
ap.add_argument("mp4")
ap.add_argument("--loop", action="store_true")
ap.add_argument("--level", action="append", default=[])
a = ap.parse_args()
html, mp4 = Path(a.html).resolve(), Path(a.mp4).resolve()

print(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_frames,bit_rate:format=duration", "-of", "compact", str(mp4)], capture_output=True, text=True).stdout.strip())
loud = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(mp4), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
for line in loud.splitlines():
    if line.strip().startswith(("I:", "Peak:")):
        print(line.strip())

w = wave.open(str(mp4.with_suffix(".wav")))
sr = w.getframerate()
pcm = array.array("h")
pcm.frombytes(w.readframes(w.getnframes()))
left = pcm[0::2]


def level(start, end):
    part = left[int(start * sr):int(end * sr)]
    rms = math.sqrt(sum(v * v for v in part) / max(1, len(part))) / 32768
    return f"{20 * math.log10(rms):.1f} dBFS" if rms else "-inf"


for item in a.level:
    name, span = item.rsplit(":", 1)
    start, end = (float(x) for x in span.split("-"))
    print(f"{name}: {level(start, end)}")

if a.loop:
    step = sum(abs(left[i] - left[i - 1]) for i in range(1000, 11000)) / 10000 / 32768
    print(f"audio seam step {abs(left[-1] - left[0]) / 32768:.5f}, typical {step:.5f}")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True, args=ARGS)
        page = browser.new_page(viewport={"width": 1320, "height": 800})
        page.route("**/three.min.js", lambda r: r.fulfill(path=str(SKILL / "assets/vendor/three.min.js"), content_type="application/javascript"))
        page.goto(f"file://{html}?render=1")
        page.wait_for_function("window.__ready===true", timeout=60000)
        print("picture seam", page.evaluate("""() => {
          const c = document.querySelector('canvas'), g = c.getContext('webgl2'), W = c.width, H = c.height, d = window.__film.dur;
          const grab = t => { window.renderAt(t); const a = new Uint8Array(W * H * 4); g.readPixels(0, 0, W, H, g.RGBA, g.UNSIGNED_BYTE, a); return a; };
          const diff = (x, y) => { let s = 0; for (let i = 0; i < x.length; i += 4) s += Math.abs(x[i] - y[i]) + Math.abs(x[i + 1] - y[i + 1]) + Math.abs(x[i + 2] - y[i + 2]); return +(s / (x.length / 4) / 3).toFixed(3); };
          const a = grab(0), b = grab(d - .01), m = d * .4, s = grab(m), n = grab(m + 1 / 60);
          return { seam: diff(a, b), ordinaryStep: diff(s, n) };
        }"""))
        browser.close()
