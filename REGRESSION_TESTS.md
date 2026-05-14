# Jarvis Regression Tests
Updated: 2026-05-08

## Active Regression Suite

Run all tests:
./tests/run_all.sh

Current automated tests:
- tests/test_compile_core.sh
- tests/test_file_renamer_behavior.sh
- tests/test_context_edit_routing.sh
- tests/test_function_edit_guards.sh
- tests/test_project_validator_registry.sh
- tests/test_retry_instruction_strengthening.sh
- tests/test_validation_rollback.sh

The runner fails if:
- compile fails
- behavior test fails
- any regression test fails
- tests leave the working tree dirty

---

## Test 1: Context routing + autonomous correction

Purpose:
Verify Jarvis edits the active project file, captures runtime failure, retries correction, and validates success.

Setup:
- project_root: /home/chris/jarvis/file_renamer
- main_script: /home/chris/jarvis/file_renamer/rename_files.py
- main_script_name: rename_files.py

Manual command inside Jarvis:
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

Manual command inside Jarvis:
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

Implementation:
tests/test_context_edit_routing.sh

Purpose:
Verify project-context edit normalization targets the active project instead of Jarvis core files.

Expected:
1. Project context is set to file_renamer.
2. LLM-provided edit referencing files.py is normalized.
3. Final target becomes:
   /home/chris/jarvis/file_renamer/rename_files.py
4. Edit instruction becomes deterministic top-of-file insertion.

Pass condition:
- normalized step exactly matches expected project target.

---

## Test 6: Function edit guard validation

Implementation:
tests/test_function_edit_guards.sh

Purpose:
Verify malformed function edit outputs are rejected before splice.

Expected rejection cases:
1. Multiple returned functions
2. Wrong returned function name
3. Top-level imports/content in function edit output

Expected acceptance case:
1. Single correctly named function definition only

Pass condition:
- malformed outputs reject correctly
- valid output passes

---

## Test 7: Project validator registry

Implementation:
tests/test_project_validator_registry.sh

Purpose:
Verify project-run validators are registered through PROJECT_RUN_VALIDATORS.

Expected:
1. rename_files.py exists in PROJECT_RUN_VALIDATORS.
2. Its validator is callable.

Pass condition:
- registry contains the expected validator.

---

## Test 8: Retry instruction strengthening

Implementation:
tests/test_retry_instruction_strengthening.sh

Purpose:
Verify failed edit classifications strengthen the next edit instruction.

Expected:
1. weak_self_edit adds behavior-changing instruction.
2. empty_diff adds no-change retry guidance.
3. diff_too_small adds meaningful-change guidance.
4. behavior_validation_failed preserves the failure message.

Pass condition:
- strengthened instruction includes expected retry guidance.

---

## Test 9: Validation rollback

Implementation:
tests/test_validation_rollback.sh

Purpose:
Verify failed validation rollback restores safe file state.

Expected:
1. Existing file restores from backup.
2. Existing file restores from in-memory old text when no backup exists.
3. Newly created failed file is removed.

Pass condition:
- rollback helper produces expected file state and message.

---

## Next Regression Targets

### Planner Determinism
Needed tests:
- reject empty plans
- reject duplicate steps
- reject vague edit steps
- reject placeholder commands
- reject noop plans
- enforce normalized context edit targets
- enforce deterministic validation replacement

### Failure Taxonomy
Needed tests:
- all record_edit_failure calls use known failure types
- retry policies map to known failure categories
- failure messages persist and clear correctly

### Multi-file Readiness
Needed tests:
- code map includes multiple project files
- file targeting chooses dependency file when explicitly requested
- main_script remains default only when no better target exists


## Consultative Sales Generated App Regression Coverage

The regression suite now protects the generated `lean_consulting_ai_sales_advisor` scaffold behavior, including:
- generated frontend/backend API contract
- `/api/next-question` backend route
- `call_ai_model()` AI boundary seam
- deterministic local fallback behavior
- SQLite-backed session persistence
- frontend `session_id` round trip
- persisted sessions across repeated backend calls
- accumulated `previous_answers`
- accumulated matched pains
- strongest observed buying-intent score preservation


## Consultative Sales Generated App Regression Update

Additional regression coverage now protects:
- basic entity extraction for prospect and company names
- urgency scoring from answer text
- adaptive follow-up question selection when company/site context is missing
- real generated HTTP route behavior for `/api/next-question`
- local AI fallback behavior when `OPENAI_API_KEY` is absent
- AI adapter contract markers including API mode and API error fallback

## Generated Sales AI Question Safety Regression Update

Additional regression coverage now protects:
- extracting AI question text from OpenAI-style `output_text`
- extracting nested provider text from `output[].content[].text`
- extracting chat-compatible text from `choices[].message.content`
- using AI question text when valid
- rejecting empty, whitespace-only, non-question, and overly long AI output
- preserving deterministic fallback behavior when AI output is unusable

## Generated Sales App Smoke Script Regression Update

Additional regression coverage now protects:
- generated `scripts/smoke_next_question.sh` exists
- the script starts `backend/app.py --serve`
- the script posts to `/api/next-question`
- the WordPress README documents the smoke script

## Generated Sales Proposal Preview Regression Update

Additional regression coverage now protects:
- proposal preview DOM hooks in the generated frontend
- proposal title, offer, and outcomes elements
- frontend rendering function for proposal preview
- use of `response.proposal`
- expected outcomes rendering support

## Generated Sales Proposal Preview Expansion Regression Update

Additional regression coverage now protects:
- diagnosed pains DOM hook
- next-step DOM hook
- frontend support for `diagnosed_pains`
- frontend support for `next_step`
