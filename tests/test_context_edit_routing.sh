#!/usr/bin/env bash
set -euo pipefail

cd /home/chris/jarvis

output="$(python3 - <<'PY'
import cli

cli.set_project_state("project_root", "/home/chris/jarvis/file_renamer")
cli.set_project_state("main_script_name", "rename_files.py")
cli.set_project_state("main_script", "/home/chris/jarvis/file_renamer/rename_files.py")

steps = [
    "edit /home/chris/jarvis/files.py to add logging.basicConfig(level=logging.INFO) after imports"
]

print(cli.normalize_context_steps(
    steps,
    "continue add logging so renamed files are printed clearly"
)[0])
PY
)"

expected="edit /home/chris/jarvis/file_renamer/rename_files.py to insert at top of file: add logging.basicConfig(level=logging.INFO) after imports"

if [[ "$output" != "$expected" ]]; then
  echo "Expected:"
  echo "$expected"
  echo
  echo "Got:"
  echo "$output"
  exit 1
fi

echo "PASS: context edit routing"
