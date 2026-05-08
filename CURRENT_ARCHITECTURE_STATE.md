# Jarvis Current Architecture State
Updated: 2026-05-07

## Current Stability Estimate
Jarvis is approximately 90–93% toward supervised stability.

Jarvis has moved from prototype agent into a bounded autonomous correction system with regression protection.

## Current Core Loop
Plan → Edit → Compile → Execute → Validate → Correct → Revalidate → Rollback if needed

## Completed Stability Milestones

### Context Routing
- Context mode switches into project_root before planning.
- Active project edits now target the correct file.
- Explicit project edits no longer drift into Jarvis core files.
- Verified with file_renamer project.
- Regression coverage added for context edit routing.

### Context Awareness
- Context info requests now display project state instead of generating edit plans.
- Lightweight project code map added.
- Project state includes:
  - project_files
  - project_code_map
  - imports
  - functions
  - classes

### Safe Editing
- Diff size limits
- Diff ratio limits
- Empty diff rejection
- Weak edit rejection
- Python compile validation
- Top-level/import routing to full-file fallback
- Deterministic top-of-file insertion handling
- Surgical full-file edit prompt

### Function Edit Safety
- Wrong-function replacement rejection
- Multiple returned function rejection
- Top-level content rejection during function edits
- Splice failure detection
- Regression coverage for malformed function edit output

### Runtime Validation
- Project auto-run after edit plans
- Runtime stderr/stdout capture
- Traceback stored in project state
- Usefulness validation for project runs

### Autonomous Correction
- Failed auto-run triggers correction retry
- Retry uses actual runtime failure message
- Project-run shell retry is bypassed
- Recursive correction retry is blocked
- Failed correction is restored from backup

### Deterministic Edit Safety
- Duplicate logging.basicConfig edits are blocked
- Top-of-file insertion now correctly places edits after imports
- Generic "files" keyword no longer routes edits into Jarvis core accidentally

### Regression Infrastructure
- tests/test_compile_core.sh
- tests/test_file_renamer_behavior.sh
- tests/test_context_edit_routing.sh
- tests/test_function_edit_guards.sh
- tests/run_all.sh
- Named test reporting
- Explicit behavior failure messages
- Dirty working tree protection
- Regression suite runs during core behavior validation

## Verified Proofs

### Autonomous Correction Proof
Test:
continue remove the import os line from rename_files.py

Observed:
- import os removed
- py_compile passed
- project runtime failed with NameError
- Jarvis captured traceback
- correction retry restored import os
- second auto-run passed

### Rollback Proof
Temporary weakened retry instruction:
failure_instruction = "make a tiny unrelated comment change only"

Observed:
- correction failed to fix runtime error
- recursive retry blocked
- failed correction restored from backup

### Regression Blocking Proof
Temporary broken rename behavior:
new_file = os.path.join(directory, filename)

Observed:
- compile test passed
- behavior test failed
- ALL TESTS PASSED did not print
- restored file returned suite to passing state

### Context Routing Proof
Observed:
- Project-context edits now correctly target project files
- Generic references to "files" no longer route into files.py
- Context info requests return project structure without generating edit plans

### Function Guard Proof
Observed:
- Multiple returned functions rejected
- Wrong function names rejected
- Top-level imports/content rejected during function replacement
- Malformed function edits blocked before splice

## Current Known Weaknesses

1. Multi-file reasoning remains immature.
2. Regression suite is still relatively small.
3. Failure classification is still shallow.
4. Project-specific validators are manual.
5. No typed plan/action schemas yet.
6. No formal confidence/risk scoring yet.
7. Non-core project behavior validation is still shallow.
8. Semantic correctness validation is still limited.

## Immediate Next Feature
Add stronger behavior validation for non-core project files.

Goal:
Move from “successful execution” toward “validated intended behavior.”

