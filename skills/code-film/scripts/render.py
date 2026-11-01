"""Render every frame, mux the synthesized mix, keep the WAV beside the MP4.
Usage: uv run --with playwright --python 3.12 python -I render.py <film.html> <out.mp4> [--fps 60] [--samples 16] [--crf 17]
Long films: run this in the background. 1080p60 at 16 samples took 0.17 to 0.25 s per frame on an M2 Max.
"""
import argparse
import base64
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

from playwright.sync_api import sync_playwright

SKILL = Path(__file__).resolve().parent.parent
ARGS = ["--ignore-gpu-blocklist"] + (["--use-angle=metal"] if sys.platform == "darwin" else [])

ap = argparse.ArgumentParser()
ap.add_argument("html")
ap.add_argument("out")
ap.add_argument("--fps", type=int, default=60)
ap.add_argument("--samples", type=int, default=16)
ap.add_argument("--crf", type=int, default=17)
a = ap.parse_args()
html, out = Path(a.html).resolve(), Path(a.out).resolve()
wav = out.with_suffix(".wav")
silent = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name

ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-c:v", "mjpeg", "-r", str(a.fps), "-i", "-",
                       "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", str(a.crf), "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True, args=ARGS)
    page = browser.new_page(viewport={"width": 1320, "height": 800})
    page.route("**/three.min.js", lambda r: r.fulfill(path=str(SKILL / "assets/vendor/three.min.js"), content_type="application/javascript"))
    page.goto(f"file://{html}?render=1")
    page.wait_for_function("window.__ready===true", timeout=60000)
    dur = page.evaluate("window.__film.dur")
    audio = page.evaluate("() => window.getAudio()")
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(audio["sr"])
        w.writeframes(base64.b64decode(audio["b64"]))
    frames, start = round(dur * a.fps), time.time()
    for f in range(frames):
        data = page.evaluate("([f, n, fps]) => { window.renderFrame(f, n, fps); return document.querySelector('canvas').toDataURL('image/jpeg', .97); }", [f, a.samples, a.fps])
        ff.stdin.write(base64.b64decode(data.split(",")[1]))
        if f % 300 == 0:
            print(f, "/", frames, round(time.time() - start), "s", flush=True)
    browser.close()
ff.stdin.close()
if ff.wait():
    sys.exit("ffmpeg failed while encoding")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", str(wav), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(out)], check=True)
Path(silent).unlink()
print("done", out, round(time.time() - start), "s")
