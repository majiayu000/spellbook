"""Focused regression tests for the cross-tool agent health scanner."""

from __future__ import annotations

import ast
import importlib.util
import io
import json
import re
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "skill-usage-stats" / "scripts" / "agent_health.py"
SOURCES = sorted(SCRIPT.parent.glob("agent_health*.py"))
SKILL = ROOT / "skills" / "skill-usage-stats" / "SKILL.md"
SPEC = importlib.util.spec_from_file_location("agent_health", SCRIPT)
agent_health = importlib.util.module_from_spec(SPEC)
sys.modules["agent_health"] = agent_health
SPEC.loader.exec_module(agent_health)


def _json_line(payload: dict[str, object]) -> str:
    return json.dumps(payload, separators=(",", ":"))


def _codex_call(call_id: str, command: str) -> str:
    return _json_line({
        "type": "response_item",
        "payload": {
            "type": "function_call",
            "name": "exec_command",
            "call_id": call_id,
            "arguments": json.dumps({"cmd": command}),
        },
    })


def _codex_denial(call_id: str) -> str:
    return _json_line({
        "type": "response_item",
        "payload": {
            "type": "function_call_output",
            "call_id": call_id,
            "output": "command denied by sandbox policy",
        },
    })


class CommandSafetyTests(unittest.TestCase):
    def test_explicit_safe_readonly_candidates(self):
        expected = {
            "git status --short": "Bash(git status --short)",
            "git log -n 5": "Bash(git log -n 5)",
            "git diff --stat": "Bash(git diff --stat)",
            "git show --stat HEAD": "Bash(git show --stat HEAD)",
            "git branch --list": "Bash(git branch --list)",
            "gh pr view 141 --json title": "Bash(gh pr view 141 --json title)",
            "gh pr list --limit 10": "Bash(gh pr list --limit 10)",
            "pwd": "Bash(pwd)",
        }
        for command, rule in expected.items():
            with self.subTest(command=command):
                self.assertEqual(agent_health._safe_readonly_rule(command), rule)

    def test_destructive_or_composed_commands_are_never_candidates(self):
        commands = [
            "gh pr merge 141", "gh pr close 141", "gh api repos/o/r",
            "git branch -D old", "git stash drop", "git stash pop",
            "git status && rm -rf /", "git log | sh", "git diff > /tmp/x",
            "git show; touch /tmp/pwn", "cat > /tmp/x", "rm -rf ~/.claude/local",
            "git diff --output=/tmp/x", "git show --ext-diff HEAD",
            "ls *", "ls $HOME", "git status $(touch /tmp/pwn)",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertIsNone(agent_health._safe_readonly_rule(command))


class ParseHealthTests(unittest.TestCase):
    def test_non_object_claude_config_fails_loud(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            claude_dir = root / ".claude"
            claude_dir.mkdir()
            claude_json = root / ".claude.json"
            claude_json.write_text("[]", encoding="utf-8")

            check = agent_health.check_claude_settings(
                "en", claude_dir=claude_dir, claude_json=claude_json, project_dir=root
            )

        self.assertEqual(check.status, "fail")
        self.assertEqual(check.data["parse_error_count"], 1)
        self.assertEqual(check.errors[0].kind, "non_object_root")

    def test_corrupt_claude_transcript_is_structured_failure(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            path.write_text('{"message": {}}\nnot-json\n', encoding="utf-8")
            check = agent_health.check_claude_sessions("en", paths=[path])

        self.assertEqual(check.status, "fail")
        self.assertEqual(check.data["parse_error_count"], 1)
        self.assertTrue(check.errors)
        self.assertEqual(check.errors[0].line, 2)

    def test_corrupt_codex_transcript_is_structured_failure(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout.jsonl"
            path.write_text(_json_line({"type": "session_meta", "payload": {}}) + "\n{broken\n")
            check = agent_health.check_codex_sessions("en", paths=[path])

        self.assertEqual(check.status, "fail")
        self.assertTrue(check.data["schema_supported"])
        self.assertEqual(check.data["parse_error_count"], 1)

    def test_malformed_verified_codex_record_is_structured_failure(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout.jsonl"
            path.write_text(_json_line({"type": "response_item", "payload": []}) + "\n")
            check = agent_health.check_codex_sessions("en", paths=[path])

        self.assertEqual(check.status, "fail")
        self.assertTrue(check.data["schema_supported"])
        self.assertEqual(check.errors[0].kind, "invalid_record_schema")


class CleanupAndLanguageTests(unittest.TestCase):
    def test_install_cleanup_is_evidence_gated_and_reversible(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            claude_dir = home / ".claude"
            (claude_dir / "local").mkdir(parents=True)
            (home / ".local" / "share" / "claude" / "versions" / "2.0.0").mkdir(parents=True)
            claude_json = home / ".claude.json"
            claude_json.write_text('{"installMethod":"native"}', encoding="utf-8")
            completed = subprocess.CompletedProcess(["claude", "--version"], 0, "2.0.0\n", "")
            with (
                mock.patch.object(agent_health.shutil, "which", return_value="/usr/local/bin/claude"),
                mock.patch.object(agent_health.subprocess, "run", return_value=completed),
            ):
                check = agent_health.check_claude_install(
                    "en", home=home, claude_dir=claude_dir, claude_json=claude_json
                )

        report = "\n".join(check.lines).lower()
        self.assertTrue(check.data["cleanup_eligible"])
        self.assertIn("quarantine", report)
        self.assertIn("separate confirmation", report)
        self.assertNotIn("rm -rf", report)

    def test_skill_guidance_has_no_automatic_local_removal(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertNotIn("rm -rf ~/.claude/local", text)
        self.assertIn("quarantine", text.lower())

    def test_lang_en_emits_no_chinese_report_lines(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            with (
                mock.patch.object(agent_health, "HOME", home),
                mock.patch.object(agent_health, "CLAUDE_DIR", home / ".claude"),
                mock.patch.object(agent_health, "CODEX_DIR", home / ".codex"),
                mock.patch.object(agent_health, "CLAUDE_JSON", home / ".claude.json"),
                mock.patch.object(agent_health.shutil, "which", return_value=None),
                redirect_stdout(io.StringIO()) as stdout,
            ):
                result = agent_health.main(["--lang", "en"])

        output = stdout.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("# Agent Health Check", output)
        self.assertIsNone(re.search(r"[\u3400-\u9fff]", output))


class CodexHealthTests(unittest.TestCase):
    def test_codex_skill_definitions_and_collisions(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / "current"
            legacy = root / "legacy"
            for directory, install_name in ((current, "alpha"), (legacy, "beta")):
                skill = directory / install_name / "SKILL.md"
                skill.parent.mkdir(parents=True)
                skill.write_text(
                    "---\nname: shared\ndescription: usable\n---\n# Skill\n", encoding="utf-8"
                )
            invalid = current / "missing-description" / "SKILL.md"
            invalid.parent.mkdir(parents=True)
            invalid.write_text("---\nname: missing-description\n---\n", encoding="utf-8")

            check = agent_health.check_codex_skills("en", roots=[current, legacy])

        self.assertEqual(check.status, "warn")
        self.assertEqual(check.data["definition_count"], 3)
        self.assertIn("shared", check.data["collisions"])
        self.assertEqual(len(check.data["invalid"]), 1)

    def test_codex_denials_use_verified_schema_and_safe_candidates_only(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout.jsonl"
            lines = [
                _json_line({"type": "session_meta", "payload": {"id": "s1"}}),
                _codex_call("safe-1", "git status --short"), _codex_denial("safe-1"),
                _codex_call("safe-2", "git status --short"), _codex_denial("safe-2"),
                _codex_call("bad", "gh pr merge 141"), _codex_denial("bad"),
            ]
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            check = agent_health.check_codex_sessions("en", paths=[path])

        self.assertEqual(check.status, "warn")
        self.assertTrue(check.data["schema_supported"])
        self.assertEqual(check.data["denial_count"], 3)
        self.assertEqual(check.data["candidates"], ["Bash(git status --short)"])
        self.assertNotIn("merge", json.dumps(check.data))

    def test_codex_config_and_plugin_mcp_surfaces(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            config.write_text(
                'model = "gpt-test"\n[mcp_servers.docs]\nenabled = false\n', encoding="utf-8"
            )
            manifest = root / "plugins" / "cache" / "demo" / ".codex-plugin" / "plugin.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps({
                "name": "demo", "version": "1.0.0", "skills": ["skills/demo"],
                "mcpServers": {"docs": {"command": "redacted"}},
            }), encoding="utf-8")

            config_check = agent_health.check_codex_config("en", path=config)
            plugin_check = agent_health.check_codex_plugins("en", plugins_dir=root / "plugins")

        self.assertEqual(config_check.status, "ok")
        self.assertEqual(config_check.data["mcp"], {"docs": False})
        self.assertEqual(plugin_check.status, "ok")
        self.assertEqual(plugin_check.data["plugin_count"], 1)
        self.assertEqual(plugin_check.data["mcp_plugin_count"], 1)

    def test_missing_codex_surface_is_unsupported_not_equivalent(self):
        with TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing"
            check = agent_health.check_codex_plugins("en", plugins_dir=missing)

        self.assertEqual(check.status, "info")
        self.assertFalse(check.data["supported"])
        self.assertIn("unsupported", " ".join(check.lines).lower())


class SourceContractTests(unittest.TestCase):
    def test_script_stays_under_hard_line_limit(self):
        for source in SOURCES:
            with self.subTest(source=source.name):
                self.assertLess(len(source.read_text(encoding="utf-8").splitlines()), 800)

    def test_public_annotations_do_not_use_bare_dict_or_tuple(self):
        failures = []
        for source in SOURCES:
            tree = ast.parse(source.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                annotations = []
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    annotations.extend(arg.annotation for arg in node.args.args if arg.annotation)
                    if node.returns:
                        annotations.append(node.returns)
                elif isinstance(node, ast.AnnAssign):
                    annotations.append(node.annotation)
                for annotation in annotations:
                    if isinstance(annotation, ast.Name) and annotation.id in {"dict", "tuple"}:
                        failures.append((source.name, getattr(node, "lineno", 0), annotation.id))
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
