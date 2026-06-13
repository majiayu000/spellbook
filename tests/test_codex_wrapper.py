import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "skills" / "codex-agent" / "scripts" / "codex-wrapper.sh"


class CodexWrapperTests(unittest.TestCase):
    def run_wrapper(self, args, env_extra=None):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bin_dir = tmp_path / "bin"
            bin_dir.mkdir()
            capture = tmp_path / "argv.txt"
            fake_codex = bin_dir / "codex"
            fake_codex.write_text(
                "#!/bin/bash\n"
                'if [[ "$1" == "exec" && "$2" == "--help" ]]; then\n'
                '  printf "%s\\n" "${CODEX_FAKE_EXEC_HELP:-}"\n'
                "  exit 0\n"
                "fi\n"
                'printf "%s\\n" "$@" > "$CODEX_WRAPPER_CAPTURE"\n',
                encoding="utf-8",
            )
            fake_codex.chmod(fake_codex.stat().st_mode | stat.S_IXUSR)

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
            env["CODEX_WRAPPER_CAPTURE"] = str(capture)
            if env_extra:
                env.update(env_extra)

            result = subprocess.run(
                ["bash", str(WRAPPER), *args],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            captured_args = capture.read_text(encoding="utf-8").splitlines() if capture.exists() else []
            return result, captured_args

    def test_rejects_workspace_read_network_write_sandbox(self):
        result, captured_args = self.run_wrapper(
            ["--dir", "/project", "--sandbox", "workspace-read-network-write", "task needing network"]
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("unsupported sandbox mode: workspace-read-network-write", result.stderr)
        self.assertEqual(captured_args, [])

    def test_rejects_unknown_full_auto_option(self):
        result, captured_args = self.run_wrapper(["--full-auto", "fix bug"])

        self.assertEqual(result.returncode, 2)
        self.assertIn("unsupported option: --full-auto", result.stderr)
        self.assertEqual(captured_args, [])

    def test_resume_preserves_requested_workdir(self):
        result, captured_args = self.run_wrapper(
            ["--dir", "/project", "--session", "abc123", "continue work"]
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            captured_args,
            [
                "exec",
                "-C",
                "/project",
                "resume",
                "abc123",
                "continue work",
            ],
        )

    def test_passes_config_overrides_to_new_exec_task(self):
        result, captured_args = self.run_wrapper(
            [
                "--dir",
                "/project",
                "--sandbox",
                "workspace-write",
                "--config",
                "sandbox_workspace_write.network_access=true",
                "install dependencies",
            ]
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            captured_args,
            [
                "exec",
                "-C",
                "/project",
                "-s",
                "workspace-write",
                "-c",
                "sandbox_workspace_write.network_access=true",
                "install dependencies",
            ],
        )

    def test_rejects_config_overrides_on_resume(self):
        result, captured_args = self.run_wrapper(
            ["--session", "abc123", "--config", "sandbox_workspace_write.network_access=true", "continue"]
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("--config is only supported for new codex exec tasks", result.stderr)
        self.assertEqual(captured_args, [])


if __name__ == "__main__":
    unittest.main()
