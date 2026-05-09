import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cli


def test_get_git_dirty_files_parses_status_lines():
    fake = type("Result", (), {
        "returncode": 0,
        "stdout": " M cli.py\\n?? scripts/install_pre_commit_hook.sh\\n",
        "stderr": "",
    })()

    with patch("cli.run_command_capture", return_value=fake):
        files, error = cli.get_git_dirty_files()

    assert error == ""
    assert files == ["cli.py", "scripts/install_pre_commit_hook.sh"]


def test_run_core_validation_uses_allowed_dirty_pattern():
    calls = []

    def fake_run_command_capture(args, cwd=None):
        calls.append(args)
        return type("Result", (), {
            "returncode": 0,
            "stdout": "",
            "stderr": "",
        })()

    def fake_subprocess_run(args, cwd=None, text=None, stdout=None, stderr=None, env=None):
        calls.append(args)
        assert env["JARVIS_ALLOWED_DIRTY_PATH"] == "(cli\\.py|tests/test_checkpoint_mode\\.py)"
        return type("Result", (), {
            "returncode": 0,
            "stdout": "ALL TESTS PASSED",
            "stderr": "",
        })()

    with patch("cli.run_command_capture", side_effect=fake_run_command_capture):
        with patch("cli.subprocess.run", side_effect=fake_subprocess_run):
            ok, output = cli.run_core_validation_for_dirty_files([
                "cli.py",
                "tests/test_checkpoint_mode.py",
            ])

    assert ok
    assert "ALL TESTS PASSED" in output


print("PASS: checkpoint mode")
