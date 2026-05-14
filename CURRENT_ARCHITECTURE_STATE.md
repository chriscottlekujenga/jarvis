# Jarvis Current Architecture State
Updated: 2026-05-08

## Current Stability Estimate
Jarvis is approximately 91–94% toward supervised stability.

Jarvis has moved from prototype agent into a constrained autonomous coding runtime with regression protection, rollback safety, context-aware routing, and project-aware validation.

## Core Principle
Predictably correct behavior under constraint.

## Current Core Loop
Plan → Edit → Compile → Execute → Validate → Correct → Revalidate → Rollback if needed

## Strategic Clarification
Jarvis has not materially deviated from the roadmap.

Implementation has clarified the correct ordering:

1. Execution safety
2. Validation correctness
3. Retry correctness
4. Regression enforcement
5. Planner determinism
6. Multi-file orchestration
7. Autonomous branching/self-improvement

Planner determinism must mature before broader autonomy.

## Completed Stability Milestones

### Context Routing
- Context mode switches into project_root before planning.
- Active project edits target the correct project file.
- Explicit project edits no longer drift into Jarvis core files.
- Generic references to "files" no longer route edits into files.py accidentally.
- Context info requests display project state instead of generating edit plans.
- Regression coverage exists for context edit routing.

### Context Awareness
- Lightweight project code map added.
- Project state displays:
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
- Undefined constant detection
- Top-level/import routing
- Deterministic top-of-file insertion after imports
- Duplicate logging.basicConfig guard
- Surgical full-file edit fallback

### Function Edit Safety
- Function-level editing exists.
- Wrong-function replacement rejection.
- Multiple returned function rejection.
- Top-level content rejection during function edits.
- Splice failure detection.
- Regression coverage for malformed function edit output.

### Runtime Validation
- Project auto-run after edit plans.
- Runtime stderr/stdout capture.
- Traceback stored in project state.
- Project-run semantic validation exists.
- Project validator registry exists.
- rename_files.py validator checks actual renamed output files.

### Autonomous Correction
- Failed auto-run triggers correction retry.
- Retry uses actual runtime failure message.
- Project-run shell retry is bypassed.
- Recursive correction retry is blocked.
- Failed correction is restored from backup.
- Retry-aware instruction strengthening exists.

### Rollback Safety
- Validation rollback helper extracted.
- Rollback covered by regression tests.
- Failed validation restores backup, in-memory old text, or removes newly created files.

### Failure Handling
- Failure class output is printed.
- Retry failure constants exist for core retry categories.
- Failure state is persisted in project_state.
- Retry instruction strengthening uses stored failure type/message.

### Regression Infrastructure
- tests/test_compile_core.sh
- tests/test_file_renamer_behavior.sh
- tests/test_context_edit_routing.sh
- tests/test_function_edit_guards.sh
- tests/test_project_validator_registry.sh
- tests/test_retry_instruction_strengthening.sh
- tests/test_validation_rollback.sh
- tests/run_all.sh
- Named test reporting
- Dirty working tree protection
- Regression suite runs during validation

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
Observed:
- failed correction rollback restores prior working file
- recursive correction retry is blocked
- validation rollback helper restores backup/in-memory state/new-file state

### Regression Blocking Proof
Observed:
- broken rename behavior fails behavior regression
- dirty working tree after tests fails regression runner
- restored file returns suite to passing state

### Context Routing Proof
Observed:
- Project-context edits target /home/chris/jarvis/file_renamer/rename_files.py
- LLM-generated references to /home/chris/jarvis/files.py are normalized away when the user did not request Jarvis core edits
- Context info requests return project structure without edit planning

### Function Guard Proof
Observed:
- Multiple returned functions rejected
- Wrong function names rejected
- Top-level imports/content rejected during function replacement
- Malformed function edits blocked before splice

### Validator Registry Proof
Observed:
- PROJECT_RUN_VALIDATORS contains rename_files.py
- rename_files.py project validator is callable
- project_run mode dispatches to active script validator

## Current Known Weaknesses

1. Planner determinism is now the highest-leverage bottleneck.
2. Multi-file reasoning remains immature.
3. Regression suite is growing but still small.
4. Failure taxonomy is only partially centralized.
5. No typed plan/action schemas yet.
6. No formal confidence/risk scoring yet.
7. Non-core project behavior validation is still shallow.
8. Semantic correctness validation is still limited.
9. Retry policies are still partly ad hoc.
10. Structured event logging is not yet implemented.

## Immediate Next Feature
Planner determinism hardening.

Goal:
Prevent vague, duplicate, malformed, noop, or weak plans before execution.

## Next Major Expansion After Planner Hardening
Multi-file orchestration.


## 2026-05-13 — Consultative Sales App Scaffold Progress

Recent commits advanced the generated `lean_consulting_ai_sales_advisor` web app from static scaffold toward a working deployable MVP architecture.

Completed:
- Added generated Python backend HTTP route for `/api/next-question`.
- Connected generated frontend to backend contract with `fetch()`.
- Added WordPress embed-kit scaffold.
- Added Cloud Run deployment scaffold and onboarding README notes.
- Added generated backend session persistence using SQLite.
- Added frontend `session_id` handling.
- Added accumulated session memory:
  - `previous_answers` accumulates across calls.
  - matched pains accumulate instead of being overwritten.
  - strongest observed buying-intent score is preserved.
- Added regression coverage for frontend/backend API contract, AI boundary contract, session persistence, and accumulated session memory.

Current generated app capability:
- Creates frontend, backend, prompts, schemas, service module, WordPress embed kit, and deployment scaffold.
- Runs locally with deterministic fallback behavior.
- Accepts prospect answers through the frontend.
- Calls the backend API.
- Tracks and persists `session_id`.
- Reloads persisted session state.
- Builds a basic proposal-readiness response.

Architecture decision:
- WordPress remains the presentation/embed layer.
- Python backend remains the consultative reasoning and AI orchestration layer.
- Do not convert backend to PHP.
- Do not move static scaffold templates to a database yet.
- Continue using targeted Python AST/scaffold extraction commands for large scaffold inspection.

Next useful work:
1. Add deterministic extraction of prospect name, company name, and urgency signals from answers.
2. Improve adaptive question selection using accumulated session state.
3. Add real AI provider adapter behind `call_ai_model()` while preserving deterministic fallback.
4. Add generated-app smoke command that starts backend and exercises `/api/next-question`.
5. Eventually externalize large scaffold strings into template files when string-maintenance cost becomes the bottleneck.


## 2026-05-14 — Consultative Sales App Capability Update

The generated consultative sales app now includes a stronger MVP backend architecture.

Added since the last checkpoint:
- Deterministic extraction of basic `prospect_name`, `company_name`, and `urgency_score`.
- Adaptive next-question logic based on known pains, company/context, urgency, buying intent, and proposal readiness.
- Real generated backend HTTP smoke coverage for `/api/next-question`.
- A real AI provider adapter behind `call_ai_model()` using stdlib HTTP calls.
- Safe `local_stub` behavior when `OPENAI_API_KEY` is not configured.
- Safe `api_error_fallback` behavior if the provider call fails.

Current AI boundary:
- `call_ai_model()` keeps deterministic fallback behavior for tests and local development.
- When `OPENAI_API_KEY` exists, the generated backend can call the configured OpenAI-compatible Responses API URL.
- `AI_MODEL` and `OPENAI_API_URL` are environment-configurable.

Current generated app behavior:
- Persists session state.
- Accumulates previous answers and matched pains.
- Extracts basic sales context.
- Asks more context-aware follow-up questions.
- Can run locally as an HTTP backend and accept real POST requests.

## 2026-05-14 — Generated Sales AI Question Safety

The generated consultative sales backend now uses AI-provided next-question text only when it passes a safety/shape check.

Protected behavior:
- Extracts text from multiple provider response formats.
- Accepts clean question text from the AI adapter.
- Rejects empty output.
- Rejects whitespace-only output.
- Rejects overly long AI text.
- Rejects AI text that does not look like a question.
- Falls back to deterministic next-question logic when AI output is unusable.

This keeps the generated app AI-capable without allowing malformed provider output to break the sales conversation flow.

## 2026-05-14 — Generated Sales App Manual Smoke Test

The generated consultative sales app now includes a local smoke script:

    scripts/smoke_next_question.sh

The script:
- starts the generated Python backend
- posts a sample answer to `/api/next-question`
- prints the JSON response
- shuts the backend down afterward

This has been manually validated from a temporary generated project and returned a real `status`, `session_id`, `next_question`, proposal payload, and `local_stub` AI mode.
