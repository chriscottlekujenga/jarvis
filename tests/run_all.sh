#!/usr/bin/env bash
set -euo pipefail

cd /home/chris/jarvis

echo "========================================"
echo "RUNNING JARVIS REGRESSION TESTS"
echo "========================================"

./tests/test_compile_core.sh
./tests/test_file_renamer_behavior.sh

echo
echo "ALL TESTS PASSED"
