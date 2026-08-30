from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


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


@pytest.mark.parametrize("timeout", ["nan", "inf", "-inf"])
def test_supervisor_rejects_non_finite_timeout(timeout: str) -> None:
    result = subprocess.run(
        [sys.executable, str(SUPERVISOR), "--", timeout, sys.executable, "-c", "print('ran')"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "timeout must be finite and positive" in result.stderr
    assert "ran" not in result.stdout


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


def test_supervisor_kills_descendant_after_group_leader_exits(tmp_path: Path) -> None:
    group_id_file = tmp_path / "group-id"
    helper = tmp_path / "leader.py"
    helper.write_text(
        """\
import os
import pathlib
import signal
import subprocess
import sys
import time

group_id_file = sys.argv[1]
child_code = '''
import signal
import time

signal.signal(signal.SIGTERM, signal.SIG_IGN)
time.sleep(60)
'''
subprocess.Popen(
    [sys.executable, "-c", child_code],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
pathlib.Path(group_id_file).write_text(str(os.getpgrp()), encoding="utf-8")
time.sleep(60)
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(SUPERVISOR), "0.3", sys.executable, str(helper), str(group_id_file)],
        capture_output=True,
        text=True,
        check=False,
    )

    group_id = int(group_id_file.read_text(encoding="utf-8"))
    with pytest.raises(ProcessLookupError):
        os.killpg(group_id, 0)
    assert result.returncode == 124
