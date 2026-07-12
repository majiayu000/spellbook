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
core = importlib.import_module("agent_health_core")


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


def _codex_output(call_id: str, output: object) -> str:
    return _json_line({
        "type": "response_item",
        "payload": {
            "type": "function_call_output",
            "call_id": call_id,
            "output": output,
        },
    })


def _codex_denial(call_id: str) -> str:
    return _codex_output(call_id, "command denied by sandbox policy")


class CommandSafetyTests(unittest.TestCase):
    def test_explicit_safe_readonly_candidates(self):
        expected = {
            "git status --short": "Bash(git status --short)",
            "git log -n 5": "Bash(git log -n 5)",
            "git diff --stat": "Bash(git diff --stat)",
            "git show --stat HEAD": "Bash(git show --stat HEAD)",
            "git branch --list": "Bash(git branch --list)",
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
            "git branch --list --edit-description", "tree -o /tmp/tree.txt",
            "tree --output=/tmp/tree.txt", "gh pr view 141 --web",
            "gh pr view 141 --json title", "gh pr list --limit 10",
            "ls *", "ls $HOME", "git status $(touch /tmp/pwn)",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertIsNone(agent_health._safe_readonly_rule(command))

    def test_background_shell_operator_is_never_a_candidate(self):
        for command in ("git status &", "git status&"):
            with self.subTest(command=command):
                self.assertIsNone(agent_health._safe_readonly_rule(command))

    def test_gh_web_boolean_forms_are_never_candidates(self):
        commands = [
            "gh pr view 141 --web=true",
            "gh pr view 141 --web=false",
            "gh pr view 141 -w=true",
            "gh pr view 141 -w=false",
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

    def test_unparseable_frontmatter_line_is_structured_failure(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "broken" / "SKILL.md"
            skill.parent.mkdir()
            skill.write_text(
                "---\nname: broken\nnot valid frontmatter\ndescription: usable\n---\n",
                encoding="utf-8",
            )

            check = agent_health.check_codex_skills("en", roots=[root])

        self.assertEqual(check.status, "fail")
        self.assertEqual(check.data["parse_error_count"], 1)
        self.assertEqual(check.errors[0].kind, "invalid_frontmatter")
        self.assertEqual(check.errors[0].line, 3)

    def test_folded_frontmatter_description_remains_valid(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "folded" / "SKILL.md"
            skill.parent.mkdir()
            skill.write_text(
                "---\n"
                "name: folded\n"
                "description: >-\n"
                "  Cross-tool health scanner with\n"
                "  structured local evidence.\n"
                "---\n",
                encoding="utf-8",
            )

            check = agent_health.check_codex_skills("en", roots=[root])

        self.assertEqual(check.status, "ok")
        self.assertEqual(check.data["parse_error_count"], 0)
        self.assertEqual(check.data["definition_count"], 1)

    def test_sequence_frontmatter_remains_valid(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "allowed-tools" / "SKILL.md"
            skill.parent.mkdir()
            skill.write_text(
                "---\n"
                "name: allowed-tools\n"
                "description: Valid list frontmatter.\n"
                "allowed-tools:\n"
                "- Read\n"
                "- Grep\n"
                "---\n",
                encoding="utf-8",
            )

            check = agent_health.check_codex_skills("en", roots=[root])

        self.assertEqual(check.status, "ok")
        self.assertEqual(check.data["parse_error_count"], 0)
        self.assertEqual(check.data["definition_count"], 1)

    def test_sequence_after_scalar_is_structured_failure(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "broken-sequence" / "SKILL.md"
            skill.parent.mkdir()
            skill.write_text(
                "---\n"
                "name: broken-sequence\n"
                "description: Scalar value cannot own a sequence.\n"
                "- Read\n"
                "---\n",
                encoding="utf-8",
            )

            check = agent_health.check_codex_skills("en", roots=[root])

        self.assertEqual(check.status, "fail")
        self.assertEqual(check.data["parse_error_count"], 1)
        self.assertEqual(check.errors[0].kind, "invalid_frontmatter")
        self.assertEqual(check.errors[0].line, 4)

    def test_response_item_payload_without_type_fails_scan(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout.jsonl"
            path.write_text(
                _json_line({"type": "response_item", "payload": {"call_id": "missing-type"}})
                + "\n",
                encoding="utf-8",
            )
            check = agent_health.check_codex_sessions("en", paths=[path])

        self.assertEqual(check.status, "fail")
        self.assertTrue(check.data["schema_supported"])
        self.assertEqual(check.data["parse_error_count"], 1)
        self.assertEqual(check.errors[0].kind, "invalid_record_schema")
        with (
            mock.patch.object(agent_health, "run_checks", return_value=[check]),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(agent_health.main(["--lang", "en"]), 1)


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

    def test_plain_permission_denied_output_is_not_a_tool_denial(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout.jsonl"
            lines = [
                _codex_call("plain-1", "git status --short"),
                _codex_output("plain-1", "Permission denied while reading a repository file"),
                _codex_call("plain-2", "git status --short"),
                _codex_output("plain-2", "Permission denied while reading a repository file"),
            ]
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            check = agent_health.check_codex_sessions("en", paths=[path])

        self.assertEqual(check.status, "ok")
        self.assertTrue(check.data["schema_supported"])
        self.assertEqual(check.data["denial_count"], 0)
        self.assertEqual(check.data["candidates"], [])

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


class HealthCoverageTests(unittest.TestCase):
    def test_claude_collectors_cover_agents_hooks_denials_context_and_metadata(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            current_agents = root / "project-agents"
            global_agents = root / "global-agents"
            for directory in (current_agents, global_agents):
                agent = directory / "reviewer.md"
                agent.parent.mkdir(parents=True)
                agent.write_text(
                    "---\nname: shared-reviewer\ndescription: Reviews evidence.\n---\n",
                    encoding="utf-8",
                )
            invalid = current_agents / "invalid.md"
            invalid.write_text("---\nname: incomplete\n---\n", encoding="utf-8")

            transcript = root / "session.jsonl"
            records = [
                {"attachment": {"hookName": "PreToolUse:Bash", "durationMs": 2501}},
                {
                    "toolDenialKind": "permission",
                    "message": {"content": [
                        {"type": "tool_use", "name": "Bash", "id": "d1", "input": {"command": "git log -n 1"}},
                        {"tool_use_id": "d1"},
                    ]},
                },
                {
                    "toolDenialKind": "permission",
                    "message": {"content": [
                        {"type": "tool_use", "name": "Bash", "id": "d2", "input": {"command": "git log -n 1"}},
                        {"tool_use_id": "d2"},
                    ]},
                },
            ]
            transcript.write_text(
                "\n".join(_json_line(record) for record in records) + "\n",
                encoding="utf-8",
            )

            claude_dir = root / ".claude"
            (claude_dir / "skills" / "demo").mkdir(parents=True)
            (claude_dir / "CLAUDE.md").write_text("one\ntwo\n", encoding="utf-8")
            claude_json = root / ".claude.json"
            claude_json.write_text(
                json.dumps({"mcpServers": {"docs": {}}, "pluginUsage": {"demo": {}}}),
                encoding="utf-8",
            )

            agents = agent_health.check_claude_agents(
                "en", roots=[current_agents, global_agents]
            )
            hooks = agent_health.check_claude_hooks("en", paths=[transcript])
            denials = agent_health.check_claude_denials("en", paths=[transcript])
            context = agent_health.check_claude_context("en", claude_dir=claude_dir)
            metadata = agent_health.check_claude_mcp_plugins(
                "en", claude_json=claude_json
            )

        self.assertEqual(agents.status, "warn")
        self.assertIn("shared-reviewer", agents.data["collisions"])
        self.assertEqual(len(agents.data["invalid"]), 1)
        self.assertEqual(hooks.status, "warn")
        self.assertEqual(hooks.data["slow"], ["PreToolUse:Bash"])
        self.assertEqual(denials.data["candidates"], ["Bash(git log -n 1)"])
        self.assertEqual(context.data["context_lines"], 3)
        self.assertEqual(context.data["skill_count"], 1)
        self.assertEqual(metadata.data["mcp"], ["docs"])
        self.assertEqual(metadata.data["plugin_count"], 1)

    def test_core_readers_report_invalid_input_without_swallowing(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad_json = root / "bad.json"
            bad_json.write_text("{", encoding="utf-8")
            bad_toml = root / "bad.toml"
            bad_toml.write_text("[broken", encoding="utf-8")
            bad_frontmatter = root / "SKILL.md"
            bad_frontmatter.write_text("---\nname: broken\n", encoding="utf-8")
            bad_jsonl = root / "session.jsonl"
            bad_jsonl.write_text("[]\n", encoding="utf-8")

            json_result = core.read_json_object(bad_json)
            toml_result = core.read_toml_object(bad_toml)
            frontmatter_result = core.read_frontmatter(bad_frontmatter)
            records, jsonl_errors = core.read_jsonl_objects([bad_jsonl, root])

        self.assertEqual(json_result.errors[0].kind, "invalid_json")
        self.assertEqual(toml_result.errors[0].kind, "invalid_toml")
        self.assertEqual(frontmatter_result.errors[0].kind, "invalid_frontmatter")
        self.assertEqual(records, [])
        self.assertEqual(
            {issue.kind for issue in jsonl_errors}, {"non_object_record", "read_error"}
        )
        self.assertIsNone(core.safe_readonly_rule("git status '"))
        self.assertTrue(core.contains_denial("command denied by sandbox policy"))
        self.assertFalse(core.contains_denial({"nested": ["blocked by policy"]}))
        self.assertFalse(core.contains_denial("log entry: request not approved"))
        self.assertEqual(core.semver("codex 2.3.4+build"), (2, 3, 4))

    def test_claude_settings_and_metadata_reject_wrong_field_types(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            claude_dir = root / ".claude"
            claude_dir.mkdir()
            (claude_dir / "settings.json").write_text(
                json.dumps({"permissions": []}), encoding="utf-8"
            )
            claude_json = root / ".claude.json"
            claude_json.write_text(
                json.dumps({"mcpServers": [], "pluginUsage": "invalid"}),
                encoding="utf-8",
            )

            settings = agent_health.check_claude_settings(
                "en", claude_dir=claude_dir, claude_json=claude_json, project_dir=root
            )
            metadata = agent_health.check_claude_mcp_plugins(
                "en", claude_json=claude_json
            )

        self.assertEqual(settings.status, "fail")
        self.assertIn("permissions must be a JSON object", settings.errors[0].message)
        self.assertEqual(metadata.status, "fail")
        self.assertEqual(metadata.data["parse_error_count"], 2)

    def test_codex_collectors_cover_install_context_custom_denial_and_schema_errors(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            config.write_text(
                '[mcp_servers.docs]\nenabled = "yes"\n', encoding="utf-8"
            )
            agents_md = root / "AGENTS.md"
            agents_md.write_text("first\nsecond\n", encoding="utf-8")

            manifest = root / "plugins" / "demo" / ".codex-plugin" / "plugin.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                json.dumps({"name": "demo", "skills": "bad", "mcpServers": 3}),
                encoding="utf-8",
            )

            transcript = root / "rollout.jsonl"
            transcript.write_text(
                "\n".join([
                    _json_line({"type": "session_meta", "payload": {"id": "s1"}}),
                    _json_line({"type": "response_item", "payload": {
                        "type": "custom_tool_call", "call_id": "custom-1"
                    }}),
                    _json_line({"type": "response_item", "payload": {
                        "type": "custom_tool_call_output", "call_id": "custom-1",
                        "output": "tool denial: not approved",
                    }}),
                ]) + "\n",
                encoding="utf-8",
            )

            completed = subprocess.CompletedProcess(
                ["codex", "--version"], 0, "codex-cli 2.3.4\n", ""
            )
            with (
                mock.patch.object(
                    agent_health.codex_checks.shutil, "which", return_value="/usr/bin/codex"
                ),
                mock.patch.object(
                    agent_health.codex_checks.subprocess, "run", return_value=completed
                ),
            ):
                install = agent_health.check_codex_install("en")
            config_check = agent_health.check_codex_config("en", path=config)
            context = agent_health.check_codex_agents_md("en", paths=[agents_md])
            plugins = agent_health.check_codex_plugins(
                "en", plugins_dir=root / "plugins"
            )
            sessions = agent_health.check_codex_sessions("en", paths=[transcript])

        self.assertEqual(install.status, "ok")
        self.assertEqual(install.data["version"], "codex-cli 2.3.4")
        self.assertEqual(config_check.status, "fail")
        self.assertEqual(context.data["documents"][0]["lines"], 3)
        self.assertEqual(plugins.status, "fail")
        self.assertEqual(plugins.data["plugin_count"], 1)
        self.assertEqual(sessions.status, "warn")
        self.assertEqual(sessions.data["unpaired_denial_count"], 1)

    def test_codex_argument_parser_rejects_unverified_shapes(self):
        parser = agent_health.codex_checks._parse_exec_command
        path = Path("rollout.jsonl")
        cases = [None, "{", "[]", json.dumps({}), json.dumps({"cmd": 3})]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                command, issue = parser(path, 7, arguments)
                self.assertIsNone(command)
                self.assertIsNotNone(issue)
                self.assertEqual(issue.line, 7)

    def test_codex_denial_parser_fails_closed_on_malformed_verified_records(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout.jsonl"
            records = [
                {"type": "session_meta", "payload": []},
                {"type": "response_item", "payload": {
                    "type": "function_call", "name": "exec_command",
                    "arguments": json.dumps({"cmd": "git status"}),
                }},
                {"type": "response_item", "payload": {
                    "type": "function_call", "call_id": "missing-name",
                }},
                {"type": "response_item", "payload": {
                    "type": "function_call_output", "output": "blocked by policy",
                }},
                {"type": "response_item", "payload": {
                    "type": "function_call_output", "call_id": "missing-output",
                }},
            ]
            path.write_text(
                "\n".join(_json_line(record) for record in records) + "\n",
                encoding="utf-8",
            )

            check = agent_health.check_codex_sessions("en", paths=[path])

        self.assertEqual(check.status, "fail")
        self.assertTrue(check.data["schema_supported"])
        self.assertEqual(check.data["parse_error_count"], 5)
        self.assertEqual(
            {issue.kind for issue in check.errors}, {"invalid_record_schema"}
        )

    def test_report_outputs_and_optional_update_check_are_explicit(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            markdown_path = root / "health.md"
            json_path = root / "health.json"
            check = core.Check("demo", "Demo", status="info")
            check.add("Unsupported test surface.")
            with (
                mock.patch.object(agent_health, "run_checks", return_value=[check]),
                redirect_stdout(io.StringIO()),
            ):
                result = agent_health.main([
                    "--lang", "en", "--out", str(markdown_path), "--json", str(json_path)
                ])

            response = mock.MagicMock()
            response.__enter__.return_value.read.return_value = b"2.1.0"
            with (
                mock.patch.dict(agent_health.os.environ, {}, clear=True),
                mock.patch.object(agent_health.urllib.request, "urlopen", return_value=response),
            ):
                update = agent_health.check_updates("2.0.0", "en")
            with mock.patch.dict(
                agent_health.os.environ,
                {"CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"},
                clear=True,
            ):
                disabled = agent_health.check_updates("2.0.0", "en")
            markdown = markdown_path.read_text(encoding="utf-8")
            payload = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        self.assertIn("# Agent Health Check", markdown)
        self.assertEqual(payload["summary"]["info"], 1)
        self.assertEqual(update.status, "warn")
        self.assertEqual(update.data["claude_latest"], "2.1.0")
        self.assertEqual(disabled.status, "info")


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
