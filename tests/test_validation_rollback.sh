#!/usr/bin/env bash
set -euo pipefail

cd /home/chris/jarvis

python3 - <<'PY'
import os
import tempfile
import cli

# --- CASE 1: restore from backup ---
with tempfile.TemporaryDirectory() as tmp:
    target = os.path.join(tmp, "sample.py")
    backup = os.path.join(tmp, "sample.py.bak")

    with open(target, "w") as f:
        f.write("BROKEN\n")

    with open(backup, "w") as f:
        f.write("ORIGINAL\n")

    msg = cli.rollback_file_after_failed_validation(
        target,
        "ORIGINAL\n",
        backup,
    )

    with open(target) as f:
        restored = f.read()

    assert restored == "ORIGINAL\n"
    assert "restored from backup" in msg

# --- CASE 2: restore from in-memory text ---
with tempfile.TemporaryDirectory() as tmp:
    target = os.path.join(tmp, "sample.py")

    with open(target, "w") as f:
        f.write("BROKEN\n")

    msg = cli.rollback_file_after_failed_validation(
        target,
        "MEMORY\n",
        None,
    )

    with open(target) as f:
        restored = f.read()

    assert restored == "MEMORY\n"
    assert "in-memory" in msg

# --- CASE 3: remove newly created file ---
with tempfile.TemporaryDirectory() as tmp:
    target = os.path.join(tmp, "new_file.py")

    with open(target, "w") as f:
        f.write("BROKEN\n")

    msg = cli.rollback_file_after_failed_validation(
        target,
        "",
        None,
    )

    assert not os.path.exists(target)
    assert "removed newly created file" in msg

print("PASS: validation rollback")
PY
