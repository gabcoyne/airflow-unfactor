# Roadmap: airflow-unfactor — Completeness Audit

## Overview

This milestone transforms the existing MCP server from a well-architected tool with critical coverage gaps into a production-ready migration assistant. Four phases deliver this in dependency order: first, the P1 Colin knowledge models that cover the five most-used missing operators; second, the server quality improvements that help every user regardless of operators encountered; third, the P2 knowledge expansion covering Azure, dbt, Jinja macros, and advanced patterns; fourth, validation hardening that ties together checklist coverage with real-world DAG testing.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: P1 Knowledge Expansion** - Colin models for the five operators most likely to cause tool failure at enterprise installations (completed 2026-02-26)
- [ ] **Phase 2: Server Quality** - Startup warning, improved suggestion matching, and expanded fallback knowledge
- [ ] **Phase 3: P2 Knowledge Expansion** - Azure, dbt, Jinja macros, scheduling, and advanced migration patterns
- [ ] **Phase 4: Validation Hardening** - Expanded validation checklist and real-world DAG regression tests

## Phase Details

### Phase 1: P1 Knowledge Expansion
**Goal**: Users get authoritative translation guidance for the five operators they are most likely to encounter in enterprise Airflow installations but currently receive nothing for
**Depends on**: Nothing (first phase)
**Requirements**: KNOW-01, KNOW-02, KNOW-03, KNOW-04, KNOW-05, KNOW-06
**Success Criteria** (what must be TRUE):
  1. `lookup_concept("KubernetesPodOperator")` returns a Kubernetes work pool pattern with architectural shift guidance, not `not_found`
  2. `lookup_concept("DatabricksSubmitRunOperator")` and `lookup_concept("DatabricksRunNowOperator")` return `prefect-databricks` task mappings
  3. `lookup_concept("SimpleHttpOperator")` returns the `httpx` task pattern
  4. `lookup_concept("SparkSubmitOperator")` returns the `prefect-shell` or Databricks/Dataproc path with decision guidance
  5. `lookup_concept("SSHOperator")` returns the `paramiko`/`fabric` + Secret block pattern
**Plans:** 3/3 plans complete
- [ ] 01-01-PLAN.md — Author kubernetes.md, http.md, sftp.md (KNOW-01, KNOW-05, KNOW-06)
- [ ] 01-02-PLAN.md — Author databricks.md, spark.md, update _index.md (KNOW-02, KNOW-03, KNOW-04)
- [ ] 01-03-PLAN.md — Compile Colin models, add parametrized tests (all KNOW-*)

### Phase 2: Server Quality
**Goal**: The server communicates its own health accurately and surfaces related operators when an exact match is not found, so users are never silently left without guidance
**Depends on**: Phase 1
**Requirements**: SRVR-01, SRVR-02, SRVR-03, SRVR-04
**Success Criteria** (what must be TRUE):
  1. Starting the MCP server against a missing or empty `colin/output/` directory prints a warning with instructions to run `colin run` — no silent failure
  2. `lookup_concept("KubernetesPodOp")` (misspelled) returns the Kubernetes entry via fuzzy match rather than bare `not_found`
  3. `lookup_concept` for a common operator not in Colin output (e.g., `ShortCircuitOperator`) returns a fallback entry rather than `not_found`
  4. When a Colin JSON file fails to parse, a warning is logged identifying the filename and error — no silent data loss
**Plans:** 2 plans
- [ ] 02-01-PLAN.md — Replace suggestions() with difflib fuzzy matching, expand FALLBACK_KNOWLEDGE to 15 entries (SRVR-02, SRVR-03)
- [ ] 02-02-PLAN.md — Add startup warning for missing Colin output, log JSON parse errors (SRVR-01, SRVR-04)

### Phase 3: P2 Knowledge Expansion
**Goal**: Users migrating Azure, dbt, and complex scheduling DAGs get authoritative translation guidance, and the scaffold tool correctly externalizes Airflow schedule definitions to `prefect.yaml`
**Depends on**: Phase 1
**Requirements**: KNOW-07, KNOW-08, KNOW-09, KNOW-10, KNOW-11, KNOW-12
**Success Criteria** (what must be TRUE):
  1. `lookup_concept("AzureDataFactoryRunPipelineOperator")` and `lookup_concept("WasbOperator")` return `prefect-azure` mappings
  2. `lookup_concept("DbtCloudRunJobOperator")` returns a `prefect-dbt` DbtCloudCredentials + task pattern
  3. `lookup_concept("macros.ds_add")` or Jinja pattern lookups return explicit Python equivalents, not `not_found`
  4. `lookup_concept("depends_on_past")` returns an explicit "no direct equivalent" entry with workaround patterns
  5. The `scaffold` tool generates `prefect.yaml` schedule config when a DAG `schedule_interval` is detected, not a placeholder
**Plans**: TBD

### Phase 4: Validation Hardening
**Goal**: The validate tool's comparison checklist explicitly covers all new operator types, and the test suite exercises real-world production-style DAGs containing those operators
**Depends on**: Phase 3
**Requirements**: VALD-01, VALD-02
**Success Criteria** (what must be TRUE):
  1. Calling `validate` on a flow converted from a Kubernetes DAG returns a checklist item that checks for Kubernetes work pool configuration
  2. Calling `validate` on a Databricks-origin flow returns checklist items checking for `prefect-databricks` block setup and job parameter mapping
  3. The test suite includes at least one fixture DAG per new operator type (Kubernetes, Databricks, Azure, dbt, HTTP, SSH) and all tests pass
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. P1 Knowledge Expansion | 3/3 | Complete   | 2026-02-26 |
| 2. Server Quality | 0/2 | Not started | - |
| 3. P2 Knowledge Expansion | 0/TBD | Not started | - |
| 4. Validation Hardening | 0/TBD | Not started | - |
