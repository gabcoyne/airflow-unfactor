---
phase: 01-p1-knowledge-expansion
plan: "01"
subsystem: colin-models
tags: [colin, knowledge, kubernetes, http, ssh, operators]
dependency_graph:
  requires: []
  provides: [KNOW-01, KNOW-05, KNOW-06]
  affects: [colin-compilation, lookup-concept-tool]
tech_stack:
  added: []
  patterns:
    - "Architectural shift Colin entry (KubernetesPodOperator -> Kubernetes work pool)"
    - "No-package Colin entry (SimpleHttpOperator -> httpx, SSHOperator -> paramiko)"
key_files:
  created:
    - colin/models/operators/kubernetes.md
    - colin/models/operators/http.md
    - colin/models/operators/sftp.md
  modified: []
decisions:
  - "kubernetes.md uses conceptual guidance (not parameter mapping) because KubernetesPodOperator is an architectural shift, not a parameter-for-parameter translation"
  - "http.md includes HttpOperator section (Airflow 2.x rename of SimpleHttpOperator) for completeness"
  - "sftp.md documents both paramiko (baseline) and fabric (higher-level) options with paramiko as primary"
metrics:
  duration: "2 minutes"
  completed: "2026-02-26"
  tasks_completed: 3
  files_created: 3
---

# Phase 01 Plan 01: Kubernetes, HTTP, and SSH Colin Models Summary

Three Colin model files authored for the infrastructure, HTTP, and SSH operator families, covering the no-package and architectural-shift translation patterns most likely to cause LLM regression without explicit guidance.

## What Was Built

`colin/models/operators/kubernetes.md` documents the KubernetesPodOperator as an ARCHITECTURAL SHIFT entry. Rather than a parameter-for-parameter mapping, it explains that Airflow's per-task pod model becomes a Prefect work pool model where infrastructure lives at the work pool level, not in task code. Explicit anti-patterns (no subprocess, no kubernetes SDK, no wrapped operator calls) prevent the most common LLM regression.

`colin/models/operators/http.md` documents SimpleHttpOperator and HttpOperator as NO-PACKAGE translations. The file explicitly warns that no `prefect-http` package exists, directs LLMs to use httpx directly inside @task, and maps http_conn_id to a Secret block, response_check to raise_for_status, and log_response to get_run_logger.

`colin/models/operators/sftp.md` documents SSHOperator as a NO-PACKAGE translation using paramiko (baseline) or fabric (higher-level). The file includes Secret block creation instructions before running, exit status checking, and explicit warning that no prefect-ssh package exists.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 (kubernetes.md) | 9913527 | Previously committed in prior session |
| Task 2 (http.md) | 1b23aaa | SimpleHttpOperator + HttpOperator sections with no-package warning |
| Task 3 (sftp.md) | 89dcc86 | SSHOperator with paramiko pattern and Secret block guidance |

## Deviations from Plan

None — plan executed exactly as written. The kubernetes.md file was found to have been committed in a prior partial session (commit 9913527); the task was already complete for that file. http.md and sftp.md were created and committed fresh.

## Verification Results

All three files pass automated checks:
- `kubernetes.md`: contains `{% section KubernetesPodOperator %}`, `{% endsection %}`, and `prefect-kubernetes` reference
- `http.md`: contains both `{% section SimpleHttpOperator %}` and `{% section HttpOperator %}`, and "NO prefect-http" warning
- `sftp.md`: contains `{% section SSHOperator %}`, `{% endsection %}`, and paramiko pattern
