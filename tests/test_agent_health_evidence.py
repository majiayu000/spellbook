"""Evidence-integrity regressions for the cross-tool health scanner."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "skill-usage-stats" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import agent_health


def _line(payload: dict[str, object]) -> str:
    return json.dumps(payload, separators=(",", ":"))


def _codex_call(call_id: str, command: str) -> str:
    return _line({
        "type": "response_item",
        "payload": {
            "type": "function_call",
            "name": "exec_command",
            "call_id": call_id,
            "arguments": json.dumps({"cmd": command}),
        },
    })


def _codex_output(call_id: str, output: str) -> str:
    return _line({
        "type": "response_item",
        "payload": {
            "type": "function_call_output",
            "call_id": call_id,
            "output": output,
        },
    })


def _codex_guardian(assessment_id: str, status: str, command: str) -> str:
    return _line({
        "type": "event_msg",
        "payload": {
            "type": "guardian_assessment",
            "id": assessment_id,
            "status": status,
            "action": {
                "type": "command",
                "source": "shell",
                "command": command,
                "cwd": "/tmp",
            },
        },
    })


def _claude_call(call_id: str, command: str) -> str:
    return _line({
        "message": {"content": [{
            "type": "tool_use",
            "name": "Bash",
            "id": call_id,
            "input": {"command": command},
        }]},
    })


def _claude_denial(call_id: str) -> str:
    return _line({
        "toolDenialKind": "permission",
        "message": {"content": [{"tool_use_id": call_id}]},
    })


def _claude_result(call_id: str) -> str:
    return _line({
        "message": {"content": [{
            "type": "tool_result",
            "tool_use_id": call_id,
            "content": "ordinary output",
        }]},
    })


class AgentDefinitionEvidenceTests(unittest.TestCase):
    def test_claude_agent_without_declared_name_is_invalid_not_invisible(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_name = root / "missing-name.md"
            missing_name.write_text(
                "---\ndescription: Has no declared name.\n---\n", encoding="utf-8"
            )
            no_frontmatter = root / "plain.md"
            no_frontmatter.write_text("# Not a valid agent definition\n", encoding="utf-8")

            check = agent_health.check_claude_agents("en", roots=[root])

        self.assertEqual(check.status, "warn")
        self.assertEqual(check.data["definition_count"], 2)
        self.assertEqual(set(check.data["invalid"]), {str(missing_name), str(no_frontmatter)})


class DenialPairingEvidenceTests(unittest.TestCase):
    def test_codex_guardian_ids_are_scoped_to_each_transcript(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first.jsonl"
            second = root / "second.jsonl"
            first.write_text(
                _codex_guardian("same-id", "denied", "git status --short") + "\n",
                encoding="utf-8",
            )
            second.write_text(
                _codex_guardian("same-id", "denied", "git log -n 1") + "\n",
                encoding="utf-8",
            )

            check = agent_health.check_codex_sessions("en", paths=[first, second])

        self.assertEqual(check.data["denial_count"], 2)
        self.assertEqual(check.data["unpaired_denial_count"], 0)
        self.assertEqual(check.data["candidates"], [])

    def test_codex_output_cannot_pair_with_a_later_call(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout.jsonl"
            path.write_text(
                "\n".join([
                    _codex_output("one", "command denied by sandbox policy"),
                    _codex_call("one", "git log -n 1 --format=%s"),
                    _codex_output("two", "command denied by sandbox policy"),
                    _codex_call("two", "git log -n 1 --format=%s"),
                ]) + "\n",
                encoding="utf-8",
            )

            check = agent_health.check_codex_sessions("en", paths=[path])

        self.assertEqual(check.status, "warn")
        self.assertEqual(check.data["denial_count"], 0)
        self.assertEqual(check.data["unmatched_output_count"], 2)
        self.assertEqual(check.data["incomplete_call_count"], 2)
        self.assertEqual(check.data["candidates"], [])

    def test_exact_denial_text_in_codex_stdout_is_not_denial_evidence(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout.jsonl"
            path.write_text(
                "\n".join([
                    _codex_call("one", "git status --short"),
                    _codex_output("one", "command denied by sandbox policy"),
                    _codex_call("two", "git status --short"),
                    _codex_output("two", "command denied by sandbox policy"),
                ]) + "\n",
                encoding="utf-8",
            )

            check = agent_health.check_codex_sessions("en", paths=[path])

        self.assertEqual(check.status, "info")
        self.assertEqual(check.data["denial_count"], 0)
        self.assertFalse(check.data["denial_evidence_supported"])
        self.assertEqual(check.data["incomplete_call_count"], 0)
        self.assertEqual(check.data["candidates"], [])

    def test_dangling_codex_call_is_incomplete_not_healthy(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout.jsonl"
            path.write_text(
                _codex_call("pending", "git status --short") + "\n",
                encoding="utf-8",
            )

            check = agent_health.check_codex_sessions("en", paths=[path])

        self.assertEqual(check.status, "warn")
        self.assertEqual(check.data["incomplete_call_count"], 1)
        self.assertEqual(check.data["denial_count"], 0)
        self.assertNotIn("no denials were observed", "\n".join(check.lines).lower())

    def test_unfinished_guardian_assessment_is_incomplete(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout.jsonl"
            path.write_text(
                _codex_guardian("pending", "in_progress", "git status --short") + "\n",
                encoding="utf-8",
            )

            check = agent_health.check_codex_sessions("en", paths=[path])

        self.assertEqual(check.status, "warn")
        self.assertEqual(check.data["incomplete_assessment_count"], 1)
        self.assertEqual(check.data["denial_count"], 0)

    def test_non_command_guardian_does_not_claim_command_denial_evidence(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout.jsonl"
            path.write_text(_line({
                "type": "event_msg",
                "payload": {
                    "type": "guardian_assessment",
                    "id": "patch-denied",
                    "status": "denied",
                    "action": {"type": "apply_patch", "cwd": "/tmp", "files": []},
                },
            }) + "\n", encoding="utf-8")

            check = agent_health.check_codex_sessions("en", paths=[path])

        self.assertEqual(check.status, "info")
        self.assertFalse(check.data["denial_evidence_supported"])
        self.assertEqual(check.data["denial_count"], 0)

    def test_claude_call_ids_are_scoped_to_each_transcript(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first.jsonl"
            second = root / "second.jsonl"
            first.write_text(
                _claude_call("same-id", "git status --short") + "\n"
                + _claude_denial("same-id") + "\n",
                encoding="utf-8",
            )
            second.write_text(
                _claude_call("same-id", "git log -n 1") + "\n"
                + _claude_denial("same-id") + "\n",
                encoding="utf-8",
            )

            check = agent_health.check_claude_denials("en", paths=[first, second])

        self.assertEqual(check.data["denial_count"], 2)
        self.assertEqual(check.data["unpaired_denial_count"], 0)
        self.assertEqual(check.data["candidates"], [])

    def test_claude_denial_cannot_pair_with_a_later_call(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            path.write_text(
                "\n".join([
                    _claude_denial("one"),
                    _claude_call("one", "git status --short"),
                    _claude_denial("two"),
                    _claude_call("two", "git status --short"),
                ]) + "\n",
                encoding="utf-8",
            )

            check = agent_health.check_claude_denials("en", paths=[path])

        self.assertEqual(check.data["denial_count"], 2)
        self.assertEqual(check.data["unpaired_denial_count"], 2)
        self.assertEqual(check.data["incomplete_call_count"], 2)
        self.assertEqual(check.data["unmatched_result_count"], 2)
        self.assertEqual(check.data["candidates"], [])

    def test_dangling_claude_call_is_incomplete_not_healthy(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            path.write_text(
                _claude_call("pending", "git status --short") + "\n",
                encoding="utf-8",
            )

            check = agent_health.check_claude_denials("en", paths=[path])

        self.assertEqual(check.status, "warn")
        self.assertEqual(check.data["incomplete_call_count"], 1)
        self.assertEqual(check.data["denial_count"], 0)
        self.assertIn("complete call/result pairs", "\n".join(check.lines))

    def test_unmatched_claude_result_is_incomplete_not_healthy(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            path.write_text(_claude_result("missing") + "\n", encoding="utf-8")

            check = agent_health.check_claude_denials("en", paths=[path])

        self.assertEqual(check.status, "warn")
        self.assertEqual(check.data["unmatched_result_count"], 1)
        self.assertEqual(check.data["denial_count"], 0)

    def test_duplicate_pending_call_ids_are_incomplete_in_both_scanners(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            codex_path = root / "rollout.jsonl"
            codex_path.write_text("\n".join([
                _codex_call("duplicate", "git status --short"),
                _codex_call("duplicate", "git status --short"),
                _codex_output("duplicate", "ordinary output"),
            ]) + "\n", encoding="utf-8")
            claude_path = root / "session.jsonl"
            claude_path.write_text("\n".join([
                _claude_call("duplicate", "git status --short"),
                _claude_call("duplicate", "git status --short"),
                _claude_result("duplicate"),
            ]) + "\n", encoding="utf-8")

            codex = agent_health.check_codex_sessions("en", paths=[codex_path])
            claude = agent_health.check_claude_denials("en", paths=[claude_path])

        self.assertEqual(codex.status, "warn")
        self.assertEqual(codex.data["duplicate_call_count"], 1)
        self.assertEqual(codex.data["incomplete_call_count"], 0)
        self.assertEqual(claude.status, "warn")
        self.assertEqual(claude.data["duplicate_call_count"], 1)
        self.assertEqual(claude.data["incomplete_call_count"], 0)


if __name__ == "__main__":
    unittest.main()
