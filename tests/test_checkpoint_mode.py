import inspect
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cli


def test_get_git_dirty_files_parses_status_lines():
    fake = type("Result", (), {
        "returncode": 0,
        "stdout": " M cli.py\n?? scripts/install_pre_commit_hook.sh\n",
        "stderr": "",
    })()

    with patch("cli.run_command_capture", return_value=fake):
        files, error = cli.get_git_dirty_files()

    assert error == ""
    assert files == ["cli.py", "scripts/install_pre_commit_hook.sh"], files


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


def test_build_allowed_dirty_path_pattern_escapes_single_file():
    assert cli.build_allowed_dirty_path_pattern("cli.py".split()) == "cli\\.py"


def test_build_allowed_dirty_path_pattern_groups_multiple_files():
    assert cli.build_allowed_dirty_path_pattern([
        "cli.py",
        "tests/test_checkpoint_mode.py",
    ]) == "(cli\\.py|tests/test_checkpoint_mode\\.py)"

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

def test_commit_checkpoint_validates_with_all_dirty_files_but_stages_selected_files():
    dirty_files = ["CHECKPOINT_SMOKE.txt", "README.md"]
    selected_files = ["README.md"]

    assert "CHECKPOINT_SMOKE.txt" in dirty_files
    assert "CHECKPOINT_SMOKE.txt" not in selected_files
    assert cli.build_allowed_dirty_path_pattern(dirty_files) == "(CHECKPOINT_SMOKE\\.txt|README\\.md)"

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


def test_context_shell_validation_rejects_unrelated_py_compile_target():
    assert not cli.context_shell_validation_step_is_allowed(
        "python3 -m py_compile files.py",
        "/home/chris/jarvis/cli.py",
    )


def test_context_shell_validation_allows_matching_py_compile_target():
    assert cli.context_shell_validation_step_is_allowed(
        "python3 -m py_compile cli.py",
        "/home/chris/jarvis/cli.py",
    )


def test_context_shell_validation_rejects_nonexistent_pytest_file():
    assert not cli.context_shell_validation_step_is_allowed(
        "python3 -m pytest tests/test_cli.py",
        "/home/chris/jarvis/cli.py",
    )


def test_context_shell_validation_allows_full_regression_suite():
    assert cli.context_shell_validation_step_is_allowed(
        "bash tests/run_all.sh",
        "/home/chris/jarvis/cli.py",
    )


def test_normalize_context_steps_drops_bad_validation_steps(monkeypatch):
    monkeypatch.setattr(cli, "get_project_state", lambda key, default="": {
        "main_script": "/home/chris/jarvis/cli.py",
        "main_script_name": "cli.py",
        "project_root": "/home/chris/jarvis",
    }.get(key, default))

    steps = [
        "edit /home/chris/jarvis/cli.py to add stricter validation",
        "python3 -m py_compile llm.py",
        "python3 -m pytest tests/test_cli.py",
        "bash tests/run_all.sh",
    ]

    normalized = cli.normalize_context_steps(
        steps,
        "edit cli.py to add stricter validation",
    )

    assert normalized == [
        "edit /home/chris/jarvis/cli.py to add stricter validation",
        "bash tests/run_all.sh",
    ]


def test_plan_targets_jarvis_core_detects_core_edit():
    assert cli.plan_targets_jarvis_core([
        "edit /home/chris/jarvis/cli.py to add stricter validation",
    ])


def test_plan_targets_jarvis_core_ignores_project_edit():
    assert not cli.plan_targets_jarvis_core([
        "edit /home/chris/jarvis/file_renamer/rename_files.py to add logging",
    ])


def test_context_shell_validation_rejects_unrelated_py_compile_for_test_edit():
    assert not cli.context_shell_validation_step_is_allowed(
        "python3 -m py_compile cli.py",
        "/home/chris/jarvis/tests/test_checkpoint_mode.py",
    )


def test_context_shell_validation_allows_matching_py_compile_for_test_edit():
    assert cli.context_shell_validation_step_is_allowed(
        "python3 -m py_compile tests/test_checkpoint_mode.py",
        "/home/chris/jarvis/tests/test_checkpoint_mode.py",
    )


def test_extract_requested_function_name_from_named_helper():
    assert cli.extract_requested_function_name(
        "add a function-level regression helper named smoke_marker_for_jarvis_core_validation that returns True"
    ) == "smoke_marker_for_jarvis_core_validation"


def test_extract_requested_function_name_from_function_named_phrase():
    assert cli.extract_requested_function_name(
        "create a function named validate_context_plan_step that returns True"
    ) == "validate_context_plan_step"


def test_deterministic_new_function_definition_returns_true():
    assert cli.deterministic_new_function_definition(
        "smoke_marker_for_jarvis_core_validation",
        "add a function named smoke_marker_for_jarvis_core_validation that returns True",
    ) == "def smoke_marker_for_jarvis_core_validation():\n    return True\n"


def test_deterministic_new_function_definition_returns_false():
    assert cli.deterministic_new_function_definition(
        "smoke_marker_for_jarvis_core_validation",
        "add a function named smoke_marker_for_jarvis_core_validation that returns False",
    ) == "def smoke_marker_for_jarvis_core_validation():\n    return False\n"


def test_append_top_level_function_before_entrypoint():
    original = 'def existing():\n    return True\n\nif __name__ == "__main__":\n    main()\n'
    addition = 'def added():\n    return False\n'

    updated = cli.append_top_level_function_before_entrypoint(original, addition)

    assert updated.index("def added") < updated.index('if __name__ == "__main__":')
    assert "def added():\n    return False\n" in updated


class SimpleMonkeyPatch:
    def __init__(self):
        self._patches = []

    def setattr(self, target, name=None, value=None):
        if isinstance(target, str):
            if name is None:
                raise TypeError("setattr expected value for dotted target")
            patcher = patch(target, name)
        else:
            if name is None:
                raise TypeError("setattr expected attribute name")
            patcher = patch.object(target, name, value)

        patcher.start()
        self._patches.append(patcher)

    def undo(self):
        while self._patches:
            self._patches.pop().stop()


def run_tests():
    test_items = [
        (name, fn)
        for name, fn in sorted(globals().items())
        if name.startswith("test_") and callable(fn)
    ]

    for name, fn in test_items:
        monkeypatch = SimpleMonkeyPatch()
        temp_dir = None

        try:
            kwargs = {}
            signature = inspect.signature(fn)

            if "monkeypatch" in signature.parameters:
                kwargs["monkeypatch"] = monkeypatch

            if "tmp_path" in signature.parameters:
                temp_dir = tempfile.TemporaryDirectory()
                kwargs["tmp_path"] = Path(temp_dir.name)

            try:
                fn(**kwargs)
            except Exception as exc:
                print(f"FAILED TEST: {name}")
                raise
        finally:
            monkeypatch.undo()
            if temp_dir is not None:
                temp_dir.cleanup()

    print(f"PASS: checkpoint mode ({len(test_items)} tests)")


if __name__ == "__main__":
    run_tests()

