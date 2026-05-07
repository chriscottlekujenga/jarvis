# Jarvis Current Architecture State
Updated: 2026-05-07

## Current Stability Estimate
Jarvis is approximately 88–92% toward supervised stability.

Jarvis has moved from prototype agent into a bounded autonomous correction system with regression protection.

## Current Core Loop
Plan → Edit → Compile → Execute → Validate → Correct → Revalidate → Rollback if needed

## Completed Stability Milestones

### Context Routing
- Context mode switches into project_root before planning.
- Active project edits now target the correct file.
- Verified with file_renamer project.

### Safe Editing
- Diff size limits
- Diff ratio limits
- Empty diff rejection
- Weak edit rejection
- Python compile validation
- Top-level/import routing to full-file fallback
- Surgical full-file edit prompt

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

### Regression Infrastructure
- tests/test_compile_core.sh
- tests/test_file_renamer_behavior.sh
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

## Current Known Weaknesses

1. Multi-file reasoning remains immature.
2. Regression suite is still small.
3. Failure classification is shallow.
4. No code map yet.
5. Project-specific validators are manual.
6. No typed plan/action schemas yet.
7. No formal confidence/risk scoring yet.

## Immediate Next Feature
Add a lightweight code map so Jarvis can understand project files before planning multi-file changes.

Goal:
Move from main_script-centered intelligence toward multi-file awareness.

