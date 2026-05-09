import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cli


APP_ROOT = "/home/chris/jarvis"


def test_project_name_sanitizes_to_safe_directory_name():
    assert cli.sanitize_project_name("My Test App!") == "my_test_app"


def test_default_projects_root_is_outside_jarvis_core():
    default_root = cli.get_default_projects_root()
    assert default_root == "/home/chris/projects"
    assert not os.path.abspath(default_root).startswith(os.path.abspath(APP_ROOT) + os.sep)


def test_create_project_creates_external_git_repo_and_updates_context():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Example App", projects_root=tmp)
        assert ok, message

        project_root = os.path.join(tmp, "example_app")
        main_script = os.path.join(project_root, "app.py")

        assert os.path.isdir(project_root)
        assert os.path.isdir(os.path.join(project_root, ".git"))
        assert os.path.exists(main_script)
        assert not os.path.abspath(project_root).startswith(os.path.abspath(APP_ROOT) + os.sep)

        commit_check = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert commit_check.returncode == 0, commit_check.stderr

        status_check = subprocess.run(
            ["git", "status", "--short"],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert status_check.returncode == 0, status_check.stderr
        assert status_check.stdout.strip() == ""

        assert cli.get_project_state("project_root") == project_root
        assert cli.get_project_state("main_script_name") == "app.py"
        assert cli.get_project_state("main_script") == main_script
        assert cli.get_current_dir() == project_root

        result = subprocess.run(
            ["python3", "-m", "py_compile", "app.py"],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert result.returncode == 0, result.stderr


def test_create_web_project_creates_web_files_without_python_compile_requirement():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Web App", projects_root=tmp, project_type="web")
        assert ok, message

        project_root = os.path.join(tmp, "web_app")
        index_path = os.path.join(project_root, "index.html")

        assert os.path.exists(index_path)
        assert os.path.exists(os.path.join(project_root, "styles.css"))
        assert os.path.exists(os.path.join(project_root, "script.js"))
        assert os.path.exists(os.path.join(project_root, "README.md"))
        assert not os.path.exists(os.path.join(project_root, "app.py"))

        assert cli.get_project_state("project_root") == project_root
        assert cli.get_project_state("project_type") == "web"
        assert cli.get_project_state("main_script_name") == "index.html"
        assert cli.get_project_state("main_script") == index_path

        commit_check = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert commit_check.returncode == 0, commit_check.stderr

        status_check = subprocess.run(
            ["git", "status", "--short"],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert status_check.returncode == 0, status_check.stderr
        assert status_check.stdout.strip() == ""


def test_create_project_rejects_unknown_project_type():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Bad Type", projects_root=tmp, project_type="mobile")
        assert not ok
        assert "Unsupported project type" in message


def test_create_project_rejects_existing_non_empty_project_without_changing_context():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Existing App", projects_root=tmp)
        assert ok, message

        original_root = cli.get_project_state("project_root")
        original_main_script = cli.get_project_state("main_script")

        ok, message = cli.create_project("Existing App", projects_root=tmp)
        assert not ok
        assert "Project already exists and is not empty" in message

        assert cli.get_project_state("project_root") == original_root
        assert cli.get_project_state("main_script") == original_main_script


def test_create_project_rejects_projects_inside_jarvis_core():
    ok, message = cli.create_project("bad_app", projects_root=APP_ROOT)
    assert not ok
    assert "Refusing to create user project inside Jarvis core" in message


def test_validate_current_python_project_uses_py_compile():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Validate Python", projects_root=tmp, project_type="python")
        assert ok, message

        ok, message = cli.validate_current_project()
        assert ok, message
        assert "python py_compile app.py" in message


def test_validate_current_web_project_checks_required_files():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Validate Web", projects_root=tmp, project_type="web")
        assert ok, message

        ok, message = cli.validate_current_project()
        assert ok, message
        assert "web files exist" in message


def test_validate_current_web_project_fails_when_required_file_missing():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Broken Web", projects_root=tmp, project_type="web")
        assert ok, message

        os.remove(os.path.join(tmp, "broken_web", "styles.css"))

        ok, message = cli.validate_current_project()
        assert not ok
        assert "missing web files styles.css" in message


def test_run_project_script_falls_back_to_python_project_validation_without_samples():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Run Python No Samples", projects_root=tmp, project_type="python")
        assert ok, message

        assert cli.run_project_script()


def test_run_project_script_falls_back_to_web_project_validation_without_samples():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Run Web No Samples", projects_root=tmp, project_type="web")
        assert ok, message

        assert cli.run_project_script()


def test_run_project_script_fallback_fails_for_broken_web_project():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Run Broken Web", projects_root=tmp, project_type="web")
        assert ok, message

        os.remove(os.path.join(tmp, "run_broken_web", "script.js"))

        assert not cli.run_project_script()


print("PASS: project creation flow")

def test_infer_project_type_from_main_script_detects_web():
    assert cli.infer_project_type_from_main_script("index.html") == "web"
    assert cli.infer_project_type_from_main_script("site.htm") == "web"


def test_infer_project_type_from_main_script_defaults_to_python():
    assert cli.infer_project_type_from_main_script("app.py") == "python"
    assert cli.infer_project_type_from_main_script("rename_files.py") == "python"
