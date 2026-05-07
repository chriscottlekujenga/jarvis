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
