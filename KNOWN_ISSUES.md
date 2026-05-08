# Jarvis Known Issues

## Current Status
Jarvis is approximately 90–93% toward supervised stability.

Core closed-loop behavior is working:
- context-aware project routing
- correct project-root execution
- safe edit flow
- compile validation
- auto-run project validation
- runtime failure capture
- bounded correction retry
- rollback recovery
- regression protection

## Known Issues

### 1. Retry loop can repeat weak fixes
Jarvis can attempt a correction that technically changes the file but does not fix the failing runtime behavior.

Needed:
- retry memory
- failed-fix tracking
- anti-loop detection
- block repeated correction strategies

### 2. Failure classification is still shallow
Failures are stored, but not deeply classified.

Needed categories:
- compile failure
- runtime exception
- usefulness failure
- empty diff
- weak edit
- wrong target
- repeated failed fix
- verifier false positive

### 3. Runtime validation is still basic
A project can run successfully without proving the user’s intended behavior was achieved.

Needed:
- behavior-specific checks
- expected output validation
- file-system result validation
- project-type-specific validators

### 4. Multi-file reasoning is immature
Jarvis is strongest on single-file scripts and main_script-centered changes.

Needed:
- dependency-aware file targeting
- multi-file edit planning
- test selection by changed file
- file relationship awareness

### 5. Planner can still generate unnecessary run steps
Context normalization blocks some bad raw project runs, but planner output can still include redundant or weak validation steps.

Needed:
- stricter context-step normalization
- deterministic validation step replacement
- drop redundant py_compile steps when auto-validation covers them

### 6. Top-level edit detection is still incomplete
Import edits and top-of-file edits now route correctly, but additional top-level patterns may still be missed.

Needed:
- broader global/constant detection
- decorator-aware edits
- entrypoint-aware edits
- CLI/parser-aware edits

### 7. Verifier can ask for bad retry commands
During project auto-run failures, command retry logic may suggest bad commands like placeholders or malformed retries.

Needed:
- disable shell-command retry during project auto-run
- route project failures to edit correction only
- reject placeholder retry commands

### 8. Non-core behavior validation is shallow
Jarvis validates runtime success for non-core projects but does not deeply validate behavioral correctness.

Needed:
- project-aware assertions
- output expectation models
- semantic validation layers
- structured validator plugins

### 9. Semantic edit idempotency is incomplete
Jarvis can still attempt duplicate edits that are semantically already satisfied.

Needed:
- semantic no-op detection
- edit intent satisfaction checks
- duplicate pattern recognition
- deterministic edit guards beyond logging config

### 10. Function-level semantic correctness is still shallow
Jarvis now blocks malformed function replacements structurally, but not logically incorrect replacements.

Needed:
- semantic equivalence validation
- function behavior tests
- stronger post-edit verification
- targeted runtime assertions

## Next Priority
Build stronger non-core behavior validation.

## Stability Goal
Jarvis should become predictably correct under constraint:
- correct target
- correct method
- correct outcome
- bounded retry
- rollback on failed correction
- no silent success

Additional stability requirements:
- bounded retry ceilings
- deterministic validation
- safe recovery behavior
- regression resistance

