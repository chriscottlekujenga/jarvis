# Jarvis Regression Tests

## Test 1: Context routing + autonomous correction

Purpose:
Verify Jarvis edits the active project file, captures runtime failure, retries correction, and validates success.

Setup:
- project_root: /home/chris/jarvis/file_renamer
- main_script: /home/chris/jarvis/file_renamer/rename_files.py
- main_script_name: rename_files.py

Command inside Jarvis:
continue remove the import os line from rename_files.py

Expected:
1. Context mode cwd is /home/chris/jarvis/file_renamer
2. Edit targets /home/chris/jarvis/file_renamer/rename_files.py
3. First edit removes import os
4. py_compile passes
5. auto-run fails with NameError: os is not defined
6. project_run skips shell retry
7. correction retry adds import os back
8. second auto-run succeeds
9. final file should be restored before commit:
   git checkout -- file_renamer/rename_files.py

Pass condition:
- final auto-run reports project run success=True
- git status --short is clean after restoring test file

---

## Test 2: Failed correction rollback recovery

Purpose:
Verify Jarvis restores the previous file state if an autonomous correction retry also fails.

Temporary setup:
Modify cli.py retry instruction:

Replace:
failure_instruction = f"fix this error without breaking existing behavior: {last_failure_message}"

With:
failure_instruction = "make a tiny unrelated comment change only"

Command inside Jarvis:
continue remove the import os line from rename_files.py

Expected:
1. First edit removes import os
2. auto-run fails with NameError
3. retry correction makes unrelated comment-only edit
4. second auto-run still fails
5. recursive retry is blocked
6. rollback restores previous working file
7. output contains:
   [ROLLBACK] restored failed correction from backup

Cleanup:
cp /tmp/cli_before_rollback_test.py cli.py
git checkout -- file_renamer/rename_files.py

Pass condition:
- rollback message appears
- repo returns to clean state

---

## Test 3: Regression suite blocks broken behavior

Purpose:
Verify the behavioral regression suite fails when application behavior changes incorrectly.

Temporary setup:
Modify:

file_renamer/rename_files.py

Replace:
new_file = os.path.join(directory, f"renamed_{filename}")

With:
new_file = os.path.join(directory, filename)

Run:
./tests/run_all.sh

Expected:
1. compile test still passes
2. rename behavior no longer changes filenames
3. PASS: file renamer behavior does NOT appear
4. ALL TESTS PASSED does NOT appear
5. shell exits early due to failed assertions

Cleanup:
git checkout -- file_renamer/rename_files.py

Pass condition:
- regression suite fails
- restored file returns suite to passing state

---

## Test 4: Regression runner detects dirty working tree

Purpose:
Verify regression execution fails if tests leave repository files modified.

Implementation:
tests/run_all.sh checks:

git status --short

Expected:
1. regression suite passes normally on clean repo
2. if a test modifies tracked files and does not restore them:
   - runner prints:
     FAILED: regression tests left working tree dirty
   - git status output is shown
   - runner exits nonzero

Pass condition:
- clean repository passes
- dirty repository fails visibly

---

## Test 5: Context edit routing normalization

Purpose:
Verify project-context edit normalization targets the active project instead of Jarvis core files.

Implementation:
tests/test_context_edit_routing.sh

Expected:
1. Project context is set to file_renamer
2. LLM-provided edit referencing files.py is normalized
3. Final target becomes:
   /home/chris/jarvis/file_renamer/rename_files.py
4. Edit instruction becomes deterministic top-of-file insertion

Pass condition:
- normalized step exactly matches expected project target

---

## Test 6: Function edit guard validation

Purpose:
Verify malformed function edit outputs are rejected before splice.

Implementation:
tests/test_function_edit_guards.sh

Expected rejection cases:
1. Multiple returned functions
2. Wrong returned function name
3. Top-level imports/content in function edit output

Expected acceptance case:
1. Single correctly named function definition only

Pass condition:
- malformed outputs reject correctly
- valid output passes

