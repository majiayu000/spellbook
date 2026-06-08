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

    def test_allows_workspace_read_network_write_sandbox(self):
        result, captured_args = self.run_wrapper(
            ["--dir", "/project", "--sandbox", "workspace-read-network-write", "task needing network"]
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            captured_args,
            [
                "exec",
                "-C",
                "/project",
                "-s",
                "workspace-read-network-write",
                "task needing network",
            ],
        )

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


if __name__ == "__main__":
    unittest.main()
