"""The skills' Chromium finders (env.mjs) must name the folder whose package.json installs playwright.

launch() throws "playwright is not installed: run ... npm install in <dir>" when the package
cannot be required. Following that hint has to work, so <dir> must hold the package.json that
declares playwright. Runs each env.mjs in place with NODE_PATH cleared and a throwaway HOME;
skipped without node, or where playwright is installed for that copy anyway (no browser is started).
"""

import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
ENV_FILES = sorted(ROOT.glob("skills/*/kit/env.mjs")) + sorted(ROOT.glob("skills/*/scripts/lib/env.mjs"))

# Never starts a browser: when playwright resolves for this copy there is nothing to check.
PROBE_JS = r"""
const { createRequire } = await import('node:module');
try { createRequire(process.argv[1]).resolve('playwright'); console.log(JSON.stringify({ resolvable: true })); process.exit(0); } catch {}
const { launch } = await import(process.argv[1]);
try { await launch(); console.log(JSON.stringify({ launched: true })); }
catch (e) { console.log(JSON.stringify({ message: e.message })); }
"""


@unittest.skipUnless(shutil.which("node"), "needs node")
class InstallHintTests(unittest.TestCase):
    def test_motion_stack_kit_copy_is_checked(self):
        self.assertIn(ROOT / "skills" / "motion-stack" / "kit" / "env.mjs", ENV_FILES)

    def test_hint_points_at_the_package_json_that_installs_playwright(self):
        for env_file in ENV_FILES:
            with self.subTest(env=str(env_file.relative_to(ROOT))):
                with TemporaryDirectory() as home:
                    env = {k: v for k, v in os.environ.items() if k != "NODE_PATH"}
                    env.update(HOME=home, USERPROFILE=home)
                    done = subprocess.run(["node", "--input-type=module", "-e", PROBE_JS, env_file.as_uri()],
                                          capture_output=True, text=True, timeout=60, env=env)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                result = json.loads(done.stdout.strip().splitlines()[-1])
                if result.get("resolvable"):
                    self.skipTest(f"playwright is installed for {env_file}")
                message = result.get("message", "")
                hint = re.search(r"npm install` in (\S+)", message)
                self.assertIsNotNone(hint, message)
                folder = Path(unquote(urlparse("file://" + hint.group(1)).path))
                manifest = folder / "package.json"
                self.assertTrue(manifest.is_file(), f"{message!r}: no package.json in {folder}")
                self.assertIn("playwright", json.loads(manifest.read_text(encoding="utf-8")).get("dependencies", {}))


if __name__ == "__main__":
    unittest.main()
