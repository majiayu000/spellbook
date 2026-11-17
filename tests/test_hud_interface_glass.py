"""hud-interface: the HTML-in-Canvas glass panel must stay clickable where it is drawn.

Opens assets/demo.html in a local Chromium with the CanvasDrawElement flag at
devicePixelRatio 1 and 2 and hit-tests the panel rows at the place the shader draws
them (the panel's own layout, 1:1 over the canvas). Needs Node, a playwright package
the skill's scripts can import and a Chromium they can find (the setup SKILL.md asks
for); skipped otherwise, and skipped for a browser without HTML-in-Canvas.
"""

import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "hud-interface"
ENV = SKILL / "scripts" / "lib" / "env.mjs"
DEMO = SKILL / "assets" / "demo.html"

# Prints, per dpr: glass mode, the panel's hit-test box next to the box it is drawn in (canvas
# origin, the panel's own layout width), which row each drawn row centre hits, and which rows
# are pressed after clicking the drawn centre of row 1.
PROBE_JS = r"""
const [envUrl, pageUrl] = process.argv.slice(1);
const { launch } = await import(envUrl);
const out = {};
for (const dpr of [1, 2]) {
  const browser = await launch({ args: ['--enable-blink-features=CanvasDrawElement', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: dpr });
    await page.goto(pageUrl, { waitUntil: 'load' }); await page.waitForTimeout(900);
    const probe = () => page.evaluate(() => {
      const panel = document.querySelector('#panel'), cv = panel.closest('canvas');
      const rows = [...panel.querySelectorAll('.hud-log-row')].slice(0, 5);
      if (!cv) return { glass: panel.dataset.hudGlass, rows: rows.length };
      // offsetLeft/offsetTop ignore the hit-test transform: this is where the texture shows the row.
      const off = el => { let x = 0, y = 0; for (; el; el = el.offsetParent) { x += el.offsetLeft; y += el.offsetTop; } return [x, y]; };
      const c = cv.getBoundingClientRect(), p = panel.getBoundingClientRect(), [px, py] = off(panel);
      const drawn = rows.map(r => { const [x, y] = off(r); return [c.x + x - px + r.offsetWidth / 2, c.y + y - py + r.offsetHeight / 2]; });
      const hits = drawn.map(([x, y]) => { const e = document.elementFromPoint(x, y), row = e && e.closest('.hud-log-row'); return row ? rows.indexOf(row) : (e ? e.tagName : null); });
      return { glass: panel.dataset.hudGlass, drawnBox: [c.x, c.y, panel.offsetWidth], hitBox: [p.x, p.y, p.width], hits, drawn };
    });
    const r = await probe();
    if (r.drawn) { await page.mouse.click(...r.drawn[1]); r.pressed = await page.evaluate(() => [...document.querySelectorAll('#panel .hud-log-row')].slice(0, 5).map(b => b.getAttribute('aria-pressed'))); }
    out[dpr] = r;
  } finally { await browser.close(); }
}
console.log(JSON.stringify(out));
"""


def browser_ready():
    if not shutil.which("node") or not ENV.exists():
        return False
    importable = subprocess.run(
        ["node", "--input-type=module", "-e",
         f"import {{ createRequire }} from 'node:module'; createRequire({json.dumps(ENV.as_uri())}).resolve('playwright');"
         f"const {{ findChromium }} = await import({json.dumps(ENV.as_uri())}); if (!findChromium()) process.exit(1);"],
        capture_output=True, text=True)
    return importable.returncode == 0


@unittest.skipUnless(browser_ready(), "needs node, playwright and a Chromium for the hud-interface scripts")
class GlassHitTestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        done = subprocess.run(["node", "--input-type=module", "-e", PROBE_JS, ENV.as_uri(), DEMO.as_uri()],
                              capture_output=True, text=True, timeout=300)
        if done.returncode:
            raise AssertionError(done.stdout + done.stderr)
        cls.result = json.loads(done.stdout.strip().splitlines()[-1])
        if any(r["glass"] != "on" for r in cls.result.values()):
            raise unittest.SkipTest("this Chromium has no HTML-in-Canvas: " + json.dumps(cls.result))

    def check(self, dpr):
        r = self.result[str(dpr)]
        for got, want in zip(r["hitBox"], r["drawnBox"]):
            self.assertAlmostEqual(got, want, delta=1, msg=f"dpr {dpr}: panel hit-test box {r['hitBox']} is not where it is drawn {r['drawnBox']}")
        self.assertEqual(r["hits"], [0, 1, 2, 3, 4], f"dpr {dpr}: drawn row centres hit {r['hits']}")
        self.assertEqual(r["pressed"], ["false", "true", "false", "false", "false"], f"dpr {dpr}: click on drawn row 1")

    def test_rows_hit_where_drawn_at_dpr1(self):
        self.check(1)

    def test_rows_hit_where_drawn_at_dpr2(self):
        self.check(2)


if __name__ == "__main__":
    unittest.main()
