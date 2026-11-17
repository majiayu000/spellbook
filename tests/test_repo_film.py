"""repo-film: lanes.py on throwaway git repositories, and the scene template's beat timing.

Synthetic repositories only. The timing checks run the template's own script in a bare
Node VM context; no browser, renderer or network is involved.
"""

import json
import math
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "repo-film"
LANES = SKILL / "scripts" / "lanes.py"
SCENE = SKILL / "template" / "scene.html"

# build() and headAt() only read window.FILM and the lanes JSON, so the inline script runs
# without a DOM. Prints the beat time of every commit node and where the graph head is.
BEATS_JS = r"""
const fs = require('fs'), vm = require('vm');
const html = fs.readFileSync(process.argv[1], 'utf8');
const src = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].pop()[1];
const ctx = vm.createContext({ window: { FILM: { hasMap: false, startLabel: '' } }, document: {} });
vm.runInContext(src, ctx);
const night = fs.readFileSync(0, 'utf8');
console.log(vm.runInContext(`night = ${night}; build(); JSON.stringify({
  G0, G1, beats: nodes.filter(n => n.kind !== 'start').map(n => n.at),
  head: [0.6, 6.5].map(t => headAt(t).x) })`, ctx));
"""


class RepoFilmTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name) / "repo"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
        self.minute = 0
        self.git("init", "-q", "-b", "main", str(self.repo), cwd=temp.name)

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.repo, env=self.env,
                              capture_output=True, text=True, check=True).stdout

    def commit(self, subject):
        self.minute += 1
        date = f"2026-11-10T20:{self.minute:02d}:00"
        (self.repo / f"f{self.minute}").write_text(subject, encoding="utf-8")
        self.git("add", "-A")
        self.env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        self.git("commit", "-q", "-m", subject)

    def merge(self, branch):
        self.minute += 1
        date = f"2026-11-10T20:{self.minute:02d}:00"
        self.env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        self.git("merge", "-q", "--no-ff", branch, "-m", f"Merge branch '{branch}'")

    def lanes(self):
        done = subprocess.run([sys.executable, str(LANES), str(self.repo), "--since", "2026-01-01",
                               "--until", "2027-01-01", "--branch", "main"],
                              env=self.env, capture_output=True, text=True, check=True)
        return json.loads(done.stdout)

    def beats(self, night):
        done = subprocess.run(["node", "-e", BEATS_JS, str(SCENE)], input=json.dumps(night),
                              capture_output=True, text=True, check=True)
        return json.loads(done.stdout)

    def assert_graph_grows(self, night):
        b = self.beats(night)
        beats = b["beats"]
        self.assertEqual(len(beats), len(night["commits"]))
        for x, at in enumerate(beats):
            self.assertTrue(isinstance(at, (int, float)) and math.isfinite(at), f"commit {x} has beat {at}")
        self.assertEqual(beats, sorted(beats))
        self.assertLess(beats[0], 2.0)                       # the first commit shows up early
        self.assertAlmostEqual(beats[-1], b["G1"])            # the last one when the growth ends
        self.assertGreater(len(set(beats)), len(beats) // 2)  # not all at once
        self.assertGreater(b["head"][1], b["head"][0])        # the camera follows the head
        return beats

    def test_stash_and_notes_are_not_branches(self):
        self.commit("feat: one")
        self.git("checkout", "-q", "-b", "wip")
        self.commit("feat: local only")
        self.git("checkout", "-q", "main")
        self.commit("fix: two")
        (self.repo / "f3").write_text("uncommitted", encoding="utf-8")
        self.git("stash", "-q")
        self.git("notes", "add", "-m", "a note", "HEAD")
        night = self.lanes()
        self.assertEqual([c["label"] for c in night["commits"]], ["one", "local only", "two"])
        self.assertEqual(night["merges"], 0)
        self.assertEqual([s["n"] for s in night["segments"]], [1])   # the local branch still counts

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed to run the scene template")
    def test_linear_history_grows_through_the_window(self):
        for i in range(8):
            self.commit(f"feat: step {i}")
        night = self.lanes()
        self.assertEqual(night["segments"], [])
        beats = self.assert_graph_grows(night)
        self.assertEqual(len(set(beats)), 8)

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed to run the scene template")
    def test_branch_right_after_the_first_commit(self):
        self.commit("feat: base")
        self.git("checkout", "-q", "-b", "side")
        self.commit("feat: side one")
        self.commit("fix: side two")
        self.git("checkout", "-q", "main")
        self.commit("docs: main one")
        self.merge("side")
        night = self.lanes()
        self.assertEqual([c["lane"] for c in night["commits"]][:2], [0, 1])
        self.assert_graph_grows(night)

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed to run the scene template")
    def test_main_line_stretch_before_the_first_branch(self):
        self.commit("feat: base")
        self.commit("feat: main two")
        self.git("checkout", "-q", "-b", "side")
        self.commit("feat: side one")
        self.git("checkout", "-q", "main")
        self.commit("docs: main three")
        self.merge("side")
        night = self.lanes()
        beats = self.assert_graph_grows(night)
        self.assertAlmostEqual(beats[0], self.beats(night)["G0"])


if __name__ == "__main__":
    unittest.main()
