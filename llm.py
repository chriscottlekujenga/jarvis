import re
import requests

OLLAMA_HOST = "http://172.19.144.1:11434"
MODEL = "qwen2.5-coder:14b"


def _clean_text(text):
    text = text.replace("```python", "")
    text = text.replace("```bash", "")
    text = text.replace("```", "")
    return text.strip()


def _looks_like_shell_command(text):
    if not text:
        return False

    s = text.strip()
    shell_prefixes = (
        "cd ", "ls", "pwd", "mkdir ", "touch ", "cp ", "mv ", "rm ",
        "cat ", "grep ", "find ", "sed ", "awk ", "chmod ", "chown ",
        "git ", "python ", "python3 ", "pip ", "pip3 ", "pytest ",
        "bash ", "sh ", "zsh ", "echo ", "nano ", "vim "
    )
    return s.startswith(shell_prefixes)


def _fallback_command(prompt):
    s = prompt.strip()
    lower = s.lower()

    if _looks_like_shell_command(s):
        return s

    m = re.search(r'create a folder named\s+([A-Za-z0-9._/-]+)', lower)
    if m:
        return f"mkdir {m.group(1)}"

    m = re.search(r'create a directory named\s+([A-Za-z0-9._/-]+)', lower)
    if m:
        return f"mkdir {m.group(1)}"

    m = re.search(r'go into\s+([A-Za-z0-9._/-]+)', lower)
    if m:
        return f"cd {m.group(1)}"

    if "initialize git" in lower or "init git" in lower:
        return "git init"

    if "create a python virtual environment" in lower or "create python virtual environment" in lower:
        return "python3 -m venv venv"

    if lower in {"cd", "mkdir", "touch"}:
        return ""

    if "print working directory" in lower:
        return "pwd"

    if lower == "pwd":
        return "pwd"

    if lower == "ls":
        return "ls"

    if lower.startswith("ls "):
        return s

    return ""


def ask_llm(prompt):
    prompt_lower = prompt.strip().lower()

    if prompt_lower in {"cd", "mkdir", "touch"}:
        return ""

    direct = _fallback_command(prompt)
    if direct:
        return direct

    payload = {
        "model": MODEL,
        "prompt": f"""
You are a Linux command generator.

Rules:
- Output EXACTLY ONE valid Linux command
- No explanations
- No markdown
- No backticks
- Must be executable in bash
- Must be NON-INTERACTIVE
- Do not output a bare shell or bare interpreter as the whole command
- Allowed examples:
  - python3 app.py
  - python3 -m py_compile cli.py
  - ls -la
- Forbidden exact outputs:
  - bash
  - sh
  - zsh
  - python
  - python3
- If the user's request is already a valid shell command, return it unchanged
- If unclear, return an empty response

User request:
{prompt}
""",
        "stream": False,
    }

    r = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=120)
    r.raise_for_status()

    cmd = _clean_text(r.json()["response"])
    cmd = cmd.split("\n")[0].strip()

    if cmd in {"bash", "sh", "zsh", "python", "python3"}:
        return ""

    if cmd == 'echo "No command generated"':
        return ""

    fallback = _fallback_command(prompt)
    if not cmd and fallback:
        return fallback

    return cmd


def ask_llm_retry(step_text, failed_command, stdout_text, stderr_text):
    payload = {
        "model": MODEL,
        "prompt": f"""
Fix this Linux command.

Return EXACTLY ONE command.
No explanation.

Original step:
{step_text}

Failed command:
{failed_command}

Stdout:
{stdout_text}

Stderr:
{stderr_text}
""",
        "stream": False,
    }

    r = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=120)
    r.raise_for_status()

    cmd = _clean_text(r.json()["response"])
    cmd = cmd.split("\n")[0].strip()

    if not cmd:
        return failed_command

    return cmd


def ask_llm_edit(file_path, old_content, instruction):
    payload = {
        "model": MODEL,
        "prompt": f"""
You are editing an EXISTING Python file.

CRITICAL RULES:
- Return ONLY the FULL file
- No explanation
- No markdown
- No code fences
- DO NOT remove existing working logic
- DO NOT rewrite the script unless the instruction truly requires it
- Only ADD or MODIFY what is necessary
- Keep the SAME structure and flow
- Prefer the smallest possible change

Instruction:
{instruction}

Target file:
{file_path}

Current file:
{old_content}
""",
        "stream": False,
    }

    r = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=180)
    r.raise_for_status()

    return _clean_text(r.json()["response"])


def ask_llm_edit_function(file_path, function_name, old_function, instruction, file_context=""):
    payload = {
        "model": MODEL,
        "prompt": f"""
You are editing ONE function from an EXISTING Python file.

CRITICAL RULES:
- Return ONLY the FULL replacement for this single function
- Do NOT return the whole file
- Do NOT return explanations
- Do NOT return markdown
- Do NOT return code fences
- Keep the SAME function name: {function_name}
- Keep existing indentation valid Python
- Preserve existing behavior except where the instruction requires a change
- Make the SMALLEST change that satisfies the instruction
- Do not add unrelated imports or helper functions outside this function
- If the function already satisfies the request, return the function unchanged

Instruction:
{instruction}

Target file:
{file_path}

Function name:
{function_name}

Useful file context:
{file_context}

Current function:
{old_function}
""",
        "stream": False,
    }

    r = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=180)
    r.raise_for_status()

    return _clean_text(r.json()["response"])


def ask_llm_plan(request_text, current_dir):
    payload = {
        "model": MODEL,
        "prompt": f"""
Create a short execution plan.

STRICT PLAN CONTRACT:
- Output ONLY numbered steps
- Exactly one step per line
- Never use backticks
- Never output raw source code
- Never output tutorial prose
- Each step must be exactly one of:
  1. a single non-interactive shell command
  2. edit <file> to <instruction>
  3. a concrete run command
- Keep steps concrete and executable
- 3-8 steps maximum
- If the request can be completed with one file, prefer one edit step
- If the request clearly needs multiple files, use multiple edit steps
- Create folders before editing files inside them
- Each edit step must name the exact file to create or modify
- Do not use placeholder commands

Good example:
1. mkdir tic_tac_toe
2. edit tic_tac_toe/ttt.py to create a complete python command-line tic-tac-toe game with a main() entrypoint for two human players
3. python3 tic_tac_toe/ttt.py

Current directory:
{current_dir}

User request:
{request_text}
""",
        "stream": False,
    }

    r = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=180)
    r.raise_for_status()
    return _clean_text(r.json()["response"]).strip()

def _looks_like_numbered_plan(text):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return False
    for line in lines:
        parts = line.split(".", 1)
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].strip():
            return False
    return True


def _looks_like_context_plan_step(step_text):
    s = (step_text or "").strip().lower()
    if not s:
        return False

    shell_prefixes = (
        "cd ", "ls", "pwd", "mkdir ", "touch ", "cp ", "mv ", "rm ",
        "cat ", "grep ", "find ", "sed ", "awk ", "chmod ", "chown ",
        "git ", "python ", "python3 ", "pip ", "pip3 ", "pytest ",
        "bash ", "sh ", "zsh ", "echo "
    )

    if s.startswith("edit ") and " to " in s:
        return True

    if s.startswith(shell_prefixes):
        return True

    return False


def _looks_like_valid_context_plan(text):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return False

    for line in lines:
        parts = line.split(".", 1)
        if len(parts) != 2 or not parts[0].isdigit():
            return False
        step_text = parts[1].strip()
        if not _looks_like_context_plan_step(step_text):
            return False

    return True


def _fallback_context_plan(user_request):
    request = (user_request or "").strip()
    lowered = request.lower()

    target_file = "cli.py"
    instruction = request or "modify the relevant function to implement the requested behavior change"

    if "verifier" in lowered:
        target_file = "verifier.py"
    elif "llm" in lowered:
        target_file = "llm.py"
    elif "executor" in lowered:
        target_file = "executor.py"
    elif "skills" in lowered:
        target_file = "skills.py"
    elif "db" in lowered:
        target_file = "db.py"
    elif "files" in lowered:
        target_file = "files.py"
    elif "jarvis.py" in lowered:
        target_file = "jarvis.py"

    if "planner" in lowered or "context plan" in lowered:
        target_file = "llm.py"

    if "normalization" in lowered or "routing" in lowered:
        target_file = "cli.py"

    return f"1. edit {target_file} to {instruction}\n2. python3 -m py_compile {target_file}"


def ask_llm_context_plan(user_request, project_state, current_dir):
    payload = {
        "model": MODEL,
        "prompt": f"""
You are modifying an existing Python project.

STRICT PLAN CONTRACT:
- Output ONLY numbered steps
- No explanation
- Exactly one step per line
- Max 2 steps total unless the request clearly requires more
- Prefer one edit step and one validation step
- Mention the exact file whenever it is reasonably inferable from the request
- Do not use backticks
- Do not output raw source code
- Do not output placeholder or fake commands
- Do not output generic edits like:
  - update documentation
  - improve comments
  - clean up code
  - refactor code
  - update user documentation
  - make miscellaneous improvements
- Every edit instruction must describe a concrete code change to behavior, logic, parsing, validation, routing, output, or a specific function
- If the request is about fixing behavior, the edit instruction must describe the behavior being fixed
- If the request is about improving output, the edit instruction must describe the exact output improvement
- If the request is about routing, normalization, planning, verification, retry logic, parsing, diff limits, or project state, target the code that implements that behavior, not documentation
- Only use these step types:
  1. edit <file> to <concrete code change instruction>
  2. a concrete shell command to validate the change
- Do not combine multiple actions in one step
- Do not use shell chaining like &&, ||, or ;
- Ensure all file paths are relative to the current directory
- If the request mentions multiple specific files, generate one numbered edit step per file, then one final concrete validation command

Good examples:
1. edit cli.py to route self-improvement requests to jarvis app files instead of the last project file
2. python3 -m py_compile cli.py

1. edit verifier.py to include the verified command in success messages
2. python3 -m py_compile verifier.py

1. edit llm.py to make context-plan prompts require concrete code-change instructions instead of generic documentation edits
2. python3 -m py_compile llm.py

1. edit cli.py to normalize context-plan edit steps so planner fluff is not treated as a shell command
2. python3 -m py_compile cli.py

Current directory:
{current_dir}

Project state:
{project_state}

User request:
{user_request}
""",
        "stream": False,
    }

    # Sends the planning prompt to Ollama
    r = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=180)
    r.raise_for_status()

    text = _clean_text(r.json()["response"]).strip()

    if not text:
        return _fallback_context_plan(user_request)

    lowered_request = (user_request or "").lower()
    improvement_request = any(word in lowered_request for word in ("improve", "update", "fix", "change", "modify"))

    if _looks_like_valid_context_plan(text):
        if improvement_request:
            lines = [line.strip().lower() for line in text.splitlines() if line.strip()]
            has_edit_step = any(line.split(".", 1)[1].strip().startswith("edit ") for line in lines if "." in line)
            if has_edit_step:
                return text
        else:
            return text

    stricter_payload = {
        "model": MODEL,
        "prompt": payload["prompt"] + "\n\nCRITICAL: Return ONLY numbered steps. Do not include prose, code, headings, or explanations.",
        "stream": False,
    }

    r = requests.post(f"{OLLAMA_HOST}/api/generate", json=stricter_payload, timeout=180)
    r.raise_for_status()
    retry_text = _clean_text(r.json()["response"]).strip()

    if retry_text and _looks_like_valid_context_plan(retry_text):
        if improvement_request:
            lines = [line.strip().lower() for line in retry_text.splitlines() if line.strip()]
            has_edit_step = any(line.split(".", 1)[1].strip().startswith("edit ") for line in lines if "." in line)
            if has_edit_step:
                return retry_text
        else:
            return retry_text

    return _fallback_context_plan(user_request)
