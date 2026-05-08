#!/usr/bin/env bash
set -euo pipefail

cd /home/chris/jarvis

python3 - <<'PY'
import cli

cases = [
    (
        cli.FAILURE_WEAK_SELF_EDIT,
        "",
        "change logging output",
        "concrete behavior-changing code edit",
    ),
    (
        cli.FAILURE_EMPTY_DIFF,
        "",
        "change logging output",
        "previous attempt produced no change",
    ),
    (
        cli.FAILURE_DIFF_TOO_SMALL,
        "",
        "change logging output",
        "previous attempt was too small",
    ),
    (
        cli.FAILURE_BEHAVIOR_VALIDATION_FAILED,
        "NameError: os is not defined",
        "fix rename behavior",
        "NameError: os is not defined",
    ),
]

for failure_type, failure_message, instruction, expected_phrase in cases:
    cli.set_project_state("last_edit_failure_type", failure_type)
    cli.set_project_state("last_edit_failure_message", failure_message)

    strengthened = cli.strengthen_edit_instruction(instruction)

    if expected_phrase not in strengthened:
        raise SystemExit(
            f"expected phrase {expected_phrase!r} not found for {failure_type}: {strengthened!r}"
        )

cli.set_project_state("last_edit_failure_type", "")
cli.set_project_state("last_edit_failure_message", "")

print("PASS: retry instruction strengthening")
PY
