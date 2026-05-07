# Jarvis Known Issues

## Current Status
Jarvis is approximately 85–90% toward supervised stability.

Core closed-loop behavior is working:
- context-aware project routing
- correct project-root execution
- safe edit flow
- compile validation
- auto-run project validation
- runtime failure capture
- bounded correction retry

## Known Issues

### 1. Retry loop can repeat weak fixes
Jarvis can attempt a correction that technically changes the file but does not fix the failing runtime behavior.

Needed:
- retry memory
- failed-fix tracking
- anti-loop detection
- block repeated correction strategies

### 2. Retry has no rollback boundary after failed correction
If the correction retry fails, Jarvis currently stops but may leave the project file in the failed corrected state.

Needed:
- backup before retry
- rollback after failed retry
- clear success/failure state consistently

### 3. Failure classification is still shallow
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

### 4. Runtime validation is still basic
A project can run successfully without proving the user’s intended behavior was achieved.

Needed:
- behavior-specific checks
- expected output validation
- file-system result validation
- project-type-specific validators

### 5. Multi-file reasoning is immature
Jarvis is strongest on single-file scripts and main_script-centered changes.

Needed:
- code map
- dependency-aware file targeting
- multi-file edit planning
- test selection by changed file

### 6. Planner can still generate unnecessary run steps
Context normalization blocks some bad raw project runs, but planner output can still include redundant or weak validation steps.

Needed:
- stricter context-step normalization
- deterministic validation step replacement
- drop redundant py_compile steps when auto-validation covers them

### 7. Import/top-level edits required special routing
Import edits now route to full-file fallback, but other top-level patterns may still be missed.

Needed:
- broaden top-level edit detection
- handle constants, globals, decorators, entrypoints, CLI args

### 8. Verifier can ask for bad retry commands
During project auto-run failures, command retry logic may suggest bad commands like placeholders or malformed retries.

Needed:
- disable shell-command retry during project auto-run
- route project failures to edit correction only
- reject placeholder retry commands

## Next Priority
Build retry memory and anti-loop protection.

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
