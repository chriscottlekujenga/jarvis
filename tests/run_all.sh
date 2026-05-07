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
run_test "file renamer behavior" "./tests/test_file_renamer_behavior.sh"

if [[ -n "$(git status --short)" ]]; then
  echo
  echo "FAILED: regression tests left working tree dirty"
  git status --short
  exit 1
fi

echo
echo "ALL TESTS PASSED"
