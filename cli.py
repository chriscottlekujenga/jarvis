import os
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


def format_project_state():
    rows = get_all_project_state()
    lines = [f"{k}: {v}" for k, v, _ in rows]

    files = list_project_python_files()
    if files:
        lines.append("project_files:")
        for path in files:
            lines.append(f"- {path}")


    return "\n".join(lines)

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
        if module_name and contains_reference(lowered, module_name):
            return file_name
    if contains_reference(lowered, "jarvis"):
        return "cli.py"
    return None


def normalize_context_steps(steps, request_text=""):
    main_script = get_project_state("main_script_name")
    normalized = []

    explicit_target = extract_explicit_python_target(request_text)
    explicit_target_base = os.path.basename(explicit_target) if explicit_target else None

    jarvis_self_request = is_jarvis_self_request(request_text)
    jarvis_target_file = infer_jarvis_target_file(request_text)

    for step in steps:
        s = step.strip().rstrip(".").replace("`", "")
        if not s:
            continue

        if is_edit_step(s):
            parts = s.split(" to ", 1)
            instruction = parts[1].strip() if len(parts) == 2 else s[5:].strip()

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

            # 🔴 FORCE jarvis file if inferred
            if jarvis_self_request and jarvis_target_file:
                target_path = resolve_edit_file_path(jarvis_target_file)
                normalized.append(f"edit {target_path} to {instruction}")
                continue

            # fallback to main script
            target_path = resolve_edit_file_path(main_script)
            normalized.append(f"edit {target_path} to {instruction}")
            continue

        if is_literal_shell_step(s):
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

def has_undefined_constants(new_text):
    stripped = new_text

    stripped = re.sub(r'"""[\s\S]*?"""', '""', stripped)
    stripped = re.sub(r"'''[\s\S]*?'''", "''", stripped)
    stripped = re.sub(r'"[^"\n]*"', '""', stripped)
    stripped = re.sub(r"'[^'\n]*'", "''", stripped)

    pattern = r'\b[A-Z][A-Z0-9_]{2,}\b'

    used_constants = set(re.findall(pattern, stripped))
    defined_constants = set()

    for line in stripped.splitlines():
        if "=" in line:
            left = line.split("=", 1)[0].strip()
            if re.match(r'^[A-Z][A-Z0-9_]+$', left):
                defined_constants.add(left)

    builtin_allowed = {
        "__name__",
        "CLI",
        "FORCE",
        "MODE",
        "NEW",
    }

    undefined = sorted(
        c for c in used_constants
        if c not in defined_constants and c not in builtin_allowed
    )
    return undefined


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


def requires_behavior_validation(file_path, instruction):
    basename = os.path.basename(file_path or "")
    if basename in CORE_BEHAVIOR_VALIDATION_FILES:
        return True

    lowered = (instruction or "").lower()
    return any(keyword in lowered for keyword in BEHAVIOR_VALIDATION_KEYWORDS)


def run_behavior_validation(file_path, instruction, validation_mode=None):
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


def strengthen_edit_instruction(instruction):
    instruction = (instruction or "").strip()
    failure_type = get_project_state("last_edit_failure_type", "")
    failure_message = get_project_state("last_edit_failure_message", "")

    if not instruction or not failure_type:
        return instruction

    if failure_type == "weak_self_edit":
        return (
            f"{instruction}. "
            f"Make a concrete behavior-changing code edit, not a wording-only change. "
            f"Modify logic, condition handling, return values, or explicit output fields named in the request."
        )

    if failure_type == "empty_diff":
        return (
            f"{instruction}. "
            f"The previous attempt produced no change. "
            f"If the file already satisfies the request, keep it unchanged. "
            f"Otherwise make an observable code change."
        )

    if failure_type == "diff_too_small":
        return (
            f"{instruction}. "
            f"The previous attempt was too small. "
            f"Make a more meaningful but still scoped behavior change."
        )

    if failure_type == "behavior_validation_failed":
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
    elif target_class:
        print(f"[CLASS] {target_class}")
        new = ask_llm_edit(file_path, old, instruction).replace("", "").strip()
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

        returned_name_match = re.search(r'(?m)^def ([A-Za-z_][A-Za-z0-9_]*)\s*\(', new_function_block)
        if not returned_name_match:
            return record_edit_failure("invalid_function_edit_definition", "Rejected: function edit did not return a function definition")

        returned_name = returned_name_match.group(1)
        if returned_name != target_function:
            return record_edit_failure("wrong_function_edit_name", f"Rejected: function edit returned {returned_name} instead of {target_function}")

        new = splice_function_block(old, target_function, new_function_block)
        if new is None:
            return record_edit_failure("splice_failed", "Rejected: failed to splice edited function back into file")
    else:
        print("[FUNCTION] none inferred, using full-file fallback")
        new = ask_llm_edit(file_path, old, instruction).replace("", "").strip()

        if os.path.basename(file_path) == "cli.py":
            new = restore_unrelated_cli_functions(old, new, instruction)

    if os.path.basename(file_path) == "cli.py" and target_function != "main":
        new = sanitize_cli_entrypoint(old, new, instruction)

    is_valid_python, python_error = validate_python_text(file_path, new)

    if not is_valid_python:
        return record_edit_failure("python_compile_failed", f"Rejected: python compile failed after edit: {python_error}")
    undefined_constants = has_undefined_constants(new)
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
    behavior_ok, behavior_msg = run_behavior_validation(file_path, instruction, validation_mode=validation_mode)
    print(behavior_msg)
    if not behavior_ok:
        if backup_path and os.path.exists(backup_path):
            shutil.copy2(backup_path, file_path)
            print(f"[ROLLBACK] restored from backup: {backup_path}")
        elif old:
            write_file_text(file_path, old)
            print("[ROLLBACK] restored previous in-memory file contents")
        else:
            try:
                os.remove(file_path)
                print("[ROLLBACK] removed newly created file after failed validation")
            except FileNotFoundError:
                pass
        return record_edit_failure("behavior_validation_failed", "[STOPPED] behavior validation failed after edit")
    set_project_state("last_edit_failure_type", "")
    set_project_state("last_edit_failure_message", "")
    print("[EDIT APPLIED]")
    return True

def run_task_usefulness_validation(command, result, current_dir, run_mode=None):
    cmd_lower = (command or '').lower().strip()
    result = result or {}

    # --- MODE: interactive CLI ---
    if run_mode == "interactive_python_cli":
        return True, "Task usefulness: interactive CLI treated as valid (skipped execution)"

    # --- MODE: project run ---
    if run_mode == "project_run":
        ok = bool(result.get("success"))
        return ok, f"Task usefulness: project run success={ok}"

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

    if not script or not source_dir:
        print("Missing script or sample input directory")
        return False

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

def execute_plan(steps):
    for step in steps:
        print(f"\n=== {step} ===")

        if is_edit_step(step):
            ok = run_edit(step)
        elif is_run_step(step):
            ok = run_project_script()
        else:
            ok = run_step(step)

        if not ok:
            print("\n[STOPPED] step failed")
            return False

    print("\n[SUCCESS] plan complete")
    return True



def build_retry_aware_context_request(request):
    request = (request or "").strip()
    failure_type = get_project_state("last_edit_failure_type", "")
    failure_message = get_project_state("last_edit_failure_message", "")

    if not request or not failure_type:
        return request

    if failure_type == "weak_self_edit":
        return (
            f"{request}. Previous attempt failed as weak_self_edit. "
            f"Generate a concrete behavior-changing edit that modifies logic or outputs, not wording."
        )

    if failure_type == "empty_diff":
        return (
            f"{request}. Previous attempt produced empty_diff. "
            f"If already correct, do not edit. Otherwise make a real behavioral change."
        )

    if failure_type == "diff_too_small":
        return (
            f"{request}. Previous attempt diff was too small. "
            f"Make a more meaningful change."
        )

    if failure_type == "python_compile_failed":
        return (
            f"{request}. Previous attempt failed to compile. "
            f"Return valid Python only."
        )

    if failure_type == "behavior_validation_failed":
        return (
            f"{request}. Previous attempt failed behavior validation: {failure_message}. "
            f"Preserve output contract while fixing logic."
        )

    return request


def context_mode(request=None):
    if request:
        lowered = request.strip().lower()
        if lowered in {"add logging", "improve logging"} or lowered.endswith("add logging"):
            print("\n[ERROR] vague instruction blocked: add logging")
            return
    if not request:
        request = input("Change > ").strip()

    if not request:
        return

    if is_jarvis_self_request(request):
        set_current_dir(get_app_root())
    else:
        project_root = get_project_state("project_root")
        if project_root:
            set_current_dir(project_root)
    request = build_retry_aware_context_request(request)

    lowered = request.lower()
    if "change cli.py" in lowered or "edit cli.py" in lowered:
        print("\n[FAST PATH] skipping planner")
        instruction = request.replace("continue", "").strip()
        for prefix in ("change cli.py to ", "edit cli.py to "):
            if instruction.lower().startswith(prefix):
                instruction = instruction[len(prefix):].strip()
                break
        execute_plan([f"edit cli.py to {instruction}"])
        return

    cwd = get_current_dir()

    print(f"\n[Context Mode] cwd: {cwd}")

    state_text = format_project_state()
    plan_text = ask_llm_context_plan(request, state_text, cwd)

    raw_steps = parse_plan_steps(plan_text)
    steps = normalize_context_steps(raw_steps, request)

    if not raw_steps:
        print("\n[ERROR] context planner returned no numbered steps")
        return

    if not steps:
        print("\n[ERROR] context planner produced no executable steps after normalization")
        print("[RAW PLAN]")
        print(plan_text if plan_text.strip() else "<empty>")
        return
    lowered_request = (request or "").lower()
    improvement_request = any(word in lowered_request for word in ("improve", "update", "fix", "change", "modify"))
    has_edit_step = any(is_edit_step(step) for step in steps)

    if is_jarvis_self_request(request) and improvement_request and not has_edit_step:
        print("\n[ERROR] self-improvement request produced no edit step after normalization")
        print("[RAW PLAN]")
        print(plan_text if plan_text.strip() else "<empty>")
        set_project_state("last_edit_failure_type", "missing_edit_step")
        set_project_state("last_edit_failure_message", "Self-improvement request normalized to no edit step")
        return

    print("\n[PLAN]")
    for step in steps:
        print(f"- {step}")

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
