import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cli


APP_ROOT = "/home/chris/jarvis"


def test_py_compile_usefulness_passes_for_existing_python_file():
    ok, msg = cli.run_task_usefulness_validation(
        "python3 -m py_compile cli.py",
        {"success": True},
        APP_ROOT,
        run_mode="shell_command",
    )
    assert ok
    assert "py_compile target_exists=True" in msg


def test_py_compile_usefulness_fails_for_missing_python_file():
    ok, msg = cli.run_task_usefulness_validation(
        "python3 -m py_compile missing_file.py",
        {"success": True},
        APP_ROOT,
        run_mode="shell_command",
    )
    assert not ok
    assert "py_compile target_exists=False" in msg


def test_py_compile_usefulness_fails_when_command_failed():
    ok, msg = cli.run_task_usefulness_validation(
        "python3 -m py_compile cli.py",
        {"success": False},
        APP_ROOT,
        run_mode="shell_command",
    )
    assert not ok
    assert "py_compile target_exists=False" in msg


print("PASS: task usefulness validation")
