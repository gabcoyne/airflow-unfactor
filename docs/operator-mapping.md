---
layout: page
title: Operator Mapping
permalink: /operator-mapping/
---

# Airflow to Prefect Operator Mapping

Reference for how Airflow operators, sensors, and patterns map to Prefect equivalents during migration.

> **See also:** [Operator Coverage Matrix](operator-coverage.md) for the complete list of 35+ supported operators with their Prefect equivalents and required packages.

## Core Operators

| Airflow | Prefect | Notes |
|---------|---------|-------|
| `PythonOperator` | `@task` | Direct mapping - just decorate your function |
| `BashOperator` | `@task` + `subprocess` | Or use `prefect-shell` integration |
| `BranchPythonOperator` | Python `if/else` | Native branching - no special operator needed |
| `DummyOperator` / `EmptyOperator` | *(removed)* | Not needed - Prefect tracks dependencies automatically |
| `TriggerDagRunOperator` | `run_deployment()` | Trigger other deployments |
| `ShortCircuitOperator` | Early `return` | Just return early from the flow |

## TaskFlow API

| Airflow | Prefect | Notes |
|---------|---------|-------|
| `@task` | `@task` | Nearly identical! |
| `@task.bash` | `@task` + `subprocess` | Run bash in a task |
| `@task.python` | `@task` | Same as `@task` |
| `@dag` | `@flow` | Similar decorator pattern |

## Sensors

| Airflow | Prefect | Notes |
|---------|---------|-------|
| `FileSensor` | Polling flow or `Automation` | Schedule a flow to check |
| `S3KeySensor` | `prefect-aws` + polling | Or use S3 event notifications |
| `HttpSensor` | Polling flow or webhook | Webhook is more efficient |
| `ExternalTaskSensor` | Event-driven or `run_deployment` | Prefect events are powerful |
| `SqlSensor` | Polling flow | Query in a scheduled flow |

### Sensor Conversion Strategy

Airflow sensors block a worker while polling. In Prefect:

1. **Polling Flow** - Schedule a lightweight flow to check conditions
2. **Automations** - React to Prefect events
3. **Webhooks** - External systems push to Prefect

```python
# Airflow: Sensor blocks a worker
S3KeySensor(task_id="wait", bucket="my-bucket", key="data.csv", poke_interval=60)

# Prefect: Polling flow (runs every 5 min, doesn't block workers)
@flow(name="check-s3")
def check_s3_and_process():
    if s3_file_exists("my-bucket", "data.csv"):
        run_deployment("process-data/main")

check_s3_and_process.serve(name="main", cron="*/5 * * * *")
```

## Control Flow

| Airflow | Prefect | Notes |
|---------|---------|-------|
| `TaskGroup` | Subflow (`@flow`) | Subflows are more powerful |
| `SubDagOperator` | Subflow | First-class subflow support |
| `>>` / `<<` operators | Function calls | Implicit from call order |
| `set_upstream/downstream` | Function calls | Just call tasks in order |

## Provider Operators

### AWS

| Airflow | Prefect | Integration |
|---------|---------|-------------|
| `S3CreateObjectOperator` | `S3Bucket.write_path()` | `prefect-aws` |
| `S3DeleteObjectsOperator` | `S3Bucket` methods | `prefect-aws` |
| `LambdaInvokeFunctionOperator` | `lambda_invoke()` | `prefect-aws` |
| `GlueJobOperator` | `GlueJobBlock` | `prefect-aws` |

### GCP

| Airflow | Prefect | Integration |
|---------|---------|-------------|
| `BigQueryInsertJobOperator` | `BigQueryWarehouse` | `prefect-gcp` |
| `GCSCreateBucketOperator` | `GcsBucket` | `prefect-gcp` |
| `DataprocSubmitJobOperator` | Custom task | `prefect-gcp` |

### Database

| Airflow | Prefect | Integration |
|---------|---------|-------------|
| `PostgresOperator` | `SqlAlchemyConnector` | `prefect-sqlalchemy` |
| `MySqlOperator` | `SqlAlchemyConnector` | `prefect-sqlalchemy` |
| `SnowflakeOperator` | `SnowflakeConnector` | `prefect-snowflake` |

### Communication

| Airflow | Prefect | Integration |
|---------|---------|-------------|
| `SlackWebhookOperator` | `SlackWebhook` block | Built-in or `prefect-slack` |
| `EmailOperator` | `EmailServerCredentials` | `prefect-email` |

## Data Passing

| Airflow | Prefect | Notes |
|---------|---------|-------|
| `ti.xcom_push()` | `return value` | Just return from task |
| `ti.xcom_pull()` | Function parameter | Pass as argument |
| `Variable.get()` | `os.environ` or `Block` | Environment vars or Blocks |
| Connections | `Block` | Type-safe credential storage |

## Execution

| Airflow | Prefect | Notes |
|---------|---------|-------|
| `LocalExecutor` | Default task runner | Single process |
| `CeleryExecutor` | Work pools + workers | Distributed execution |
| `KubernetesExecutor` | Kubernetes work pool | Pod per flow (not per task!) |
| `executor_config` | `task_runner` | Per-flow configuration |

### Key Difference: Execution Model

Airflow executes each **task** in a separate process/pod.
Prefect executes each **flow** in a single process/pod, with tasks sharing memory.

This means:
- Faster data passing (in-memory, not serialized)
- Lower infrastructure overhead
- Simpler debugging

## Adding New Operator Support

The operator registry is maintained in `src/airflow_unfactor/converters/provider_mappings.py`. To add support for a new operator:

1. Add an `OperatorMapping` entry to the appropriate provider section
2. Add the operator to `get_operators_by_category()` for documentation
3. Add tests in `tests/test_provider_operators.py`
4. Run `python scripts/generate_operator_docs.py` to regenerate the coverage matrix

The [Operator Coverage Matrix](operator-coverage.md) is auto-generated from the registry and should always stay in sync.