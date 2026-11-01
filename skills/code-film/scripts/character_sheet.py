"""Build the sign-off sheets for a character file: turnaround, expressions, walk test.
Usage: uv run --with playwright --python 3.12 python -I character_sheet.py <character.js> <outdir> [--no-walk]
Writes turnaround.jpg, expressions.jpg, walk.mp4 and sheet.html into outdir.
"""
import base64
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SKILL = Path(__file__).resolve().parent.parent
ARGS = ["--ignore-gpu-blocklist"] + (["--use-angle=metal"] if sys.platform == "darwin" else [])

char, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
html = out / "sheet.html"
html.write_text((SKILL / "assets/character-sheet.tpl.html").read_text().replace("/*@@CHARACTER@@*/", char.read_text()))
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True, args=ARGS)
    page = browser.new_page(viewport={"width": 1320, "height": 800})
    logs = []
    page.on("pageerror", lambda e: logs.append(str(e)))
    page.on("console", lambda m: logs.append(m.text) if m.type == "error" else None)
    page.route("**/three.min.js", lambda r: r.fulfill(path=str(SKILL / "assets/vendor/three.min.js"), content_type="application/javascript"))
    page.goto(f"file://{html}?render=1")
    try:
        page.wait_for_function("window.__ready===true", timeout=60000)
    except Exception:
        sys.exit("Character did not build:\n" + "\n".join(logs[:8]))
    for kind, name in [("turn", "turnaround.jpg"), ("faces", "expressions.jpg")]:
        data = page.evaluate("([k, n]) => window.composeSheet(k, n)", [kind, 16])
        (out / name).write_bytes(base64.b64decode(data.split(",")[1]))
    browser.close()
if "--no-walk" not in sys.argv:
    subprocess.run([sys.executable, "-I", str(SKILL / "scripts/render.py"), str(html), str(out / "walk.mp4"), "--samples", "8", "--crf", "19"], check=True)
    (out / "walk.wav").unlink(missing_ok=True)
print("sheets in", out)
