# Requirements: airflow-unfactor Completeness Audit

**Defined:** 2026-02-26
**Core Value:** Every Airflow 2.x operator, pattern, and connection type a user encounters in production should have translation guidance.

## v1 Requirements

Requirements for completeness milestone. Each maps to roadmap phases.

### P1 Knowledge Expansion

- [x] **KNOW-01**: Colin model for KubernetesPodOperator → Kubernetes work pool pattern with architectural shift guidance
- [x] **KNOW-02**: Colin model for DatabricksSubmitRunOperator → prefect-databricks DatabricksSubmitRun task
- [x] **KNOW-03**: Colin model for DatabricksRunNowOperator → prefect-databricks DatabricksRunNow task
- [x] **KNOW-04**: Colin model for SparkSubmitOperator → shell/Databricks/Dataproc execution paths
- [x] **KNOW-05**: Colin model for HttpOperator/SimpleHttpOperator → httpx task pattern
- [x] **KNOW-06**: Colin model for SSHOperator → paramiko/fabric task with Secret block

### P2 Knowledge Expansion

- [x] **KNOW-07**: Colin model for Azure operators (AzureDataFactoryRunPipelineOperator, WasbOperator) → prefect-azure
- [x] **KNOW-08**: Colin model for DbtCloudRunJobOperator → prefect-dbt DbtCloudCredentials + tasks
- [x] **KNOW-09**: Extended Jinja macro patterns: `{{ macros.ds_add() }}`, `{{ dag_run.conf }}`, `{{ next_ds }}`, `{{ prev_ds }}`, `{{ run_id }}`
- [x] **KNOW-10**: `depends_on_past` concept entry with explicit "no direct equivalent" workarounds
- [x] **KNOW-11**: Deferrable operator / async sensor migration gotchas (poke vs reschedule vs deferrable semantics)
- [x] **KNOW-12**: Schedule translation in scaffold tool: `schedule_interval`/cron → `prefect.yaml` schedule config

### Server Quality

- [x] **SRVR-01**: Startup warning when Colin output directory is missing or empty with instructions to run `colin run`
- [x] **SRVR-02**: Replace character-overlap suggestion algorithm with `difflib.SequenceMatcher` in knowledge.py
- [x] **SRVR-03**: Expand FALLBACK_KNOWLEDGE from 6 to ~15-20 highest-frequency operator entries
- [x] **SRVR-04**: Log warnings when Colin JSON files fail to parse (include filename and error type)

### Validation

- [ ] **VALD-01**: Expand validate tool `comparison_guidance` checklist for Kubernetes, Databricks, Azure, dbt, HTTP, SSH operator types
- [ ] **VALD-02**: Test against real-world production-style DAGs covering all new operator types

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Long-tail Operators

- **KNOW-13**: Docker operator → Docker work pool
- **KNOW-14**: SlackAPIPostOperator / SlackWebhookOperator → prefect-slack
- **KNOW-15**: PagerdutyEventsOperator → pagerduty API task
- **KNOW-16**: SparkJDBCOperator / SparkSqlOperator / PySparkOperator (on-cluster Spark)
- **KNOW-17**: SFTPOperator / FTPOperator for legacy file transfer
- **KNOW-18**: Timetable / custom schedule migration (CronTriggerTimetable, EventsTimetable, DatasetTriggeredTimetable)

### Advanced Patterns

- **PTRN-01**: Astronomer Cosmos / dbt TaskGroup → DbtCoreOperation.map() pattern
- **PTRN-02**: Backfill / catchup semantics deep treatment
- **PTRN-03**: SubDagOperator (deprecated) migration guidance

## Out of Scope

| Feature | Reason |
|---------|--------|
| Airflow 1.x compatibility | 1.x is EOL; operator APIs are substantially different; doubles knowledge surface for diminishing returns |
| TaskFlow API decorator patterns | Can add later; TaskFlow is syntactic sugar over standard operators |
| Runtime flow execution | Converted code needs review before execution; running unreviewed code risks data corruption |
| AST-based structural analysis | LLMs understand intent from raw source better than AST captures structure |
| Automatic block/secret creation | Requires live Prefect API credentials; blocks are environment-specific |
| UI/visual migration dashboard | Engineering effort better spent on knowledge completeness |
| Semantic equivalence checking | Undecidable in general; heuristics mislead users into false confidence |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| KNOW-01 | Phase 1 | Complete |
| KNOW-02 | Phase 1 | Complete |
| KNOW-03 | Phase 1 | Complete |
| KNOW-04 | Phase 1 | Complete |
| KNOW-05 | Phase 1 | Complete |
| KNOW-06 | Phase 1 | Complete |
| SRVR-01 | Phase 2 | Complete |
| SRVR-02 | Phase 2 | Complete |
| SRVR-03 | Phase 2 | Complete |
| SRVR-04 | Phase 2 | Complete |
| KNOW-07 | Phase 3 | Complete |
| KNOW-08 | Phase 3 | Complete |
| KNOW-09 | Phase 3 | Complete |
| KNOW-10 | Phase 3 | Complete |
| KNOW-11 | Phase 3 | Complete |
| KNOW-12 | Phase 3 | Complete |
| VALD-01 | Phase 4 | Pending |
| VALD-02 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-26*
*Last updated: 2026-02-26 after initial definition*
