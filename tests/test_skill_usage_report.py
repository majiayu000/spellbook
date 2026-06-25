"""Tests for the skill-usage-stats report script.

unittest + TemporaryDirectory, loading the in-skill script via importlib.
Fixtures use compact JSON (_dumps) to match real agent log format, since the
script's pre-filter substrings and ripgrep patterns expect no spaces.
"""

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
REPORT_SCRIPT = ROOT / "skills" / "skill-usage-stats" / "scripts" / "skill_usage_report.py"

# Register in sys.modules BEFORE exec_module: frozen dataclasses need
# sys.modules[cls.__module__] at class-definition time.
_spec = importlib.util.spec_from_file_location("skill_usage_report", REPORT_SCRIPT)
sur = importlib.util.module_from_spec(_spec)
sys.modules["skill_usage_report"] = sur
_spec.loader.exec_module(sur)

CODEX_FNAME = "rollout-2026-05-16T12-00-00-019abcde-0000-1111-2222-333333333333.jsonl"
CODEX_SESSION_ID = "019abcde-0000-1111-2222-333333333333"


def _dumps(obj):
    return json.dumps(obj, separators=(",", ":"))


def claude_line(skill, ts="2026-05-16T12:17:33.911Z", cwd="/p/proj1", session_id="s-A"):
    return _dumps({
        "timestamp": ts, "cwd": cwd, "sessionId": session_id, "gitBranch": "main",
        "message": {"role": "assistant",
                    "content": [{"type": "tool_use", "name": "Skill", "input": {"skill": skill, "args": "x"}}]},
    })


def codex_func_call(skill, ts="2026-05-16T12:18:00.000Z", workdir="/p/proj1"):
    args = _dumps({"cmd": f"sed -n '1,220p' /Users/u/.codex/skills/{skill}/SKILL.md", "workdir": workdir})
    return _dumps({
        "timestamp": ts, "type": "response_item",
        "payload": {"type": "function_call", "name": "exec_command", "arguments": args, "call_id": "c1"},
    })


def codex_mention(skill):
    return _dumps({
        "timestamp": "2026-05-16T12:19:00.000Z", "type": "response_item",
        "payload": {"type": "message", "role": "assistant",
                    "content": [{"type": "output_text", "text": f"see skills/{skill}/SKILL.md for details"}]},
    })


def write_codex_rollout(parent_sessions_dir, body):
    day_dir = parent_sessions_dir / "2026" / "05" / "16"
    day_dir.mkdir(parents=True, exist_ok=True)
    path = day_dir / CODEX_FNAME
    path.write_text(body, encoding="utf-8")
    return path


class ClaudeParseTests(unittest.TestCase):
    def test_extracts_skill_name_cwd_session(self):
        hits = sur._parse_claude_line(claude_line("x-post-eval"))
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].skill, "x-post-eval")
        self.assertEqual(hits[0].cwd, "/p/proj1")
        self.assertEqual(hits[0].session_id, "s-A")

    def test_empty_for_non_skill_tool(self):
        line = _dumps({"timestamp": "2026-05-16T12:00:00Z",
                       "message": {"content": [{"type": "tool_use", "name": "Read", "input": {}}]}})
        self.assertEqual(sur._parse_claude_line(line), [])

    def test_empty_for_garbage(self):
        self.assertEqual(sur._parse_claude_line("not json at all"), [])
        self.assertEqual(sur._parse_claude_line(""), [])

    def test_multiple_tools_in_one_line(self):
        line = _dumps({
            "timestamp": "2026-05-16T12:00:00Z", "cwd": "/p", "sessionId": "s",
            "message": {"content": [
                {"type": "tool_use", "name": "Skill", "input": {"skill": "a"}},
                {"type": "tool_use", "name": "Skill", "input": {"skill": "b"}},
            ]},
        })
        self.assertEqual([h.skill for h in sur._parse_claude_line(line)], ["a", "b"])


class CodexParseTests(unittest.TestCase):
    def test_extracts_skill_from_function_call(self):
        hit = sur._parse_codex_line(codex_func_call("code-review"), Path(CODEX_FNAME))
        self.assertIsNotNone(hit)
        self.assertEqual(hit.skill, "code-review")
        self.assertEqual(hit.cwd, "/p/proj1")

    def test_ignores_non_function_call_mention(self):
        self.assertIsNone(sur._parse_codex_line(codex_mention("code-review"), Path(CODEX_FNAME)))

    def test_workdir_fallback_to_session_meta(self):
        args = _dumps({"cmd": "sed -n '1p' /Users/u/.codex/skills/x/SKILL.md"})
        line = _dumps({"timestamp": "2026-05-16T12:00:00Z", "type": "response_item",
                       "payload": {"type": "function_call", "name": "exec_command", "arguments": args}})
        hit = sur._parse_codex_line(line, Path(CODEX_FNAME), meta_fallback={"cwd": "/meta/cwd", "id": "abc"})
        self.assertEqual(hit.cwd, "/meta/cwd")

    def test_session_id_from_filename(self):
        hit = sur._parse_codex_line(codex_func_call("x"), Path(CODEX_FNAME))
        self.assertEqual(hit.session_id, CODEX_SESSION_ID)

    def test_session_id_prefers_meta(self):
        hit = sur._parse_codex_line(codex_func_call("x"), Path(CODEX_FNAME),
                                    meta_fallback={"id": "meta-id", "cwd": "/p"})
        self.assertEqual(hit.session_id, "meta-id")

    def test_filename_uuid_regex_rejects_greedy_collision(self):
        m = sur.CODEX_FNAME_UUID_RE.search(Path(CODEX_FNAME).name)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), CODEX_SESSION_ID)


class CollectTests(unittest.TestCase):
    def test_collect_claude_counts_all_hits(self):
        with TemporaryDirectory() as t:
            proj = Path(t) / "projects" / "proj1"
            proj.mkdir(parents=True)
            (proj / "s.jsonl").write_text(
                claude_line("a") + "\n" + claude_line("a") + "\n" + claude_line("b") + "\n", encoding="utf-8")
            hits, fails, _ = sur.collect_claude(Path(t))
            self.assertEqual(len(hits), 3)
            self.assertEqual(fails, 0)

    def test_collect_codex_call_mode_counts_each_read(self):
        with TemporaryDirectory() as t:
            sessions = Path(t) / ".codex" / "sessions"
            write_codex_rollout(sessions,
                codex_func_call("code-review") + "\n" + codex_func_call("code-review") + "\n" + codex_func_call("x-post") + "\n")
            hits, _, _ = sur.collect_codex(Path(t) / ".codex", dedup_mode="call")
            self.assertEqual(len(hits), 3)

    def test_collect_codex_session_mode_dedups_per_session(self):
        with TemporaryDirectory() as t:
            sessions = Path(t) / ".codex" / "sessions"
            write_codex_rollout(sessions,
                codex_func_call("code-review") + "\n" + codex_func_call("code-review") + "\n" + codex_func_call("x-post") + "\n")
            hits, _, _ = sur.collect_codex(Path(t) / ".codex", dedup_mode="session")
            self.assertEqual(len(hits), 2)
            self.assertEqual(sorted(h.skill for h in hits), ["code-review", "x-post"])

    def test_collect_codex_ignores_mention_and_keeps_zero_failures(self):
        with TemporaryDirectory() as t:
            sessions = Path(t) / ".codex" / "sessions"
            write_codex_rollout(sessions, codex_mention("ghost") + "\n" + codex_func_call("real") + "\n")
            hits, fails, _ = sur.collect_codex(Path(t) / ".codex", dedup_mode="call")
            self.assertEqual([h.skill for h in hits], ["real"])
            self.assertEqual(fails, 0)

    def test_python_fallback_matches_rg_path(self):
        with TemporaryDirectory() as t:
            proj = Path(t) / "projects" / "p"
            proj.mkdir(parents=True)
            (proj / "s.jsonl").write_text(claude_line("a") + "\n", encoding="utf-8")
            self.assertEqual(len(list(sur._python_fallback(sur.CLAUDE_PRE_GREP, Path(t)))), 1)


class AggregateTests(unittest.TestCase):
    def test_zombie_detection(self):
        agg = sur.aggregate([sur.ClaudeHit("used", "2026-05-01T00:00:00Z", "/p", "s")], [], installed={"used", "zombie"})
        zombies = agg.installed - set(agg.stats)
        self.assertIn("zombie", zombies)
        self.assertNotIn("used", zombies)

    def test_runtime_flags_and_last_runtime(self):
        agg = sur.aggregate(
            [sur.ClaudeHit("x", "2026-05-01T00:00:00Z", "/p", "s")],
            [sur.CodexHit("x", "2026-06-01T00:00:00Z", "/p", "s2")], installed=set())
        stat = agg.stats["x"]
        self.assertEqual(stat.runtimes, {"claude", "codex"})
        self.assertEqual(stat.last_runtime, "codex")

    def test_first_and_last_used(self):
        hits = [sur.CodexHit("x", "2026-05-01T00:00:00Z", "/p", "s1"),
                sur.CodexHit("x", "2026-06-01T00:00:00Z", "/p", "s2"),
                sur.CodexHit("x", "2026-04-01T00:00:00Z", "/p", "s3")]
        agg = sur.aggregate([], hits, installed=set())
        self.assertEqual(agg.stats["x"].first_used, "2026-04-01T00:00:00Z")
        self.assertEqual(agg.stats["x"].last_used, "2026-06-01T00:00:00Z")

    def test_by_month_counter(self):
        hits = [sur.CodexHit("x", "2026-04-15T00:00:00Z", "/p", "s1"),
                sur.CodexHit("x", "2026-05-20T00:00:00Z", "/p", "s2"),
                sur.CodexHit("y", "2026-05-01T00:00:00Z", "/p", "s3")]
        agg = sur.aggregate([], hits, installed=set())
        self.assertEqual(agg.by_month["2026-04"], 1)
        self.assertEqual(agg.by_month["2026-05"], 2)


class RenderTests(unittest.TestCase):
    def _agg(self):
        return sur.aggregate(
            [sur.ClaudeHit("used", "2026-05-01T00:00:00Z", "/p", "s")], [], installed={"used", "zombie"})

    def test_markdown_default_is_chinese(self):
        md = sur.render_markdown(self._agg(), 10)  # default lang
        for section in ["# Skill 使用证据报告", "## 概览", "## 按总证据数排序的 skill",
                        "## 无本地证据的 skill", "## 月度趋势", "## 项目分布", "## 注意事项"]:
            self.assertIn(section, md)

    def test_markdown_english_when_requested(self):
        md = sur.render_markdown(self._agg(), 10, "en")
        for section in ["# Skill Usage Evidence Report", "## Overview", "## Top Skills",
                        "## Skills with No Local Evidence", "## Monthly Trend", "## Top Projects", "## Caveats"]:
            self.assertIn(section, md)

    def test_markdown_lists_zombie(self):
        self.assertIn("`zombie`", sur.render_markdown(self._agg(), 10))

    def test_table_lists_used_skill(self):
        self.assertIn("used", sur.render_table(self._agg(), 10))

    def test_csv_has_header_and_status(self):
        csv_text = sur.render_csv(self._agg())
        self.assertTrue(csv_text.startswith("skill,claude_calls,codex_calls"))
        self.assertIn("no_local_evidence", csv_text)

    def test_json_round_trips(self):
        payload = json.loads(sur.render_json(self._agg()))
        self.assertEqual(payload["installed_count"], 2)


class SinceFilterTests(unittest.TestCase):
    def test_codex_roots_for_since_restricts_months(self):
        with TemporaryDirectory() as t:
            sessions = Path(t) / "sessions"
            for ym in ["2026/04", "2026/05", "2026/06"]:
                (sessions / ym).mkdir(parents=True)
            self.assertEqual(len(sur._codex_roots_for_since(sessions, "2026-05")), 2)

    def test_collect_claude_since_filters_old_hits(self):
        with TemporaryDirectory() as t:
            proj = Path(t) / "projects" / "p"
            proj.mkdir(parents=True)
            (proj / "s.jsonl").write_text(
                claude_line("old", ts="2026-04-01T00:00:00Z") + "\n" + claude_line("new", ts="2026-06-01T00:00:00Z") + "\n",
                encoding="utf-8")
            hits, _, _ = sur.collect_claude(Path(t), since="2026-05")
            skills = [h.skill for h in hits]
            self.assertIn("new", skills)
            self.assertNotIn("old", skills)


if __name__ == "__main__":
    unittest.main()
