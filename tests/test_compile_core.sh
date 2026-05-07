#!/usr/bin/env bash
set -euo pipefail

cd /home/chris/jarvis

python3 -m py_compile \
  jarvis.py \
  cli.py \
  db.py \
  executor.py \
  files.py \
  llm.py \
  skills.py \
  verifier.py

echo "PASS: core files compile"
