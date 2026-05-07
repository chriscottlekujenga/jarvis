import difflib
import os
import shutil
from datetime import datetime


def read_file_text(file_path):
    if not os.path.exists(file_path):
        return ""

    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def write_file_text(file_path, content):
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def make_backup(file_path):
    if not os.path.exists(file_path):
        return ""

    backup_path = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    return backup_path


def restore_backup(file_path, backup_path):
    if not backup_path:
        return False
    if not os.path.exists(backup_path):
        return False

    shutil.copy2(backup_path, file_path)
    return True


def show_diff(old_text, new_text, file_path):
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"{file_path} (old)",
        tofile=f"{file_path} (new)",
    )

    diff_text = "".join(diff)
    if not diff_text:
        print("\nNo changes detected.\n")
    else:
        print("\n=== Diff Preview ===\n")
        print(diff_text)
