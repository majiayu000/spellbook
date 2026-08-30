from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR = ROOT / "skills" / "codex" / "scripts" / "run_with_timeout.py"


def test_supervisor_returns_child_status() -> None:
    result = subprocess.run(
        [sys.executable, str(SUPERVISOR), "5", sys.executable, "-c", "raise SystemExit(7)"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 7


def test_supervisor_reports_missing_command() -> None:
    result = subprocess.run(
        [sys.executable, str(SUPERVISOR), "5", "/definitely/missing/codex"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 127
    assert "cannot start command" in result.stderr


def test_supervisor_terminates_the_child_process_group(tmp_path: Path) -> None:
    terminated = tmp_path / "grandchild-terminated"
    helper = tmp_path / "parent.py"
    helper.write_text(
        """\
import subprocess
import sys
import time

marker = sys.argv[1]
child_code = '''
import pathlib
import signal
import sys
import time

def stop(signum, frame):
    pathlib.Path(sys.argv[1]).write_text("terminated", encoding="utf-8")
    raise SystemExit(0)

signal.signal(signal.SIGTERM, stop)
time.sleep(60)
'''
subprocess.Popen([sys.executable, "-c", child_code, marker])
time.sleep(60)
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(SUPERVISOR), "0.3", sys.executable, str(helper), str(terminated)],
        capture_output=True,
        text=True,
        check=False,
    )

    for _ in range(20):
        if terminated.exists():
            break
        time.sleep(0.05)
    assert result.returncode == 124
    assert terminated.read_text(encoding="utf-8") == "terminated"
