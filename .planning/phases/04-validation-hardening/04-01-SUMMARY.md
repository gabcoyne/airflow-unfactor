---
phase: 04-validation-hardening
plan: 01
subsystem: validate-tool
tags: [validate, operator-guidance, fixtures, tdd, VALD-01, VALD-02]
dependency_graph:
  requires: []
  provides: [conditional-operator-guidance, fixture-dags]
  affects: [src/airflow_unfactor/tools/validate.py, tests/test_validate.py]
tech_stack:
  added: []
  patterns: [conditional-content-injection, parametrized-integration-tests]
key_files:
  created:
    - tests/fixtures/kubernetes_pod_operator.py
    - tests/fixtures/databricks_submit_run.py
    - tests/fixtures/azure_data_factory.py
    - tests/fixtures/dbt_cloud_run_job.py
    - tests/fixtures/http_operator.py
    - tests/fixtures/ssh_operator.py
  modified:
    - src/airflow_unfactor/tools/validate.py
    - tests/test_validate.py
decisions:
  - validate.py appends extras only when detected; base 9-item guidance unchanged so existing tests need no modification
  - Guidance items use descriptive labels (Kubernetes:, Databricks:, etc.) instead of numbered prefixes to avoid conflicts when multiple operators appear
  - FIXTURES_DIR defined at module level in test_validate.py for reuse across test classes
metrics:
  duration: "103 seconds"
  completed_date: "2026-02-27"
  tasks_completed: 2
  files_changed: 8
---

# Phase 4 Plan 01: Conditional Operator-Specific Guidance in validate_conversion Summary

**One-liner:** Conditional operator-specific guidance injection (Kubernetes/Databricks/Azure/dbt/HTTP/SSH) into validate_conversion, with six production-style fixture DAGs and a TestPhase4Validation class covering 8 parametrized + 2 standalone test cases.

## What Was Built

The `validate_conversion` function in `src/airflow_unfactor/tools/validate.py` previously returned a static 9-item checklist regardless of DAG content. Users converting operator-specific DAGs (Kubernetes, Databricks, Azure Data Factory, dbt Cloud, HTTP, SSH) received no targeted guidance.

This plan:

1. Refactored the guidance string into a local variable and added conditional detection logic that appends operator-specific checklist items when those operators appear in the original DAG source.

2. Created six production-style fixture DAGs under `tests/fixtures/` — each with a realistic `DAG()` context manager, realistic operator parameters, and a two-task dependency chain.

3. Added `TestPhase4Validation` to `tests/test_validate.py` with 6 parametrized tests proving each fixture gets its expected guidance fragment, plus two standalone tests verifying (a) no regression on plain DAGs and (b) correct stacking when multiple operator families appear together.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add conditional operator-specific guidance + fixtures | 3b94827 | validate.py, 6 fixture DAGs |
| 2 | Add TestPhase4Validation integration tests | fccf6b2 | test_validate.py |

## Verification Results

- `uv run pytest tests/test_validate.py -x -q` — 12 passed (4 existing + 6 parametrized + 2 standalone)
- `uv run pytest -q` — 144 passed (136 pre-existing + 8 new)
- All six fixture DAGs pass `py_compile` syntax check
- Base 9-item guidance string is unchanged in validate.py

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files created:
- FOUND: src/airflow_unfactor/tools/validate.py (modified)
- FOUND: tests/fixtures/kubernetes_pod_operator.py
- FOUND: tests/fixtures/databricks_submit_run.py
- FOUND: tests/fixtures/azure_data_factory.py
- FOUND: tests/fixtures/dbt_cloud_run_job.py
- FOUND: tests/fixtures/http_operator.py
- FOUND: tests/fixtures/ssh_operator.py
- FOUND: tests/test_validate.py (modified)

Commits verified:
- FOUND: 3b94827
- FOUND: fccf6b2
