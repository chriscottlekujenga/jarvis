#!/usr/bin/env bash
set -euo pipefail

cd /home/chris/jarvis

python3 - <<'PY'
import re

def validate_function_edit_output(new_function_block, target_function):
    returned_defs = re.findall(r'(?m)^def ([A-Za-z_][A-Za-z0-9_]*)\s*\(', new_function_block)
    if not returned_defs:
        return "invalid_function_edit_definition"

    if len(returned_defs) != 1:
        return "invalid_function_edit_definition"

    returned_name = returned_defs[0]
    if returned_name != target_function:
        return "wrong_function_edit_name"

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
        return "invalid_function_edit_definition"

    return "ok"

cases = [
    ("def target():\n    return True\n\ndef extra():\n    return False\n", "target", "invalid_function_edit_definition"),
    ("def wrong():\n    return True\n", "target", "wrong_function_edit_name"),
    ("import os\n\ndef target():\n    return True\n", "target", "invalid_function_edit_definition"),
    ("def target():\n    return True\n", "target", "ok"),
]

for block, target, expected in cases:
    got = validate_function_edit_output(block, target)
    if got != expected:
        raise SystemExit(f"expected {expected}, got {got}, block={block!r}")

print("PASS: function edit guards")
PY
