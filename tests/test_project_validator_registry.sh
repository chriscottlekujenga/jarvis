#!/usr/bin/env bash
set -euo pipefail

cd /home/chris/jarvis

python3 - <<'PY'
import cli

assert "rename_files.py" in cli.PROJECT_RUN_VALIDATORS

validator = cli.PROJECT_RUN_VALIDATORS["rename_files.py"]

assert callable(validator)

print("PASS: project validator registry")
PY
