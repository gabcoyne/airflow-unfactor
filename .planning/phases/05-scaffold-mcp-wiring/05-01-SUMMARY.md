---
phase: 05-scaffold-mcp-wiring
plan: 01
subsystem: api
tags: [mcp, fastmcp, scaffold, prefect, schedule]

# Dependency graph
requires:
  - phase: 03-p2-knowledge-expansion
    provides: schedule_interval handling in scaffold_project (tools/scaffold.py)
provides:
  - schedule_interval parameter exposed through MCP scaffold() wrapper
  - MCP-level tests proving parameter flows end-to-end to prefect.yaml
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - MCP wrapper parameters mirror underlying scaffold_project() signature

key-files:
  created:
    - tests/test_server_scaffold.py
  modified:
    - src/airflow_unfactor/server.py

key-decisions:
  - "MCP wrapper signature extended by adding schedule_interval as the last optional parameter to avoid breaking callers"
  - "MCP-level tests import scaffold() directly from server.py and call via asyncio.run() — same pattern as existing test_scaffold.py"

patterns-established:
  - "MCP wrapper tests: import decorated function from server.py, call with asyncio.run(), assert on JSON result and generated files"

requirements-completed: [KNOW-12]

# Metrics
duration: 5min
completed: 2026-02-27
---

# Phase 5 Plan 01: Scaffold MCP Wiring Summary

**schedule_interval parameter wired through the MCP scaffold() wrapper so LLMs calling the tool can trigger schedule-aware prefect.yaml generation**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-27T14:08:00Z
- **Completed:** 2026-02-27T14:12:55Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `schedule_interval: str | None = None` parameter to the `scaffold()` MCP wrapper in server.py
- Passed `schedule_interval=schedule_interval` through to `scaffold_project()` call — closing the gap identified in KNOW-12
- Created `tests/test_server_scaffold.py` with 3 MCP-level tests proving the parameter flows from wrapper to prefect.yaml output
- Full suite grows from 144 to 147 tests, all passing

## Task Commits

1. **Task 1: Wire schedule_interval in server.py** - `6aadf7a` (feat)
2. **Task 2: MCP-level scaffold tests** - `133689d` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/airflow_unfactor/server.py` - Added schedule_interval param to scaffold() signature and forwarded it to scaffold_project()
- `tests/test_server_scaffold.py` - Three MCP-level tests: cron forwarding, no-regression without schedule, @daily preset in report

## Decisions Made

- Used `str | None = None` type for schedule_interval to match the existing scaffold_project() signature exactly
- Placed schedule_interval as the last parameter in scaffold() to avoid breaking existing callers
- MCP-level tests use asyncio.run() directly (same pattern as test_scaffold.py), keeping test approach consistent

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- KNOW-12 fully closed: MCP scaffold tool now exposes schedule_interval end-to-end
- All 147 tests pass, no regressions
- No further scaffold wiring work planned

---
*Phase: 05-scaffold-mcp-wiring*
*Completed: 2026-02-27*

## Self-Check: PASSED

- src/airflow_unfactor/server.py — FOUND
- tests/test_server_scaffold.py — FOUND
- Commit 6aadf7a — FOUND
- Commit 133689d — FOUND
