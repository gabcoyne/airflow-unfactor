---
name: Airflow to Prefect Concept Mappings
colin:
  output:
    format: json
---

{% section dag-to-flow %}
## id
dag-to-flow

## airflow
### name
DAG (Directed Acyclic Graph)
### description
Top-level workflow container. Defined with `DAG()` context manager or `@dag` decorator. Contains tasks and their dependencies.
### module
airflow.models.dag

## prefect
### name
Flow
### description
Top-level workflow container. Defined with `@flow` decorator on a Python function.
### package
prefect
### import_statement
from prefect import flow

## rules
- Replace `with DAG(...) as dag:` context manager with `@flow` decorator
- DAG `dag_id` becomes the flow function name or `name=` parameter
- `schedule_interval` / `schedule` moves to deployment configuration in `prefect.yaml`
- `default_args` like `retries`, `retry_delay` become `@task` decorator defaults
- `catchup=False` has no direct equivalent; Prefect deployments run from creation time by default
- `tags` map directly to `@flow(tags=[...])`
- `params` become flow function parameters with type annotations

## example
### before
```python
from airflow import DAG
from datetime import datetime

with DAG(
    dag_id="etl_pipeline",
    schedule_interval="0 6 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["etl"],
) as dag:
    ...
```
### after
```python
from prefect import flow

@flow(name="etl-pipeline", tags=["etl"])
def etl_pipeline():
    ...
```

## related
- operator-to-task
- schedule-cron
{% endsection %}

{% section operator-to-task %}
## id
operator-to-task

## airflow
### name
Operator
### description
Base unit of work in a DAG. Each operator type wraps specific logic (Python callable, Bash command, SQL query, etc.).
### module
airflow.models.baseoperator

## prefect
### name
Task
### description
Base unit of work in a flow. Defined with `@task` decorator on a Python function.
### package
prefect
### import_statement
from prefect import task

## rules
- Replace each operator instantiation with a `@task`-decorated function
- The operator's `task_id` becomes the function name
- `python_callable` (PythonOperator) becomes the function body
- `op_args` / `op_kwargs` become function parameters
- `retries` maps to `@task(retries=N)`
- `retry_delay` maps to `@task(retry_delay_seconds=N)`
- `trigger_rule` requires state inspection (see trigger-rule pattern)
- `pool` maps to work pool / task concurrency limits

## example
### before
```python
task1 = PythonOperator(
    task_id="extract",
    python_callable=extract_data,
    op_kwargs={"source": "api"},
    retries=3,
)
```
### after
```python
@task(retries=3)
def extract(source: str):
    return extract_data(source=source)
```

## related
- dag-to-flow
- xcom-to-return-values
{% endsection %}

{% section xcom-to-return-values %}
## id
xcom-to-return-values

## airflow
### name
XCom
### description
Cross-communication mechanism for passing data between tasks. Tasks push/pull via `ti.xcom_push()` / `ti.xcom_pull()`.
### module
airflow.models.xcom

## prefect
### name
Task return values
### description
Tasks return values directly. Downstream tasks receive them as function arguments.
### package
prefect
### import_statement
from prefect import task, flow

## rules
- Replace `ti.xcom_push(key, value)` with `return value` from the task
- Replace `ti.xcom_pull(task_ids='...')` with passing the upstream task's return value as a parameter
- Multiple return values: return a dict or tuple
- For large data, use Prefect artifacts or result serializers instead of returning directly
- Remove all `provide_context=True` arguments (no longer needed)

## example
### before
```python
def extract(**context):
    data = fetch_api()
    context['ti'].xcom_push(key='data', value=data)

def transform(**context):
    data = context['ti'].xcom_pull(task_ids='extract', key='data')
    return process(data)
```
### after
```python
@task
def extract():
    return fetch_api()

@task
def transform(data):
    return process(data)

@flow
def pipeline():
    data = extract()
    result = transform(data)
```

## gotchas
- Prefect task results must be serializable
- Large datasets should use result storage, not return values
- XCom with custom keys: restructure to use multiple return values or a dict
{% endsection %}

{% section connection-to-block %}
## id
connection-to-block

## airflow
### name
Connection
### description
Stores credentials and connection parameters for external systems. Managed via Airflow UI/CLI/env.
### module
airflow.models.connection

## prefect
### name
Block
### description
Typed configuration objects storing credentials and connection parameters. Created via UI, CLI, or code.
### package
prefect
### import_statement
from prefect.blocks.core import Block

## rules
- Each Airflow connection type maps to a specific Prefect block type
- Create blocks via `prefect block register` then configure in UI, or create in code
- Replace `BaseHook.get_connection(conn_id)` with `Block.load("block-name")`
- Connection extras map to block configuration fields
- See connections.md for specific connection-to-block mappings

## example
### before
```python
from airflow.hooks.base import BaseHook
conn = BaseHook.get_connection("postgres_default")
uri = conn.get_uri()
```
### after
```python
from prefect_sqlalchemy import SqlAlchemyConnector
connector = SqlAlchemyConnector.load("postgres-default")
```

## related
- hook-to-integration-client
{% endsection %}

{% section variable-to-prefect-variable %}
## id
variable-to-prefect-variable

## airflow
### name
Variable
### description
Key-value store for DAG configuration. Accessed via `Variable.get()`.
### module
airflow.models.variable

## prefect
### name
Variable
### description
Key-value store for flow configuration. Accessed via `variables.get()`.
### package
prefect
### import_statement
from prefect.variables import Variable

## rules
- Replace `Variable.get("key")` with `Variable.get("key")` (similar API)
- Replace `Variable.get("key", default)` with `Variable.get("key", default=default)`
- JSON variables: `Variable.get("key", deserialize_json=True)` becomes `json.loads(Variable.get("key"))`
- Set variables via CLI: `prefect variable set key=value`
- Consider using Prefect blocks for structured configuration instead of flat variables

## example
### before
```python
from airflow.models import Variable
api_url = Variable.get("api_url")
config = Variable.get("config", deserialize_json=True)
```
### after
```python
from prefect.variables import Variable
api_url = Variable.get("api_url")
config = json.loads(Variable.get("config"))
```
{% endsection %}

{% section sensor-to-polling %}
## id
sensor-to-polling

## airflow
### name
Sensor
### description
Operators that wait for a condition to be met before proceeding. Supports `poke` and `reschedule` modes.
### module
airflow.sensors.base

## prefect
### name
Polling task or event trigger
### description
Use a task with retry/polling logic, or Prefect events and automations for event-driven patterns.
### package
prefect
### import_statement
from prefect import task

## rules
- Simple sensors: convert to a `@task` with a polling loop and `time.sleep()`
- `poke_interval` becomes the sleep duration in the polling loop
- `timeout` becomes task timeout or max retries
- `mode='reschedule'` sensors: use `@task(retries=N, retry_delay_seconds=M)`
- For file sensors: use `pathlib.Path.exists()` in a polling task
- For external trigger sensors: use Prefect events + automations
- S3/GCS sensors: use integration packages with polling

## example
### before
```python
wait_for_file = FileSensor(
    task_id="wait_for_file",
    filepath="/data/input.csv",
    poke_interval=60,
    timeout=3600,
)
```
### after
```python
@task(retries=60, retry_delay_seconds=60)
def wait_for_file(filepath: str):
    from pathlib import Path
    if not Path(filepath).exists():
        raise Exception(f"File {filepath} not found, retrying...")
    return filepath
```
{% endsection %}

{% section dataset-to-automation %}
## id
dataset-to-automation

## airflow
### name
Dataset
### description
Represents a logical dataset that triggers downstream DAGs when updated.
### module
airflow.datasets

## prefect
### name
Automation / Event
### description
Use Prefect events and automations for data-driven triggering between flows.
### package
prefect
### import_statement
from prefect.events import emit_event

## rules
- Replace `Dataset("s3://bucket/path")` with Prefect event emission
- Producer DAG: emit an event when data is ready using `emit_event()`
- Consumer DAG: create an automation that triggers the flow on the event
- Alternative: use `run_deployment()` to directly trigger downstream flows

## example
### before
```python
# Producer
dag = DAG(schedule=[Dataset("s3://bucket/output")])

# Consumer
dag = DAG(schedule=[Dataset("s3://bucket/output")])
```
### after
```python
# Producer flow
@flow
def producer():
    write_data()
    emit_event(event="data.ready", resource={"prefect.resource.id": "s3://bucket/output"})

# Automation triggers consumer flow on "data.ready" event
```
{% endsection %}

{% section hook-to-integration-client %}
## id
hook-to-integration-client

## airflow
### name
Hook
### description
Interface to external systems (databases, APIs, cloud services). Wraps connections with typed clients.
### module
airflow.hooks.base

## prefect
### name
Integration block/client
### description
Prefect integration packages provide typed blocks that wrap external system clients.
### package
varies by integration
### import_statement
varies by integration

## rules
- Replace `SomeHook(conn_id)` with the corresponding Prefect integration block
- Hook methods map to block methods (often similar names)
- `get_conn()` becomes loading the block and accessing its client
- Common mappings: PostgresHook → SqlAlchemyConnector, S3Hook → S3Bucket, GCSHook → GcsBucket

## example
### before
```python
from airflow.providers.postgres.hooks.postgres import PostgresHook
hook = PostgresHook(postgres_conn_id="my_db")
records = hook.get_records("SELECT * FROM table")
```
### after
```python
from prefect_sqlalchemy import SqlAlchemyConnector
connector = SqlAlchemyConnector.load("my-db")
with connector.get_connection() as conn:
    records = conn.execute("SELECT * FROM table").fetchall()
```
{% endsection %}

{% section pool-to-work-pool %}
## id
pool-to-work-pool

## airflow
### name
Pool
### description
Limits concurrent task execution across DAGs. Tasks assigned to a pool share its slot limit.
### module
airflow.models.pool

## prefect
### name
Work pool / concurrency limit
### description
Work pools manage infrastructure for flow runs. Concurrency limits control parallel execution.
### package
prefect
### import_statement
from prefect import task

## rules
- Airflow pools limiting concurrency: use `@task(tags=["pool-name"])` with tag-based concurrency limits
- Set concurrency limits via CLI: `prefect concurrency-limit create pool-name N`
- For infrastructure-level pooling: use work pools with concurrency settings
- `pool_slots` parameter: use task-level concurrency via tags

## example
### before
```python
task = PythonOperator(
    task_id="api_call",
    pool="api_pool",
    pool_slots=1,
    python_callable=call_api,
)
```
### after
```python
@task(tags=["api-pool"])
def api_call():
    return call_api()

# CLI: prefect concurrency-limit create api-pool 5
```
{% endsection %}

{% section callback-to-state-hook %}
## id
callback-to-state-hook

## airflow
### name
Callbacks
### description
Functions called on task/DAG state changes: `on_success_callback`, `on_failure_callback`, `on_retry_callback`.
### module
airflow.models.baseoperator

## prefect
### name
State change hooks
### description
Functions triggered on flow/task state transitions. Defined as `on_completion`, `on_failure`, `on_cancellation`.
### package
prefect
### import_statement
from prefect import flow, task

## rules
- `on_success_callback` → `on_completion` (check state is Completed)
- `on_failure_callback` → `on_failure`
- `on_retry_callback` → no direct equivalent; use retry hooks or custom logic
- DAG-level callbacks → `@flow(on_failure=[...], on_completion=[...])`
- Task-level callbacks → `@task(on_failure=[...], on_completion=[...])`
- For complex alerting: use Prefect automations instead of inline callbacks

## example
### before
```python
def alert_on_failure(context):
    send_slack(f"Task {context['task_instance'].task_id} failed")

task = PythonOperator(
    task_id="etl",
    on_failure_callback=alert_on_failure,
)
```
### after
```python
def alert_on_failure(flow, flow_run, state):
    send_slack(f"Flow {flow_run.name} failed")

@flow(on_failure=[alert_on_failure])
def etl():
    ...
```
{% endsection %}

{% section schedule-cron %}
## id
schedule-cron

## airflow
### name
Schedule (cron)
### description
Cron expressions or timedelta for DAG scheduling via `schedule_interval` or `schedule`.
### module
airflow.models.dag

## prefect
### name
Deployment schedule
### description
Schedules defined in deployment configuration (`prefect.yaml` or `flow.deploy()`).
### package
prefect
### import_statement
from prefect import flow

## rules
- `schedule_interval="0 6 * * *"` → `cron: "0 6 * * *"` in `prefect.yaml` schedule
- `schedule_interval=timedelta(hours=1)` → `interval: 3600` in deployment
- `schedule_interval="@daily"` → `cron: "0 0 * * *"`
- Schedules are NOT on the flow itself — they live in deployment config
- Multiple schedules per deployment are supported

## example
### before
```python
dag = DAG(
    dag_id="hourly_etl",
    schedule_interval="0 * * * *",
)
```
### after
```yaml
# prefect.yaml
deployments:
  - name: hourly-etl
    flow: flows/etl.py:hourly_etl
    schedule:
      cron: "0 * * * *"
```
{% endsection %}

{% section schedule-timetable %}
## id
schedule-timetable

## airflow
### name
Timetable
### description
Custom scheduling logic beyond cron. Allows business-day-only schedules, event-driven triggers, etc.
### module
airflow.timetables.base

## prefect
### name
RRule or custom schedule
### description
Use RRule schedules for complex patterns, or automations for event-driven triggering.
### package
prefect
### import_statement
from prefect.client.schemas.schedules import RRuleSchedule

## rules
- Simple timetables (business days): use RRule with `BYDAY`
- Complex custom timetables: use Prefect automations for event-driven triggering
- Data-dependent schedules: use `emit_event()` + automations
- AfterDatasetChanged timetable: convert to event-based automation

## example
### before
```python
from airflow.timetables.trigger import CronTriggerTimetable
dag = DAG(
    timetable=CronTriggerTimetable("0 9 * * MON-FRI"),
)
```
### after
```yaml
# prefect.yaml
deployments:
  - name: business-days
    schedule:
      rrule: "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9"
```
{% endsection %}
