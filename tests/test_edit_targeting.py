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


def test_project_request_ignores_llm_chosen_core_file():
    setup_context()
    steps = ["edit cli.py to add logging.basicConfig after imports"]
    normalized = cli.normalize_context_steps(steps, "add logging to the app")
    assert normalized
    assert normalized[0].startswith(f"edit {PROJECT_ROOT}/rename_files.py to ")


def test_jarvis_self_request_can_target_core_file():
    setup_context()
    steps = ["edit cli.py to improve retry logic"]
    normalized = cli.normalize_context_steps(steps, "improve Jarvis retry logic")
    assert normalized == [f"edit {APP_ROOT}/cli.py to improve retry logic"]


def test_explicit_project_file_request_targets_project_even_in_context_mode():
    setup_context()
    steps = ["edit rename_files.py to add logging.basicConfig after imports"]
    normalized = cli.normalize_context_steps(steps, "change rename_files.py to add logging")
    assert normalized
    assert normalized[0].startswith(f"edit {PROJECT_ROOT}/rename_files.py to ")


def test_explicit_core_file_request_targets_core_even_from_project_context():
    setup_context()
    steps = ["edit cli.py to change help output text"]
    normalized = cli.normalize_context_steps(steps, "change cli.py help output text")
    assert normalized == [f"edit {APP_ROOT}/cli.py to change help output text"]

def test_context_normalization_drops_chained_shell_validation_step():
    setup_context()
    steps = [
        'python3 -m http.server --port 8000 & curl http://localhost:8000 | grep "Welcome" && echo "ok" || echo "failed"'
    ]
    normalized = cli.normalize_context_steps(steps, "change the heading")
    assert normalized == []


def test_context_normalization_keeps_simple_safe_shell_step():
    setup_context()
    steps = ["ls"]
    normalized = cli.normalize_context_steps(steps, "list files")
    assert normalized == ["ls"]

def test_strip_model_edit_artifacts_removes_html_language_label():
    raw = "html\n<!doctype html>\n<html>\n</html>\n"
    cleaned = cli.strip_model_edit_artifacts(raw, "/tmp/index.html")
    assert cleaned.startswith("<!doctype html>")
    assert not cleaned.startswith("html\n")


def test_strip_model_edit_artifacts_removes_code_fence_and_language_label():
    raw = "```html\n<!doctype html>\n<html>\n</html>\n```"
    cleaned = cli.strip_model_edit_artifacts(raw, "/tmp/index.html")
    assert cleaned.startswith("<!doctype html>")
    assert "```" not in cleaned
    assert not cleaned.startswith("html\n")


def test_strip_model_edit_artifacts_does_not_remove_real_html_tag():
    raw = "<html>\n<body></body>\n</html>\n"
    cleaned = cli.strip_model_edit_artifacts(raw, "/tmp/index.html")
    assert cleaned == raw

def test_extract_requested_heading_text_from_heading_instruction():
    assert cli.extract_requested_heading_text(
        'change the heading to say "Welcome Home"'
    ) == "Welcome Home"


def test_deterministic_html_h1_edit_changes_only_first_h1_text():
    old = "<!doctype html>\n<h1>Hello from Jarvis</h1>\n<p>Body</p>\n"
    new = cli.deterministic_html_h1_edit(
        old,
        'change the heading to say "Welcome Home"',
    )
    assert "<h1>Welcome Home</h1>" in new
    assert "<p>Body</p>" in new
    assert "Hello from Jarvis" not in new


def test_deterministic_html_h1_edit_returns_none_without_h1():
    old = "<!doctype html>\n<p>No heading</p>\n"
    assert cli.deterministic_html_h1_edit(
        old,
        'change the heading to say "Welcome Home"',
    ) is None

def test_extract_requested_heading_text_from_h1_content_instruction():
    assert cli.extract_requested_heading_text(
        'change the content of the <h1> tag to "Welcome to Test Web Epsilon"'
    ) == "Welcome to Test Web Epsilon"


def test_deterministic_html_h1_edit_handles_h1_content_instruction():
    old = "<!doctype html>\n<h1>Hello from Jarvis</h1>\n"
    new = cli.deterministic_html_h1_edit(
        old,
        'change the content of the <h1> tag to "Welcome to Test Web Epsilon"',
    )
    assert new is not None
    assert "<h1>Welcome to Test Web Epsilon</h1>" in new

