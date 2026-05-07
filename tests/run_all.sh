#!/usr/bin/env bash
set -euo pipefail

cd /home/chris/jarvis

echo "========================================"
echo "RUNNING JARVIS REGRESSION TESTS"
echo "========================================"

./tests/test_compile_core.sh

echo
echo "ALL TESTS PASSED"
