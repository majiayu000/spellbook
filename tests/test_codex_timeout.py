from __future__ import annotations

import os
import runpy
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR = ROOT / "skills" / "codex" / "scripts" / "run_with_timeout.py"


def process_group_has_live_members(group_id: int) -> bool:
    timeout_module = runpy.run_path(str(SUPERVISOR))
    return timeout_module["process_group_has_live_members"](group_id)


def test_process_group_inspection_ignores_zombies(monkeypatch: pytest.MonkeyPatch) -> None:
    timeout_module = runpy.run_path(str(SUPERVISOR))
    has_live_members = timeout_module["process_group_has_live_members"]

    def zombie_processes(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="123 Z\n123 Z+\n", stderr="")

    monkeypatch.setattr(os, "killpg", lambda group_id, sent_signal: None)
    monkeypatch.setattr(subprocess, "run", zombie_processes)
    assert not has_live_members(123)


def test_process_group_inspection_finds_non_zombie_member(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeout_module = runpy.run_path(str(SUPERVISOR))
    has_live_members = timeout_module["process_group_has_live_members"]

    def live_processes(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="123 Z\n123 S\n", stderr="")

    monkeypatch.setattr(os, "killpg", lambda group_id, sent_signal: None)
    monkeypatch.setattr(subprocess, "run", live_processes)
    assert has_live_members(123)


def test_process_group_inspection_is_conservative_without_ps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeout_module = runpy.run_path(str(SUPERVISOR))
    has_live_members = timeout_module["process_group_has_live_members"]

    def missing_ps(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("ps")

    monkeypatch.setattr(os, "killpg", lambda group_id, sent_signal: None)
    monkeypatch.setattr(subprocess, "run", missing_ps)
    assert has_live_members(123)


def test_supervisor_returns_child_status() -> None:
    result = subprocess.run(
        [sys.executable, str(SUPERVISOR), "5", sys.executable, "-c", "raise SystemExit(7)"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 7


def test_supervisor_translates_child_signal_to_shell_status() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SUPERVISOR),
            "5",
            sys.executable,
            "-c",
            "import os, signal; os.kill(os.getpid(), signal.SIGTERM)",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 128 + signal.SIGTERM


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
    live_members = process_group_has_live_members(group_id)
    if live_members:
        os.killpg(group_id, signal.SIGKILL)
    assert result.returncode == 124
    assert not live_members


def test_supervisor_keeps_deadline_after_leader_exits_normally(tmp_path: Path) -> None:
    child_pid_file = tmp_path / "child-pid"
    group_id_file = tmp_path / "group-id"
    helper = tmp_path / "short-leader.py"
    helper.write_text(
        """\
import os
import pathlib
import subprocess
import sys
import time

child_pid_file, group_id_file = sys.argv[1:]
child_code = '''
import os
import pathlib
import sys
import time

target = pathlib.Path(sys.argv[1])
temporary = target.with_suffix(".tmp")
temporary.write_text(str(os.getpid()), encoding="utf-8")
temporary.replace(target)
time.sleep(60)
'''
pathlib.Path(group_id_file).write_text(str(os.getpgrp()), encoding="utf-8")
subprocess.Popen(
    [sys.executable, "-c", child_code, child_pid_file],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
while not pathlib.Path(child_pid_file).exists():
    time.sleep(0.01)
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SUPERVISOR),
            "0.3",
            sys.executable,
            str(helper),
            str(child_pid_file),
            str(group_id_file),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    group_id = int(group_id_file.read_text(encoding="utf-8"))
    live_members = process_group_has_live_members(group_id)
    if live_members:
        os.killpg(group_id, signal.SIGKILL)
    assert result.returncode == 124
    assert not live_members


@pytest.mark.parametrize(
    "termination_signal",
    [signal.SIGHUP, signal.SIGINT, signal.SIGQUIT, signal.SIGTERM],
)
def test_supervisor_forwards_termination_signal_to_process_group(
    tmp_path: Path, termination_signal: signal.Signals
) -> None:
    child_pid_file = tmp_path / "child-pid"
    helper = tmp_path / "child.py"
    helper.write_text(
        """\
import os
import pathlib
import sys
import time

target = pathlib.Path(sys.argv[1])
temporary = target.with_suffix(".tmp")
temporary.write_text(str(os.getpid()), encoding="utf-8")
temporary.replace(target)
time.sleep(60)
""",
        encoding="utf-8",
    )
    supervisor = subprocess.Popen(
        [sys.executable, str(SUPERVISOR), "60", sys.executable, str(helper), str(child_pid_file)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(100):
        if child_pid_file.exists():
            break
        time.sleep(0.05)
    child_pid = int(child_pid_file.read_text(encoding="utf-8"))

    supervisor.send_signal(termination_signal)
    return_code = supervisor.wait(timeout=10)
    live_members = process_group_has_live_members(child_pid)
    if live_members:
        os.killpg(child_pid, signal.SIGKILL)
    assert return_code == 128 + termination_signal
    assert not live_members
