import json
import os
import re

from db import SKILLS_DIR, now

VAR_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def parse_plan_steps(plan_text):
    steps = []

    for line in plan_text.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("- "):
            line = line[2:].strip()
        elif line.startswith("* "):
            line = line[2:].strip()

        if "." in line:
            left, right = line.split(".", 1)
            if left.strip().isdigit():
                line = right.strip()

        if line:
            steps.append(line)

    return steps


def extract_variables_from_steps(steps):
    seen = []
    for step in steps:
        for match in VAR_PATTERN.findall(step):
            if match not in seen:
                seen.append(match)
    return seen


def skill_path(skill_name):
    safe_name = skill_name.strip().replace(" ", "_")
    return os.path.join(SKILLS_DIR, f"{safe_name}.json")


def validate_skill_name(skill_name):
    if not skill_name:
        return False, "Skill name is required."
    if len(skill_name) > 80:
        return False, "Skill name is too long."
    if any(ch in skill_name for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
        return False, "Skill name contains invalid characters."
    return True, ""


def validate_skill_steps(steps):
    if not steps:
        return False, "Skill must have at least one step."

    cleaned = []
    for step in steps:
        s = step.strip()
        if not s:
            continue
        cleaned.append(s)

    if not cleaned:
        return False, "Skill must have at least one non-empty step."

    return True, ""


def validate_variable_name(name):
    return re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", name) is not None


def validate_skill_variables(variables):
    seen = set()

    for var_name in variables:
        if not validate_variable_name(var_name):
            return False, f"Invalid variable name: {var_name}"
        if var_name in seen:
            return False, f"Duplicate variable name: {var_name}"
        seen.add(var_name)

    return True, ""


def validate_declared_variables_used(steps, variables):
    used_vars = set(extract_variables_from_steps(steps))

    for var_name in variables:
        if var_name not in used_vars:
            return False, f"Variable not used in steps: {var_name}"

    return True, ""


def save_skill(skill_name, plan_text, vars_input=""):
    ok, msg = validate_skill_name(skill_name)
    if not ok:
        return False, msg

    steps = parse_plan_steps(plan_text)

    ok, msg = validate_skill_steps(steps)
    if not ok:
        return False, msg

    auto_variables = extract_variables_from_steps(steps)

    if vars_input.strip():
        variables = [v.strip() for v in vars_input.split(",") if v.strip()]
        for var_name in auto_variables:
            if var_name not in variables:
                variables.append(var_name)
    else:
        variables = auto_variables

    ok, msg = validate_skill_variables(variables)
    if not ok:
        return False, msg

    ok, msg = validate_declared_variables_used(steps, variables)
    if not ok:
        return False, msg

    data = {
        "name": skill_name,
        "created_at": now(),
        "variables": variables,
        "steps": steps,
        "raw_text": plan_text,
    }

    path = skill_path(skill_name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return True, path


def list_skills():
    return sorted([os.path.splitext(f)[0] for f in os.listdir(SKILLS_DIR) if f.endswith(".json")])


def load_skill(skill_name):
    path = skill_path(skill_name)
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def prompt_for_missing_skill_values(variables, provided_values):
    values = list(provided_values)

    for i, var_name in enumerate(variables):
        existing_value = values[i].strip() if i < len(values) else ""
        if existing_value:
            continue

        while True:
            entered = input(f"{var_name} > ").strip()
            if entered:
                if i < len(values):
                    values[i] = entered
                else:
                    values.append(entered)
                break
            print("Value required.")

    return values


def apply_skill_variables(steps, variables, values):
    mapping = {}
    for i, var_name in enumerate(variables):
        mapping[var_name] = values[i] if i < len(values) else ""

    rendered = []
    for step in steps:
        new_step = step
        for var_name, var_value in mapping.items():
            new_step = new_step.replace("{" + var_name + "}", var_value)
        rendered.append(new_step)

    return rendered
