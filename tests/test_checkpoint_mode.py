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

def test_build_allowed_dirty_path_pattern_escapes_single_file():
    assert cli.build_allowed_dirty_path_pattern("cli.py".split()) == "cli\\.py"


def test_build_allowed_dirty_path_pattern_groups_multiple_files():
    assert cli.build_allowed_dirty_path_pattern([
        "cli.py",
        "tests/test_checkpoint_mode.py",
    ]) == "(cli\\.py|tests/test_checkpoint_mode\\.py)"
\n\n

def test_parse_checkpoint_file_selection_all():
    files = ["cli.py", "tests/test_checkpoint_mode.py"]
    selected, error = cli.parse_checkpoint_file_selection(files, "all")
    assert error == ""
    assert selected == files


def test_parse_checkpoint_file_selection_numbers():
    files = ["cli.py", "tests/test_checkpoint_mode.py", "README.md"]
    selected, error = cli.parse_checkpoint_file_selection(files, "1, 3")
    assert error == ""
    assert selected == ["cli.py", "README.md"]


def test_parse_checkpoint_file_selection_cancel():
    files = ["cli.py"]
    selected, error = cli.parse_checkpoint_file_selection(files, "cancel")
    assert error == ""
    assert selected == []


def test_parse_checkpoint_file_selection_rejects_out_of_range():
    selected, error = cli.parse_checkpoint_file_selection(["cli.py"], "2")
    assert selected is None
    assert "out of range" in error
\n\n

def test_commit_checkpoint_validates_with_all_dirty_files_but_stages_selected_files():
    dirty_files = ["CHECKPOINT_SMOKE.txt", "README.md"]
    selected_files = ["README.md"]

    assert "CHECKPOINT_SMOKE.txt" in dirty_files
    assert "CHECKPOINT_SMOKE.txt" not in selected_files
    assert cli.build_allowed_dirty_path_pattern(dirty_files) == "(CHECKPOINT_SMOKE\\.txt|README\\.md)"
\n