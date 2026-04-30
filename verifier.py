import os


def verify_step(command_kind, command, result, current_dir, run_mode=None):
    if not result["success"]:
        return False, f"Command '{command}' failed with exit code {result['returncode']}."

    if command_kind == "cd":
        if not result.get("target_dir"):
            return False, f"Command '{command}' missing target directory."

        expected_dir = os.path.abspath(result["target_dir"])
        actual_dir = os.path.abspath(result["cwd_after"])
        ok = actual_dir == expected_dir
        return ok, f"Command '{command}': cd reports expected directory: {expected_dir}, actual directory: {actual_dir}, match result: {ok}"

    if command_kind == "git_init":
        git_dir = os.path.join(current_dir, ".git")
        exists = os.path.isdir(git_dir)
        return exists, f"Command '{command}': .git directory path: {git_dir}, exists: {exists}"

    if command_kind == "mkdir":
        target_path = os.path.abspath(result["target_path"])
        exists = os.path.isdir(target_path)
        return exists, f"Command '{command}': mkdir reports target directory: {target_path}, exists: {exists}"

    if command_kind == "venv":
        target_path = os.path.abspath(result["target_path"])
        exists = os.path.isdir(target_path)
        return exists, f"Command '{command}': venv reports virtual environment directory: {target_path}, exists: {exists}"

    if command_kind == "touch":
        target_path = os.path.abspath(result["target_path"])
        exists = os.path.exists(target_path)
        return exists, f"Command '{command}': touch reports file path: {target_path}, exists: {exists}"

    if command_kind == "pwd":
        current_directory = result["stdout"].strip()
        if not current_directory:
            return False, f"Command '{command}' returned empty stdout."
        return True, f"Command '{command}': pwd reports current directory: {current_directory}"

    if command_kind == "ls":
        if result["returncode"] != 0:
            return False, f"Command '{command}' failed with exit code {result['returncode']}."
        if "No such file or directory" in result["stderr"]:
            return False, f"Command '{command}' failed: path does not exist."

        stdout = (result.get("stdout") or "").strip()
        if not stdout:
            return False, f"Command '{command}' returned empty listing."

        return True, f"Command '{command}': ls returned valid listing"
    return True, f"Command '{command}': Basic verification passed."
