import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cli


APP_ROOT = "/home/chris/jarvis"
PROJECT_ROOT = "/home/chris/jarvis/file_renamer"


def test_jarvis_core_context_uses_app_root():
    cli.set_project_state("project_root", PROJECT_ROOT)

    ctx = cli.build_execution_context(f"{APP_ROOT}/cli.py", "test")

    assert ctx["target_scope"] == "jarvis_core"
    assert ctx["validation_cwd"] == APP_ROOT
    assert ctx["allowed_dirty_paths"] == ["cli.py"]


def test_core_command_normalization_handles_relative_paths():
    cli.set_project_state("project_root", PROJECT_ROOT)

    ctx = cli.build_execution_context(f"{APP_ROOT}/cli.py", "test")

    assert cli.normalize_command_for_execution_context(
        "python3 -m py_compile cli.py", ctx
    ) == f"python3 -m py_compile {APP_ROOT}/cli.py"

    assert cli.normalize_command_for_execution_context(
        "python3 -m py_compile ./cli.py", ctx
    ) == f"python3 -m py_compile {APP_ROOT}/cli.py"

    assert cli.normalize_command_for_execution_context(
        "sed -n '1,20p' ./verifier.py", ctx
    ) == f"sed -n '1,20p' {APP_ROOT}/verifier.py"


def test_project_context_does_not_rewrite_project_commands():
    cli.set_project_state("project_root", PROJECT_ROOT)

    ctx = cli.build_execution_context(f"{PROJECT_ROOT}/rename_files.py", "test")

    command = "python3 rename_files.py samples"
    assert cli.normalize_command_for_execution_context(command, ctx) == command


def test_allowed_dirty_pattern_matches_target_file_only():
    cli.set_project_state("project_root", PROJECT_ROOT)

    ctx = cli.build_execution_context(f"{APP_ROOT}/cli.py", "test")

    assert cli.allowed_dirty_pattern(ctx) == "cli\\.py"
