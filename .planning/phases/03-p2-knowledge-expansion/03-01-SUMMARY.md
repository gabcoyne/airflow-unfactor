---
phase: 03-p2-knowledge-expansion
plan: "01"
subsystem: colin-knowledge
tags: [azure, dbt, colin-models, operator-mappings, intent-first]
dependency_graph:
  requires: []
  provides: [azure-operator-knowledge, dbt-cloud-operator-knowledge]
  affects: [colin/models/operators/_index.md, lookup_concept-tool]
tech_stack:
  added: [prefect-azure[blob_storage], prefect-dbt[cloud], azure-mgmt-datafactory, azure-identity]
  patterns: [intent-first-colin-model, architecture-shift-entry, credential-block-pattern]
key_files:
  created:
    - colin/models/operators/azure.md
    - colin/models/operators/dbt.md
  modified:
    - colin/models/operators/_index.md
decisions:
  - "WasbDeleteOperator included in azure.md per RESEARCH.md Open Question 3 recommendation — same credential pattern, minimal scope"
  - "ADF section includes full polling loop in the @task example, not just fire-and-forget — mirrors wait_for_termination=True behavior"
  - "Warning text in azure.md notes explicitly contains the bad import string as a cautionary example — this is intentional content, not a linting issue"
metrics:
  duration: "2 minutes"
  completed_date: "2026-02-27"
  tasks_completed: 2
  files_created: 2
  files_modified: 1
---

# Phase 3 Plan 01: Azure and dbt Cloud Colin Models Summary

Two new Colin model files authored with intent-first structure: `azure.md` covering Azure Data Factory and Blob Storage operators, and `dbt.md` covering dbt Cloud job triggering, both registered in the operator index.

## What Was Built

`colin/models/operators/azure.md` — Three operator sections following the kubernetes.md intent-first template:

1. `AzureDataFactoryRunPipelineOperator` — ARCHITECTURE SHIFT entry. No `prefect-azure` ADF module exists; the correct pattern is `azure-mgmt-datafactory` SDK inside a `@task` with `ClientSecretCredential` from Prefect Secret blocks, plus a polling loop that mirrors `wait_for_termination=True`.

2. `WasbOperator` — Clean mapping to `AzureBlobStorageCredentials` + `blob_storage_download`/`blob_storage_upload` from `prefect_azure.blob_storage`. Covers both connection string and service principal credential setup.

3. `WasbDeleteOperator` — Companion entry using `credentials.get_client()` → `BlobServiceClient.delete_blob()`. Points to WasbOperator section for credential setup.

`colin/models/operators/dbt.md` — One operator section:

1. `DbtCloudRunJobOperator` — Maps to `trigger_dbt_cloud_job_run_and_wait_for_completion` with `DbtCloudCredentials` block. Explicit warning to use the `_and_wait_for_completion` variant (not fire-and-forget) to match the operator's default `wait_for_termination=True` behavior. Covers `retry_filtered_models_attempts` parameter.

`colin/models/operators/_index.md` — Updated to aggregate both new files via `ref()` syntax, adding "Azure Provider Operators" and "dbt Provider Operators" sections.

## Decisions Made

1. WasbDeleteOperator included as a third section in azure.md. RESEARCH.md Open Question 3 recommended inclusion since it shares the same credential pattern and adds minimal scope.

2. ADF task example includes the full polling loop (not just `create_run()`), since the plan specifies mirroring `wait_for_termination=True` and RESEARCH.md Pattern 2 recommends showing the complete pattern.

3. The warning in azure.md notes contains the string `from prefect_azure import DataFactory*` as a cautionary example telling users NOT to do this. This is correct content, not an error — the grep-based verification check produces a false positive on this string.

## Deviations from Plan

None — plan executed exactly as written. WasbDeleteOperator inclusion was specified in the plan (Task 1, Section 3).

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | d60c678 | Azure operator Colin models (azure.md) — 3 sections |
| Task 2 | 3c6c5d3 | dbt Cloud Colin model (dbt.md) + _index.md update |

## Self-Check: PASSED

- azure.md: FOUND
- dbt.md: FOUND
- commit d60c678: FOUND
- commit 3c6c5d3: FOUND
