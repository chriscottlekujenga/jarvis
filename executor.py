import os
import subprocess

from db import save_command
from llm import ask_llm_retry
from verifier import verify_step

CURRENT_DIR = os.getcwd()
MAX_RETRY_ATTEMPTS = 1


def get_current_dir():
    return CURRENT_DIR


def set_current_dir(path):
    global CURRENT_DIR
    CURRENT_DIR = path


def resolve_path_from(base_dir, path_text):
    path_text = path_text.strip()
    path_text = os.path.expanduser(path_text)

    if os.path.isabs(path_text):
        return os.path.abspath(path_text)

    return os.path.abspath(os.path.join(base_dir, path_text))


def classify_command(cmd):
    s = cmd.strip()
    parts = s.split()
    if not parts:
        return {"kind": "unknown", "valid": False}

    if len(parts) == 1 and parts[0] in ("cd", "mkdir", "touch"):
        return {"kind": parts[0], "valid": False, "reason": "missing_args"}

    if "&&" in s or "||" in s or ";" in s:
        return {"kind": "invalid", "valid": False, "reason": "chained"}

    head = parts[0]

    if head == "cd":
        return {"kind": "cd", "valid": True}
    if head == "mkdir":
        return {"kind": "mkdir", "valid": True}
    if head == "touch":
        return {"kind": "touch", "valid": True}
    if head == "ls":
        return {"kind": "ls", "valid": True}
    if head == "pwd":
        return {"kind": "pwd", "valid": True}
    if head == "git" and len(parts) > 1 and parts[1] == "init":
        return {"kind": "git_init", "valid": True}
    if head in ("python3", "python") and "-m" in parts and "venv" in parts:
        return {"kind": "venv", "valid": True}

    return {"kind": "unknown", "valid": True}



def make_result(
    success,
    stdout="",
    stderr="",
    returncode=0,
    cwd_before=None,
    cwd_after=None,
    target_path=None,
    target_dir=None,
    command_kind=None,
):
    return {
        "success": success,
        "stdout": stdout,
        "stderr": stderr,
        "returncode": returncode,
        "cwd_before": cwd_before,
        "cwd_after": cwd_after,
        "target_path": target_path,
        "target_dir": target_dir,
        "command_kind": command_kind,
    }

def is_safe(cmd):
    if "&&" in cmd or "||" in cmd or ";" in cmd:
        return False

    blocked = [
        "rm -rf /",
        "shutdown",
        "reboot",
        "mkfs",
        "dd if=",
        "poweroff",
        "halt",
        "chmod -R 777 /",
        "chown -R /",
    ]
    return not any(b in cmd for b in blocked)


def run_command(cmd):
    global CURRENT_DIR

    print(f"\nRunning: {cmd}\n")
    cwd_before = CURRENT_DIR

    # Interactive command guard
    cmd_lower = (cmd or "").lower()
    if any(x in cmd_lower for x in ["hangman.py", "tic_tac_toe", "ttt.py"]):
        print("[SKIPPED] interactive command detected")
        print(f"Run manually: {cmd}")
        return {
            "success": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0,
            "cwd_before": cwd_before,
            "cwd_after": cwd_before,
        }
    info = classify_command(cmd)
    parts = cmd.split()

    if info["kind"] == "cd":
        try:
            if len(parts) < 2:
                raise ValueError("missing target directory")
            target_dir = resolve_path_from(cwd_before, parts[1])
            os.chdir(target_dir)
            CURRENT_DIR = target_dir
            print(f"Changed directory to {CURRENT_DIR}")
            return make_result(
                success=True,
                stdout=f"Changed directory to {CURRENT_DIR}",
                stderr="",
                returncode=0,
                cwd_before=cwd_before,
                cwd_after=CURRENT_DIR,
                target_dir=target_dir,
                command_kind="cd",
            )
        except Exception as e:
            msg = f"cd error: {e}"
            print(msg)
            target_dir = resolve_path_from(cwd_before, parts[1]) if len(parts) >= 2 else None
            return make_result(
                success=False,
                stdout="",
                stderr=msg,
                returncode=1,
                cwd_before=cwd_before,
                cwd_after=cwd_before,
                target_dir=target_dir,
                command_kind="cd",
            )

    result_meta = {
        "cwd_before": cwd_before,
        "cwd_after": CURRENT_DIR,
        "command_kind": info["kind"],
        "target_path": None,
        "target_dir": None,
    }

    cmd_lower = cmd.lower()

    if info["kind"] in ("mkdir", "touch", "venv") and len(parts) >= 2:
        result_meta["target_path"] = resolve_path_from(cwd_before, parts[-1])

    try:
        if info["kind"] != "unknown":
            result = subprocess.run(
                parts,
                shell=False,
                cwd=cwd_before,
                capture_output=True,
                text=True,
            )
        else:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd_before,
                capture_output=True,
                text=True,
            )

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        return make_result(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            cwd_before=result_meta.get("cwd_before"),
            cwd_after=result_meta.get("cwd_after"),
            target_path=result_meta.get("target_path"),
            target_dir=result_meta.get("target_dir"),
            command_kind=result_meta.get("command_kind"),
        )
    except Exception as e:
        msg = f"Error: {e}"
        print(msg)
        return make_result(
            success=False,
            stdout="",
            stderr=msg,
            returncode=1,
            cwd_before=result_meta.get("cwd_before"),
            cwd_after=result_meta.get("cwd_after"),
            target_path=result_meta.get("target_path"),
            target_dir=result_meta.get("target_dir"),
            command_kind=result_meta.get("command_kind"),
        )


def try_step_with_retry(step_text, command, run_mode=None):
    save_command(step_text, command, "generated")

    info = classify_command(command)

    if not info.get("valid", False):
        print("Blocked by command classification.")
        save_command(step_text, command, "blocked")
        return False, command, "blocked", {
            "success": False,
            "stdout": "",
            "stderr": "Blocked by classification.",
            "returncode": 1,
        }

    if not is_safe(command):
        print("Blocked.")
        save_command(step_text, command, "blocked")
        return False, command, "blocked", {
            "success": False,
            "stdout": "",
            "stderr": "Blocked by safety policy.",
            "returncode": 1,
        }

    run_result = run_command(command)
    verified, verify_msg = verify_step(info["kind"], command, run_result, CURRENT_DIR, run_mode=run_mode)
    print(f"Verifier: {verify_msg}")

    if run_result["success"] and verified:
        save_command(step_text, command, "success")
        return True, command, "success", run_result

    save_command(step_text, command, "failed")

    for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        print(f"\nRetry attempt {attempt}/{MAX_RETRY_ATTEMPTS}")
        fixed_command = ask_llm_retry(
            step_text,
            command,
            run_result["stdout"],
            run_result["stderr"],
        ).strip()

        retry_info = classify_command(fixed_command)

        if not fixed_command:
            print("Retry generation returned empty command.")
            return False, command, "failed", run_result

        if not retry_info.get("valid", False):
            print("Retry command failed classification.")
            return False, command, "failed", run_result

        if retry_info["kind"] != info["kind"]:
            print("Retry changed command kind. Rejecting.")
            return False, command, "failed", run_result

        if fixed_command == command:
            print("Retry did not improve the command.")
            return False, command, "failed", run_result

        print(f"Suggested retry command: {fixed_command}")
        save_command(step_text, fixed_command, "retry_generated")

        if not is_safe(fixed_command):
            print("Blocked retry command.")
            save_command(step_text, fixed_command, "blocked")
            continue

        retry_confirm = input("Run retry command? (y/n): ").strip().lower()
        if retry_confirm != "y":
            print("Retry skipped.")
            save_command(step_text, fixed_command, "skipped")
            continue

        retry_result = run_command(fixed_command)
        retry_info = classify_command(fixed_command)
        verified, verify_msg = verify_step(retry_info["kind"], fixed_command, retry_result, CURRENT_DIR, run_mode=run_mode)
        print(f"Verifier: {verify_msg}")

        if retry_result["success"] and verified:
            save_command(step_text, fixed_command, "success")
            return True, fixed_command, "success", retry_result

        save_command(step_text, fixed_command, "failed")
        command = fixed_command
        run_result = retry_result

    return False, command, "failed", run_result
