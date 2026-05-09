import os
import subprocess
import re
import json
import shutil
import tempfile
import importlib
import difflib
import py_compile

import db as db_mod
import executor as executor_mod
import files as files_mod
import llm as llm_mod
import skills as skills_mod


DB_FILE = db_mod.DB_FILE
init_db = db_mod.init_db
get_project_state = db_mod.get_project_state
set_project_state = db_mod.set_project_state
clear_project_state = db_mod.clear_project_state
get_all_project_state = db_mod.get_all_project_state

get_current_dir = executor_mod.get_current_dir
set_current_dir = executor_mod.set_current_dir
is_safe = executor_mod.is_safe
try_step_with_retry = executor_mod.try_step_with_retry

read_file_text = files_mod.read_file_text
write_file_text = files_mod.write_file_text
make_backup = files_mod.make_backup
restore_backup = files_mod.restore_backup
show_diff = files_mod.show_diff

ask_llm = llm_mod.ask_llm
ask_llm_edit = llm_mod.ask_llm_edit
ask_llm_edit_function = llm_mod.ask_llm_edit_function
ask_llm_plan = llm_mod.ask_llm_plan
ask_llm_context_plan = llm_mod.ask_llm_context_plan

parse_plan_steps = skills_mod.parse_plan_steps

NEW_FILE_MAX_CHANGED_LINES = 400
NEW_FILE_MAX_DIFF_RATIO = 1.0
MAX_DIFF_RATIO = 0.35
MAX_CHANGED_LINES = 8
APP_FILE_MAX_DIFF_RATIO = 0.60
APP_FILE_MAX_CHANGED_LINES = 80
MIN_SELF_EDIT_KEYWORD_HITS = 1

JARVIS_APP_FILES = [
    "jarvis.py",
    "cli.py",
    "db.py",
    "executor.py",
    "files.py",
    "llm.py",
    "skills.py",
    "verifier.py",
]

FAILURE_WEAK_SELF_EDIT = "weak_self_edit"
FAILURE_EMPTY_DIFF = "empty_diff"
FAILURE_DIFF_TOO_SMALL = "diff_too_small"
FAILURE_PYTHON_COMPILE_FAILED = "python_compile_failed"
FAILURE_BEHAVIOR_VALIDATION_FAILED = "behavior_validation_failed"

JARVIS_SELF_KEYWORDS = [
    "jarvis",
    "jarvis.py",
    "cli.py",
    "db.py",
    "executor.py",
    "files.py",
    "llm.py",
    "skills.py",
    "verifier.py",
    "context mode",
    "planner",
    "routing",
    "self-improvement",
    "self improvement",
    "edit step",
    "edit steps",
    "run_edit",
    "execute_plan",
    "project state",
    "diff limit",
    "diff guard",
    "self-modification",
    "self modification",
]

WEAK_EDIT_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "so",
    "that",
    "the",
    "to",
    "up",
    "with",
    "when",
    "like",
    "this",
    "these",
    "those",
    "instead",
    "than",
    "then",
    "still",
    "make",
    "making",
    "update",
    "add",
    "change",
    "replace",
    "modify",
    "remove",
    "include",
    "allow",
    "increase",
    "decrease",
    "use",
    "using",
    "request",
    "requests",
    "file",
    "files",
    "python",
    "py",
}

FUNCTION_HINT_KEYWORDS = {
    "routing": ["normalize_context_steps", "infer_jarvis_target_file", "is_jarvis_self_request", "context_mode"],
    "route": ["normalize_context_steps", "infer_jarvis_target_file", "is_jarvis_self_request", "context_mode"],
    "self": ["is_jarvis_self_request", "infer_jarvis_target_file", "normalize_context_steps"],
    "context": ["context_mode", "normalize_context_steps"],
    "plan": ["planner_mode", "build_mode", "execute_plan"],
    "planner": ["planner_mode", "build_mode", "execute_plan"],
    "build": ["build_mode", "execute_plan"],
    "skill": ["skills_mode", "run_skill_mode", "save_skill_mode", "view_skill_mode"],
    "skills": ["skills_mode", "run_skill_mode", "save_skill_mode", "view_skill_mode"],
    "diff": ["choose_diff_limits", "calculate_diff_stats", "run_edit"],
    "guard": ["choose_diff_limits", "run_edit", "is_weak_self_edit"],
    "weak": ["is_weak_self_edit", "has_meaningful_keyword_overlap"],
    "whitespace": ["is_whitespace_only_change", "is_weak_self_edit"],
    "entrypoint": ["sanitize_cli_entrypoint", "main"],
    "startup": ["sanitize_cli_entrypoint", "main"],
    "main": ["main", "sanitize_cli_entrypoint"],
    "retry": ["run_step"],
    "verify": ["run_project_script", "execute_plan"],
    "edit": ["run_edit"],
}

FROZEN_CLI_FUNCTIONS = [
    "is_edit_step",
    "is_context_instruction",
    "is_run_step",
    "get_app_root",
    "get_skills_dir",
    "is_app_file_path",
    "list_python_files_under",
    "list_project_python_files",
    "list_app_python_files",
    "list_known_python_files",
    "format_project_state",
    "is_jarvis_self_request",
    "infer_jarvis_target_file",
    "normalize_context_steps",
    "get_main_script_path",
    "resolve_edit_file_path",
    "calculate_diff_stats",
    "choose_diff_limits",
    "extract_function_block",
    "extract_main_entrypoint_block",
    "instruction_mentions_entrypoint",
    "sanitize_cli_entrypoint",
    "normalize_text_without_whitespace",
    "is_whitespace_only_change",
    "extract_changed_line_text",
    "extract_instruction_keywords",
    "has_meaningful_keyword_overlap",
    "is_weak_self_edit",
    "extract_top_level_functions",
    "find_function_block",
    "build_function_edit_context",
    "infer_target_function",
    "splice_function_block",
    "validate_python_text",
    "restore_unrelated_cli_functions",
    "run_step",
    "run_project_script",
    "execute_plan",
    "context_mode",
    "planner_mode",
    "build_mode",
    "skills_mode",
    "view_skill_mode",
    "run_skill_mode",
    "save_skill_mode",
    "showfile_mode",
    "history_mode",
    "plans_mode",
    "edits_mode",
    "help_mode",
    "main",
]


def is_edit_step(step):
    return step.lower().startswith("edit ")


def is_context_instruction(step):
    return step.lower().startswith((
        "add ", "change ", "replace ", "update ", "modify ", "remove "
    ))


def is_vague_edit_instruction(instruction):
    lowered = (instruction or "").strip().lower()

    vague_exact = {
        "add logging",
        "improve logging",
        "add comments",
        "improve comments",
        "clean up code",
        "refactor code",
    }
    if lowered in vague_exact:
        return True

    if not isinstance(instruction, str):
        return False

    lowered = instruction.strip().lower()
    if not lowered:
        return True

    if "documentation" in lowered or "comments" in lowered:
        return True

    exact_vague_phrases = (
        "update documentation",
        "update user documentation",
        "improve comments",
        "clean up code",
        "cleanup code",
        "refactor code",
        "make miscellaneous improvements",
        "miscellaneous improvements",
        "update documentation to reflect",
        "reflect any changes made",
    )
    if any(phrase in lowered for phrase in exact_vague_phrases):
        return True

    generic_action_phrases = (
        "update ",
        "improve ",
        "enhance ",
        "optimize ",
        "adjust ",
        "refine ",
        "clean up ",
        "cleanup ",
        "refactor ",
    )

    generic_object_phrases = (
        "data handling",
        "handling processes",
        "processing",
        "logic",
        "behavior",
        "functionality",
        "system",
        "processes",
        "workflow",
        "workflows",
        "consistency",
        "robustness",
        "maintainability",
        "readability",
        "performance",
        "structure",
        "normalization",
        "normalization process",
        "input formats",
    )

    concrete_markers = (
        "function ",
        "success message",
        "error message",
        "stdout",
        "stderr",
        "cwd",
        "project state",
        "diff limit",
        "diff guard",
        "routing",
        "context mode",
        "planner",
        "parse",
        "normalize_context_steps",
        "is_jarvis_self_request",
        "infer_jarvis_target_file",
        "verify_step",
        ".py",
    )

    if any(lowered.startswith(action) for action in generic_action_phrases):
        if any(obj in lowered for obj in generic_object_phrases):
            return True

    if any(marker in lowered for marker in concrete_markers):
        return False

    return False
def is_concrete_code_instruction(instruction):
    if not isinstance(instruction, str):
        return False

    lowered = instruction.strip().lower()
    if not lowered:
        return False

    concrete_markers = (
        "function ",
        "method ",
        "success message",
        "error message",
        "message",
        "output",
        "stdout",
        "stderr",
        "cwd",
        "path",
        "directory",
        "file",
        "exists",
        "match",
        "mkdir",
        "cd",
        "venv",
        "touch",
        "pwd",
        "ls",
        "verification",
        "verifier",
        "verify_step",
        "project state",
        "diff limit",
        "diff guard",
        "routing",
        "context mode",
        "planner",
        "parse",
        "normalization",
        "normalize_context_steps",
        "is_jarvis_self_request",
        "infer_jarvis_target_file",
        "ask_llm_context_plan",
        ".py",
    )

    strong_verbs = (
        "add ",
        "change ",
        "update ",
        "improve ",
        "fix ",
        "make ",
        "return ",
        "print ",
        "show ",
        "use ",
        "set ",
        "keep ",
        "reject ",
        "allow ",
    )

    has_marker = any(marker in lowered for marker in concrete_markers)
    has_strong_verb = any(lowered.startswith(verb) for verb in strong_verbs)

    return has_marker or has_strong_verb


def is_run_step(step):
    """
    Determines if a given step involves running a script or validating/test changes.

    Args:
        step (str): The step description to evaluate.

    Returns:
        bool: True if the step contains phrases indicating a run or validation action, False otherwise.
    """
    lowered = step.lower()
    run_phrases = [
        "run the script against",
        "run the script with",
        "run the script",
        "validate changes",
        "validate the changes",
        "test the changes",
        "run test cases",
        "run the project script",
    ]
    return any(phrase in lowered for phrase in run_phrases)
def has_unsafe_shell_chaining(step):
    s = step or ""
    unsafe_tokens = ("&&", "||", ";", " & ", " &", "& ")
    return any(token in s for token in unsafe_tokens)


def is_literal_shell_step(step):
    if not isinstance(step, str):
        return False

    s = step.strip()
    if not s:
        return False

    lowered = s.lower()

    if is_edit_step(s) or is_run_step(s):
        return False

    if lowered.startswith(("add ", "change ", "replace ", "update ", "modify ", "remove ")):
        return False

    blocked_prose_prefixes = (
        "open ",
        "save ",
        "review ",
        "inspect ",
        "check ",
        "verify ",
        "locate ",
        "find ",
        "look for ",
        "make sure ",
        "ensure ",
    )
    if lowered.startswith(blocked_prose_prefixes):
        return False

    blocked_interactive_prefixes = (
        "nano ",
        "vim ",
        "vi ",
        "less ",
        "more ",
        "man ",
        "top ",
        "htop ",
    )
    if lowered.startswith(blocked_interactive_prefixes):
        return False

    shell_prefixes = (
        "cd ", "ls", "pwd", "mkdir ", "touch ", "cp ", "mv ", "rm ",
        "cat ", "grep ", "find ", "sed ", "awk ", "chmod ", "chown ",
        "git ", "python ", "python3 ", "pip ", "pip3 ", "pytest ",
        "bash ", "sh ", "zsh ", "echo "
    )
    for prefix in shell_prefixes:
        if lowered.startswith(prefix):
            return True

    return False
def get_app_root():
    return os.path.dirname(os.path.abspath(__file__))


def get_skills_dir():
    return os.path.join(get_app_root(), "skills")


def is_app_file_path(file_path):
    if not file_path:
        return False
    return os.path.basename(file_path) in JARVIS_APP_FILES


def list_python_files_under(root_dir):
    if not root_dir or not os.path.isdir(root_dir):
        return []

    results = []
    for root, _, files in os.walk(root_dir):
        for name in files:
            if name.endswith(".py"):
                results.append(os.path.join(root, name))

    results.sort()
    return results


def list_project_python_files():
    project_root = get_project_state("project_root")
    return list_python_files_under(project_root)


def list_app_python_files():
    return list_python_files_under(get_app_root())


def list_known_python_files():
    seen = set()
    results = []

    for path in list_app_python_files() + list_project_python_files():
        if path not in seen:
            seen.add(path)
            results.append(path)

    return results


def build_code_map_for_files(files):
    lines = []

    for path in files:
        try:
            content = read_file_text(path)
        except Exception:
            continue

        rel_path = path
        project_root = get_project_state("project_root")
        if project_root and path.startswith(project_root):
            rel_path = os.path.relpath(path, project_root)

        functions = re.findall(r"(?m)^def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", content)
        classes = re.findall(r"(?m)^class\s+([A-Za-z_][A-Za-z0-9_]*)\s*[(:]", content)

        imports = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                imports.append(stripped)

        lines.append(f"- {rel_path}")
        if imports:
            lines.append(f"  imports: {', '.join(imports[:8])}")
        if classes:
            lines.append(f"  classes: {', '.join(classes[:12])}")
        if functions:
            lines.append(f"  functions: {', '.join(functions[:20])}")

    return lines


def format_project_state():
    rows = get_all_project_state()
    lines = [f"{k}: {v}" for k, v, _ in rows]
    files = list_project_python_files()
    if files:
        lines.append("project_files:")
        for path in files:
            lines.append(f"- {path}")

        code_map = build_code_map_for_files(files)
        if code_map:
            lines.append("project_code_map:")
            lines.extend(code_map)

    return "\\n".join(lines)

def contains_reference(text, term):
    if not text or not term:
        return False
    return re.search(r"\b" + re.escape(term.lower()) + r"\b", text.lower()) is not None

def extract_explicit_python_target(text):
    if not text:
        return None

    matches = re.findall(r'([A-Za-z0-9_./\\-]+\.py)\b', text)
    if not matches:
        return None

    target = matches[0].strip().strip('"').strip("'")
    return target or None



def is_jarvis_self_request(text):
    lowered = (text or "").lower()

    explicit_target = extract_explicit_python_target(text)
    if explicit_target:
        explicit_base = os.path.basename(explicit_target)
        return explicit_base in JARVIS_APP_FILES

    for file_name in JARVIS_APP_FILES:
        if contains_reference(lowered, file_name.lower()):
            return True
    for file_name in JARVIS_APP_FILES:
        module_name = file_name[:-3].lower() if file_name.endswith(".py") else file_name.lower()
        if module_name == "files":
            continue
        if module_name and contains_reference(lowered, module_name):
            return True
    for keyword in JARVIS_SELF_KEYWORDS:
        if contains_reference(lowered, keyword.lower()):
            return True
    if "self-improvement" in lowered or "self improvement" in lowered:
        return True
    return False


def infer_jarvis_target_file(text):
    lowered = (text or "").lower()

    explicit_target = extract_explicit_python_target(text)
    if explicit_target:
        explicit_base = os.path.basename(explicit_target)
        if explicit_base in JARVIS_APP_FILES:
            return explicit_base
        return None

    direct_keyword_targets = [
        ("context mode", "cli.py"),
        ("planner", "cli.py"),
        ("routing", "cli.py"),
        ("edit step", "cli.py"),
        ("edit steps", "cli.py"),
        ("project state", "cli.py"),
        ("diff limit", "cli.py"),
        ("diff guard", "cli.py"),
        ("self-modification", "cli.py"),
        ("self modification", "cli.py"),
        ("run_edit", "cli.py"),
        ("execute_plan", "cli.py"),
    ]
    for term, file_name in direct_keyword_targets:
        if contains_reference(lowered, term):
            return file_name
    for file_name in JARVIS_APP_FILES:
        if contains_reference(lowered, file_name.lower()):
            return file_name
    for file_name in JARVIS_APP_FILES:
        module_name = file_name[:-3].lower() if file_name.endswith(".py") else file_name.lower()
        if module_name == "files":
            continue
        if module_name and contains_reference(lowered, module_name):
            return file_name
    if contains_reference(lowered, "jarvis"):
        return "cli.py"
    return None


def normalize_context_steps(steps, request_text=""):
    main_script = get_project_state("main_script") or get_project_state("main_script_name")
    normalized = []

    explicit_target = extract_explicit_python_target(request_text)
    explicit_target_base = os.path.basename(explicit_target) if explicit_target else None

    if explicit_target_base and explicit_target_base not in JARVIS_APP_FILES:
        project_root = get_project_state("project_root")
        if project_root:
            candidate = os.path.join(project_root, explicit_target_base)
            if os.path.exists(candidate):
                explicit_target = candidate

    jarvis_self_request = is_jarvis_self_request(request_text)
    jarvis_target_file = infer_jarvis_target_file(request_text)

    for step in steps:
        s = step.strip().rstrip(".").replace("`", "")
        if not s:
            continue

        if is_edit_step(s):
            parts = s.split(" to ", 1)
            instruction = parts[1].strip() if len(parts) == 2 else s[5:].strip()

            if instruction.lower().startswith("add logging.basicconfig") and " after imports" in instruction.lower():
                instruction = "insert at top of file: " + instruction

            if "top of the file" in instruction.lower() or "top of file" in instruction.lower():
                target_name = main_script

                # Only allow Jarvis-core routing if the USER explicitly requested Jarvis itself.
                if explicit_target_base:
                    target_name = explicit_target_base
                elif jarvis_self_request and jarvis_target_file:
                    target_name = jarvis_target_file

                cleaned_instruction = instruction.replace(
                    "insert at top of file: ",
                    "",
                    1,
                )

                normalized.append(
                    f"edit {resolve_edit_file_path(target_name)} "
                    f"to insert at top of file: {cleaned_instruction}"
                )
                continue

            if is_vague_edit_instruction(instruction):
                continue

            # Improve explicit file targeting comments
            if explicit_target_base:
                for prefix in (
                    f"change {explicit_target_base} to ",
                    f"modify {explicit_target_base} to ",
                    f"update {explicit_target_base} to ",
                    f"fix {explicit_target_base} to ",
                ):
                    if instruction.lower().startswith(prefix):
                        instruction = instruction[len(prefix):].strip()
                        break

            # 🔴 FORCE explicit file if user named one
            if explicit_target_base:
                target_path = resolve_edit_file_path(explicit_target_base)
                normalized.append(f"edit {target_path} to {instruction}")
                continue

            # 🔴 FORCE Jarvis file only when the USER requested a Jarvis/self edit.
            if jarvis_self_request and jarvis_target_file:
                target_path = resolve_edit_file_path(jarvis_target_file)
                normalized.append(f"edit {target_path} to {instruction}")
                continue

            # 🔴 In project context, ignore LLM-chosen Jarvis core targets.
            # If the user did not explicitly request Jarvis itself, project edits go to main_script.
            target_path = resolve_edit_file_path(main_script)
            normalized.append(f"edit {target_path} to {instruction}")
            continue

        if is_literal_shell_step(s):
            if has_unsafe_shell_chaining(s):
                continue

            # BLOCK raw project script runs in context mode; auto-run handles project validation.
            main_script_name = get_project_state("main_script_name")
            main_script_path = get_project_state("main_script")
            shell_lower = s.lower()

            if main_script_name:
                main_script_lower = main_script_name.lower()
                if main_script_lower in shell_lower:
                    continue
                if shell_lower.startswith(("python ", "python3 ")) and main_script_lower in shell_lower.split():
                    continue

            if main_script_path and main_script_path.lower() in shell_lower:
                continue

            if shell_lower.startswith(("python ", "python3 ")) and (
                "--help" in shell_lower
                or "-h" in shell_lower
                or "<" in shell_lower
                or ">" in shell_lower
                or " path" in shell_lower
                or "/path" in shell_lower
            ):
                continue

            normalized.append(s)

    return normalized
def get_main_script_path():
    main_script = get_project_state("main_script")
    if main_script:
        return main_script

    name = get_project_state("main_script_name")
    root = get_project_state("project_root")
    if name and root:
        return os.path.join(root, name)

    return None


def resolve_edit_file_path(file_name):
    if not file_name:
        return get_main_script_path()

    candidate = file_name.strip()

    if os.path.isabs(candidate):
        return candidate

    cwd = get_current_dir()
    cwd_path = os.path.join(cwd, candidate)
    if os.path.exists(cwd_path):
        return cwd_path

    project_root = get_project_state("project_root")
    if project_root:
        project_direct = os.path.join(project_root, candidate)
        if os.path.exists(project_direct):
            return project_direct

        for path in list_project_python_files():
            if os.path.basename(path) == candidate:
                return path

    app_root = get_app_root()
    app_direct = os.path.join(app_root, candidate)
    if os.path.exists(app_direct):
        return app_direct

    for path in list_app_python_files():
        if os.path.basename(path) == candidate:
            return path

    return cwd_path


def calculate_diff_stats(old_text, new_text):
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines)
    changed = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            changed += max(i2 - i1, j2 - j1)

    if not old_lines:
        ratio = changed / max(len(new_lines), 1)
    else:
        ratio = changed / len(old_lines)

    return changed, ratio


def choose_diff_limits(file_path, is_new_file=False):
    if is_new_file:
        return NEW_FILE_MAX_CHANGED_LINES, NEW_FILE_MAX_DIFF_RATIO
    if is_app_file_path(file_path):
        return 2000, 0.9  # Increased limits for editing jarvis app files
    return MAX_CHANGED_LINES, MAX_DIFF_RATIO
def extract_function_block(text, function_name):
    found = find_function_block(text, function_name)
    if not found:
        return None
    return found["block"]


def extract_main_entrypoint_block(text):
    pattern = r'(?ms)^if __name__ == ["\']__main__["\']:\n(?:^[ \t].*\n|^\n)*'
    match = re.search(pattern, text)
    if not match:
        return None
    return match.group(0)


def instruction_mentions_entrypoint(instruction):
    lowered = (instruction or "").lower()
    entry_keywords = [
        "__main__",
        "entrypoint",
        "entry point",
        "startup",
        "main()",
        "def main",
    ]
    return any(keyword in lowered for keyword in entry_keywords)


def strip_model_edit_artifacts(text, file_path=""):
    if text is None:
        return text
def extract_requested_heading_text(instruction):
    if not instruction:
        return None

    patterns = [
        r'heading\s+(?:to say|to read|text to|from .*? to)\s+["\'](.+?)["\']',
        r'(?:content|text)\s+(?:of|inside)\s+the\s+<h1>\s+tags?\s+(?:from\s+["\'].+?["\']\s+)?to\s+["\'](.+?)["\']',
        r'text\s+of\s+the\s+first\s+<h1>\s+tag\s+to\s+["\'](.+?)["\']',
        r'<h1>\s+tags?\s+to\s+["\'](.+?)["\']',
        r'h1\s+(?:to say|to read|text to)\s+["\'](.+?)["\']',
    ]

    for pattern in patterns:
        match = re.search(pattern, instruction, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None


def deterministic_html_h1_edit(old_text, instruction):
    heading_text = extract_requested_heading_text(instruction)
    if not heading_text:
        return None

    pattern = r'(<h1[^>]*>)(.*?)(</h1>)'
    match = re.search(pattern, old_text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None

    return re.sub(
        pattern,
        lambda m: f"{m.group(1)}{heading_text}{m.group(3)}",
        old_text,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )


def strip_model_edit_artifacts(text, file_path=""):
    if text is None:
        return text

    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    extension = os.path.splitext(file_path or "")[1].lower()
    language_labels = {
        ".html": {"html"},
        ".css": {"css"},
        ".js": {"javascript", "js"},
        ".py": {"python", "py"},
        ".json": {"json"},
        ".md": {"markdown", "md"},
    }

    labels = language_labels.get(extension, set())
    lines = cleaned.splitlines()

    if lines and lines[0].strip().lower() in labels:
        cleaned = "\n".join(lines[1:]).lstrip("\n")

    if text.endswith("\n") and not cleaned.endswith("\n"):
        cleaned += "\n"

    return cleaned


def sanitize_cli_entrypoint(old_text, new_text, instruction):
    old_block = extract_main_entrypoint_block(old_text)
    new_block = extract_main_entrypoint_block(new_text)

    if old_block is None:
        return new_text

    if not instruction_mentions_entrypoint(instruction):
        if new_block is None:
            return new_text.rstrip() + "\n\n" + old_block.rstrip() + "\n"
        if new_block != old_block:
            return new_text.replace(new_block, old_block, 1)

    lines = new_text.splitlines()

    cleaned_lines = []
    seen_main_call_in_entrypoint = False
    in_entrypoint = False

    for line in lines:
        if re.match(r'^if __name__ == ["\']__main__["\']:$', line.strip()):
            in_entrypoint = True
            seen_main_call_in_entrypoint = False
            cleaned_lines.append(line)
            continue

        if in_entrypoint:
            if line.startswith("    ") or line.strip() == "":
                if line.strip() == "main()":
                    if seen_main_call_in_entrypoint:
                        continue
                    seen_main_call_in_entrypoint = True
                cleaned_lines.append(line)
                continue
            in_entrypoint = False

        cleaned_lines.append(line)

    result = "\n".join(cleaned_lines).rstrip() + "\n"

    block = extract_main_entrypoint_block(result)
    if block is None:
        result = result.rstrip() + "\n\nif __name__ == \"__main__\":\n    main()\n"

    return result


def normalize_text_without_whitespace(text):
    return re.sub(r"\s+", "", text or "")


def is_whitespace_only_change(old_text, new_text):
    if old_text == new_text:
        return False
    return normalize_text_without_whitespace(old_text) == normalize_text_without_whitespace(new_text)


def extract_changed_line_text(old_text, new_text):
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines)

    changed_chunks = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        if i1 != i2:
            changed_chunks.extend(old_lines[i1:i2])

        if j1 != j2:
            changed_chunks.extend(new_lines[j1:j2])

    return "\n".join(changed_chunks).lower()


def extract_instruction_keywords(instruction):
    lowered = (instruction or "").lower()
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]+", lowered)

    keywords = []
    for token in tokens:
        if token in WEAK_EDIT_STOPWORDS:
            continue
        if len(token) < 4:
            continue
        keywords.append(token)

    seen = set()
    unique_keywords = []
    for token in keywords:
        if token not in seen:
            seen.add(token)
            unique_keywords.append(token)

    return unique_keywords


def has_meaningful_keyword_overlap(instruction, old_text, new_text):
    keywords = extract_instruction_keywords(instruction)
    if not keywords:
        return True

    changed_text = extract_changed_line_text(old_text, new_text)
    hits = 0

    for keyword in keywords:
        if keyword in changed_text:
            hits += 1

    return hits >= MIN_SELF_EDIT_KEYWORD_HITS


def is_weak_self_edit(file_path, instruction, old_text, new_text):
    if not is_app_file_path(file_path):
        return False

    if not is_jarvis_self_request(instruction):
        return False

    if is_whitespace_only_change(old_text, new_text):
        return True

    if not has_meaningful_keyword_overlap(instruction, old_text, new_text):
        return True

    return False

def has_undefined_constants(new_text, old_text=""):
    def strip_literals(text):
        text = re.sub(r'"""[\s\S]*?"""' , '""', text)
        text = re.sub(r"'''[\s\S]*?'''" , "''", text)
        text = re.sub(r'"[^"\n]*"', '""', text)
        text = re.sub(r"'[^'\n]*'", "''", text)
        return text

    def scan(text):
        stripped = strip_literals(text)
        pattern = r"\b[A-Z][A-Z0-9_]{2,}\b"
        used_constants = set(re.findall(pattern, stripped))
        defined_constants = set()

        for line in stripped.splitlines():
            if "=" in line:
                left = line.split("=", 1)[0].strip()
                if re.match(r"^[A-Z][A-Z0-9_]+$", left):
                    defined_constants.add(left)

        builtin_allowed = {
            "__name__",
            "CLI",
            "FORCE",
            "MODE",
            "NEW",
            "IGNORECASE",
            "INFO",
            "DEBUG",
            "WARNING",
            "ERROR",
            "CRITICAL",
        }

        return set(
            c for c in used_constants
            if c not in defined_constants and c not in builtin_allowed
        )

    return sorted(scan(new_text) - scan(old_text))
def extract_top_level_functions(text):
    boundary_matches = list(re.finditer(
        r'(?m)^(?:def [A-Za-z_][A-Za-z0-9_]*\s*\(|class [A-Za-z_][A-Za-z0-9_]*\s*(?:\(|:)|if __name__ == ["\']__main__["\']:\s*$)',
        text,
    ))
    function_matches = list(re.finditer(r'(?m)^def ([A-Za-z_][A-Za-z0-9_]*)\s*\(', text))

    items = []

    for match in function_matches:
        name = match.group(1)
        start = match.start()

        decorator_start = start
        before = text[:start]
        while True:
            line_start = before.rfind("\n", 0, decorator_start - 1) + 1
            previous_line = text[line_start:decorator_start]
            if previous_line.startswith("@") and previous_line.strip():
                decorator_start = line_start
                before = text[:decorator_start]
                continue
            break

        end = len(text)
        for boundary in boundary_matches:
            if boundary.start() > start:
                end = boundary.start()
                break

        block = text[decorator_start:end]
        items.append({
            "name": name,
            "start": decorator_start,
            "end": end,
            "block": block,
        })

    return items


def find_function_block(text, function_name):
    for item in extract_top_level_functions(text):
        if item["name"] == function_name:
            return item
    return None


def build_function_edit_context(file_text, function_name):
    function_names = [item["name"] for item in extract_top_level_functions(file_text)]
    sibling_names = [name for name in function_names if name != function_name]

    import_lines = []
    for line in file_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            import_lines.append(line)

    context_lines = []
    if import_lines:
        context_lines.append("Imports:")
        context_lines.extend(import_lines[:25])

    if sibling_names:
        context_lines.append("")
        context_lines.append("Other top-level functions in this file:")
        for name in sibling_names[:50]:
            context_lines.append(f"- {name}")

    return "\n".join(context_lines).strip()




def infer_target_class(file_text, instruction):
    # Detects class names mentioned in the instruction
    matches = re.findall(r'class\s+([A-Za-z_][A-Za-z0-9_]*)', file_text)
    instruction_lower = instruction.lower()

    for cls in matches:
        if cls.lower() in instruction_lower:
            return cls

    return None

def extract_requested_function_name(instruction):
    instruction = instruction or ""
    patterns = [
        r'add\s+a\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(',
        r'add\s+an\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(',
        r'add\s+def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(',
        r'create\s+a\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(',
        r'create\s+def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(',
        r'add\s+a\s+([A-Za-z_][A-Za-z0-9_]*)\s+function',
        r'create\s+a\s+([A-Za-z_][A-Za-z0-9_]*)\s+function',
    ]
    for pattern in patterns:
        match = re.search('(?i)' + pattern, instruction)
        if match:
            return match.group(1)

    # Detect new function request
    new_function_pattern = r'def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\('
    match = re.search(new_function_pattern, instruction)
    if match:
        return match.group(1)

    return None
def infer_target_function(file_path, file_text, instruction):
    if not file_path or not file_path.endswith(".py"):
        return None

    functions = extract_top_level_functions(file_text)
    if not functions:
        return None

    lowered_instruction = (instruction or "").lower()

    if "top of file" in lowered_instruction or "top of the file" in lowered_instruction:
        return None

    # 1. Prefer exact mentioned function names anywhere in the instruction.
    mentioned_exact = []
    for item in functions:
        name = item["name"].lower()
        if re.search(rf"\b{re.escape(name)}\b", lowered_instruction):
            mentioned_exact.append(item["name"])

    if mentioned_exact:
        mentioned_exact.sort(key=len, reverse=True)
        return mentioned_exact[0]

    # 2. Special handling for main/entrypoint language.
    if any(token in lowered_instruction for token in ["main()", "startup", "entrypoint", "entry point"]):
        for item in functions:
            if item["name"] == "main":
                return "main"

    # 3. Fall back to keyword scoring.
    keywords = extract_instruction_keywords(instruction)
    best_name = None
    best_score = 0

    for item in functions:
        name = item["name"]
        block_lower = item["block"].lower()
        name_lower = name.lower()
        score = 0

        for keyword in keywords:
            if keyword == name_lower:
                score += 10
            elif keyword in name_lower:
                score += 5
            elif keyword in block_lower:
                score += 2

            hinted = FUNCTION_HINT_KEYWORDS.get(keyword, [])
            if name in hinted:
                score += 4

        if score > best_score:
            best_score = score
            best_name = name

    if best_name and best_score > 0:
        return best_name

    if len(functions) == 1:
        return functions[0]["name"]

    return None
def splice_function_block(file_text, function_name, new_block):
    current = find_function_block(file_text, function_name)
    if not current:
        return None

    replacement = new_block.rstrip() + "\n"
    return file_text[:current["start"]] + replacement + file_text[current["end"]:]


def validate_python_text(file_path, text):
    if not file_path.endswith(".py"):
        return True, ""

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py") as temp_file:
            temp_file.write(text)
            temp_path = temp_file.name

        py_compile.compile(temp_path, doraise=True)
        return True, ""
    except Exception as exc:
        return False, str(exc)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


BEHAVIOR_VALIDATION_KEYWORDS = (
    "logic",
    "control flow",
    "routing",
    "context",
    "planner",
    "normalize",
    "parse",
    "state",
    "verify",
    "verification",
    "retry",
    "execute",
    "execution",
    "diff",
    "guard",
    "import",
    "entrypoint",
    "main",
)


CORE_BEHAVIOR_VALIDATION_FILES = {
    "cli.py",
    "llm.py",
    "executor.py",
    "verifier.py",
    "db.py",
    "skills.py",
    "jarvis.py",
}



LAST_EXECUTION_CONTEXT = None


def is_jarvis_core_file(file_path):
    if not file_path:
        return False
    app_root = get_app_root()
    abs_path = os.path.abspath(file_path)
    basename = os.path.basename(abs_path)
    return basename in JARVIS_APP_FILES and os.path.dirname(abs_path) == app_root


def build_execution_context(file_path=None, instruction=""):
    app_root = get_app_root()
    project_root = get_project_state("project_root") or get_current_dir() or app_root
    target_file = os.path.abspath(file_path) if file_path else ""

    target_scope = "jarvis_core" if is_jarvis_core_file(target_file) else "project"
    validation_cwd = app_root if target_scope == "jarvis_core" else project_root

    allowed_dirty_paths = []
    if target_file and target_file.startswith(app_root + os.sep):
        allowed_dirty_paths.append(os.path.relpath(target_file, app_root))

    return {
        "app_root": app_root,
        "project_root": project_root,
        "target_file": target_file,
        "target_scope": target_scope,
        "validation_cwd": validation_cwd,
        "allowed_dirty_paths": allowed_dirty_paths,
        "instruction": instruction or "",
    }


def allowed_dirty_pattern(execution_context):
    paths = list((execution_context or {}).get("allowed_dirty_paths") or [])
    if not paths:
        return ""
    escaped = [re.escape(path) for path in paths]
    if len(escaped) == 1:
        return escaped[0]
    return "(" + "|".join(escaped) + ")"


def normalize_command_for_execution_context(command, execution_context):
    command = command or ""
    if not execution_context:
        return command

    if execution_context.get("target_scope") != "jarvis_core":
        return command

    app_root = execution_context.get("app_root") or get_app_root()
    replacements = {}

    for name in JARVIS_APP_FILES:
        replacements[name] = os.path.join(app_root, name)

    replacements["tests/run_all.sh"] = os.path.join(app_root, "tests", "run_all.sh")

    normalized = command
    for relative_path, absolute_path in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        normalized = re.sub(
            rf'(?<![\w/.-])(?:\./)?{re.escape(relative_path)}(?![\w/.-])',
            absolute_path,
            normalized,
        )

    return normalized

def requires_behavior_validation(file_path, instruction):
    basename = os.path.basename(file_path or "")
    if basename in CORE_BEHAVIOR_VALIDATION_FILES:
        return True

    lowered = (instruction or "").lower()
    return any(keyword in lowered for keyword in BEHAVIOR_VALIDATION_KEYWORDS)


def run_behavior_validation(file_path, instruction, validation_mode=None, execution_context=None):
    execution_context = execution_context or build_execution_context(file_path, instruction)
    basename = os.path.basename(file_path or "")

    if validation_mode == "new_python_file":
        return True, f"Behavior validation passed for {basename} (new python file compile-only mode)"

    if basename not in CORE_BEHAVIOR_VALIDATION_FILES:
        return True, f"Behavior validation skipped for non-core file: {basename}"

    if not requires_behavior_validation(file_path, instruction):
        return True, "Behavior validation skipped: compile-only change."

    module_name = os.path.splitext(basename)[0]
    try:
        module = importlib.import_module(module_name)
        module = importlib.reload(module)

        if basename == "verifier.py":
            cases = [
                (
                    "cd demo",
                    {"success": True, "target_dir": "/tmp/demo", "cwd_after": "/tmp/demo"},
                    "/tmp",
                    True,
                    ("expected", "actual", "match"),
                ),
                (
                    "git init",
                    {"success": True},
                    "/tmp",
                    True,
                    (".git", "exists"),
                ),
                (
                    "mkdir demo",
                    {"success": True, "target_path": "/tmp/demo_dir"},
                    "/tmp",
                    True,
                    ("target", "exists"),
                ),
                (
                    "touch demo.txt",
                    {"success": True, "target_path": "/tmp/demo.txt"},
                    "/tmp",
                    True,
                    ("file path", "exists"),
                ),
                (
                    "pwd",
                    {"success": True, "stdout": "/tmp\n"},
                    "/tmp",
                    True,
                    ("pwd", "/tmp"),
                ),
                (
                    "ls -la",
                    {"success": True, "stdout": "file.txt\n"},
                    "/tmp",
                    True,
                    ("listing", "successfully"),
                ),
            ]

            original_isdir = module.os.path.isdir
            original_exists = module.os.path.exists
            try:
                module.os.path.isdir = lambda p: True
                module.os.path.exists = lambda p: True

                for command, result, current_dir, expected_ok, required_terms in cases:
                    ok, msg = module.verify_step(command, result, current_dir)
                    if ok != expected_ok:
                        return False, f"Behavior validation failed: {command} returned ok={ok}, expected {expected_ok}"
                    if not isinstance(msg, str) or not msg.strip():
                        return False, f"Behavior validation failed: {command} returned empty/non-string message: {msg}"

                    lowered_msg = msg.lower()
                    for term in required_terms:
                        if str(term).lower() not in lowered_msg:
                            return False, f"Behavior validation failed: {command} message missing '{term}': {msg}"

                empty_ok, empty_msg = module.verify_step(
                    "pwd",
                    {"success": True, "stdout": ""},
                    "/tmp",
                )
                if empty_ok is not False:
                    return False, "Behavior validation failed: pwd empty stdout should return False"
                if "empty stdout" not in str(empty_msg).lower():
                    return False, f"Behavior validation failed: pwd empty stdout message unexpected: {empty_msg}"
            finally:
                module.os.path.isdir = original_isdir
                module.os.path.exists = original_exists
        elif basename == "cli.py":
            if not callable(getattr(module, "normalize_context_steps", None)):
                return False, "Behavior validation failed: normalize_context_steps missing"
            if not callable(getattr(module, "format_project_state", None)):
                return False, "Behavior validation failed: format_project_state missing"

            normalized = module.normalize_context_steps(
                ["edit verifier.py to improve output"],
                "continue improve verifier output"
            )
            if not normalized or not normalized[0].startswith("edit "):
                return False, f"Behavior validation failed: normalize_context_steps returned {normalized}"

        elif basename == "llm.py":
            if not callable(getattr(module, "ask_llm_plan", None)):
                return False, "Behavior validation failed: ask_llm_plan missing"
            if not callable(getattr(module, "ask_llm_context_plan", None)):
                return False, "Behavior validation failed: ask_llm_context_plan missing"

        elif basename == "executor.py":
            if not callable(getattr(module, "run_command", None)):
                return False, "Behavior validation failed: run_command missing"

        elif basename == "db.py":
            if not callable(getattr(module, "get_project_state", None)):
                return False, "Behavior validation failed: get_project_state missing"
            if not callable(getattr(module, "set_project_state", None)):
                return False, "Behavior validation failed: set_project_state missing"

        elif basename == "skills.py":
            has_skill_api = any(
                callable(getattr(module, name, None))
                for name in ("save_skill", "load_skill", "parse_skill_steps")
            )
            if not has_skill_api:
                return False, "Behavior validation failed: expected skills API not found"

        elif basename == "jarvis.py":
            if not hasattr(module, "__file__"):
                return False, "Behavior validation failed: jarvis module import did not succeed"

        test_script = os.path.join(get_app_root(), "tests", "run_all.sh")
        if os.path.exists(test_script):
            env_prefix = ""
            allowed_dirty = allowed_dirty_pattern(execution_context)
            if allowed_dirty:
                env_prefix = f"JARVIS_ALLOWED_DIRTY_PATH='{allowed_dirty}' "
            validation_command = test_script
            if allowed_dirty:
                validation_command = f"env JARVIS_ALLOWED_DIRTY_PATH={allowed_dirty} {test_script}"
            result = executor_mod.run_command(validation_command)
            if not result.get("success"):
                return False, (
                    "Behavior validation failed: regression suite failed. "
                    + (result.get("stderr") or result.get("stdout") or "")
                )

        return True, f"Behavior validation passed for {basename}"

    except Exception as exc:
        return False, f"Behavior validation failed for {basename}: {exc}"


def choose_validation_mode(file_path, old_text, instruction):
    file_path = file_path or ""
    old_text = old_text or ""

    if file_path.endswith(".py") and not old_text.strip():
        return "new_python_file"

    if file_path.endswith(".py"):
        return "existing_python_file"

    return "generic"


def restore_unrelated_cli_functions(old_text, new_text, instruction):
    requested = (instruction or "").lower()
    restored = new_text

    for function_name in FROZEN_CLI_FUNCTIONS:
        if function_name.lower() in requested:
            continue

        old_block = extract_function_block(old_text, function_name)
        new_block = extract_function_block(restored, function_name)

        if old_block and new_block and old_block != new_block:
            restored = restored.replace(new_block, old_block, 1)

    restored = sanitize_cli_entrypoint(old_text, restored, instruction)
    return restored


def record_edit_failure(reason, message):
    set_project_state("last_edit_failure_type", reason)
    set_project_state("last_edit_failure_message", message)
    print(f"[FAILURE_CLASS] {reason}")
    print(message)
    return False


def clear_edit_failure_state():
    set_project_state("last_edit_failure_type", "")
    set_project_state("last_edit_failure_message", "")

def strengthen_edit_instruction(instruction):
    instruction = (instruction or "").strip()
    failure_type = get_project_state("last_edit_failure_type", "")
    failure_message = get_project_state("last_edit_failure_message", "")

    if not instruction or not failure_type:
        return instruction

    if failure_type == FAILURE_WEAK_SELF_EDIT:
        return (
            f"{instruction}. "
            f"Make a concrete behavior-changing code edit, not a wording-only change. "
            f"Modify logic, condition handling, return values, or explicit output fields named in the request."
        )

    if failure_type == FAILURE_EMPTY_DIFF:
        return (
            f"{instruction}. "
            f"The previous attempt produced no change. "
            f"If the file already satisfies the request, keep it unchanged. "
            f"Otherwise make an observable code change."
        )

    if failure_type == FAILURE_DIFF_TOO_SMALL:
        return (
            f"{instruction}. "
            f"The previous attempt was too small. "
            f"Make a more meaningful but still scoped behavior change."
        )

    if failure_type == FAILURE_BEHAVIOR_VALIDATION_FAILED:
        return (
            f"{instruction}. "
            f"The previous attempt failed behavior validation: {failure_message}. "
            f"Preserve the required interface and output contract."
        )

    return instruction

def run_edit(step):
    parts = step.split(" to ", 1)
    if len(parts) != 2:
        print("Bad edit step.")
        return False

    step_head = parts[0].strip()
    file_name = step_head[5:].strip()
    instruction = parts[1].strip()
    instruction = strengthen_edit_instruction(instruction)

    file_path = resolve_edit_file_path(file_name)
    execution_context = build_execution_context(file_path, instruction)
    global LAST_EXECUTION_CONTEXT
    LAST_EXECUTION_CONTEXT = execution_context
    print(f"[TARGET RESOLVED] {file_name} -> {file_path}")
    old = read_file_text(file_path) if os.path.exists(file_path) else ""
    is_new_file = not os.path.exists(file_path)
    print(f"\n[EDIT] {file_path}")
    print(f"[INSTRUCTION] {instruction}")

    if is_new_file:
        print("This file is treated as new.")

    max_changed_lines, max_diff_ratio = choose_diff_limits(file_path, is_new_file=is_new_file)
    print(f"Chosen diff limits: max_changed_lines={max_changed_lines}, max_diff_ratio={max_diff_ratio:.0%}")

    new = None
    target_class = infer_target_class(old, instruction)
    requested_function = extract_requested_function_name(instruction)

    lowered_instruction = (instruction or "").lower()
    force_full_file_edit = (
        "import " in lowered_instruction
        or "from " in lowered_instruction
        or "top of file" in lowered_instruction
        or "top of the file" in lowered_instruction
    )

    if requested_function and not find_function_block(old, requested_function):
        print(f"[FUNCTION] {requested_function} does not exist, generating function definition")
        new_function_definition = ask_llm_edit_function(
            file_path=file_path,
            function_name=requested_function,
            old_function=f"def {requested_function}(*args, **kwargs):\n    pass\n",
            instruction=instruction,
            file_context=old,
        ).replace("", "").strip()

        returned_name_match = re.search(r'(?m)^def ([A-Za-z_][A-Za-z0-9_]*)\s*\(', new_function_definition)
        if not returned_name_match:
            print("Rejected: generated new function is not a function definition")
            return False

        returned_name = returned_name_match.group(1)
        if returned_name != requested_function:
            return record_edit_failure("wrong_generated_function_name", f"Rejected: generated new function returned {returned_name} instead of {requested_function}")

        separator = "\n\n" if old and not old.endswith("\n\n") else ""
        new = old.rstrip() + separator + new_function_definition + "\n"
        target_function = None
        max_diff_ratio = 1.0
        max_changed_lines = max(max_changed_lines, 50)
        # Stop here so we do not fall through to fallback logic
    else:
        target_function = infer_target_function(file_path, old, instruction)

    if new is not None:
        pass
    elif "insert at top of file:" in instruction.lower():
        print("[DETERMINISTIC EDIT] top-of-file insertion")

        line = instruction.split("insert at top of file:", 1)[1].strip()

        if "comment" in line:
            new_line = "# " + line.replace("add a harmless comment", "").strip().capitalize()
        else:
            new_line = line

        lines = old.splitlines()

        insert_index = 0
        for i, existing in enumerate(lines):
            stripped = existing.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                insert_index = i + 1

        lines.insert(insert_index, new_line)

        new = "\n".join(lines)
        if old.endswith("\n"):
            new += "\n"
    elif os.path.splitext(file_path)[1].lower() in {".html", ".htm"}:
        deterministic_new = deterministic_html_h1_edit(old, instruction)
        if isinstance(deterministic_new, str):
            print("[DETERMINISTIC EDIT] html h1 replacement")
            new = deterministic_new
        else:
            print("[FUNCTION] none inferred, using full-file fallback")
            new = ask_llm_edit(file_path, old, instruction)
    elif (
        re.search(r'change the string from ["\\\'](.+?)["\\\'] to ["\\\'](.+?)["\\\']', instruction, re.IGNORECASE)
        or re.search(r'change the string ["\\\'](.+?)["\\\'] to ["\\\'](.+?)["\\\']', instruction, re.IGNORECASE)
        or re.search(r'replace the string ["\\\'](.+?)["\\\'] with ["\\\'](.+?)["\\\']', instruction, re.IGNORECASE)
    ):
        print("[DETERMINISTIC EDIT] quoted string replacement")
        match = (
            re.search(r'change the string from ["\\\'](.+?)["\\\'] to ["\\\'](.+?)["\\\']', instruction, re.IGNORECASE)
            or re.search(r'change the string ["\\\'](.+?)["\\\'] to ["\\\'](.+?)["\\\']', instruction, re.IGNORECASE)
            or re.search(r'replace the string ["\\\'](.+?)["\\\'] with ["\\\'](.+?)["\\\']', instruction, re.IGNORECASE)
        )
        source_text = match.group(1)
        replacement_text = match.group(2)
        if source_text not in old:
            return record_edit_failure("string_not_found", f"Rejected: string not found: {source_text}")
        new = old.replace(source_text, replacement_text, 1)
    elif force_full_file_edit:
        if "logging.basicconfig" in lowered_instruction and "logging.basicConfig(" in old:
            print("[NO-OP] logging.basicConfig already present")
            return True

        print("[FUNCTION] none inferred, using full-file fallback")

        new = ask_llm_edit(file_path, old, instruction)

    elif target_class:
        print(f"[CLASS] {target_class}")
        new = ask_llm_edit(file_path, old, instruction).replace("", "").strip()
    elif "print " in instruction.lower() and target_function == "main":
        print("[DETERMINISTIC EDIT] print insertion")
        new = old.replace(
            "set_current_dir(os.getcwd())\n",
            "set_current_dir(os.getcwd())\n\n    print(\"Hello\")\n"
        )
    elif "logging" in instruction.lower() and target_function == "main":
        print("[DETERMINISTIC EDIT] logging setup")
        if "logging.basicConfig(" in old:
            print("[NO-OP] already satisfied")
            return True
        if "import logging" not in old:
            old = "import logging\n" + old
        new = old.replace(
            "set_current_dir(os.getcwd())\n",
            "set_current_dir(os.getcwd())\n\n    logging.basicConfig(level=logging.INFO)\n"
        )
    elif target_function:
        function_info = find_function_block(old, target_function)
        function_block = function_info["block"]
        function_context = build_function_edit_context(old, target_function)

        print(f"[FUNCTION] {target_function}")

        new_function_block = ask_llm_edit_function(
            file_path=file_path,
            function_name=target_function,
            old_function=function_block,
            instruction=instruction,
            file_context=function_context,
        ).replace("", "").strip()

        returned_defs = re.findall(r'(?m)^def ([A-Za-z_][A-Za-z0-9_]*)\s*\(', new_function_block)
        if not returned_defs:
            return record_edit_failure("invalid_function_edit_definition", "Rejected: function edit did not return a function definition")

        if len(returned_defs) != 1:
            return record_edit_failure("invalid_function_edit_definition", f"Rejected: function edit returned multiple functions: {returned_defs}")

        returned_name = returned_defs[0]
        if returned_name != target_function:
            return record_edit_failure("wrong_function_edit_name", f"Rejected: function edit returned {returned_name} instead of {target_function}")

        top_level_lines = []
        for line in new_function_block.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if line.startswith((" ", "\t")):
                continue
            if stripped.startswith("#"):
                continue
            if stripped.startswith(f"def {target_function}("):
                continue
            top_level_lines.append(stripped)

        if top_level_lines:
            return record_edit_failure("invalid_function_edit_definition", f"Rejected: function edit returned top-level content: {top_level_lines[:3]}")

        new = splice_function_block(old, target_function, new_function_block)
        if new is None:
            return record_edit_failure("splice_failed", "Rejected: failed to splice edited function back into file")
    else:
        print("[FUNCTION] none inferred, using full-file fallback")
        new = ask_llm_edit(file_path, old, instruction).strip()

        if new.count("import ") < old.count("import "):
            return record_edit_failure("unsafe_full_file_edit", "Rejected: lost import statements")

        if len(new) < len(old) * 0.5:
            return record_edit_failure("unsafe_full_file_edit", "Rejected: file shrunk too much")

        if os.path.basename(file_path) == "cli.py":
            new = restore_unrelated_cli_functions(old, new, instruction)

    new = strip_model_edit_artifacts(new, file_path)

    if new is None:
        return record_edit_failure("empty_edit_output", "Rejected: edit produced no file content")

    if os.path.basename(file_path) == "cli.py" and target_function != "main":
        new = sanitize_cli_entrypoint(old, new, instruction)

    is_valid_python, python_error = validate_python_text(file_path, new)

    if not is_valid_python:
        return record_edit_failure("python_compile_failed", f"Rejected: python compile failed after edit: {python_error}")
    if os.path.splitext(file_path)[1].lower() == ".py":
        undefined_constants = has_undefined_constants(new, old)
        if undefined_constants:
            return record_edit_failure("undefined_constants", f"Rejected: undefined constants introduced: {undefined_constants}")

    changed_lines, diff_ratio = calculate_diff_stats(old, new)

    if changed_lines == 0:
        return record_edit_failure("empty_diff", "Rejected: empty diff")

    if is_whitespace_only_change(old, new):
        return record_edit_failure("whitespace_only_edit", "Rejected: whitespace-only edit")

    if is_weak_self_edit(file_path, instruction, old, new):
        return record_edit_failure("weak_self_edit", "Rejected: weak self-edit that does not meaningfully match the instruction")

    # NEW: minimum meaningful diff guardrail
    if changed_lines <= 2 and diff_ratio < 0.02:
        if is_jarvis_self_request(instruction):
            return record_edit_failure("diff_too_small", "Rejected: diff too small to represent meaningful improvement")

    if changed_lines > max_changed_lines:
        return record_edit_failure("too_many_lines_changed", f"Rejected: too many lines changed ({changed_lines})")

    if diff_ratio > max_diff_ratio:
        return record_edit_failure("diff_too_large", f"Rejected: diff too large ({diff_ratio:.0%})")

    show_diff(old, new, file_path)
    validation_mode = choose_validation_mode(file_path, old, instruction)
    backup_path = make_backup(file_path)
    write_file_text(file_path, new)
    behavior_ok, behavior_msg = run_behavior_validation(file_path, instruction, validation_mode=validation_mode, execution_context=execution_context)
    LAST_EXECUTION_CONTEXT = execution_context
    print(behavior_msg)
    if not behavior_ok:
        print(rollback_file_after_failed_validation(file_path, old, backup_path))
        return record_edit_failure(FAILURE_BEHAVIOR_VALIDATION_FAILED, "[STOPPED] behavior validation failed after edit")
    clear_edit_failure_state()
    print("[EDIT APPLIED]")
    return True



def rollback_file_after_failed_validation(file_path, old_text, backup_path):
    if backup_path and os.path.exists(backup_path):
        shutil.copy2(backup_path, file_path)
        return f"[ROLLBACK] restored from backup: {backup_path}"

    if old_text:
        write_file_text(file_path, old_text)
        return "[ROLLBACK] restored previous in-memory file contents"

    try:
        os.remove(file_path)
        return "[ROLLBACK] removed newly created file after failed validation"
    except FileNotFoundError:
        return "[ROLLBACK] new file already absent after failed validation"


def validate_rename_files_project(command, result):
    parts = (command or "").strip().split()
    sample_dir = parts[-1].strip("\'\"") if parts else ""

    renamed = any(
        f.startswith("renamed_")
        for f in os.listdir(sample_dir)
    ) if os.path.isdir(sample_dir) else False

    return renamed, f"Task usefulness: rename_files renamed_files_exist={renamed} path={sample_dir}"


PROJECT_RUN_VALIDATORS = {
    "rename_files.py": validate_rename_files_project,
}


def validate_project_run_result(command, result):
    ok = bool((result or {}).get("success"))
    if not ok:
        return False, "Task usefulness: project run success=False"

    script = get_project_state("main_script") or ""
    script_name = os.path.basename(script)

    validator = PROJECT_RUN_VALIDATORS.get(script_name)
    if validator:
        return validator(command, result)

    return True, "Task usefulness: project run success=True"


def validate_current_project():
    project_root = get_project_state("project_root")
    project_type = get_project_state("project_type") or "python"
    main_script_name = get_project_state("main_script_name")
    main_script = get_project_state("main_script")

    if not project_root or not os.path.isdir(project_root):
        return False, "Project validation failed: project_root missing"

    if project_type == "python":
        if not main_script_name:
            return False, "Project validation failed: main_script_name missing"

        result = subprocess.run(
            ["python3", "-m", "py_compile", main_script_name],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            return False, result.stderr.strip() or "Project validation failed: python compile failed"

        return True, f"Project validation passed: python py_compile {main_script_name}"

    if project_type == "web":
        required_files = ["index.html", "styles.css", "script.js"]
        missing = [
            name for name in required_files
            if not os.path.isfile(os.path.join(project_root, name))
        ]
        if missing:
            return False, f"Project validation failed: missing web files {', '.join(missing)}"

        if main_script and not os.path.isfile(main_script):
            return False, f"Project validation failed: main_script missing {main_script}"

        return True, "Project validation passed: web files exist"

    return False, f"Project validation failed: unsupported project_type {project_type}"


def run_task_usefulness_validation(command, result, current_dir, run_mode=None):
    cmd_lower = (command or '').lower().strip()
    result = result or {}

    # --- MODE: interactive CLI ---
    if run_mode == "interactive_python_cli":
        return True, "Task usefulness: interactive CLI treated as valid (skipped execution)"

    # --- MODE: project run ---
    if run_mode == "project_run":
        return validate_project_run_result(command, result)

    # --- MODE: shell command ---
    if cmd_lower.startswith('mkdir '):
        target_path = result.get('target_path')
        ok = bool(target_path) and os.path.isdir(target_path)
        return ok, f"Task usefulness: mkdir target exists={ok} path={target_path}"

    if cmd_lower.startswith('touch '):
        target_path = result.get('target_path')
        ok = bool(target_path) and os.path.exists(target_path)
        return ok, f"Task usefulness: touch target exists={ok} path={target_path}"

    if cmd_lower.startswith('cd '):
        expected_dir = result.get('target_dir')
        actual_dir = result.get('cwd_after')
        ok = bool(expected_dir) and bool(actual_dir) and os.path.abspath(expected_dir) == os.path.abspath(actual_dir)
        return ok, f"Task usefulness: cd matched={ok} expected={expected_dir} actual={actual_dir}"

    if cmd_lower == 'pwd' or cmd_lower.startswith('pwd '):
        stdout = (result.get('stdout') or '').strip()
        ok = bool(stdout)
        return ok, f"Task usefulness: pwd produced_path={ok} value={stdout}"

    if cmd_lower.startswith('ls'):
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        success = result.get('success', False)

        if not success:
            return False, f"Task usefulness: ls produced_listing=False stderr={stderr}"

        ok = bool(stdout)
        return ok, f"Task usefulness: ls produced_listing={ok}"

    if 'git init' in cmd_lower:
        git_dir = os.path.join(current_dir, '.git')
        ok = os.path.isdir(git_dir)
        return ok, f"Task usefulness: git init created_git_dir={ok} path={git_dir}"

    if " -m py_compile " in cmd_lower:
        parts = (command or "").strip().split()
        target = parts[-1].strip("\'\"") if parts else ""
        if target and not os.path.isabs(target):
            target = os.path.join(current_dir, target)
        ok = bool(result.get("success")) and target.endswith(".py") and os.path.isfile(target)
        return ok, f"Task usefulness: py_compile target_exists={ok} path={target}"

    if cmd_lower.startswith(("python ", "python3 ")) and " -m " not in cmd_lower:
        parts = (command or "").strip().split()
        script = ""
        for part in parts[1:]:
            candidate = part.strip("\'\"")
            if candidate.endswith(".py"):
                script = candidate
                break

        script_path = script
        if script_path and not os.path.isabs(script_path):
            script_path = os.path.join(current_dir, script_path)

        stderr = result.get("stderr") or ""
        ok = (
            bool(result.get("success"))
            and bool(script_path)
            and os.path.isfile(script_path)
            and "traceback" not in stderr.lower()
        )
        return ok, f"Task usefulness: python_script success={bool(result.get('success'))} script_exists={os.path.isfile(script_path) if script_path else False} traceback={'traceback' in stderr.lower()} path={script_path}"

    return True, 'Task usefulness: no extra validation for this command.'



def run_step(step):
    if is_literal_shell_step(step):
        cmd = step.strip()
    else:
        cmd = ask_llm(step).strip()

    if not cmd or cmd == 'echo "No command generated"':
        print(f"\n[ERROR] No executable command generated for step: {step}")
        return False

    print(f"\n[CMD] {cmd}")

    if not is_safe(cmd):
        print("[BLOCKED]")
        return False

    if is_interactive_command(cmd):
        run_mode = "interactive_python_cli"
    else:
        run_mode = "shell_command"

    success, final_cmd, _, final_result = try_step_with_retry(step, cmd, run_mode=run_mode)
    if not success:
        return False

    if run_mode == "interactive_python_cli":
        print("[USEFULNESS] interactive CLI run skipped → treated as valid smoke test")
        return True

    usefulness_ok, usefulness_msg = run_task_usefulness_validation(
        final_cmd, final_result, get_current_dir(), run_mode=run_mode
    )
    print(f"[USEFULNESS] {usefulness_msg}")

    if not usefulness_ok:
        set_project_state("last_edit_failure_type", "task_usefulness_failed")
        set_project_state("last_edit_failure_message", usefulness_msg)
        print("[STOPPED] task usefulness validation failed")
        return False

    return True



def is_interactive_command(command):
    command = (command or "").strip().lower()

    interactive_signals = [
        "hangman.py",
        "tic_tac_toe",
        "ttt.py",
    ]

    if any(signal in command for signal in interactive_signals):
        return True

    return False



def run_project_script():
    script = get_project_state("main_script")
    sample_input_dir = get_project_state("sample_input_dir")
    sample_dir = get_project_state("sample_dir")
    project_root = get_project_state("project_root")

    pristine_dir = None
    if project_root:
        pristine_dir = os.path.join(project_root, "samples_pristine")

    source_dir = None
    if sample_input_dir and os.path.isdir(sample_input_dir):
        source_dir = sample_input_dir
    elif pristine_dir and os.path.isdir(pristine_dir):
        source_dir = pristine_dir
    elif sample_dir and os.path.isdir(sample_dir):
        source_dir = sample_dir

    if not script:
        print("Missing script")
        return False

    if not source_dir:
        ok, message = validate_current_project()
        print(f"[PROJECT VALIDATION] {message}")
        return ok

    temp_root = tempfile.mkdtemp(prefix="jarvis_smoke_")
    temp_sample_dir = os.path.join(temp_root, "samples")
    shutil.copytree(source_dir, temp_sample_dir)

    cmd = f'python3 "{script}" "{temp_sample_dir}"'

    print("\nRunning project script:")
    print(cmd)

    if is_interactive_command(cmd):
        run_mode = "interactive_python_cli"
    else:
        run_mode = "project_run"

    if run_mode == "interactive_python_cli":
        print(f"[SKIPPED] interactive program detected")
        print(f"Run manually: {cmd}")
        shutil.rmtree(temp_root, ignore_errors=True)
        return True

    success, final_cmd, _, final_result = try_step_with_retry("run", cmd, run_mode=run_mode)

    if not success:
        failure_text = ""
        if isinstance(final_result, dict):
            failure_text = (
                final_result.get("stderr")
                or final_result.get("stdout")
                or final_result.get("error")
                or ""
            )
        else:
            failure_text = str(final_result or "")

        set_project_state("last_edit_failure_type", "project_run_failed")
        set_project_state("last_edit_failure_message", failure_text.strip() or "project run failed")
        shutil.rmtree(temp_root, ignore_errors=True)
        return False

    if success:
        usefulness_ok, usefulness_msg = run_task_usefulness_validation(
            final_cmd, final_result, get_current_dir(), run_mode=run_mode
        )
        print(f"[USEFULNESS] {usefulness_msg}")

        if not usefulness_ok:
            print("[STOPPED] task usefulness validation failed")
            shutil.rmtree(temp_root, ignore_errors=True)
            return False

    shutil.rmtree(temp_root, ignore_errors=True)
    return success

def execute_plan(steps, retry_depth=0):
    for step in steps:
        print(f"\n=== {step} ===")

        if is_edit_step(step):
            ok = run_edit(step)
        elif is_run_step(step):
            ok = run_project_script()
        else:
            command_step = normalize_command_for_execution_context(step, LAST_EXECUTION_CONTEXT)
            if command_step != step:
                print(f"[CONTEXT COMMAND] {step} -> {command_step}")
            ok = run_step(command_step)

        if not ok:
            print("\n[STOPPED] step failed")
            return False

    print("\n[SUCCESS] plan complete")

    if any(is_edit_step(s) for s in steps):
        print("\n[AUTO-RUN] executing project for validation")
        auto_ok = run_project_script()
        if not auto_ok:
            print("\n[RETRY] auto-run failed, attempting correction")

            last_failure_message = get_project_state("last_edit_failure_message", "unknown failure")
            failure_instruction = f"fix this error without breaking existing behavior: {last_failure_message}"

            retry_request = build_retry_aware_context_request(failure_instruction)

            retry_target = resolve_edit_file_path(get_project_state("main_script_name"))
            retry_backup_path = make_backup(retry_target)
            retry_steps = [f"edit {get_project_state('main_script_name')} to {retry_request}"]

            if retry_depth >= 1:
                set_project_state("last_edit_failure_type", "retry_loop_blocked")
                set_project_state("last_edit_failure_message", "Correction retry already attempted once; blocking recursive retry.")
                print("\n[STOPPED] retry loop blocked")
                return False

            retry_success = execute_plan(retry_steps, retry_depth=retry_depth + 1)

            if not retry_success:
                if retry_backup_path and restore_backup(retry_target, retry_backup_path):
                    print(f"\n[ROLLBACK] restored failed correction from backup: {retry_backup_path}")
                print("\n[STOPPED] auto-run validation failed after retry")
                return False

            return True

    return True



def build_retry_aware_context_request(request):
    request = (request or "").strip()
    failure_type = get_project_state("last_edit_failure_type", "")
    failure_message = get_project_state("last_edit_failure_message", "")

    if not request or not failure_type:
        return request

    if failure_type == FAILURE_WEAK_SELF_EDIT:
        return (
            f"{request}. Previous attempt failed as weak_self_edit. "
            f"Generate a concrete behavior-changing edit that modifies logic or outputs, not wording."
        )

    if failure_type == FAILURE_EMPTY_DIFF:
        return (
            f"{request}. Previous attempt produced empty_diff. "
            f"If already correct, do not edit. Otherwise make a real behavioral change."
        )

    if failure_type == FAILURE_DIFF_TOO_SMALL:
        return (
            f"{request}. Previous attempt diff was too small. "
            f"Make a more meaningful change."
        )

    if failure_type == FAILURE_PYTHON_COMPILE_FAILED:
        return (
            f"{request}. Previous attempt failed to compile. "
            f"Return valid Python only."
        )

    if failure_type == FAILURE_BEHAVIOR_VALIDATION_FAILED:
        return (
            f"{request}. Previous attempt failed behavior validation: {failure_message}. "
            f"Preserve output contract while fixing logic."
        )

    return request


def is_context_info_request(request):
    lowered = (request or "").lower()
    info_terms = [
        "show project structure",
        "project structure",
        "show structure",
        "show code map",
        "code map",
        "what files",
        "list files",
    ]
    return any(term in lowered for term in info_terms)



def sanitize_project_name(name):
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip().lower()).strip("_")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned


def get_default_projects_root():
    return "/home/chris/projects"


def create_project(project_name, projects_root=None, project_type="python"):
    clean_name = sanitize_project_name(project_name)
    if not clean_name:
        return False, "Project name is required."

    project_type = (project_type or "python").strip().lower()
    if project_type not in {"python", "web"}:
        return False, f"Unsupported project type: {project_type}"

    projects_root = projects_root or get_default_projects_root()
    project_root = os.path.abspath(os.path.join(projects_root, clean_name))
    app_root = os.path.abspath(get_app_root())

    if project_root == app_root or project_root.startswith(app_root + os.sep):
        return False, f"Refusing to create user project inside Jarvis core: {project_root}"

    if os.path.exists(project_root) and os.listdir(project_root):
        return False, f"Project already exists and is not empty: {project_root}"

    os.makedirs(project_root, exist_ok=True)

    readme_path = os.path.join(project_root, "README.md")

    if project_type == "python":
        main_script_name = "app.py"
        main_script = os.path.join(project_root, main_script_name)
        if not os.path.exists(main_script):
            write_file_text(main_script, 'def main():\n    print("Hello from Jarvis project")\n\n\nif __name__ == "__main__":\n    main()\n')
    else:
        main_script_name = "index.html"
        main_script = os.path.join(project_root, main_script_name)
        index_path = main_script
        styles_path = os.path.join(project_root, "styles.css")
        script_path = os.path.join(project_root, "script.js")

        if not os.path.exists(index_path):
            write_file_text(index_path, '<!doctype html>\n<html lang="en">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>Jarvis Web Project</title>\n  <link rel="stylesheet" href="styles.css">\n</head>\n<body>\n  <main>\n    <h1>Hello from Jarvis</h1>\n  </main>\n  <script src="script.js"></script>\n</body>\n</html>\n')
        if not os.path.exists(styles_path):
            write_file_text(styles_path, 'body {\n  font-family: system-ui, sans-serif;\n  margin: 2rem;\n}\n')
        if not os.path.exists(script_path):
            write_file_text(script_path, 'console.log("Jarvis web project ready");\n')

    if not os.path.exists(readme_path):
        write_file_text(readme_path, f"# {clean_name}\n\nCreated by Jarvis as a {project_type} project.\n")

    git_dir = os.path.join(project_root, ".git")
    if not os.path.isdir(git_dir):
        result = subprocess.run(
            ["git", "init"],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            return False, result.stderr.strip() or "git init failed"

    if project_type == "python":
        compile_result = subprocess.run(
            ["python3", "-m", "py_compile", main_script_name],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if compile_result.returncode != 0:
            return False, compile_result.stderr.strip() or "initial project validation failed"

    commit_check = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=project_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if commit_check.returncode != 0:
        add_result = subprocess.run(
            ["git", "add", "."],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if add_result.returncode != 0:
            return False, add_result.stderr.strip() or "git add failed"

        commit_result = subprocess.run(
            ["git", "commit", "-m", "initial project scaffold"],
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if commit_result.returncode != 0:
            return False, commit_result.stderr.strip() or "initial project commit failed"

    set_project_state("project_root", project_root)
    set_project_state("project_type", project_type)
    set_project_state("main_script_name", main_script_name)
    set_project_state("main_script", main_script)
    set_current_dir(project_root)

    return True, f"Created {project_type} project: {project_root}"


def create_project_mode(project_name, project_type="python"):
    ok, message = create_project(project_name, project_type=project_type)
    print(message)
    if not ok:
        print("[FAILED]")
        return
    print("[OK]")


def context_mode(request=None):
    if not request:
        request = input("Enter request: ").strip()
        if not request:
            return

    project_root = get_project_state("project_root")
    if project_root and os.path.isdir(project_root):
        set_current_dir(project_root)

    cwd = get_current_dir()

    print(f"\n[Context Mode] cwd: {cwd}")

    if is_context_info_request(request):
        print("\n[PROJECT STATE]")
        print(format_project_state())
        return

    state_text = format_project_state()
    plan_text = ask_llm_context_plan(request, state_text, cwd)

    steps = parse_plan_steps(plan_text)
    steps = normalize_context_steps(steps, request)

    print("\n[PLAN]")
    for i, step in enumerate(steps, 1):
        print(f"{i}. {step}")

    if not steps:
        print("[ERROR] No valid steps generated.")
        return

    confirm = input("\nUse this plan? (y/n): ").strip().lower()
    if confirm != "y":
        print("[SKIPPED]")
        return

    execute_plan(steps)

def planner_mode(request=None):
    if not request:
        request = input("Goal > ").strip()

    if not request:
        return

    cwd = get_current_dir()
    plan_text = ask_llm_plan(request, cwd)
    steps = parse_plan_steps(plan_text)

    print("\n[PLANNER]")
    for i, step in enumerate(steps, 1):
        print(f"{i}. {step}")


def build_mode(request=None):
    if not request:
        request = input("Build goal > ").strip()

    if not request:
        return

    cwd = get_current_dir()
    plan_text = ask_llm_plan(request, cwd)
    steps = parse_plan_steps(plan_text)

    # Add validation for malformed build plans
    if not validate_build_plan(steps):
        print("\nMalformed build plan detected. Please provide a valid build request.")
        return

    # Add validation for build plan steps
    for step in steps:
        if not is_valid_step(step):
            print(f"\nInvalid step detected: {step}. Please ensure all steps are properly formatted.")
            return

    print("\n[BUILD PLAN]")
    for i, step in enumerate(steps, 1):
        print(f"{i}. {step}")

    use_plan = input("\nUse this plan? (y/n): ").strip().lower()
    if use_plan != "y":
        return

    execute_plan(steps)
def validate_build_plan(steps):
    if not steps or not isinstance(steps, list):
        return False

    for step in steps:
        if not is_valid_step(step):
            return False

    return True


def is_valid_step(step):
    # Rejects placeholder and chained commands
    if not isinstance(step, str):
        return False

    s = step.strip()
    if not s:
        return False

    if "`" in s:
        return False

    if "No command generated" in s:
        return False

    if "run/validate the relevant script or test command" in s.lower():
        return False

    if "&&" in s or "||" in s or ";" in s:
        return False

    if re.search(r'\b\d+\.\s+[\w\s]+', s) and re.search(r'\b\d+\.\s+[\w\s]+\b\d+\.\s+', s):
        return False

    code_like_patterns = [
        r'^\s*def\s+[A-Za-z_][A-Za-z0-9_]*\s*\(',
        r'^\s*class\s+[A-Za-z_][A-Za-z0-9_]*\s*[:(]',
        r'^\s*if __name__ == ["\']__main__["\']\s*:',
        r'^\s*return\b',
        r'^\s*print\s*\(',
    ]

    for pattern in code_like_patterns:
        if re.search(pattern, s):
            return False

    return True
def list_skill_files():
    skill_dir = get_skills_dir()
    if not os.path.isdir(skill_dir):
        return []

    names = []
    for name in os.listdir(skill_dir):
        if name.endswith(".json") or name.endswith(".txt"):
            names.append(name)

    names.sort()
    return names


def resolve_skill_path(name):
    if not name:
        return None

    skill_dir = get_skills_dir()
    candidates = [
        name,
        f"{name}.json",
        f"{name}.txt",
    ]

    for candidate in candidates:
        path = os.path.join(skill_dir, candidate)
        if os.path.exists(path):
            return path

    normalized = re.sub(r"\s+", "_", name.strip().lower())
    for file_name in list_skill_files():
        base = os.path.splitext(file_name)[0].lower()
        if base == normalized or base == name.strip().lower():
            return os.path.join(skill_dir, file_name)

    return None


def load_skill_definition(path):
    text = read_file_text(path)

    if path.endswith(".json"):
        data = json.loads(text)
        steps = data.get("steps", [])
        variables = data.get("variables", [])
        return {
            "name": data.get("name", os.path.splitext(os.path.basename(path))[0]),
            "steps": steps,
            "variables": variables,
        }

    steps = parse_plan_steps(text)
    return {
        "name": os.path.splitext(os.path.basename(path))[0],
        "steps": steps,
        "variables": [],
    }


def extract_step_variables(steps):
    found = []
    seen = set()

    for step in steps:
        for match in re.findall(r"{([a-zA-Z_][a-zA-Z0-9_]*)}", step):
            if match not in seen:
                seen.add(match)
                found.append(match)

    return found


def substitute_skill_variables(steps, values):
    rendered = []
    for step in steps:
        rendered_step = step
        for key, value in values.items():
            rendered_step = rendered_step.replace("{" + key + "}", value)
        rendered.append(rendered_step)
    return rendered


def skills_mode():
    files = list_skill_files()
    if not files:
        print("No skills found.")
        return

    print("\n[SKILLS]")
    for name in files:
        print(f"- {name}")


def view_skill_mode(name):
    path = resolve_skill_path(name)
    if not path:
        print("Skill not found.")
        return

    print(f"\n[SKILL] {path}\n")
    print(read_file_text(path))


def run_skill_mode(name):
    path = resolve_skill_path(name)
    if not path:
        print("Skill not found.")
        return

    skill = load_skill_definition(path)
    steps = skill["steps"]
    variables = list(skill.get("variables", []))

    for var_name in extract_step_variables(steps):
        if var_name not in variables:
            variables.append(var_name)

    values = {}
    for var_name in variables:
        values[var_name] = input(f"{var_name} > ").strip()

    rendered_steps = substitute_skill_variables(steps, values)

    print(f"\n[RUN SKILL] {skill['name']}")
    for i, step in enumerate(rendered_steps, 1):
        print(f"{i}. {step}")

    confirm = input("\nRun this skill? (y/n): ").strip().lower()
    if confirm != "y":
        return

    execute_plan(rendered_steps)


def save_skill_mode():
    skill_dir = get_skills_dir()
    os.makedirs(skill_dir, exist_ok=True)

    name = input("Skill name > ").strip()
    if not name:
        print("No skill name.")
        return

    print("Paste skill steps. Type END on its own line when done.")
    lines = []
    while True:
        line = input()
        if line == "END":
            break
        lines.append(line)

    raw_text = "\n".join(lines).strip()
    if not raw_text:
        print("No skill steps.")
        return

    variables_text = input("Variables (comma separated, optional) > ").strip()
    variables = [v.strip() for v in variables_text.split(",") if v.strip()]

    steps = parse_plan_steps(raw_text)
    path_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name).strip("_")
    if not path_name:
        path_name = "skill"

    path = os.path.join(skill_dir, f"{path_name}.json")
    data = {
        "name": name,
        "steps": steps,
        "variables": variables,
    }

    write_file_text(path, json.dumps(data, indent=2))
    print(f"Saved skill: {path}")


def showfile_mode(arg):
    if not arg:
        print("Usage: showfile <path>")
        return

    candidate = arg.strip()
    possible_paths = []

    if os.path.isabs(candidate):
        possible_paths.append(candidate)
    else:
        possible_paths.append(os.path.join(get_current_dir(), candidate))
        possible_paths.append(os.path.join(get_app_root(), candidate))
        project_root = get_project_state("project_root")
        if project_root:
            possible_paths.append(os.path.join(project_root, candidate))

    for path in possible_paths:
        if os.path.exists(path) and os.path.isfile(path):
            print(f"\n[FILE] {path}\n")
            print(read_file_text(path))
            return

    print("File not found.")


def _call_optional_db_rows(*function_names):
    for name in function_names:
        fn = getattr(db_mod, name, None)
        if callable(fn):
            try:
                return fn()
            except TypeError:
                continue
    return None


def history_mode():
    rows = _call_optional_db_rows("get_command_history", "get_history")
    if rows is None:
        print("History not available in current db module.")
        return

    print("\n[HISTORY]")
    for row in rows:
        print(row)


def plans_mode():
    rows = _call_optional_db_rows("get_saved_plans", "get_plans")
    if rows is None:
        print("Plans not available in current db module.")
        return

    print("\n[PLANS]")
    for row in rows:
        if not isinstance(row, dict) or 'plan_id' not in row or 'description' not in row:
            print(f"Malformed plan detected: {row}")
            continue
        print(row)
def edits_mode():
    rows = _call_optional_db_rows("get_file_edits", "get_edits")
    if rows is None:
        print("Edits not available in current db module.")
        return

    print("\n[EDITS]")
    for row in rows:
        print(row)


def help_mode():
    print("""
Commands:
  continue <request>     Autonomous context-aware edit/run loop
  context                Prompt for a continue-style request
  planner                Generate and show a plan
  plan <goal>            Generate and show a plan for a goal
  build <goal>           Generate a plan and execute it
  create project <name> Create a new Python user app project outside Jarvis core
  create python project <name> Create a new Python user app project
  create web project <name> Create a new web project
  skills                 List saved skills
  saveskill              Save a skill
  viewskill <name>       Show a saved skill
  runskill <name>        Run a saved skill
  state                  Show project state
  pwd                    Show current working directory
  dbpath                 Show sqlite db path
  showfile <path>        Show a file
  history                Show command history if available
  plans                  Show saved plans if available
  edits                  Show file edits if available
  help                   Show this help
  exit                   Quit
""".strip())


def main():
    init_db()
    set_current_dir(os.getcwd())
    
    print("Jarvis ready.")
    print(f"DB path: {DB_FILE}")

    while True:
        cwd = get_current_dir()
        user_input = input(f"\nJarvis [{cwd}] > ").strip()
        if user_input.strip().lower().startswith("edit "):
            run_edit(user_input)
            continue

        if not user_input:
            continue

        if user_input in ["exit", "quit"]:
            break

        elif user_input.startswith("continue "):
            context_mode(user_input[9:].strip())

        elif user_input == "context":
            context_mode()

        elif user_input == "planner":
            planner_mode()

        elif user_input.startswith("plan "):
            planner_mode(user_input[5:].strip())

        elif user_input.startswith("build "):
            build_mode(user_input[6:].strip())

        elif user_input.startswith("create python project "):
            create_project_mode(user_input[len("create python project "):].strip(), project_type="python")

        elif user_input.startswith("create web project "):
            create_project_mode(user_input[len("create web project "):].strip(), project_type="web")

        elif user_input.startswith("create project "):
            create_project_mode(user_input[len("create project "):].strip(), project_type="python")

        elif user_input == "skills":
            skills_mode()

        elif user_input == "saveskill":
            save_skill_mode()

        elif user_input.startswith("viewskill "):
            view_skill_mode(user_input[len("viewskill "):].strip())

        elif user_input.startswith("runskill "):
            run_skill_mode(user_input[len("runskill "):].strip())

        elif user_input == "state":
            for k, v, _ in get_all_project_state():
                print(f"{k}: {v}")

        elif user_input == "clearstate":
            clear_project_state()
            print("Project state cleared.")

        elif user_input.startswith("setcontext "):
            parts = user_input[len("setcontext "):].strip().split()
            if len(parts) != 2:
                print("Usage: setcontext <project_root> <main_script_name>")
            else:
                project_root, main_script_name = parts
                set_project_state("project_root", project_root)
                set_project_state("main_script_name", main_script_name)
                set_project_state("main_script", os.path.join(project_root, main_script_name))
                set_current_dir(project_root)
                print(f"Context set: project_root={project_root}, main_script_name={main_script_name}")

        elif user_input == "pwd":
            cmd = "pwd"
            print(f"Suggested command: {cmd}")
            confirm = input("Run it? (y/n): ").strip().lower()

            if confirm != "y":
                print("[SKIPPED]")
                continue

            if not is_safe(cmd):
                print("[BLOCKED]")
                continue

            run_mode = "shell_command"
            success, final_cmd, _, final_result = try_step_with_retry(user_input, cmd, run_mode=run_mode)
            if not success:
                print("[FAILED]")
                continue

            usefulness_ok, usefulness_msg = run_task_usefulness_validation(
                final_cmd, final_result, get_current_dir(), run_mode=run_mode
            )
            print(f"[USEFULNESS] {usefulness_msg}")
            if not usefulness_ok:
                set_project_state("last_edit_failure_type", "task_usefulness_failed")
                set_project_state("last_edit_failure_message", usefulness_msg)
                print("[FAILED]")

        elif user_input == "dbpath":
            print(DB_FILE)

        elif user_input.startswith("showfile "):
            showfile_mode(user_input[len("showfile "):].strip())

        elif user_input == "history":
            history_mode()

        elif user_input == "plans":
            plans_mode()

        elif user_input == "edits":
            edits_mode()

        elif user_input in ["help", "?"]:
            help_mode()

        else:
            cmd = ask_llm(user_input).strip()

            if not cmd or cmd == 'echo "No command generated"':
                print(f'[ERROR] No executable command generated for: {user_input}')
                continue

            print(f"Suggested command: {cmd}")
            confirm = input("Run it? (y/n): ").strip().lower()

            if confirm != "y":
                print("[SKIPPED]")
                continue

            if not is_safe(cmd):
                print("[BLOCKED]")
                continue

            if is_interactive_command(cmd):
                run_mode = "interactive_python_cli"
            else:
                run_mode = "shell_command"

            success, final_cmd, _, final_result = try_step_with_retry(user_input, cmd, run_mode=run_mode)
            if not success:
                print("[FAILED]")
                continue

            if run_mode == "interactive_python_cli":
                print("[USEFULNESS] interactive CLI run skipped → treated as valid smoke test")
                continue

            usefulness_ok, usefulness_msg = run_task_usefulness_validation(
                final_cmd, final_result, get_current_dir(), run_mode=run_mode
            )
            print(f"[USEFULNESS] {usefulness_msg}")
            if not usefulness_ok:
                set_project_state("last_edit_failure_type", "task_usefulness_failed")
                set_project_state("last_edit_failure_message", usefulness_msg)
                print("[FAILED]")
if __name__ == "__main__":
    main()
