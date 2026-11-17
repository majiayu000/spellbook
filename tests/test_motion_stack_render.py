"""motion-stack kit/render.mjs end to end on a tiny synthetic scene.

Needs Node, ffmpeg, a playwright package the kit can import and a Chromium the kit can find
(the same setup SKILL.md asks for); skipped otherwise. Nothing leaves the temporary directory.
"""

import json
import os
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


@unittest.skipUnless(kit_ready(), "needs node, ffmpeg, playwright and a Chromium for the motion-stack kit")
class ManifestPathTests(unittest.TestCase):
    """SKILL.md says to hand the manifest over with the film: it must not carry the user's home path."""

    def test_manifest_has_no_home_path(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        home = Path(temp.name).resolve() / "home"
        work = home / "Videos" / "film"
        work.mkdir(parents=True)
        (work / "scene.html").write_text(SCENE % {"seconds": 1, "tone": 0.3}, encoding="utf-8")
        # The Chromium the kit would use, reached through the throwaway home like a browser cache there.
        found = subprocess.run(
            ["node", "--input-type=module", "-e",
             f"const m = await import({json.dumps((RENDER.parent / 'env.mjs').as_uri())}); console.log(m.findChromium().path);"],
            capture_output=True, text=True, check=True).stdout.strip()
        (home / "browser").symlink_to(Path(found).parent, target_is_directory=True)
        env = {**os.environ, "HOME": str(home), "CHROMIUM_PATH": str(home / "browser" / Path(found).name)}
        # repo-film's make.mjs passes an absolute --out like this one.
        done = subprocess.run(["node", str(RENDER), "scene.html", "--out", str(work / "out" / "film.mp4"), "--no-audio"],
                              cwd=work, env=env, capture_output=True, text=True, timeout=300)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        text = (work / "out" / "film.mp4.manifest.json").read_text(encoding="utf-8")
        self.assertNotIn(str(home), text)
        manifest = json.loads(text)
        self.assertEqual(manifest["engine"]["chromium"], "~/browser/" + Path(found).name)
        self.assertTrue(manifest["command"].endswith("scene.html --out out/film.mp4 --no-audio"), manifest["command"])
        self.assertEqual(manifest["out"], "out/film.mp4")


FAILING_FFMPEG = """#!/bin/sh
# Stands in for an ffmpeg that cannot open its encoder: it leaves the empty output file and exits at once.
for last in "$@"; do :; done
: > "$last"
echo "fake ffmpeg: could not open encoder" >&2
exit 187
"""


@unittest.skipUnless(kit_ready(), "needs node, ffmpeg, playwright and a Chromium for the motion-stack kit")
class EncoderFailureTests(unittest.TestCase):
    """When the video cannot be encoded, the render stops there, says why and leaves no half-written video."""

    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        (self.work / "scene.html").write_text(SCENE % {"seconds": 1, "tone": 0.3}, encoding="utf-8")
        self.failing_ffmpeg = self.work / "ffmpeg"
        self.failing_ffmpeg.write_text(FAILING_FFMPEG, encoding="utf-8")
        self.failing_ffmpeg.chmod(0o755)

    def render(self, *args):
        done = subprocess.run(["node", str(RENDER), "scene.html", "--out", "out/film.mp4", *args],
                              cwd=self.work, capture_output=True, text=True, timeout=60)
        self.assertNotEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("\n    at ", done.stderr)  # a message, not a stack trace
        out = self.work / "out"
        return done, sorted(p.name for p in out.iterdir()) if out.exists() else []

    def test_odd_size_stops_before_the_first_frame(self):
        # libx264 with yuv420p needs even sides; ffmpeg itself only says so after reading frames.
        done, left = self.render("--width", "65")
        self.assertIn("even width and height", done.stderr)
        self.assertNotIn("frame ", done.stdout)
        self.assertEqual(left, [])

    def test_encoder_exit_stops_the_render(self):
        done, left = self.render("--ffmpeg", str(self.failing_ffmpeg), "--no-audio")
        self.assertIn("exit 187", done.stderr)
        self.assertEqual(left, [])


if __name__ == "__main__":
    unittest.main()
