#!/usr/bin/env bash
set -euo pipefail

cd /home/chris/jarvis

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "alpha" > "$TMP_DIR/file1.txt"
echo "beta" > "$TMP_DIR/file2.txt"
mkdir "$TMP_DIR/subdir"

python3 file_renamer/rename_files.py "$TMP_DIR"

if ! test -f "$TMP_DIR/renamed_file1.txt"; then
  echo "FAIL: renamed_file1.txt was not created"
  exit 1
fi

if ! test -f "$TMP_DIR/renamed_file2.txt"; then
  echo "FAIL: renamed_file2.txt was not created"
  exit 1
fi

if ! test -d "$TMP_DIR/subdir"; then
  echo "FAIL: subdir was not preserved"
  exit 1
fi

if test -f "$TMP_DIR/file1.txt"; then
  echo "FAIL: file1.txt was not renamed"
  exit 1
fi

if test -f "$TMP_DIR/file2.txt"; then
  echo "FAIL: file2.txt was not renamed"
  exit 1
fi

echo "PASS: file renamer behavior"
