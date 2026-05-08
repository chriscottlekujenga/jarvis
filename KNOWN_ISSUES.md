# Jarvis Known Issues
Updated: 2026-05-08

## Current Status
Jarvis is approximately 91–94% toward supervised stability.

Core closed-loop behavior is working:
- context-aware project routing
- correct project-root execution
- safe edit flow
- function-level editing
- compile validation
- auto-run project validation
- runtime failure capture
- bounded correction retry
- rollback recovery
- project validator registry
- regression protection

## Strategic Clarification
Jarvis has not deviated from the roadmap.

The live build clarified that planner determinism must mature before broader autonomy, multi-file orchestration, or autonomous self-improvement.

## Known Issues

### 1. Planner determinism is still immature
Planner output can still be vague, redundant, malformed, or weak.

Needed:
- invalid plan rejection
- duplicate-step rejection
- noop-plan rejection
- exact edit/run structure enforcement
- deterministic validation-step generation
- stronger target inference
- regression tests for plan normalization

### 2. Retry loop can repeat weak fixes
Jarvis can attempt a correction that technically changes the file but does not fix the failing runtime behavior.

Needed:
- retry memory
- failed-fix tracking
- anti-loop detection
- block repeated correction strategies
- retry policy objects

### 3. Failure classification is only partially centralized
Some core retry failure constants exist, but failure taxonomy is not yet complete.

Needed:
- complete failure type constants
- failure categories
- retry strategy per category
- structured failure records
- failure analytics

### 4. Runtime validation is still shallow
Jarvis can run a project successfully without fully proving intended behavior.

Needed:
- behavior-specific checks
- expected output validation
- file-system result validation
- project-type-specific validators
- stronger semantic validators

### 5. Multi-file reasoning is immature
Jarvis is strongest on single-file scripts and main_script-centered changes.

Needed:
- dependency-aware file targeting
- multi-file edit planning
- changed-file test selection
- file relationship awareness
- import graph/code map improvements

### 6. Top-level edit detection is incomplete
Import edits and top-of-file edits route correctly, but additional top-level patterns may still be missed.

Needed:
- global/constant detection
- decorator-aware edits
- entrypoint-aware edits
- CLI/parser-aware edits

### 7. Verifier can still produce weak command retry behavior
Project-run shell retry is bypassed, but verifier logic still needs more systematic policy.

Needed:
- stronger command retry policy
- placeholder retry rejection
- project failure → edit correction only
- command verification taxonomy

### 8. Non-core behavior validation is shallow
Project-aware validation exists through PROJECT_RUN_VALIDATORS, but coverage is currently limited.

Needed:
- validator plugins per project type
- more project validators
- output expectation models
- structured validator interfaces

### 9. Semantic edit idempotency is incomplete
Jarvis can still attempt edits that are semantically already satisfied.

Needed:
- semantic no-op detection
- edit intent satisfaction checks
- duplicate pattern recognition
- deterministic edit guards beyond logging config

### 10. Function-level semantic correctness is shallow
Jarvis blocks malformed function replacements structurally, but not logically incorrect replacements.

Needed:
- semantic equivalence validation
- function behavior tests
- targeted runtime assertions
- post-edit behavior checks by function

### 11. No typed plan/action schemas yet
Plans and actions are still largely string-based.

Needed:
- typed PlanStep
- typed EditIntent
- typed ValidationResult
- typed FailureRecord
- typed ProjectContext
- strict LLM output validation before execution

### 12. Structured event logging is missing
Console output is useful for humans but not enough for long-term self-improvement.

Needed:
- SQLite event records
- step start/end records
- file target decision records
- validation result records
- rollback records
- retry decision records

## Next Priority
Planner determinism hardening.

## Stability Goal
Jarvis should become predictably correct under constraint:
- correct target
- correct method
- correct outcome
- bounded retry
- rollback on failed correction
- no silent success

