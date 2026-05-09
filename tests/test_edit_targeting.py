import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cli


APP_ROOT = "/home/chris/jarvis"
PROJECT_ROOT = "/home/chris/jarvis/file_renamer"


def setup_context():
    cli.set_project_state("project_root", PROJECT_ROOT)
    cli.set_project_state("main_script_name", "rename_files.py")
    cli.set_project_state("main_script", f"{PROJECT_ROOT}/rename_files.py")
    cli.set_current_dir(PROJECT_ROOT)


def test_explicit_jarvis_core_file_resolves_to_app_root():
    setup_context()
    assert cli.resolve_edit_file_path("cli.py") == f"{APP_ROOT}/cli.py"


def test_explicit_project_file_resolves_to_project_root():
    setup_context()
    assert cli.resolve_edit_file_path("rename_files.py") == f"{PROJECT_ROOT}/rename_files.py"


def test_absolute_path_wins():
    setup_context()
    assert cli.resolve_edit_file_path(f"{APP_ROOT}/executor.py") == f"{APP_ROOT}/executor.py"


def test_context_step_with_explicit_core_file_targets_core():
    setup_context()
    steps = ["edit cli.py to change help output text"]
    normalized = cli.normalize_context_steps(steps, "change cli.py help output text")
    assert normalized == [f"edit {APP_ROOT}/cli.py to change help output text"]


def test_context_step_without_self_request_targets_project_main_script():
    setup_context()
    steps = ["edit the file to add logging.basicConfig after imports"]
    normalized = cli.normalize_context_steps(steps, "add logging to the file")
    assert normalized
    assert normalized[0].startswith(f"edit {PROJECT_ROOT}/rename_files.py to ")


print("PASS: edit targeting guards")
