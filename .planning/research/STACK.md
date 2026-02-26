# Stack Research

**Domain:** Airflow-to-Prefect migration tooling — operator and provider ecosystem mapping
**Researched:** 2026-02-26
**Confidence:** HIGH (official Airflow docs + official Prefect docs + verified provider package listings)

---

## Overview: What the Migration Tool Must Cover

The tool's value is comprehensive operator coverage. A migration session is only useful if the operator the user encounters actually has translation guidance. The Airflow 2.x provider ecosystem contains 90+ provider packages with hundreds of individual operators. This document maps the landscape by priority — what users most commonly encounter and what Prefect equivalents exist.

The existing Colin knowledge base covers: **Core operators** (PythonOperator, BashOperator, BranchPythonOperator, ShortCircuitOperator, TriggerDagRunOperator, EmailOperator, LatestOnlyOperator, EmptyOperator, PythonVirtualenvOperator), **Sensors** (FileSensor, S3KeySensor, HttpSensor, SqlSensor, DateTimeSensor, GCSObjectExistenceSensor, ExternalTaskSensor), **AWS operators** (S3, Lambda, Glue, ECS, SageMaker, Step Functions, Athena, Redshift, SNS), **GCP operators** (BigQuery, GCS, Dataproc, PubSub, DataFusion), **Database operators** (PostgreSQL, MySQL, MSSQL, generic SQLExecuteQuery, Snowflake, SQLite), and **Patterns** (TaskGroup, trigger rules, Jinja templating, dynamic mapping, callbacks, default_args, branching, short-circuit).

**Gaps identified in the current knowledge base** are the primary subject of this research.

---

## Tier 1: Critical Coverage Gaps (High Production Frequency)

These operators appear in a large fraction of real-world Airflow installations and are NOT currently in the Colin knowledge base.

### KubernetesPodOperator (CNCF Kubernetes provider)

**Airflow:** `airflow.providers.cncf.kubernetes.operators.pod.KubernetesPodOperator`
**Package:** `apache-airflow-providers-cncf-kubernetes`
**Production importance:** CRITICAL. Used in essentially every production Kubernetes-hosted Airflow deployment. Enables task-level resource isolation, custom Docker images, and language-agnostic execution. Over 300 DAGs / 5000 tasks/day deployments commonly rely on it.

**Prefect equivalent:**
- Infrastructure-level: Use a **Kubernetes work pool** (`prefect-kubernetes`). Each flow run spawns a Kubernetes Job with configurable CPU/memory. This maps to the KubernetesPodOperator's cluster-level resource management.
- Task-level: Use `@task` + a Kubernetes work pool for that task's deployment. There is no direct per-task Kubernetes pod spawning in Prefect — it's a deployment-level concern.
- Package: `prefect-kubernetes`

**Translation rules:**
- `image` → set as the Docker image in the Kubernetes work pool's base job template
- `task_id`, `name` → flow/task name in the deployment
- `env_vars` → environment variables in the work pool configuration
- `container_resources` (requests/limits) → pod customization in the base job template
- `cmds`, `arguments` → override the container command in the job template
- For a single-task isolation pattern, wrap logic in a subflow and deploy it to a Kubernetes work pool

**Gap status:** Not in Colin. HIGH priority to add.

---

### DockerOperator (Docker provider)

**Airflow:** `airflow.providers.docker.operators.docker.DockerOperator`
**Package:** `apache-airflow-providers-docker`
**Production importance:** HIGH. Common in on-prem and development environments for containerized task execution.

**Prefect equivalent:**
- Use `prefect-docker` with a **Docker work pool** for running flows in containers
- For one-off container invocations within a task: use `docker` Python SDK directly
- Package: `prefect-docker`

**Translation rules:**
- `image` → Docker work pool base image configuration
- `command` → overridden in deployment
- `environment` → environment variables in work pool
- `volumes` → requires custom Docker work pool configuration

**Gap status:** Not in Colin. MEDIUM-HIGH priority.

---

### DatabricksRunNowOperator / DatabricksSubmitRunOperator (Databricks provider)

**Airflow:** `airflow.providers.databricks.operators.databricks`
**Package:** `apache-airflow-providers-databricks`
**Production importance:** HIGH. Databricks is one of the most common data platform targets for Airflow DAGs that run Spark jobs. Both operators see heavy production use in data lake and lakehouse architectures.

Available operators:
- `DatabricksRunNowOperator` — triggers an existing Databricks job (recommended by Databricks)
- `DatabricksSubmitRunOperator` — submits ad-hoc runs without pre-existing job definition
- `DatabricksSqlOperator` — executes SQL in Databricks SQL endpoint or cluster
- `DatabricksCopyIntoOperator` — COPY INTO for data loading
- `DatabricksCreateJobsOperator` — creates/resets job definitions

**Prefect equivalent:**
- Package: `prefect-databricks`
- `DatabricksSubmitRunOperator` → `DatabricksSubmitRun` task from `prefect_databricks`
- `DatabricksRunNowOperator` → `DatabricksJobRunNow` task or direct Databricks SDK call
- The `prefect-databricks` package provides ready-made tasks wrapping the Databricks REST API

**Translation rules:**
- `databricks_conn_id` → `DatabricksCredentials` block
- `json` (job spec) → task configuration dict
- `wait_for_termination=True` → default polling behavior in prefect-databricks tasks
- `notebook_params` / `python_params` → passed as task parameters

**Gap status:** Not in Colin. HIGH priority (Databricks is a top production target).

---

### HttpOperator (HTTP provider)

**Airflow:** `airflow.providers.http.operators.http.SimpleHttpOperator`
**Package:** `apache-airflow-providers-http`
**Production importance:** HIGH. Nearly every pipeline that calls external REST APIs uses this operator. It is arguably the most generic integration point in Airflow.

**Prefect equivalent:**
- Direct `httpx` or `requests` call within a `@task`
- No dedicated prefect-http package exists; this is intentional — use Python HTTP libraries directly

**Translation rules:**
- `http_conn_id` → store base URL + credentials in a `Secret` block or environment variable
- `endpoint` → appended to base URL in task code
- `method` → `httpx.get()`, `httpx.post()`, etc.
- `data` / `json` → request body
- `headers` → passed to httpx call
- `response_check` callable → conditional check in the task body
- `log_response=True` → use `logger = get_run_logger(); logger.info(response.text)`

**Gap status:** Not in Colin. HIGH priority.

---

### SlackAPIPostOperator (Slack provider)

**Airflow:** `airflow.providers.slack.operators.slack.SlackAPIPostOperator`
**Package:** `apache-airflow-providers-slack`
**Production importance:** HIGH. Slack notifications are one of the most common operator uses for alerting on pipeline success or failure. Also: `SlackWebhookOperator`.

**Prefect equivalent:**
- Package: `prefect-slack`
- `SlackWebhook` block for webhook-based notifications
- `send_incoming_webhook_message()` task from `prefect_slack`

**Translation rules:**
- `slack_conn_id` → `SlackWebhook` block loaded by name
- `text` / `blocks` → message content
- For on-failure alerts: use `@flow(on_failure=[slack_notifier])` hook
- `prefect-slack` ships a built-in `SlackNotify` notifier for automation-based alerting

**Gap status:** Not in Colin. HIGH priority (alert operators are extremely common).

---

### DbtCloudRunJobOperator (dbt Cloud provider)

**Airflow:** `airflow.providers.dbt.cloud.operators.dbt.DbtCloudRunJobOperator`
**Package:** `apache-airflow-providers-dbt-cloud`
**Production importance:** HIGH. dbt is the dominant SQL transformation tool; many Airflow pipelines are primarily dbt orchestration wrappers. Also used: community `airflow-dbt` / `airflow-dbt-python` for dbt Core.

Available operators:
- `DbtCloudRunJobOperator` — runs a dbt Cloud job, polls for completion
- `DbtCloudGetJobRunArtifactOperator` — downloads run artifacts
- Community `DbtRunOperator`, `DbtTestOperator`, `DbtSeedOperator` (airflow-dbt-python)

**Prefect equivalent:**
- Package: `prefect-dbt`
- dbt Cloud: `DbtCloudJob.trigger()` → run a dbt Cloud job
- dbt Core: `DbtCoreOperation` for running dbt CLI commands
- `prefect-dbt` integrates with both dbt Cloud and dbt Core

**Translation rules:**
- `job_id` → dbt Cloud job ID passed to `DbtCloudJob` block
- `dbt_cloud_conn_id` → `DbtCloudCredentials` block
- `wait_for_termination=True` → default in prefect-dbt
- For dbt Core: `DbtCoreOperation(commands=["dbt run", "dbt test"]).run()` pattern

**Gap status:** Not in Colin. HIGH priority (dbt is ubiquitous in data engineering).

---

### SnowflakeSqlApiOperator / SQLColumnCheckOperator (Snowflake + common-sql providers)

**Airflow:** `airflow.providers.snowflake.operators.snowflake.SnowflakeSqlApiOperator`
**Package:** `apache-airflow-providers-snowflake`
**Production importance:** HIGH. The existing Colin entry covers `SnowflakeOperator`, but `SnowflakeSqlApiOperator` (which runs multiple SQL statements) and data quality operators are also common in production.

Also missing from Colin:
- `SQLColumnCheckOperator` — data quality checks (airflow.providers.common.sql)
- `SQLTableCheckOperator` — table-level quality checks
- `SQLCheckOperator` — generic SQL check

**Prefect equivalent:**
- `SnowflakeConnector` (prefect-snowflake) handles both single and multi-statement execution
- For data quality: use `@task` with assertion-based checks; no dedicated DQ framework in Prefect (use Great Expectations or similar directly)

**Gap status:** Partially in Colin (SnowflakeOperator exists). Quality check operators missing. MEDIUM priority.

---

## Tier 2: Important Coverage (Medium Production Frequency)

These operators appear in significant fractions of production DAGs and benefit from explicit translation guidance.

### AWS EMR Operators

**Airflow:** `airflow.providers.amazon.aws.operators.emr`
- `EmrCreateJobFlowOperator` — creates EMR cluster
- `EmrAddStepsOperator` — adds Spark/Hadoop steps
- `EmrTerminateJobFlowOperator` — terminates cluster
- `EmrServerlessStartJobRunOperator` — for EMR Serverless
**Package:** `apache-airflow-providers-amazon`

**Prefect equivalent:**
- `prefect-aws` + `AwsCredentials` block
- Direct `boto3` EMR/EMR Serverless client calls
- No dedicated EMR abstraction in prefect-aws; use `AwsCredentials.get_boto3_session().client("emr")`

**Gap status:** Not in Colin. MEDIUM-HIGH priority (common in data lake pipelines).

---

### AWS Batch Operator

**Airflow:** `airflow.providers.amazon.aws.operators.batch.BatchOperator`
**Package:** `apache-airflow-providers-amazon`

**Prefect equivalent:**
- `prefect-aws` provides `batch_submit` task
- `AwsCredentials` block for auth

**Gap status:** Not in Colin. MEDIUM priority.

---

### AWS SQS / EventBridge Operators

**Airflow:** `SqsPublishOperator`, `EventBridgePutEventsOperator`
**Package:** `apache-airflow-providers-amazon`

**Prefect equivalent:**
- Direct `boto3` calls via `AwsCredentials` block
- SQS and EventBridge have no dedicated prefect-aws abstraction

**Gap status:** Not in Colin. LOW-MEDIUM priority.

---

### Google Cloud Dataflow Operators

**Airflow:** `airflow.providers.google.cloud.operators.dataflow`
- `DataflowTemplatedJobStartOperator` — runs a Dataflow template
- `DataflowStartFlexTemplateOperator` — runs a Flex template
- `BeamRunPythonPipelineOperator` — runs an Apache Beam Python pipeline
**Package:** `apache-airflow-providers-google`

**Prefect equivalent:**
- `prefect-gcp` + `GcpCredentials` block
- Direct `google.cloud.dataflow_v1beta3` client calls
- Beam: run via `prefect-shell` with `ShellOperation(["python pipeline.py --runner=DataflowRunner"])`

**Gap status:** Not in Colin. MEDIUM priority.

---

### Google Cloud Run / Cloud Functions Operators

**Airflow:** `CloudRunExecuteJobOperator`, `CloudFunctionsInvokeFunctionOperator`
**Package:** `apache-airflow-providers-google`

**Prefect equivalent:**
- `prefect-gcp` has Cloud Run support (primarily as a work pool)
- For Cloud Run job invocation from a task: use `google.cloud.run_v2` client
- Cloud Functions: direct HTTP call via `httpx` with GCP credentials

**Gap status:** Not in Colin. MEDIUM priority.

---

### Google Cloud Composer / Vertex AI Operators

**Airflow:** `VertexAICreateCustomTrainingJobOperator`, `VertexAIRunPipelineJobOperator`
**Package:** `apache-airflow-providers-google`

**Prefect equivalent:**
- `prefect-gcp` provides `VertexAIWorker` for running flows on Vertex AI
- For triggering Vertex AI pipelines from tasks: use `google.cloud.aiplatform` SDK

**Gap status:** Not in Colin. MEDIUM priority (MLOps use case).

---

### Azure Data Factory Operator

**Airflow:** `AzureDataFactoryRunPipelineOperator`
**Package:** `apache-airflow-providers-microsoft-azure`

**Prefect equivalent:**
- `prefect-azure` package
- `AzureDataFactoryCredentials` block + `run_pipeline` task pattern
- Direct Azure SDK (`azure-mgmt-datafactory`) also viable

**Translation rules:**
- `azure_data_factory_conn_id` → `AzureDataFactoryCredentials` block
- `pipeline_name` → pipeline name string parameter
- `wait_for_termination=True` → polling in task body

**Gap status:** Not in Colin. MEDIUM priority.

---

### Azure Blob Storage (WASB) Operators

**Airflow:** `WasbHook`, `LocalFilesystemToWasbOperator`, `WasbDeleteBlobOperator`
**Package:** `apache-airflow-providers-microsoft-azure`

**Prefect equivalent:**
- `prefect-azure` provides `AzureBlobStorageCredentials` and blob operations
- `AzureContainerInstanceCredentials` block for ACI-based execution

**Gap status:** Not in Colin. MEDIUM priority.

---

### SparkSubmitOperator (Apache Spark provider)

**Airflow:** `airflow.providers.apache.spark.operators.spark_submit.SparkSubmitOperator`
**Package:** `apache-airflow-providers-apache-spark`

**Prefect equivalent:**
- `prefect-shell` + `ShellOperation(["spark-submit ...])`
- Or: Databricks/Dataproc for managed Spark (these have prefect integrations)

**Translation rules:**
- `application` → spark-submit argument
- `conf` dict → `--conf key=value` flags
- `deploy_mode`, `master` → spark-submit arguments

**Gap status:** Not in Colin. MEDIUM priority (on-prem Spark users).

---

### SSHOperator (SSH provider)

**Airflow:** `airflow.providers.ssh.operators.ssh.SSHOperator`
**Package:** `apache-airflow-providers-ssh`

**Prefect equivalent:**
- Use `paramiko` or `fabric` library within a `@task`
- No dedicated prefect-ssh package exists

**Translation rules:**
- `ssh_conn_id` → SSH credentials stored in Prefect `Secret` block
- `command` → executed via `paramiko.SSHClient.exec_command()`

**Gap status:** Not in Colin. MEDIUM priority.

---

### PaperMillOperator / Jupyter Notebooks (Papermill provider)

**Airflow:** `airflow.providers.papermill.operators.papermill.PapermillOperator`
**Package:** `apache-airflow-providers-papermill`

**Prefect equivalent:**
- `papermill.execute_notebook()` called within a `@task`
- No dedicated prefect-papermill package

**Gap status:** Not in Colin. LOW-MEDIUM priority (data science workflows).

---

## Tier 3: Niche Coverage (Lower Frequency, Specialized Use Cases)

These providers are used in specific industry or architecture contexts. Coverage is beneficial but lower priority than Tier 1-2.

| Provider | Key Operators | Prefect Equivalent | Priority |
|----------|--------------|-------------------|----------|
| `apache-kafka` | `ProduceToTopicOperator` | `kafka-python` directly in `@task` | LOW |
| `apache-spark` (Livy) | `LivyOperator` | HTTP call to Livy REST API | LOW |
| `elasticsearch` | `ElasticSearchSQLHook` | `elasticsearch-py` in `@task` | LOW |
| `mongo` | `MongoHook` | `pymongo` in `@task` | LOW |
| `redis` | `RedisPublishOperator` | `prefect-redis` or `redis-py` | LOW |
| `sftp` | `SFTPOperator` | `paramiko` / `pysftp` in `@task` | LOW |
| `salesforce` | `SalesforceToS3Operator` | `simple-salesforce` in `@task` | LOW |
| `databricks` (SQL) | `DatabricksSqlOperator` | `prefect-databricks` | MEDIUM |
| `snowflake` | `SnowflakeSqlApiOperator` | `prefect-snowflake` | MEDIUM |
| `dingding` / `telegram` | Notification operators | Custom HTTP call or prefect-slack | LOW |
| `opsgenie` | `OpsgenieAlertOperator` | `requests` in `@task` | LOW |
| `pagerduty` | `PagerdutyEventsOperator` | `pdpyras` library in `@task` | LOW |

---

## Operator Coverage Matrix: Current State vs. Needed

### Core / Standard Provider (`apache-airflow-providers-standard`)

| Operator | Colin Coverage | Prefect Equivalent | Notes |
|----------|---------------|-------------------|-------|
| PythonOperator | YES | `@task` | Complete |
| BashOperator | YES | `prefect-shell` ShellOperation | Complete |
| PythonVirtualenvOperator | YES | Subprocess/Docker task | Complete |
| EmptyOperator / DummyOperator | YES | Remove or no-op task | Complete |
| BranchPythonOperator | YES | Python if/else in flow | Complete |
| ShortCircuitOperator | YES | Early return from flow | Complete |
| TriggerDagRunOperator | YES | `run_deployment()` | Complete |
| EmailOperator | YES | `prefect-email` | Complete |
| LatestOnlyOperator | YES | Not needed (Prefect default) | Complete |
| ExternalTaskSensor | YES | Events/automations | Complete |
| GenericTransfer | NO | `@task` with direct DB clients | LOW priority |
| SubDagOperator | NO | Subflows (natural in Prefect) | Deprecated in Airflow 2.x |
| @task decorator (TaskFlow) | PARTIAL | Direct `@task` | TaskFlow is already Prefect-like |

### Sensor Operators

| Sensor | Colin Coverage | Prefect Equivalent | Notes |
|--------|---------------|-------------------|-------|
| FileSensor | YES | `@task` with retries | Complete |
| S3KeySensor | YES | `@task` with retries + S3Bucket | Complete |
| HttpSensor | YES | `@task` with retries + httpx | Complete |
| SqlSensor | YES | `@task` with retries + SQLAlchemy | Complete |
| DateTimeSensor | YES | `time.sleep()` or schedule | Complete |
| GCSObjectExistenceSensor | YES | `@task` with retries + GcsBucket | Complete |
| ExternalTaskSensor | YES | Events/automations | Complete |
| TimeSensor | NO | `time.sleep()` or schedule | LOW (trivial) |
| DayOfWeekSensor | NO | Python datetime check | LOW (trivial) |
| BigQueryTableExistenceSensor | NO | `@task` with retries + BigQuery client | MEDIUM |
| RedshiftClusterSensor | NO | `@task` with retries + boto3 | LOW |

### AWS Provider (`apache-airflow-providers-amazon`)

| Operator | Colin Coverage | Prefect Equivalent | Notes |
|----------|---------------|-------------------|-------|
| S3CreateObjectOperator | YES | `S3Bucket.write_path` | Complete |
| S3CopyObjectOperator | YES | `S3Bucket.copy_object` | Complete |
| S3DeleteObjectsOperator | YES | `boto3` via AwsCredentials | Complete |
| LambdaInvokeFunctionOperator | YES | `boto3` via AwsCredentials | Complete |
| GlueJobOperator | YES | `boto3` via AwsCredentials | Complete |
| EcsRunTaskOperator | YES | ECS work pool or `boto3` | Complete |
| SageMakerTrainingOperator | YES | `boto3` via AwsCredentials | Complete |
| StepFunctionStartExecutionOperator | YES | `boto3` via AwsCredentials | Complete |
| AthenaOperator | YES | `boto3` via AwsCredentials | Complete |
| RedshiftSQLOperator | YES | `prefect-sqlalchemy` | Complete |
| SnsPublishOperator | YES | `boto3` via AwsCredentials | Complete |
| BatchOperator | NO | `prefect-aws` batch_submit | HIGH gap |
| EmrCreateJobFlowOperator | NO | `boto3` via AwsCredentials | MEDIUM gap |
| EmrAddStepsOperator | NO | `boto3` via AwsCredentials | MEDIUM gap |
| EmrServerlessStartJobRunOperator | NO | `boto3` via AwsCredentials | MEDIUM gap |
| SqsPublishOperator | NO | `boto3` via AwsCredentials | LOW gap |
| EventBridgePutEventsOperator | NO | `boto3` via AwsCredentials | LOW gap |
| DynamoDBToS3Operator | NO | `boto3` via AwsCredentials | LOW gap |
| RdsOperator | NO | `boto3` via AwsCredentials | LOW gap |

### GCP Provider (`apache-airflow-providers-google`)

| Operator | Colin Coverage | Prefect Equivalent | Notes |
|----------|---------------|-------------------|-------|
| BigQueryInsertJobOperator | YES | `BigQueryWarehouse` | Complete |
| GCSToGCSOperator | YES | `GcsBucket` operations | Complete |
| DataprocSubmitJobOperator | YES | `google.cloud.dataproc_v1` | Complete |
| GCSToLocalFilesystemOperator | YES | `GcsBucket.download_object_to_path` | Complete |
| PubSubPublishMessageOperator | YES | `google.cloud.pubsub_v1` | Complete |
| CloudDataFusionStartPipelineOperator | YES | `httpx` + GcpCredentials | Complete |
| DataflowTemplatedJobStartOperator | NO | `google.cloud.dataflow_v1beta3` | MEDIUM gap |
| DataflowStartFlexTemplateOperator | NO | `google.cloud.dataflow_v1beta3` | MEDIUM gap |
| CloudRunExecuteJobOperator | NO | `google.cloud.run_v2` | MEDIUM gap |
| VertexAICreateCustomTrainingJobOperator | NO | `prefect-gcp` VertexAI worker | MEDIUM gap |
| BigQueryCheckOperator | NO | `@task` + BigQueryWarehouse | MEDIUM gap |
| CloudFunctionsInvokeFunctionOperator | NO | `httpx` with GCP auth | LOW gap |
| CloudSqlExportInstanceOperator | NO | `google.cloud.sql_v1` | LOW gap |

### Azure Provider (`apache-airflow-providers-microsoft-azure`)

| Operator | Colin Coverage | Prefect Equivalent | Notes |
|----------|---------------|-------------------|-------|
| AzureDataFactoryRunPipelineOperator | NO | `prefect-azure` + ADF SDK | MEDIUM gap |
| LocalFilesystemToWasbOperator | NO | `prefect-azure` AzureBlob | MEDIUM gap |
| WasbDeleteBlobOperator | NO | `prefect-azure` AzureBlob | MEDIUM gap |
| AzureBatchOperator | NO | Azure SDK in `@task` | LOW gap |
| AzureContainerInstanceOperator | NO | `prefect-azure` ACI worker | LOW gap |

### Database Operators

| Operator | Colin Coverage | Prefect Equivalent | Notes |
|----------|---------------|-------------------|-------|
| PostgresOperator | YES | `prefect-sqlalchemy` | Complete |
| MySqlOperator | YES | `prefect-sqlalchemy` | Complete |
| MsSqlOperator | YES | `prefect-sqlalchemy` | Complete |
| SQLExecuteQueryOperator | YES | `prefect-sqlalchemy` | Complete |
| SnowflakeOperator | YES | `prefect-snowflake` | Complete |
| SqliteOperator | YES | `sqlite3` stdlib | Complete |
| OracleOperator | NO | `prefect-sqlalchemy` + cx_Oracle | LOW gap |
| TrinoOperator | NO | `prefect-sqlalchemy` + trino driver | LOW gap |
| PrestoOperator | NO | `prefect-sqlalchemy` + presto driver | LOW gap |
| SQLColumnCheckOperator | NO | Custom assertions in `@task` | MEDIUM gap |
| SQLTableCheckOperator | NO | Custom assertions in `@task` | MEDIUM gap |

### Container / Compute Operators

| Operator | Colin Coverage | Prefect Equivalent | Notes |
|----------|---------------|-------------------|-------|
| KubernetesPodOperator | NO | Kubernetes work pool | CRITICAL gap |
| DockerOperator | NO | Docker work pool or `docker` SDK | HIGH gap |
| SparkSubmitOperator | NO | `prefect-shell` + spark-submit | MEDIUM gap |

### External Integration Operators (Not in Colin)

| Operator | Package | Prefect Equivalent | Priority |
|----------|---------|-------------------|----------|
| DatabricksRunNowOperator | `apache-airflow-providers-databricks` | `prefect-databricks` | HIGH |
| DatabricksSubmitRunOperator | `apache-airflow-providers-databricks` | `prefect-databricks` | HIGH |
| DbtCloudRunJobOperator | `apache-airflow-providers-dbt-cloud` | `prefect-dbt` | HIGH |
| SimpleHttpOperator | `apache-airflow-providers-http` | `httpx`/`requests` in `@task` | HIGH |
| SlackAPIPostOperator | `apache-airflow-providers-slack` | `prefect-slack` | HIGH |
| SlackWebhookOperator | `apache-airflow-providers-slack` | `prefect-slack` SlackWebhook | HIGH |
| SSHOperator | `apache-airflow-providers-ssh` | `paramiko`/`fabric` in `@task` | MEDIUM |
| SFTPOperator | `apache-airflow-providers-sftp` | `paramiko`/`pysftp` in `@task` | LOW |
| PapermillOperator | `apache-airflow-providers-papermill` | `papermill.execute_notebook()` | MEDIUM |
| LivyOperator | `apache-airflow-providers-apache-spark` | `httpx` Livy REST API | LOW |

---

## Prefect Integration Package Reference

Complete mapping of Prefect integration packages relevant to this tool:

| Package | Version | Covers | Airflow Provider Equivalent |
|---------|---------|--------|-----------------------------|
| `prefect` (core) | 3.x | `@task`, `@flow`, `run_deployment()`, events | Core/standard operators |
| `prefect-aws` | Latest | S3Bucket, AwsCredentials, ECSWorker, batch_submit | `apache-airflow-providers-amazon` |
| `prefect-gcp` | Latest | GcpCredentials, GcsBucket, BigQueryWarehouse, GcpSecret, VertexAIWorker | `apache-airflow-providers-google` |
| `prefect-azure` | Latest | AzureBlobStorageCredentials, AzureContainerInstanceCredentials | `apache-airflow-providers-microsoft-azure` |
| `prefect-databricks` | Latest | DatabricksCredentials, DatabricksSubmitRun, DatabricksJobRunNow | `apache-airflow-providers-databricks` |
| `prefect-dbt` | Latest | DbtCloudCredentials, DbtCloudJob, DbtCoreOperation | `apache-airflow-providers-dbt-cloud` + community dbt |
| `prefect-snowflake` | Latest | SnowflakeConnector, SnowflakeCredentials | `apache-airflow-providers-snowflake` |
| `prefect-sqlalchemy` | Latest | SqlAlchemyConnector | `postgres`, `mysql`, `mssql`, `common-sql` |
| `prefect-kubernetes` | Latest | KubernetesWorker, KubernetesJob | `apache-airflow-providers-cncf-kubernetes` |
| `prefect-docker` | Latest | DockerWorker, DockerContainer | `apache-airflow-providers-docker` |
| `prefect-shell` | Latest | ShellOperation | `apache-airflow` BashOperator, SparkSubmit |
| `prefect-slack` | Latest | SlackWebhook, send_incoming_webhook_message | `apache-airflow-providers-slack` |
| `prefect-email` | Latest | EmailServerCredentials, email_send_message | `apache-airflow` EmailOperator |
| `prefect-ray` | Latest | RayTaskRunner | (no direct Airflow equivalent) |
| `prefect-dask` | Latest | DaskTaskRunner | (no direct Airflow equivalent) |

---

## Critical Architectural Differences: Translation Guide

These architectural mismatches must be communicated to the LLM during migration.

### Operators → Tasks (Conceptual Shift)

Airflow operators are classes with a single `execute()` method. Prefect replaces every operator with a plain Python function decorated with `@task`. The entire provider ecosystem collapses into: "install the Python library, call it inside a `@task`."

### Connections → Blocks

Airflow connections (stored in metadata DB, referenced by `conn_id` string) become Prefect blocks (Python objects stored in Prefect Cloud/server, loaded by name). The translation is:
- `postgres_default` connection → `SqlAlchemyConnector.load("postgres-default")` block
- `aws_default` connection → `AwsCredentials.load("aws-default")` block
- `google_cloud_default` connection → `GcpCredentials.load("gcp-default")` block
- `snowflake_default` → `SnowflakeConnector.load("snowflake-default")` block
- `databricks_default` → `DatabricksCredentials.load("databricks-default")` block

### Sensors → Retry-Based Tasks or Events

Airflow sensors (persistent polling workers) have two Prefect equivalents:
1. **Retry-based task:** `@task(retries=N, retry_delay_seconds=N)` with an exception raised if not ready
2. **Event-driven:** External system (Lambda, EventBridge) calls Prefect API when condition is met

Pattern 1 is simpler and covers most use cases. Pattern 2 is more resource-efficient for long waits.

### Executors → Work Pools

Airflow executors (LocalExecutor, KubernetesExecutor, CeleryExecutor) become Prefect work pools:
- `LocalExecutor` → Process work pool or subprocess
- `KubernetesExecutor` / `KubernetesPodOperator` → Kubernetes work pool
- `CeleryExecutor` → Prefect worker (workers handle concurrency natively)
- `ECSExecutor` → ECS work pool (prefect-aws)
- Docker containers → Docker work pool

### XCom → Return Values

Airflow's cross-communication mechanism (push/pull via metadata database) is replaced with direct Python return values. Tasks return data; downstream tasks receive it as function arguments. Large data should use Prefect artifacts or result storage rather than in-memory passing.

### Jinja Templating → Python Expressions

Airflow's Jinja templates (`{{ ds }}`, `{{ params.x }}`, `{{ var.value.key }}`) are replaced with Python expressions:
- `{{ ds }}` → `runtime.flow_run.scheduled_start_time.strftime("%Y-%m-%d")`
- `{{ params.x }}` → flow function parameter `x`
- `{{ var.value.key }}` → Prefect variable `Variable.get("key")` or Secret block
- `{{ conn.my_conn.host }}` → block attribute access

### Default Args → Task Decorator Defaults

Airflow's `default_args` dict (applied to all operators in a DAG) has no direct equivalent. Translate as shared `@task` decorator parameters using `functools.partial` or a custom task factory.

### DAG Scheduling → Deployment Schedules

Airflow's `schedule_interval` (cron or timedelta) becomes a Prefect deployment schedule, defined in `prefect.yaml` or via the Prefect UI/API. The flow code itself does not contain schedule information.

---

## Coverage Priority Ranking for Roadmap

Based on production frequency and gap severity:

| Rank | Gap | Priority | Effort |
|------|-----|----------|--------|
| 1 | KubernetesPodOperator | CRITICAL | Medium (architectural docs needed) |
| 2 | DatabricksRunNowOperator / Submit | HIGH | Low (prefect-databricks exists) |
| 3 | SimpleHttpOperator / HttpOperator | HIGH | Low (direct httpx pattern) |
| 4 | SlackAPIPostOperator / Webhook | HIGH | Low (prefect-slack exists) |
| 5 | DbtCloudRunJobOperator | HIGH | Low (prefect-dbt exists) |
| 6 | DockerOperator | HIGH | Medium (work pool architecture) |
| 7 | EmrCreateJobFlowOperator + AddSteps | MEDIUM | Low (boto3 pattern) |
| 8 | BatchOperator | MEDIUM | Low (prefect-aws batch_submit) |
| 9 | AzureDataFactoryRunPipelineOperator | MEDIUM | Low (prefect-azure) |
| 10 | DataflowTemplatedJobStartOperator | MEDIUM | Low (GCP SDK pattern) |
| 11 | SSHOperator | MEDIUM | Low (paramiko pattern) |
| 12 | SQLColumnCheckOperator / quality | MEDIUM | Low (assertion pattern) |
| 13 | PapermillOperator | MEDIUM | Low (direct papermill call) |
| 14 | SparkSubmitOperator | MEDIUM | Low (shell pattern) |
| 15 | Azure Blob operators | MEDIUM | Low (prefect-azure) |

---

## Airflow Version Considerations

**Airflow 2.x timeline relevant to migration:**
- 2.0 (2021): TaskFlow API introduced, providers split into separate packages
- 2.2 (2021): Dynamic Task Mapping foundation
- 2.3 (2022): Dynamic Task Mapping (`expand()`) released
- 2.4 (2022): Data-aware scheduling, dataset triggers
- 2.5 (2022): TaskGroup improvements
- 2.6 (2023): Deferrable operators widely adopted
- 2.7 (2023): `@task.branch`, `@task.sensor` decorators
- 2.8 (2024): Expanded TaskFlow API, Edge labels
- 2.9 (2024): Airflow as a dataset consumer improvements
- 2.10 (2024): Last major 2.x release before Airflow 3.0

**Target scope:** Airflow 2.0–2.10. The tool's test fixtures from Astronomer 2.9 are good but miss patterns introduced post-2.4 (dynamic task mapping, deferrable operators, dataset triggers).

**Deprecated patterns to handle:**
- `DummyOperator` → `EmptyOperator` (same translation, different import)
- `SubDagOperator` → subflows (deprecated in 2.x, removed in 3.x)
- Classic TaskFlow patterns pre-2.0 (`provide_context=True`) → not needed in Prefect

---

## Sources

- [Apache Airflow Providers Index](https://airflow.apache.org/docs/apache-airflow-providers/packages-ref.html) — verified 90+ provider packages, authoritative list (HIGH confidence)
- [Apache Airflow AWS Operators](https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/operators/index.html) — complete AWS operator list, version 9.21.0 (HIGH confidence)
- [Apache Airflow Google Operators](https://airflow.apache.org/docs/apache-airflow-providers-google/stable/operators/cloud/index.html) — 40+ GCP operators, version 19.5.0 (HIGH confidence)
- [Prefect Migrate from Airflow Guide](https://docs.prefect.io/v3/how-to-guides/migrate/airflow) — official migration patterns (HIGH confidence)
- [Prefect Integrations Index](https://docs.prefect.io/integrations/integrations) — complete prefect integration package list (HIGH confidence)
- [Prefect AWS Integration](https://docs.prefect.io/integrations/prefect-aws) — blocks and tasks (HIGH confidence)
- [Prefect GCP Integration](https://docs.prefect.io/integrations/prefect-gcp) — blocks and tasks (HIGH confidence)
- [Databricks Airflow Integration](https://airflow.apache.org/docs/apache-airflow-providers-databricks/stable/operators/index.html) — operator list (HIGH confidence)
- [2024 State of Airflow Report - Astronomer](https://www.astronomer.io/state-of-airflow/) — production usage context (MEDIUM confidence; detailed operator breakdowns not published publicly)
- [Airflow Survey 2024](https://airflow.apache.org/blog/airflow-survey-2024/) — 5,250 responses, usage context (MEDIUM confidence; operator-level data not in public summary)
- Existing Colin knowledge base (`colin/models/operators/`) — ground truth for current coverage (HIGH confidence)

---

*Stack research for: airflow-unfactor completeness milestone*
*Researched: 2026-02-26*
