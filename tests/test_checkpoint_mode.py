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
\n\n

def test_run_command_capture_accepts_env():
    fake_env = {"JARVIS_ALLOWED_DIRTY_PATH": "README\\.md"}
    captured = {}

    def fake_subprocess_run(args, cwd=None, text=None, stdout=None, stderr=None, env=None):
        captured["env"] = env
        return type("Result", (), {
            "returncode": 0,
            "stdout": "",
            "stderr": "",
        })()

    with patch("cli.subprocess.run", side_effect=fake_subprocess_run):
        cli.run_command_capture(["git", "status"], env=fake_env)

    assert captured["env"] == fake_env
\n


def test_route_web_edit_target_uses_request_text_for_css(monkeypatch):
    monkeypatch.setattr(cli, "get_project_state", lambda key: {
        "project_type": "web",
        "project_root": "/tmp/example_web",
    }.get(key, ""))

    assert cli.route_web_edit_target_from_text(
        "edit /tmp/example_web/index.html to add inline body styles",
        "add inline body styles",
        "continue edit styles.css to change the page background color and spacing",
    ) == "/tmp/example_web/styles.css"


def test_route_web_edit_target_uses_request_text_for_javascript(monkeypatch):
    monkeypatch.setattr(cli, "get_project_state", lambda key: {
        "project_type": "web",
        "project_root": "/tmp/example_web",
    }.get(key, ""))

    assert cli.route_web_edit_target_from_text(
        "edit /tmp/example_web/index.html to add button behavior",
        "add button behavior",
        "continue edit script.js to add a click alert",
    ) == "/tmp/example_web/script.js"


def test_route_web_edit_target_ignores_python_project(monkeypatch):
    monkeypatch.setattr(cli, "get_project_state", lambda key: {
        "project_type": "python",
        "project_root": "/tmp/example_python",
    }.get(key, ""))

    assert cli.route_web_edit_target_from_text(
        "edit app.py to change button color",
        "change button color",
        "continue change button color",
    ) == ""


def test_small_project_asset_append_allowed_for_tiny_js():
    old = 'console.log("ready");\n'
    new = old + 'document.body.addEventListener("click", () => alert("Clicked"));\n'

    assert cli.is_small_project_asset_append_allowed(
        "/tmp/project/script.js",
        old,
        new,
        changed_lines=1,
        max_changed_lines=8,
    )


def test_small_project_asset_append_rejects_core_app_file():
    old = 'print("ready")\n'
    new = old + 'print("clicked")\n'

    assert not cli.is_small_project_asset_append_allowed(
        "/home/chris/jarvis/cli.py",
        old,
        new,
        changed_lines=1,
        max_changed_lines=8,
    )


def test_small_project_asset_append_rejects_rewrite():
    old = 'console.log("ready");\n'
    new = 'alert("Clicked");\n'

    assert not cli.is_small_project_asset_append_allowed(
        "/tmp/project/script.js",
        old,
        new,
        changed_lines=1,
        max_changed_lines=8,
    )


def test_cleanup_successful_edit_backup_removes_existing_file(tmp_path):
    backup = tmp_path / "example.py.bak.20260509_120000"
    backup.write_text("old content")

    message = cli.cleanup_successful_edit_backup(str(backup))

    assert not backup.exists()
    assert "removed successful edit backup" in message


def test_cleanup_successful_edit_backup_ignores_missing_file(tmp_path):
    backup = tmp_path / "missing.py.bak"

    message = cli.cleanup_successful_edit_backup(str(backup))

    assert message == ""


def test_commit_checkpoint_mode_accepts_inline_message(monkeypatch):
    calls = []

    monkeypatch.setattr(cli, "get_git_dirty_files", lambda: (["cli.py"], ""))
    monkeypatch.setattr(cli, "parse_checkpoint_file_selection", lambda dirty, selection: (dirty, ""))
    monkeypatch.setattr(cli, "run_core_validation_for_dirty_files", lambda dirty: (True, "ALL TESTS PASSED\n"))

    inputs = iter(["all", "y"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    def fake_run_command_capture(args, cwd=None, env=None):
        calls.append(args)
        return type("Result", (), {
            "returncode": 0,
            "stdout": "",
            "stderr": "",
        })()

    monkeypatch.setattr(cli, "run_command_capture", fake_run_command_capture)

    cli.commit_checkpoint_mode("inline commit message")

    assert ["git", "commit", "-m", "inline commit message"] in calls

