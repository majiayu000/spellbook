"""motion-stack kit/render.mjs end to end on a tiny synthetic scene.

Needs Node, ffmpeg, a playwright package the kit can import and a Chromium the kit can find
(the same setup SKILL.md asks for); skipped otherwise. Nothing leaves the temporary directory.
"""

import json
import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / "skills" / "motion-stack" / "kit" / "render.mjs"

SCENE = """<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0">
<canvas id="c" width="64" height="36"></canvas><script>
const SECONDS = %(seconds)s, TONE = %(tone)s;
window.motion = { width: 64, height: 36, fps: 10, duration: 1,
  frame(t) { const g = document.getElementById('c').getContext('2d'); g.fillStyle = `rgb(${Math.round(t * 200)},40,90)`; g.fillRect(0, 0, 64, 36); },
  audio() { const sr = 48000, ch = new Float32Array(Math.round(SECONDS * sr));
    for (let i = 0; i < ch.length; i++) ch[i] = TONE * Math.sin(2 * Math.PI * 440 * i / sr);
    return { sampleRate: sr, channels: [ch] }; } };
</script></body></html>
"""


def kit_ready():
    if not shutil.which("node") or not RENDER.exists():
        return False
    importable = subprocess.run(
        ["node", "--input-type=module", "-e",
         f"import {{ createRequire }} from 'node:module'; createRequire({json.dumps(RENDER.as_uri())}).resolve('playwright');"],
        capture_output=True, text=True)
    if importable.returncode:
        return False
    return subprocess.run(["node", str(RENDER), "--check"], capture_output=True, text=True).returncode == 0


@unittest.skipUnless(kit_ready(), "needs node, ffmpeg, playwright and a Chromium for the motion-stack kit")
class RenderLoudnessTests(unittest.TestCase):
    def render(self, seconds, tone, *args):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        work = Path(temp.name)
        (work / "scene.html").write_text(SCENE % {"seconds": seconds, "tone": tone}, encoding="utf-8")
        done = subprocess.run(["node", str(RENDER), "scene.html", "--out", "out/film.mp4", *args],
                              cwd=work, capture_output=True, text=True, timeout=300)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        manifest = json.loads((work / "out" / "film.mp4.manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(p.name for p in (work / "out").iterdir()),
                         ["film.mp4", "film.mp4.manifest.json", "film.wav"])
        return manifest["audio"]["loudness"]

    def test_short_range_keeps_the_level_and_writes_the_manifest(self):
        # SKILL.md: `--from 0 --to 0.1` to get the WAV quickly; 0.1 s is shorter than one loudness block
        loud = self.render(1, 0.3, "--from", "0", "--to", "0.1")
        self.assertIn("skipped", loud)

    def test_silent_sound_keeps_the_level_and_writes_the_manifest(self):
        loud = self.render(1, 0)
        self.assertIn("skipped", loud)

    def test_audible_sound_is_brought_to_the_target(self):
        loud = self.render(1, 0.3)
        self.assertNotIn("skipped", loud)
        self.assertAlmostEqual(loud["after_lufs"], -14, delta=1.5)


if __name__ == "__main__":
    unittest.main()
