# Feature Research

**Domain:** Airflow-to-Prefect migration tooling (MCP server for LLM-assisted DAG conversion)
**Researched:** 2026-02-26
**Confidence:** HIGH (operator landscape verified against Apache Airflow provider docs and Prefect migration guides; gap analysis verified against current Colin output)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = the tool fails on real production DAGs.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Core operator coverage: `PythonOperator`, `BashOperator`, `EmptyOperator` | Present in virtually every Airflow DAG | LOW | Already covered in Colin + fallback |
| Branching: `BranchPythonOperator`, `ShortCircuitOperator` | Very common control-flow pattern | LOW | Already in Colin core |
| TaskGroup → subflow | Widely used for DAG organization in 2.x | LOW | Already in patterns |
| XCom → return values | The fundamental data-passing mechanism | LOW | Covered in concepts |
| `schedule_interval` / cron → deployment schedule | Every scheduled DAG has this | LOW | Covered in concepts |
| `default_args` → `@task` defaults | Nearly universal across production DAGs | LOW | Covered in patterns |
| `TriggerDagRunOperator` → `run_deployment` | Cross-DAG orchestration is table stakes for complex orgs | MEDIUM | Covered in Colin core |
| `ExternalTaskSensor` → events/polling | Extremely common for cross-DAG dependencies | MEDIUM | Covered in sensors |
| Sensor-to-polling-task pattern (general) | Every production DAG has at least one sensor | LOW | Covered as concept; specific sensors below |
| Database operators: `PostgresOperator`, `MySqlOperator`, `SnowflakeOperator`, `SQLExecuteQueryOperator` | SQL is the backbone of most ETL DAGs | LOW | Covered in database operators |
| AWS S3 operators: `S3CreateObjectOperator`, `S3CopyObjectOperator`, `S3DeleteObjectsOperator` | AWS is the dominant cloud in Airflow deployments | MEDIUM | Covered in AWS operators |
| AWS sensor: `S3KeySensor` | File-arrival patterns are universal in data pipelines | LOW | Covered in sensors |
| GCP operators: `BigQueryInsertJobOperator`, `GCSToGCSOperator`, `GCSToLocalFilesystemOperator` | GCP/BigQuery is the second most common cloud stack | MEDIUM | Covered in GCP operators |
| Connection → Block mappings for: postgres, mysql, aws, s3, gcp, gcs, bigquery, snowflake, azure, dbt, slack | Every non-trivial DAG uses connections | LOW | Covered in connections |
| Jinja template variable replacement (`{{ ds }}`, `{{ params.x }}`) | Present in nearly all production DAGs | MEDIUM | Covered in patterns |
| Callback → state hook mapping (`on_failure_callback`, `on_success_callback`) | Standard for operational alerting | MEDIUM | Covered in patterns |
| Trigger rule translation (`all_done`, `none_failed`, `one_success`) | Required for branching DAGs | HIGH | Covered in patterns; conceptually complex |
| Validation: return original DAG + converted flow for LLM comparison | Core quality gate in the workflow | LOW | Existing `validate` tool |
| Syntax check for generated code | Immediate feedback loop | LOW | Existing `validation.py` |
| Scaffold: Prefect project directory structure | Sets up the landing zone for generated code | LOW | Existing `scaffold` tool |
| **`KubernetesPodOperator` → Kubernetes work pool** | Extremely common for isolation/resource control; used at most mid-to-large orgs | HIGH | **NOT COVERED — gap** |
| **`DatabricksSubmitRunOperator` / `DatabricksRunNowOperator` → prefect-databricks** | Databricks is near-universal in modern data stacks | HIGH | **NOT COVERED — gap** |
| **`SparkSubmitOperator` → Databricks or Dataproc** | Spark jobs appear in most analytics pipelines | HIGH | **NOT COVERED — gap** |
| **Dynamic task mapping: `.expand()` → `.map()`** | Airflow 2.3+ feature; increasingly common in production | MEDIUM | Covered in patterns |
| **`HttpOperator` / `SimpleHttpOperator`** | API calls appear in nearly every pipeline | MEDIUM | **NOT COVERED — gap** |
| **`EmailOperator`** | Ubiquitous for notifications | LOW | Covered in core operators |

**Summary of table-stakes gaps:**
1. `KubernetesPodOperator` — most critical missing operator
2. `DatabricksSubmitRunOperator` / `DatabricksRunNowOperator` — Databricks is dominant
3. `SparkSubmitOperator` — common in on-prem/hybrid Spark shops
4. `HttpOperator` / `SimpleHttpOperator` — API calls in every pipeline
5. `SSHOperator` — present in many legacy/hybrid environments

---

### Differentiators (Competitive Advantage)

Features that set this tool apart from manual migration and from Prefect's own static migration docs.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Live Prefect docs search** (`search_prefect_docs`) | Fills gaps in Colin knowledge with current docs — static guides go stale | LOW | Existing, working |
| **Colin-compiled knowledge from live sources** | Translation rules come from actual Airflow source code, not just docs summaries | MEDIUM | Existing pipeline |
| **Provider-specific operator coverage beyond AWS/GCP** (Azure, Databricks, dbt, Spark, Kubernetes) | Most orgs use at least one non-AWS/GCP service; Prefect's migration docs only cover basics | HIGH | Gap to close |
| **Gotchas and caveats per operator** (serialization, backfill semantics, trigger rule edge cases) | LLMs hallucinate subtleties; explicit gotchas prevent bad conversions | MEDIUM | Already in some entries; needs broader coverage |
| **Startup warning when Colin output is missing** | Clear signal to run `colin run` before attempting migration | LOW | Gap from CONCERNS.md |
| **Astronomer Cosmos / dbt knowledge** | Cosmos is the dominant dbt-on-Airflow pattern; many shops run dbt via TaskGroups of dbt operators | HIGH | **NOT COVERED — gap** |
| **dbt Core vs dbt Cloud knowledge** | `prefect-dbt` supports both; mapping depends on which flavor the user runs | MEDIUM | Connections covered; operators not |
| **Sensor gotchas: reschedule mode vs poke mode** | Deferrable operators (Airflow 2.2+) changed sensor behavior; migrators need to know poke_interval semantics changed | MEDIUM | Not in current knowledge base |
| **Multi-operator suggestion quality** | When a lookup fails, return the closest operator family, not just character-overlap suggestions | MEDIUM | Known concern (CONCERNS.md) |
| **Jinja template coverage beyond `{{ ds }}`** | Production DAGs use `{{ execution_date }}`, `{{ next_ds }}`, `{{ prev_ds }}`, `{{ macros.ds_add() }}`, `{{ run_id }}`, `{{ dag_run.conf }}` | MEDIUM | `{{ ds }}` and `{{ params.x }}` covered; others are gaps |
| **`depends_on_past` equivalence guidance** | No direct Prefect equivalent; LLMs need explicit guidance on alternatives | MEDIUM | Noted in default-args pattern but not detailed |
| **Backfill / catchup semantics** | `catchup=False` behavior differs; production teams need to understand the contract | MEDIUM | Briefly noted; needs full treatment |
| **AzureOperators** (`WasbHook`, `AzureBlobStorageOperator`, `AzureDataFactoryRunPipelineOperator`) | Azure is the third major cloud; meaningful user population | HIGH | Connection block covered; operators not |

---

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem valuable but create problems in an LLM-centric migration tool.

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| **Automatic code generation in the MCP server** | "Just convert my DAG automatically" | DAG logic is too varied and idiomatic; any deterministic translation will produce wrong code that users ship without review. The LLM reading raw source generates better, contextual code. | Provide raw source + knowledge; let LLM generate. This is the existing, correct approach. |
| **AST-based structural analysis** | More "reliable" than raw text | Airflow DAGs rely heavily on runtime patterns (globals, loops, conditionals at module level); AST catches the structure but misses the intent. LLMs understand intent from raw source. | Keep raw source reading; never add an AST intermediary. |
| **Airflow 1.x support** | Some orgs haven't migrated yet | Airflow 1.x operator names, hook APIs, and scheduling semantics are substantially different. Adding 1.x doubles the knowledge surface with diminishing returns (1.x is EOL). | Explicitly document "Airflow 2.x only" and suggest upgrading to 2.x first if on 1.x. |
| **Runtime flow execution** | "Run the converted flow for me" | This is out of scope and dangerous — converted code needs review before execution. Running unconverted logic against production infra risks data corruption. | Validate syntax only; scaffold project; direct users to run via Prefect CLI. |
| **UI / visual migration dashboard** | Nice-to-have for enterprise pitches | Takes engineering effort away from knowledge completeness, which is the actual bottleneck. An incomplete knowledge base with a great UI is worse than complete knowledge without one. | Focus engineering on operator/pattern coverage and validation quality. |
| **Streaming DAG conversion (line-by-line)** | Feels faster | DAG context (imports, globals, task dependency graph) requires full-file understanding. Partial reads produce incomplete conversions. | Always read the full DAG file; `read_dag` already does this. |
| **Semantic equivalence checking** | Verify the converted flow does the same thing | True semantic equivalence is undecidable in general; heuristics mislead users into false confidence. | Validate syntax + return both sources for side-by-side LLM review via `validate` tool. |
| **Automatic block/secret creation** | "Create my Prefect blocks for me" | Requires live Prefect API credentials and cluster access; adds authentication complexity to a documentation tool. Blocks are also environment-specific. | Document what blocks to create (connections knowledge); let users create via CLI/UI. |

---

## Feature Dependencies

```
[Scaffold tool]
    └──requires──> [read_dag] (reads source to understand project name/structure)

[validate tool]
    └──requires──> [read_dag] (needs both source files)
    └──requires──> [validation.py] (syntax checking)

[lookup_concept]
    └──requires──> [Colin output OR fallback knowledge]
    └──enhances──> [search_prefect_docs] (fallback when lookup fails)

[search_prefect_docs]
    └──requires──> [Prefect MCP server availability]
    └──enhances──> [lookup_concept] (coverage extension)

[KubernetesPodOperator knowledge]
    └──requires──> [Colin model expansion] (new colin/models/operators/kubernetes.md)

[DatabricksSubmitRunOperator knowledge]
    └──requires──> [Colin model expansion] (new colin/models/operators/databricks.md)

[Cosmos/dbt knowledge]
    └──requires──> [Colin model expansion] (expand connections.md dbt section + new operators)

[Startup warning for missing Colin output]
    └──requires──> [server.py modification] (check colin/output on startup)

[Improved suggestion algorithm]
    └──requires──> [knowledge.py modification] (difflib or Levenshtein scoring)
```

### Dependency Notes

- **KubernetesPodOperator requires Colin expansion:** A new `colin/models/operators/kubernetes.md` model is needed. The Colin pipeline compiles from Airflow provider source; CNCF Kubernetes provider operators need to be in scope.
- **Databricks operators require Colin expansion:** `DatabricksSubmitRunOperator`, `DatabricksRunNowOperator`, and `DatabricksCreateJobsOperator` map to `prefect-databricks`; connections are already covered but operators are not.
- **Startup warning is independent:** Modifying `server.py` to check for Colin output existence on startup is a small, self-contained change that unblocks all users who forgot to run `colin run`.
- **Suggestion algorithm improvement is independent:** Replacing character-overlap scoring with `difflib.SequenceMatcher` is contained to `knowledge.py`; no dependencies.

---

## MVP Definition

### Launch With (v1 — completeness milestone)

Minimum set to call this tool credible for real migration projects.

- [x] Core operators: PythonOperator, BashOperator, EmptyOperator, BranchPythonOperator, ShortCircuitOperator — **DONE**
- [x] Database operators: PostgresOperator, MySqlOperator, SnowflakeOperator, SQLExecuteQueryOperator — **DONE**
- [x] AWS operators: S3, Lambda, Glue, ECS, SageMaker, Athena, Redshift, SNS — **DONE**
- [x] GCP operators: BigQuery, GCS, Dataproc, PubSub, Data Fusion — **DONE**
- [x] Sensors: FileSensor, S3KeySensor, HttpSensor, SqlSensor, GCSObjectExistenceSensor — **DONE**
- [x] Patterns: dynamic mapping, branching, callbacks, trigger rules, Jinja `{{ ds }}` — **DONE**
- [ ] **KubernetesPodOperator** — why essential: used at the majority of serious Airflow deployments for isolation
- [ ] **DatabricksSubmitRunOperator / DatabricksRunNowOperator** — why essential: Databricks is the most common data platform in enterprise shops
- [ ] **SparkSubmitOperator** — why essential: Spark jobs are foundational in analytics pipelines
- [ ] **HttpOperator / SimpleHttpOperator** — why essential: API calls appear in nearly every non-trivial pipeline
- [ ] **SSHOperator** — why essential: frequent in hybrid/on-prem environments and as a general escape hatch
- [ ] Startup warning when Colin output is missing — why essential: silent failure confuses all fresh-install users

### Add After Validation (v1.x)

- [ ] **Jinja macro coverage**: `{{ macros.ds_add() }}`, `{{ run_id }}`, `{{ dag_run.conf }}`, `{{ next_ds }}`, `{{ prev_ds }}`
- [ ] **Azure operators**: `AzureBlobStorageOperator`, `AzureDataFactoryRunPipelineOperator`, `WasbHook`
- [ ] **Cosmos/dbt operator patterns**: TaskGroup-of-dbt-operators → `DbtCoreOperation.map()`
- [ ] **Deferrable operator / async sensor gotchas**: document poke vs reschedule vs deferrable migration semantics
- [ ] **`depends_on_past` equivalence**: explicit guidance since there is no Prefect equivalent
- [ ] **Improved suggestion algorithm**: `difflib.SequenceMatcher` over character overlap
- [ ] **Silent JSON parse failure warnings**: log which Colin files failed to parse (CONCERNS.md item)

### Future Consideration (v2+)

- [ ] **Backfill / catchup semantics documentation**: deep treatment of `catchup=True` vs `catchup=False` vs Prefect's no-backfill default
- [ ] **Apache Spark provider (on-cluster) operators**: `SparkJDBCOperator`, `SparkSqlOperator`, `PySparkOperator`
- [ ] **Messaging operators**: `SlackAPIPostOperator`, `PagerdutyEventsOperator` — nice-to-have for notification patterns
- [ ] **Docker operator**: `DockerOperator` → Prefect Docker work pool — valuable but edge case
- [ ] **FTP/SFTP/SSH file transfer operators**: `SFTPOperator`, `FTPOperator` — legacy environments
- [ ] **Timetable / custom schedule migration**: `CronTriggerTimetable`, `EventsTimetable`, `DatasetTriggeredTimetable`

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| KubernetesPodOperator knowledge | HIGH | MEDIUM (new Colin model) | P1 |
| DatabricksSubmitRunOperator / DatabricksRunNowOperator | HIGH | MEDIUM (new Colin model) | P1 |
| HttpOperator / SimpleHttpOperator | HIGH | LOW (simple pattern, uses httpx) | P1 |
| SSHOperator | MEDIUM | LOW (paramiko pattern) | P1 |
| SparkSubmitOperator | HIGH | MEDIUM (Dataproc or Databricks path) | P1 |
| Startup warning (missing Colin output) | HIGH | LOW (server.py check) | P1 |
| Improved suggestion algorithm | MEDIUM | LOW (difflib swap in knowledge.py) | P2 |
| Jinja macro coverage expansion | HIGH | LOW (extend patterns.json) | P2 |
| Azure operators | MEDIUM | MEDIUM (new Colin model) | P2 |
| Cosmos/dbt operator patterns | MEDIUM | HIGH (complex; Cosmos creates TaskGroups dynamically) | P2 |
| Deferrable/async sensor migration notes | MEDIUM | LOW (gotchas in existing sensor entries) | P2 |
| `depends_on_past` guidance | MEDIUM | LOW (one new concept entry) | P2 |
| Silent JSON parse warnings | LOW | LOW (exception handler change) | P3 |
| Docker operator | LOW | MEDIUM | P3 |
| Backfill semantics deep treatment | MEDIUM | MEDIUM | P3 |

**Priority key:**
- P1: Must have for this milestone (completeness audit goal)
- P2: Should have, add in this milestone if capacity allows
- P3: Nice to have, defer to next milestone

---

## Competitor Feature Analysis

There are no direct automated Airflow→Prefect migration tools. The relevant comparisons are:

| Feature | Prefect's Static Migration Docs | Manual Migration | airflow-unfactor |
|---------|----------------------------------|------------------|------------------|
| Core operator mappings | Yes (limited) | Manual research | Yes, plus gotchas |
| Provider-specific operators | Partial (S3KeySensor, PostgresHook) | Manual | Extensive (AWS, GCP, DB) |
| Dynamic task mapping | Yes | Manual | Yes |
| Branching patterns | Yes | Manual | Yes |
| Trigger rule translation | No | Manual | Yes |
| Sensor patterns | Minimal | Manual | Yes, with polling conversion |
| Connection → Block mappings | Yes | Manual | Yes, with config code |
| Jinja template replacement | Partial | Manual | Yes |
| Live docs search | No | Manual | Yes (search_prefect_docs) |
| Validation / side-by-side review | No | Manual | Yes |
| Project scaffolding | No | Manual | Yes |
| **KubernetesPodOperator** | Mentioned only | Manual | **Gap — P1** |
| **Databricks operators** | Not covered | Manual | **Gap — P1** |
| **Cosmos/dbt patterns** | Not covered | Manual | **Gap — P2** |

Prefect's own migration guide ([docs.prefect.io/v3/how-to-guides/migrate/airflow](https://docs.prefect.io/v3/how-to-guides/migrate/airflow)) is the closest comparison point. It covers concepts but not the long tail of providers. This tool's advantage is depth of operator coverage, gotcha documentation, and the LLM-readable format that enables code generation rather than just explanation.

---

## Operator Coverage Map

### Currently Covered (Colin output + fallback)

**Core operators:** PythonOperator, BashOperator, PythonVirtualenvOperator, EmptyOperator/DummyOperator, BranchPythonOperator, ShortCircuitOperator, TriggerDagRunOperator, EmailOperator, LatestOnlyOperator, ExternalTaskSensor

**Sensors:** FileSensor, S3KeySensor, HttpSensor, SqlSensor, DateTimeSensor, GCSObjectExistenceSensor

**Database:** PostgresOperator, MySqlOperator, MsSqlOperator, SQLExecuteQueryOperator, SnowflakeOperator, SqliteOperator

**AWS:** S3CreateObjectOperator, S3CopyObjectOperator, S3DeleteObjectsOperator, LambdaInvokeFunctionOperator, GlueJobOperator, EcsRunTaskOperator, SageMakerTrainingOperator, StepFunctionStartExecutionOperator, AthenaOperator, RedshiftSQLOperator, SnsPublishOperator

**GCP:** BigQueryInsertJobOperator, GCSToGCSOperator, GCSToLocalFilesystemOperator, DataprocSubmitJobOperator, CloudDataFusionStartPipelineOperator, PubSubPublishMessageOperator

**Patterns:** taskgroup-to-subflow, trigger-rule-to-state, jinja-ds-to-runtime, jinja-params-to-flow-params, dynamic-mapping, branch-to-conditional, short-circuit-to-early-return, trigger-dag-to-run-deployment, default-args-to-task-defaults, callbacks-to-hooks

**Concepts:** dag-to-flow, operator-to-task, xcom-to-return-values, connection-to-block, variable-to-prefect-variable, sensor-to-polling, dataset-to-automation, hook-to-integration-client, pool-to-work-pool, callback-to-state-hook, schedule-cron, schedule-timetable

**Connections:** postgres, mysql, aws, s3, gcp, gcs, bigquery, azure, databricks, snowflake, ssh, http, slack, dbt, redis, mongo

### P1 Gaps (Must Close This Milestone)

| Missing Operator/Pattern | Airflow Module | Prefect Equivalent |
|--------------------------|----------------|--------------------|
| `KubernetesPodOperator` | `airflow.providers.cncf.kubernetes.operators.pod` | Kubernetes work pool or `KubernetesJob` task |
| `DatabricksSubmitRunOperator` | `airflow.providers.databricks.operators.databricks` | `DatabricksSubmitRun` from prefect-databricks |
| `DatabricksRunNowOperator` | `airflow.providers.databricks.operators.databricks` | `DatabricksRunNow` from prefect-databricks |
| `SparkSubmitOperator` | `airflow.providers.apache.spark.operators.spark_submit` | Databricks/Dataproc task or `spark-submit` via ShellOperation |
| `HttpOperator` / `SimpleHttpOperator` | `airflow.providers.http.operators.http` | `httpx` task directly |
| `SSHOperator` | `airflow.providers.ssh.operators.ssh` | `paramiko`/`fabric` in a task |

### P2 Gaps (Add If Capacity Allows)

| Missing Operator/Pattern | Airflow Module | Prefect Equivalent |
|--------------------------|----------------|--------------------|
| `AzureBlobStorageOperator` | `airflow.providers.microsoft.azure.operators.wasb_delete` | `AzureBlobStorageCredentials` + azure-storage-blob |
| `AzureDataFactoryRunPipelineOperator` | `airflow.providers.microsoft.azure.operators.data_factory` | Azure REST API via httpx |
| Cosmos/dbt TaskGroup pattern | `astronomer-cosmos` | `DbtCoreOperation` or `prefect-dbt` tasks |
| `DockerOperator` | `airflow.providers.docker.operators.docker` | Docker work pool |
| `{{ macros.ds_add() }}` Jinja macro | Airflow Jinja macros | `timedelta` arithmetic in Python |
| `{{ dag_run.conf }}` Jinja variable | Airflow runtime context | `prefect.runtime.flow_run.parameters` |
| `depends_on_past` concept | DAG parameter | No direct equivalent — document workarounds |

---

## Sources

- [Prefect: How to Migrate from Airflow](https://docs.prefect.io/v3/how-to-guides/migrate/airflow) — HIGH confidence, official docs
- [Prefect: Migrate from Airflow Tutorial](https://docs.prefect.io/v3/tutorials/airflow) — HIGH confidence, official docs
- [Prefect: Airflow Migration Playbook (blog)](https://www.prefect.io/blog/airflow-to-prefect-migration-playbook) — MEDIUM confidence
- [Apache Airflow: Providers Packages Reference](https://airflow.apache.org/docs/apache-airflow-providers/packages-ref.html) — HIGH confidence, official docs
- [Apache Airflow: Dynamic Task Mapping](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/dynamic-task-mapping.html) — HIGH confidence, official docs
- [Astronomer: Airflow Operators](https://www.astronomer.io/docs/learn/2.x/what-is-an-operator) — MEDIUM confidence, managed Airflow vendor
- [Astronomer: Trigger Rules](https://www.astronomer.io/docs/learn/airflow-trigger-rules) — MEDIUM confidence, managed Airflow vendor
- [Astronomer: Deferrable Operators](https://www.astronomer.io/docs/learn/deferrable-operators) — MEDIUM confidence
- [Astronomer Cosmos documentation](https://astronomer.github.io/astronomer-cosmos/) — MEDIUM confidence
- Colin output analysis (`colin/output/*.json`) — HIGH confidence, project-internal compiled knowledge
- CONCERNS.md audit — HIGH confidence, project-internal

---

*Feature research for: Airflow-to-Prefect migration MCP server (airflow-unfactor)*
*Researched: 2026-02-26*
