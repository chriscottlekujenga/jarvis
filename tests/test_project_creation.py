import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

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



def test_infer_project_type_from_main_script_detects_web():
    assert cli.infer_project_type_from_main_script("index.html") == "web"
    assert cli.infer_project_type_from_main_script("site.htm") == "web"


def test_infer_project_type_from_main_script_defaults_to_python():
    assert cli.infer_project_type_from_main_script("app.py") == "python"
    assert cli.infer_project_type_from_main_script("rename_files.py") == "python"


def test_choose_web_app_blueprint_selects_storefront():
    selected = cli.choose_web_app_blueprint("Build a web app storefront with products, pricing, and checkout")
    assert selected["name"] == "product_storefront"
    assert "product" in selected["description"].lower()


def test_choose_web_app_blueprint_selects_dashboard():
    selected = cli.choose_web_app_blueprint("Build an admin dashboard with metrics, charts, and KPI status")
    assert selected["name"] == "dashboard_app"
    assert "metrics" in selected["description"].lower()


def test_choose_web_app_blueprint_selects_workflow_tool():
    selected = cli.choose_web_app_blueprint("Build a calculator tool with a form and generated plan")
    assert selected["name"] == "workflow_tool"
    assert "workflow" in selected["description"].lower()


def test_choose_web_app_blueprint_selects_content_portal():
    selected = cli.choose_web_app_blueprint("Build a course portal with lessons, guides, and searchable resources")
    assert selected["name"] == "content_portal"
    assert "content" in selected["description"].lower()


def test_choose_web_app_blueprint_defaults_to_small_business_landing():
    selected = cli.choose_web_app_blueprint("Build a simple website for a local bakery")
    assert selected["name"] == "small_business_landing"
    assert "business" in selected["description"].lower()


def test_create_project_mode_prints_and_stores_web_blueprint(capsys=None):
    output = []
    stored_state = {}

    def fake_print(*args, **kwargs):
        output.append(" ".join(str(arg) for arg in args))

    def fake_set_project_state(key, value):
        stored_state[key] = value

    with patch("builtins.print", side_effect=fake_print):
        with patch("cli.set_project_state", side_effect=fake_set_project_state):
            with patch("cli.create_project", return_value=(True, "Created web project: /tmp/example")):
                cli.create_project_mode("bakery website with products and ordering", project_type="web")

    rendered = "\n".join(output)

    assert "[WEB BLUEPRINT]" in rendered
    assert "Selected:" in rendered
    assert "Reason:" in rendered
    assert "Created web project" in rendered
    assert "[OK]" in rendered
    assert stored_state["web_blueprint"] == "product_storefront"
    assert "products" in stored_state["web_blueprint_reason"].lower()


def test_create_project_mode_does_not_print_or_store_blueprint_for_python_project():
    output = []

    def fake_print(*args, **kwargs):
        output.append(" ".join(str(arg) for arg in args))

    with patch("builtins.print", side_effect=fake_print):
        with patch("cli.set_project_state") as mocked_set_project_state:
            with patch("cli.create_project", return_value=(True, "Created python project: /tmp/example")):
                cli.create_project_mode("utility script", project_type="python")

    rendered = "\n".join(output)

    assert "[WEB BLUEPRINT]" not in rendered
    assert "Created python project" in rendered
    assert "[OK]" in rendered
    mocked_set_project_state.assert_not_called()


def test_choose_web_app_blueprint_handles_underscored_ordering_request():
    selected = cli.choose_web_app_blueprint("bakery_ordering_smoke")
    assert selected["name"] == "product_storefront"


def test_format_project_state_includes_web_blueprint_state():
    rows = [
        ("project_type", "web", "now"),
        ("web_blueprint", "product_storefront", "now"),
        ("web_blueprint_reason", "The request emphasizes products, ordering, pricing, or purchase flow.", "now"),
    ]

    with patch("cli.get_all_project_state", return_value=rows):
        with patch("cli.list_project_python_files", return_value=[]):
            rendered = cli.format_project_state()

    assert "project_type: web" in rendered
    assert "web_blueprint: product_storefront" in rendered
    assert "web_blueprint_reason: The request emphasizes products, ordering, pricing, or purchase flow." in rendered


def test_context_mode_passes_web_blueprint_state_to_context_planner():
    captured = {}

    def fake_ask_llm_context_plan(request, project_state, cwd):
        captured["request"] = request
        captured["project_state"] = project_state
        captured["cwd"] = cwd
        return "1. edit index.html to add a storefront hero section"

    with patch("cli.get_project_state", side_effect=lambda key, default=None: {
        "project_root": "/tmp/example_web_project",
    }.get(key, default)):
        with patch("cli.os.path.isdir", return_value=True):
            with patch("cli.set_current_dir"):
                with patch("cli.get_current_dir", return_value="/tmp/example_web_project"):
                    with patch("cli.format_project_state", return_value="project_type: web\nweb_blueprint: product_storefront\nweb_blueprint_reason: The request emphasizes products, ordering, pricing, or purchase flow."):
                        with patch("cli.ask_llm_context_plan", side_effect=fake_ask_llm_context_plan):
                            with patch("cli.parse_plan_steps", return_value=["edit index.html to add a storefront hero section"]):
                                with patch("cli.normalize_context_steps", return_value=["edit /tmp/example_web_project/index.html to add a storefront hero section"]):
                                    with patch("builtins.input", return_value="n"):
                                        cli.context_mode("add product cards")

    assert captured["request"] == "add product cards"
    assert "web_blueprint: product_storefront" in captured["project_state"]
    assert "web_blueprint_reason:" in captured["project_state"]


def test_web_template_builder_function_exists():
    assert callable(getattr(cli, "build_web_project_templates", None))


def test_build_web_project_templates_creates_product_storefront_content():
    templates = cli.build_web_project_templates("bakery_ordering_smoke", "product_storefront")

    assert "Product Storefront" in templates["index"]
    assert "View Products" in templates["index"]
    assert "product-grid" in templates["index"]
    assert "product-card" in templates["styles"]
    assert "product storefront ready" in templates["script"]


def test_create_web_project_uses_product_storefront_template_for_ordering_request():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Bakery Ordering", projects_root=tmp, project_type="web")
        assert ok, message

        project_root = os.path.join(tmp, "bakery_ordering")
        index_text = Path(os.path.join(project_root, "index.html")).read_text()
        styles_text = Path(os.path.join(project_root, "styles.css")).read_text()
        script_text = Path(os.path.join(project_root, "script.js")).read_text()

        assert "Product Storefront" in index_text
        assert "View Products" in index_text
        assert "product-grid" in index_text
        assert "product-card" in styles_text
        assert "product storefront ready" in script_text


def run_tests():
    test_items = [
        (name, fn)
        for name, fn in sorted(globals().items())
        if name.startswith("test_") and callable(fn)
    ]

    for name, fn in test_items:
        try:
            fn()
        except Exception:
            print(f"FAILED TEST: {name}")
            raise

    print(f"PASS: project creation flow ({len(test_items)} tests)")


if __name__ == "__main__":
    run_tests()
