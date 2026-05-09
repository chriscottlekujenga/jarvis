#!/usr/bin/env bash
set -euo pipefail

cd /home/chris/jarvis

run_test() {
  local name="$1"
  local command="$2"

  echo
  echo "----------------------------------------"
  echo "RUNNING: $name"
  echo "----------------------------------------"

  if ! bash -c "$command"; then
    echo
    echo "FAILED: $name"
    exit 1
  fi

  echo "PASSED: $name"
}

echo "========================================"
echo "RUNNING JARVIS REGRESSION TESTS"
echo "========================================"

run_test "core compile" "./tests/test_compile_core.sh"
run_test "execution context" "python3 tests/test_execution_context.py"
run_test "file renamer behavior" "./tests/test_file_renamer_behavior.sh"
run_test "context edit routing" "./tests/test_context_edit_routing.sh"
run_test "function edit guards" "./tests/test_function_edit_guards.sh"
run_test "project validator registry" "./tests/test_project_validator_registry.sh"
run_test "retry instruction strengthening" "./tests/test_retry_instruction_strengthening.sh"
run_test "validation rollback" "./tests/test_validation_rollback.sh"

status_output="$(git status --short)"

if [[ -n "${JARVIS_ALLOWED_DIRTY_PATH:-}" ]]; then
  status_output="$(printf "%s\n" "$status_output" | grep -vE "^[ MARCUD?!]{1,2} ${JARVIS_ALLOWED_DIRTY_PATH}$" || true)"
fi

if [[ -n "$status_output" ]]; then
  echo
  echo "FAILED: regression tests left working tree dirty"
  printf "%s\n" "$status_output"
  exit 1
fi

echo
echo "ALL TESTS PASSED"
