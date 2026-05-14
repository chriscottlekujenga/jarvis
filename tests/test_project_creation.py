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



def test_create_regular_web_project_keeps_generic_readme():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Simple Web App", projects_root=tmp, project_type="web")
        assert ok, message

        readme_text = Path(os.path.join(tmp, "simple_web_app", "README.md")).read_text()

        assert "Created by Jarvis as a web project." in readme_text
        assert "AI consultative sales platform" not in readme_text

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



def test_choose_web_app_blueprint_selects_consultative_sales_platform():
    selected = cli.choose_web_app_blueprint(
        "Build an AI consultative sales discovery app with pain detection, buying intent, and proposal generation"
    )

    assert selected["name"] == "consultative_sales_platform"
    assert "sales discovery" in selected["description"].lower()
    assert "buying intent" in selected["reason"].lower()


def test_choose_web_app_blueprint_selects_consultative_sales_platform_for_lean_sales_advisor():
    selected = cli.choose_web_app_blueprint(
        "Create a Lean consulting AI sales advisor that interviews prospects and generates proposals"
    )

    assert selected["name"] == "consultative_sales_platform"

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
    assert stored_state["project_blueprint"] == "product_storefront"
    assert "products" in stored_state["project_blueprint_reason"].lower()
    assert stored_state["project_capability_type"] == "static_web"
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



def test_infer_project_capability_type_marks_consultative_sales_as_ai_interactive():
    assert cli.infer_project_capability_type("consultative_sales_platform") == "ai_interactive"


def test_infer_project_capability_type_marks_static_blueprints_as_static_web():
    assert cli.infer_project_capability_type("product_storefront") == "static_web"
    assert cli.infer_project_capability_type("dashboard_app") == "static_web"


def test_create_project_mode_stores_ai_interactive_project_blueprint():
    stored_state = {}

    def fake_set_project_state(key, value):
        stored_state[key] = value

    with patch("builtins.print"):
        with patch("cli.set_project_state", side_effect=fake_set_project_state):
            with patch("cli.create_project", return_value=(True, "Created web project: /tmp/example")):
                cli.create_project_mode("lean consulting ai sales advisor", project_type="web")

    assert stored_state["project_blueprint"] == "consultative_sales_platform"
    assert stored_state["project_capability_type"] == "ai_interactive"
    assert stored_state["web_blueprint"] == "consultative_sales_platform"

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


def test_build_web_project_templates_creates_dashboard_content():
    templates = cli.build_web_project_templates("sales_metrics_dashboard", "dashboard_app")

    assert "Dashboard App" in templates["index"]
    assert "metric-grid" in templates["index"]
    assert "metric-card" in templates["styles"]
    assert "dashboard app ready" in templates["script"]


def test_create_web_project_uses_dashboard_template_for_dashboard_request():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Sales Metrics Dashboard", projects_root=tmp, project_type="web")
        assert ok, message

        project_root = os.path.join(tmp, "sales_metrics_dashboard")
        index_text = Path(os.path.join(project_root, "index.html")).read_text()
        styles_text = Path(os.path.join(project_root, "styles.css")).read_text()
        script_text = Path(os.path.join(project_root, "script.js")).read_text()

        assert "Dashboard App" in index_text
        assert "metric-grid" in index_text
        assert "metric-card" in styles_text
        assert "dashboard app ready" in script_text



def test_build_consultative_sales_app_scaffold_creates_expected_files():
    scaffold = cli.build_consultative_sales_app_scaffold("lean_consulting_ai_sales_advisor")

    expected_paths = {
        "frontend/index.html",
        "frontend/styles.css",
        "frontend/script.js",
        "backend/app.py",
        "prompts/sales_reasoning_system.txt",
        "prompts/next_question_prompt.txt",
        "prompts/proposal_generation_prompt.txt",
        "service_modules/lean_consulting.json",
        "schemas/session_state.json",
        "schemas/proposal_output.json",
        ".env.example",
    }

    assert expected_paths.issubset(set(scaffold))
    assert "AI Consultative Sales Platform" in scaffold["frontend/index.html"]
    assert "OPENAI_API_KEY" in scaffold[".env.example"]
    assert "lean_consulting" in scaffold["service_modules/lean_consulting.json"]
    assert "roi_logic" in scaffold["service_modules/lean_consulting.json"]
    assert "proposal_sections" in scaffold["service_modules/lean_consulting.json"]
    assert "sales reasoning engine" in scaffold["prompts/sales_reasoning_system.txt"].lower()
    assert "one strong question" in scaffold["prompts/next_question_prompt.txt"].lower()
    assert "proposal readiness" in scaffold["prompts/proposal_generation_prompt.txt"].lower()
    assert "load_service_module" in scaffold["backend/app.py"]
    assert "score_basic_buying_intent" in scaffold["backend/app.py"]
    assert "generate_next_question_stub" in scaffold["backend/app.py"]
    assert "score_proposal_readiness" in scaffold["backend/app.py"]
    assert "generate_proposal_stub" in scaffold["backend/app.py"]
    assert "get_ai_model" in scaffold["backend/app.py"]
    assert "has_api_key" in scaffold["backend/app.py"]
    assert "call_ai_model" in scaffold["backend/app.py"]
    assert "build_next_question_response" in scaffold["backend/app.py"]
    assert "build_proposal_response" in scaffold["backend/app.py"]
    assert "ConsultativeSalesRequestHandler" in scaffold["backend/app.py"]
    assert "run_server" in scaffold["backend/app.py"]
    assert "/api/next-question" in scaffold["backend/app.py"]
    assert "fetch(" in scaffold["frontend/script.js"]
    assert "/api/next-question" in scaffold["frontend/script.js"]
    assert "session_state" in scaffold["frontend/script.js"]
    assert "renderBackendResponse" in scaffold["frontend/script.js"]
    assert "requestNextQuestion" in scaffold["frontend/script.js"]
    assert "/api/next-question" in scaffold["frontend/script.js"]


def test_create_web_project_scaffolds_consultative_sales_platform_files():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Lean Consulting AI Sales Advisor", projects_root=tmp, project_type="web")
        assert ok, message

        project_root = os.path.join(tmp, "lean_consulting_ai_sales_advisor")

        expected_paths = [
            "frontend/index.html",
            "frontend/styles.css",
            "frontend/script.js",
            "backend/app.py",
            "prompts/sales_reasoning_system.txt",
            "prompts/next_question_prompt.txt",
            "prompts/proposal_generation_prompt.txt",
            "service_modules/lean_consulting.json",
            "schemas/session_state.json",
            "schemas/proposal_output.json",
            ".env.example",
        ]

        for relative_path in expected_paths:
            assert os.path.exists(os.path.join(project_root, relative_path)), relative_path

        assert "OPENAI_API_KEY" in Path(os.path.join(project_root, ".env.example")).read_text()
        assert "AI Consultative Sales Platform" in Path(os.path.join(project_root, "frontend/index.html")).read_text()
        assert "lean_consulting" in Path(os.path.join(project_root, "service_modules/lean_consulting.json")).read_text()

        readme_text = Path(os.path.join(project_root, "README.md")).read_text()
        assert "AI consultative sales platform" in readme_text
        assert "python3 backend/app.py" in readme_text
        assert "ai_mode: local_stub" in readme_text
        assert "ai_mode: api_ready" in readme_text
        assert "call_ai_model()" in readme_text


def test_validate_consultative_sales_app_scaffold_passes_for_generated_scaffold():
    with tempfile.TemporaryDirectory() as tmp:
        scaffold = cli.build_consultative_sales_app_scaffold("lean_consulting_ai_sales_advisor")
        cli.write_scaffold_files(tmp, scaffold)

        ok, message = cli.validate_consultative_sales_app_scaffold(tmp)

        assert ok, message
        assert "validation passed" in message.lower()


def test_validate_consultative_sales_app_scaffold_fails_when_env_key_missing():
    with tempfile.TemporaryDirectory() as tmp:
        scaffold = cli.build_consultative_sales_app_scaffold("lean_consulting_ai_sales_advisor")
        scaffold[".env.example"] = "AI_MODEL=gpt-4.1-mini\nAPP_ENV=development\n"
        cli.write_scaffold_files(tmp, scaffold)

        ok, message = cli.validate_consultative_sales_app_scaffold(tmp)

        assert not ok
        assert "OPENAI_API_KEY" in message


def test_create_web_project_rejects_invalid_consultative_sales_scaffold():
    with tempfile.TemporaryDirectory() as tmp:
        broken_scaffold = cli.build_consultative_sales_app_scaffold("lean_consulting_ai_sales_advisor")
        broken_scaffold.pop("backend/app.py")

        with patch("cli.build_consultative_sales_app_scaffold", return_value=broken_scaffold):
            ok, message = cli.create_project("Lean Consulting AI Sales Advisor", projects_root=tmp, project_type="web")

        assert not ok
        assert "missing AI scaffold file backend/app.py" in message


def test_validate_consultative_sales_app_scaffold_fails_when_roi_logic_missing():
    with tempfile.TemporaryDirectory() as tmp:
        scaffold = cli.build_consultative_sales_app_scaffold("lean_consulting_ai_sales_advisor")
        scaffold["service_modules/lean_consulting.json"] = scaffold["service_modules/lean_consulting.json"].replace('"roi_logic"', '"missing_return_logic"')
        cli.write_scaffold_files(tmp, scaffold)

        ok, message = cli.validate_consultative_sales_app_scaffold(tmp)

        assert not ok
        assert "ROI logic" in message


def test_validate_consultative_sales_app_scaffold_fails_when_prompt_marker_missing():
    with tempfile.TemporaryDirectory() as tmp:
        scaffold = cli.build_consultative_sales_app_scaffold("lean_consulting_ai_sales_advisor")
        scaffold["prompts/sales_reasoning_system.txt"] = "Generic prompt only.\n"
        cli.write_scaffold_files(tmp, scaffold)

        ok, message = cli.validate_consultative_sales_app_scaffold(tmp)

        assert not ok
        assert "sales reasoning prompt" in message


def test_validate_consultative_sales_app_scaffold_fails_when_backend_reasoning_marker_missing():
    with tempfile.TemporaryDirectory() as tmp:
        scaffold = cli.build_consultative_sales_app_scaffold("lean_consulting_ai_sales_advisor")
        scaffold["backend/app.py"] = scaffold["backend/app.py"].replace("score_basic_buying_intent", "missing_score_function")
        cli.write_scaffold_files(tmp, scaffold)

        ok, message = cli.validate_consultative_sales_app_scaffold(tmp)

        assert not ok
        assert "score_basic_buying_intent" in message


def test_generated_consultative_sales_backend_runs_with_local_stub():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Lean Consulting AI Sales Advisor", projects_root=tmp, project_type="web")
        assert ok, message

        project_root = os.path.join(tmp, "lean_consulting_ai_sales_advisor")
        result = subprocess.run(
            ["python3", "backend/app.py"],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert result.returncode == 0, result.stderr
        assert '"status": "ready"' in result.stdout
        assert '"service_key": "lean_consulting"' in result.stdout
        assert "operational problem" in result.stdout
        assert '"proposal_readiness_score": 0' in result.stdout
        assert '"proposal"' in result.stdout
        assert '"recommended_offer": "operational assessment"' in result.stdout
        assert '"ai_mode": "local_stub"' in result.stdout
        assert '"ai_model": "gpt-4.1-mini"' in result.stdout
        assert '"session_state"' in result.stdout
        assert '"matched_signals"' in result.stdout
        assert '"matched_pains"' in result.stdout


def test_validate_consultative_sales_app_scaffold_fails_when_frontend_contract_marker_missing():
    with tempfile.TemporaryDirectory() as tmp:
        scaffold = cli.build_consultative_sales_app_scaffold("lean_consulting_ai_sales_advisor")
        scaffold["frontend/script.js"] = scaffold["frontend/script.js"].replace("renderBackendResponse", "missing_render_contract")
        cli.write_scaffold_files(tmp, scaffold)

        ok, message = cli.validate_consultative_sales_app_scaffold(tmp)

        assert not ok
        assert "renderBackendResponse" in message


def test_generated_frontend_script_contains_backend_response_shape():
    scaffold = cli.build_consultative_sales_app_scaffold("lean_consulting_ai_sales_advisor")
    script = scaffold["frontend/script.js"]

    assert "status" in script
    assert "service_key" in script
    assert "next_question" in script
    assert "session_state" in script
    assert "/api/next-question" in script


def test_validate_consultative_sales_app_scaffold_fails_when_proposal_marker_missing():
    with tempfile.TemporaryDirectory() as tmp:
        scaffold = cli.build_consultative_sales_app_scaffold("lean_consulting_ai_sales_advisor")
        scaffold["backend/app.py"] = scaffold["backend/app.py"].replace("generate_proposal_stub", "missing_proposal_builder")
        cli.write_scaffold_files(tmp, scaffold)

        ok, message = cli.validate_consultative_sales_app_scaffold(tmp)

        assert not ok
        assert "generate_proposal_stub" in message


def test_generated_backend_contains_proposal_readiness_contract():
    scaffold = cli.build_consultative_sales_app_scaffold("lean_consulting_ai_sales_advisor")
    backend = scaffold["backend/app.py"]

    assert "proposal_readiness_score" in backend
    assert "score_proposal_readiness" in backend
    assert "generate_proposal_stub" in backend
    assert "expected_outcomes" in backend


def test_validate_consultative_sales_app_scaffold_fails_when_api_boundary_marker_missing():
    with tempfile.TemporaryDirectory() as tmp:
        scaffold = cli.build_consultative_sales_app_scaffold("lean_consulting_ai_sales_advisor")
        scaffold["backend/app.py"] = scaffold["backend/app.py"].replace("call_ai_model", "missing_ai_boundary")
        cli.write_scaffold_files(tmp, scaffold)

        ok, message = cli.validate_consultative_sales_app_scaffold(tmp)

        assert not ok
        assert "call_ai_model" in message


def test_generated_backend_contains_api_boundary_contract():
    scaffold = cli.build_consultative_sales_app_scaffold("lean_consulting_ai_sales_advisor")
    backend = scaffold["backend/app.py"]

    assert "OPENAI_API_KEY" in backend
    assert "AI_MODEL" in backend
    assert "api" in backend
    assert "api_error_fallback" in backend
    assert "local_stub" in backend
    assert "call_ai_model" in backend
    assert "build_next_question_response" in backend
    assert "build_proposal_response" in backend
    assert "import sqlite3" in backend
    assert "DB_PATH" in backend
    assert "def init_db" in backend
    assert "def load_persisted_session_state" in backend
    assert "def save_persisted_session_state" in backend
    assert "session_id" in backend


def test_validate_consultative_sales_app_scaffold_fails_when_response_builder_missing():
    with tempfile.TemporaryDirectory() as tmp:
        scaffold = cli.build_consultative_sales_app_scaffold("lean_consulting_ai_sales_advisor")
        scaffold["backend/app.py"] = scaffold["backend/app.py"].replace("build_next_question_response", "missing_next_question_response")
        cli.write_scaffold_files(tmp, scaffold)

        ok, message = cli.validate_consultative_sales_app_scaffold(tmp)

        assert not ok
        assert "build_next_question_response" in message



def test_generated_backend_ai_adapter_uses_local_stub_without_api_key():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Lean Consulting AI Sales Advisor", projects_root=tmp, project_type="web")
        assert ok, message

        project_root = os.path.join(tmp, "lean_consulting_ai_sales_advisor")
        result = subprocess.run(
            [
                "python3",
                "-c",
                "import os; os.environ.pop('OPENAI_API_KEY', None); import backend.app as app; result = app.call_ai_model('next_question_prompt.txt', {'answer': 'test'}); print(result['ai_mode']); print(result['model']); print(result['payload_keys'])",
            ],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert result.returncode == 0, result.stderr
        assert "local_stub" in result.stdout
        assert "gpt-4.1-mini" in result.stdout
        assert "answer" in result.stdout


def test_generated_backend_response_builder_contract_runs_directly():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Lean Consulting AI Sales Advisor", projects_root=tmp, project_type="web")
        assert ok, message

        project_root = os.path.join(tmp, "lean_consulting_ai_sales_advisor")
        result = subprocess.run(
            [
                "python3",
                "-c",
                "import backend.app as app; response = app.build_next_question_response('We have missed delivery dates and low OEE.'); print(response['status']); print(response['matched_pains']); print(response['session_state']['buying_intent_score']); print(bool(response['session_id']))",
            ],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert result.returncode == 0, result.stderr
        assert "ready" in result.stdout
        assert "missed delivery dates" in result.stdout
        assert "low OEE" in result.stdout
        assert "True" in result.stdout


def test_generated_backend_persists_session_state_across_calls():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Lean Consulting AI Sales Advisor", projects_root=tmp, project_type="web")
        assert ok, message

        project_root = os.path.join(tmp, "lean_consulting_ai_sales_advisor")
        result = subprocess.run(
            [
                "python3",
                "-c",
                "import backend.app as app; first = app.build_next_question_response('We have missed delivery dates.'); second = app.build_next_question_response('We also have low OEE.', session_id=first['session_id']); print(first['session_id'] == second['session_id']); print(second['session_state']['buying_intent_score'] >= first['session_state']['buying_intent_score']); print(len(second['session_state']['previous_answers']) == 2); print('missed delivery dates' in second['session_state']['known_pains']); print('low OEE' in second['session_state']['known_pains'])",
            ],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout.count("True") == 5



def test_generated_backend_extracts_basic_entities_and_urgency():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Lean Consulting AI Sales Advisor", projects_root=tmp, project_type="web")
        assert ok, message

        project_root = os.path.join(tmp, "lean_consulting_ai_sales_advisor")
        result = subprocess.run(
            [
                "python3",
                "-c",
                "import backend.app as app; response = app.build_next_question_response('My name is Chris from Acme Manufacturing. We have an urgent deadline and missed delivery dates.'); state = response['session_state']; print(state['prospect_name']); print(state['company_name']); print(state['urgency_score'] > 0)",
            ],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert result.returncode == 0, result.stderr
        assert "Chris" in result.stdout
        assert "Acme Manufacturing" in result.stdout
        assert "True" in result.stdout



def test_generated_backend_asks_context_question_when_company_missing():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Lean Consulting AI Sales Advisor", projects_root=tmp, project_type="web")
        assert ok, message

        project_root = os.path.join(tmp, "lean_consulting_ai_sales_advisor")
        result = subprocess.run(
            [
                "python3",
                "-c",
                "import backend.app as app; service = app.load_service_module(); state = app.build_initial_session_state(); state['known_pains'] = ['missed delivery dates']; state['urgency_score'] = 60; state['buying_intent_score'] = 60; print(app.generate_next_question_stub(state, service))",
            ],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert result.returncode == 0, result.stderr
        question = result.stdout.lower()
        assert "company" in question or "site" in question or "process area" in question



def test_generated_backend_http_route_smoke():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Lean Consulting AI Sales Advisor", projects_root=tmp, project_type="web")
        assert ok, message

        project_root = os.path.join(tmp, "lean_consulting_ai_sales_advisor")
        command = """
import json
import subprocess
import sys
import time
import urllib.request

server = subprocess.Popen(
    [sys.executable, "backend/app.py", "--serve"],
    cwd=".",
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
try:
    time.sleep(1)
    req = urllib.request.Request(
        "http://127.0.0.1:8080/api/next-question",
        data=json.dumps({"answer": "We have urgent missed delivery dates."}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    body = urllib.request.urlopen(req, timeout=5).read().decode("utf-8")
    data = json.loads(body)
    print(data["status"])
    print(bool(data["session_id"]))
    print(data["session_state"]["urgency_score"] > 0)
finally:
    server.terminate()
    server.wait(timeout=5)
"""
        result = subprocess.run(
            ["python3", "-c", command],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert result.returncode == 0, result.stderr
        assert "ready" in result.stdout
        assert result.stdout.count("True") == 2


def test_generated_backend_contains_http_route_contract():
    scaffold = cli.build_consultative_sales_app_scaffold("lean_consulting_ai_sales_advisor")
    backend = scaffold["backend/app.py"]

    assert "BaseHTTPRequestHandler" in backend
    assert "ConsultativeSalesRequestHandler" in backend
    assert "do_POST" in backend
    assert "/api/next-question" in backend
    assert "ALLOWED_ORIGINS" in backend
    assert "--serve" in backend


def test_generated_app_env_example_documents_ai_runtime_settings():
    scaffold = cli.build_consultative_sales_app_scaffold("lean_consulting_ai_sales_advisor")
    env_text = scaffold[".env.example"]

    assert "APP_ENV=development" in env_text
    assert "OPENAI_API_KEY=" in env_text
    assert "AI_MODEL=gpt-4.1-mini" in env_text
    assert "OPENAI_API_URL=https://api.openai.com/v1/responses" in env_text
    assert env_text.count("OPENAI_API_KEY=") == 1
    assert env_text.count("AI_MODEL=") == 1



def test_generated_backend_extracts_ai_response_text_when_available():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Lean Consulting AI Sales Advisor", projects_root=tmp, project_type="web")
        assert ok, message

        project_root = os.path.join(tmp, "lean_consulting_ai_sales_advisor")
        result = subprocess.run(
            [
                "python3",
                "-c",
                "import backend.app as app; ai = {'ai_mode': 'api', 'response': {'output_text': 'What is the biggest operational issue affecting delivery right now?'}}; print(app.extract_ai_text(ai))",
            ],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert result.returncode == 0, result.stderr
        assert "What is the biggest operational issue affecting delivery right now?" in result.stdout




def test_generated_backend_rejects_bad_ai_question_text():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Lean Consulting AI Sales Advisor", projects_root=tmp, project_type="web")
        assert ok, message

        project_root = os.path.join(tmp, "lean_consulting_ai_sales_advisor")
        command = """
import backend.app as app

bad_questions = [
    {'response': {'output_text': ''}},
    {'response': {'output_text': '   '}},
    {'response': {'output_text': 'This is not a question'}},
    {'response': {'output_text': 'Q' * 301 + '?'}},
]

for ai in bad_questions:
    print(repr(app.extract_ai_text(ai)))
"""
        result = subprocess.run(
            ["python3", "-c", command],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout.strip().splitlines() == ["''", "''", "''", "''"]


def test_generated_backend_accepts_clean_ai_question_text():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Lean Consulting AI Sales Advisor", projects_root=tmp, project_type="web")
        assert ok, message

        project_root = os.path.join(tmp, "lean_consulting_ai_sales_advisor")
        command = """
import backend.app as app

ai = {'response': {'output_text': '   What operational constraint is most affecting delivery this week?   '}}
print(app.extract_ai_text(ai))
"""
        result = subprocess.run(
            ["python3", "-c", command],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "What operational constraint is most affecting delivery this week?"


def test_generated_backend_extracts_nested_provider_response_text():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Lean Consulting AI Sales Advisor", projects_root=tmp, project_type="web")
        assert ok, message

        project_root = os.path.join(tmp, "lean_consulting_ai_sales_advisor")
        command = """
import backend.app as app

responses = [
    {"response": {"output": [{"content": [{"text": "What constraint is slowing the team down most?"}]}]}},
    {"response": {"choices": [{"message": {"content": "What have you already tried to fix the missed deliveries?"}}]}},
]

for ai in responses:
    print(app.extract_ai_text(ai))
"""
        result = subprocess.run(
            ["python3", "-c", command],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert result.returncode == 0, result.stderr
        assert "What constraint is slowing the team down most?" in result.stdout
        assert "What have you already tried to fix the missed deliveries?" in result.stdout


def test_generated_backend_uses_ai_question_when_available():
    with tempfile.TemporaryDirectory() as tmp:
        ok, message = cli.create_project("Lean Consulting AI Sales Advisor", projects_root=tmp, project_type="web")
        assert ok, message

        project_root = os.path.join(tmp, "lean_consulting_ai_sales_advisor")
        result = subprocess.run(
            [
                "python3",
                "-c",
                "import backend.app as app; app.call_ai_model = lambda prompt_name, payload: {'ai_mode': 'api', 'response': {'output_text': 'Which workflow constraint is causing the most missed deliveries?'}}; response = app.build_next_question_response('We are behind on deliveries at Acme.'); print(response['next_question']); print(response['ai_mode'])",
            ],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert result.returncode == 0, result.stderr
        assert "Which workflow constraint is causing the most missed deliveries?" in result.stdout
        assert "api" in result.stdout


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
