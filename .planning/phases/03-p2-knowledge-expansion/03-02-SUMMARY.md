---
phase: 03-p2-knowledge-expansion
plan: 02
subsystem: knowledge-expansion
tags: [jinja, patterns, concepts, scaffold, normalization]
dependency_graph:
  requires: []
  provides:
    - jinja-template-variables section in patterns.md
    - depends-on-past concept entry in concepts.md
    - deferrable-operators concept entry in concepts.md
    - normalize_query() in knowledge.py
    - schedule_interval parameter in scaffold.py
  affects:
    - lookup_concept tool (query normalization)
    - scaffold tool (schedule-aware prefect.yaml)
tech_stack:
  added: []
  patterns:
    - Query normalization before lookup (strips Jinja syntax)
    - Schedule translation helper (_schedule_yaml)
    - Preset alias expansion (@daily -> cron)
key_files:
  created: []
  modified:
    - colin/models/patterns.md
    - colin/models/concepts.md
    - src/airflow_unfactor/knowledge.py
    - src/airflow_unfactor/tools/scaffold.py
    - tests/test_scaffold.py
    - tests/test_knowledge.py
decisions:
  - normalize_query strips {{ }}, macros., and var.value. prefixes — applied at lookup() entry point so all callers benefit without changes
  - _schedule_yaml returns empty string for None/@once (no schedule section in prefect.yaml, no comments or placeholders)
  - schedule_interval is str | None not str | timedelta — MCP receives strings from LLM, digit strings represent seconds
  - depends-on-past and deferrable-operators both use equivalent: none with explicit workaround — honest about paradigm gaps
metrics:
  duration: "4 minutes"
  completed_date: "2026-02-27"
  tasks_completed: 2
  files_modified: 6
requirements_satisfied:
  - KNOW-09
  - KNOW-10
  - KNOW-11
  - KNOW-12
---

# Phase 03 Plan 02: Knowledge Expansion — Jinja Macros, Concepts, Normalization, Schedule Scaffold Summary

**One-liner:** Jinja macro translations with paradigm shift guidance, depends_on_past/deferrable concept entries with equivalent: none + workarounds, query normalization stripping {{ }} syntax, and schedule-aware scaffold generating real prefect.yaml cron/interval config.

## What Was Built

### Task 1: Patterns and Concepts Expansion

Added a comprehensive `{% section jinja-template-variables %}` to `colin/models/patterns.md` covering 13 Airflow Jinja macros. Each entry explains intent first (what the macro achieves) then the Python equivalent using `prefect.runtime`. For `prev_ds` and `next_ds`, the section includes a PARADIGM SHIFT explanation: Prefect flows don't own their schedule — the deployment does. These concepts don't map directly.

Added `{% section depends-on-past %}` to `colin/models/concepts.md` with `### equivalent: none` and a Prefect API workaround showing how to query `get_client()` for the previous run's state. The tone is honest and opinionated: most flows benefit from independence; only add this pattern for strict sequential integrity.

Added `{% section deferrable-operators %}` to `colin/models/concepts.md` with `### equivalent: none` and three patterns based on wait duration: retry-based (short waits), event-driven Automations (long waits, closest to Airflow's reschedule mode), and explicit polling loop (same overhead as poke mode). Explicit about the trade-offs.

### Task 2: Query Normalization and Schedule-Aware Scaffold

Added `normalize_query(query: str) -> str` to `src/airflow_unfactor/knowledge.py`. Strips `{{ }}` wrappers, `macros.` prefix, and `var.value.` prefix before lookup. Called at the top of `lookup()` so all paths (exact, case-insensitive, substring, fallback) benefit. Import `re` added.

Added `_schedule_yaml(schedule_interval: str | None) -> str` helper to `src/airflow_unfactor/tools/scaffold.py`. Returns empty string for None and `@once`. Converts `@preset` aliases to cron strings. Passes digit-only strings as interval seconds. Returns formatted cron/interval YAML block otherwise.

Added `schedule_interval: str | None = None` parameter to `scaffold_project()`. Generates a real deployment entry in `prefect.yaml` when provided (with entrypoint and work_pool) or falls back to commented-out example when None. Included `schedule` field in the JSON report.

## Verification Results

All must-have truths verified:
- `lookup_concept('macros.ds_add')` — `normalize_query` strips `{{ macros.ds_add(ds, 5) }}` to `ds_add(ds, 5)`, substring match finds `ds_add` entry
- `lookup_concept('dag_run.conf')` — handled via `jinja-template-variables` section
- `lookup_concept('depends_on_past')` — concept entry with workaround code pattern (after Colin compilation)
- `lookup_concept('deferrable')` — concept entry explaining Prefect alternatives
- `scaffold_project(schedule_interval='0 6 * * *')` — generates `cron: "0 6 * * *"` under deployments
- `scaffold_project(schedule_interval=None)` — omits real schedules section (outputs `[]`)

All 121 tests pass (up from 97 at start of phase 3).

## Deviations from Plan

None — plan executed exactly as written.

## Commits

1. `159d198` — feat(03-02): expand Jinja macro translations and add concept entries
2. `721dd83` — feat(03-02): add query normalization and schedule-aware scaffold

## Self-Check: PASSED

- `colin/models/patterns.md` — jinja-template-variables section present
- `colin/models/concepts.md` — depends-on-past and deferrable-operators sections present with equivalent: none
- `src/airflow_unfactor/knowledge.py` — normalize_query() function present and called in lookup()
- `src/airflow_unfactor/tools/scaffold.py` — _schedule_yaml() and schedule_interval parameter present
- `tests/test_scaffold.py` — TestScheduleYaml and TestScheduleTranslation classes present
- `tests/test_knowledge.py` — TestNormalizeQuery class present
- All commits exist in git log
