---
phase: 02-server-quality
plan: "02"
subsystem: server
tags: [logging, warnings, diagnostics, mcp, testing]

# Dependency graph
requires: []
provides:
  - "Startup warning in main() when colin/output is missing or empty (SRVR-01)"
  - "Parse error logging in load_knowledge() for corrupt JSON files (SRVR-04)"
  - "TestStartupWarning test class in tests/test_server.py"
  - "TestParseErrorLogging test class in tests/test_knowledge.py"
affects: [future server plans, operator knowledge loading]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy import pattern: logging/Path imported inside main() to avoid side-effects at import time"
    - "Structured warning format: 'Failed to parse {filename}: {ErrorType}: {message}'"

key-files:
  created:
    - tests/test_server.py
  modified:
    - src/airflow_unfactor/server.py
    - src/airflow_unfactor/knowledge.py
    - tests/test_knowledge.py

key-decisions:
  - "Startup warning placed in main() only (not load_knowledge() or module level) to avoid firing during tests"
  - "logging and Path imported lazily inside main() to keep module-level import side-effect free"
  - "TestStartupWarning mocks pathlib.Path globally since Path is imported inside main()"

patterns-established:
  - "Warning pattern: check exists() + glob('*.json') before mcp.run() to give operators actionable guidance"
  - "Parse error pattern: catch exception as e, log filename + type(e).__name__ + e, then continue"

requirements-completed: [SRVR-01, SRVR-04]

# Metrics
duration: 3min
completed: 2026-02-26
---

# Phase 02 Plan 02: Server Quality — Startup Warnings Summary

**Startup warning in main() when colin/output is missing/empty, plus structured parse error logging in load_knowledge() for corrupt JSON files, with 6 new tests covering both behaviors.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-26T22:21:30Z
- **Completed:** 2026-02-26T22:23:33Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `server.py main()` now emits a WARNING with actionable "Run `colin run`" message when colin/output is missing or has no JSON files (SRVR-01)
- `knowledge.py load_knowledge()` logs a structured WARNING with filename, error type, and message for each unparseable JSON file — valid files continue loading (SRVR-04)
- 6 new tests: 3 startup warning tests + 3 parse error logging tests; full suite at 72 passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Add startup warning in main() and parse error logging in load_knowledge()** - `04e0793` (feat)
2. **Task 2: Create tests/test_server.py and extend test_knowledge.py** - `fd527f2` (test)

**Plan metadata:** (docs commit — see final commit)

## Files Created/Modified

- `src/airflow_unfactor/server.py` - Added colin/output check in main() with WARNING emission before mcp.run()
- `src/airflow_unfactor/knowledge.py` - Added logger at module level; except block now logs filename + error type + message
- `tests/test_server.py` - New file with TestStartupWarning class (3 tests for SRVR-01)
- `tests/test_knowledge.py` - Added TestParseErrorLogging class (3 tests for SRVR-04)

## Decisions Made

- Warning placed in `main()` only — this avoids spurious warnings during tests that call `load_knowledge()` directly with temp directories; the plan explicitly required this
- `logging` and `Path` imported lazily inside `main()` body (alongside the existing `sys` import pattern) to avoid import-time side effects
- Mocking strategy for `TestStartupWarning` patches `pathlib.Path` globally (not `airflow_unfactor.server.Path`) because `Path` is imported inside the function body, not at module level

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Minor: Initial test run failed because `sys.argv` contained pytest args, triggering the unrecognized arguments guard in `main()`. Fixed by patching `sys.argv` to `["airflow-unfactor"]` in all test cases.

## Next Phase Readiness

- SRVR-01 and SRVR-04 complete; server quality phase progressing
- Remaining server quality requirements (SRVR-02, SRVR-03) can proceed independently

---
*Phase: 02-server-quality*
*Completed: 2026-02-26*
