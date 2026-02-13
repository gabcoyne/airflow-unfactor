---
layout: page
title: Migration Playbooks
permalink: /playbooks/
---

# Migration Playbooks

Step-by-step guides for common Airflow → Prefect migration patterns. Each playbook covers a specific scenario with concrete actions.

## Playbook: Schedule Migration

**When to use:** Your DAG has a `schedule_interval` or `schedule` parameter.

### Step 1: Identify the Schedule

```python
# Airflow
with DAG("my_dag", schedule_interval="0 6 * * *") as dag:  # Airflow 2.x
with DAG("my_dag", schedule="@daily") as dag:              # Airflow 2.4+
```

### Step 2: Choose Prefect Approach

| Approach | When to Use |
|----------|-------------|
| `.serve(cron="...")` | Local development, simple deployments |
| Deployment YAML | Production, version-controlled schedules |
| Prefect UI | Ad-hoc schedule changes |

### Step 3: Implement

**Option A: `.serve()` for simple deployments**
```python
@flow(name="my_dag")
def my_dag():
    ...

if __name__ == "__main__":
    my_dag.serve(name="main", cron="0 6 * * *")
```

**Option B: Deployment YAML**
```yaml
# prefect.yaml
deployments:
  - name: my-dag
    entrypoint: flows/my_dag.py:my_dag
    schedule:
      cron: "0 6 * * *"
      timezone: "America/New_York"
```

### Step 4: Handle Catchup

```python
# Airflow: catchup=False skips historical runs
with DAG("my_dag", catchup=False) as dag:

# Prefect: Deployments skip missed runs by default
# No action needed - this is the default behavior
```

### Step 5: Verify

```bash
# Deploy and check
prefect deploy --name my-dag
prefect deployment ls
```

---

## Playbook: Sensor to Event-Driven

**When to use:** Your DAG uses sensors (FileSensor, S3KeySensor, HttpSensor, etc.)

### Step 1: Identify Sensor Type

| Airflow Sensor | Prefect Approach |
|---------------|------------------|
| FileSensor, S3KeySensor | Polling flow or cloud events |
| HttpSensor | Webhook or polling |
| ExternalTaskSensor | Event-driven automations |
| SqlSensor | Polling flow |

### Step 2: Choose Pattern

**Pattern A: Polling Flow (simplest)**
```python
from prefect import flow
from prefect.deployments import run_deployment

@flow
def check_s3_and_trigger():
    if file_exists("s3://bucket/data.csv"):
        run_deployment("process-data/main")
    # If file doesn't exist, flow completes - runs again on schedule

# Schedule to check every 5 minutes
check_s3_and_trigger.serve(name="sensor", cron="*/5 * * * *")
```

**Pattern B: Event-Driven (production)**
```python
# 1. Emit event when file arrives (external system or Lambda)
from prefect.events import emit_event

def on_s3_file_uploaded(key: str):
    emit_event("s3-file-arrived", resource={"key": key})

# 2. Configure automation in Prefect UI or YAML
# Triggers process-data deployment when event fires
```

**Automation YAML:**
```yaml
triggers:
  - type: event
    match:
      prefect.resource.name: s3-file-arrived
    actions:
      - type: run-deployment
        deployment: process-data/main
```

### Step 3: Remove Blocking Behavior

```python
# Airflow: Sensor blocks a worker while waiting
FileSensor(task_id="wait", filepath="/data/file.csv", poke_interval=60)

# Prefect: No blocking - polling flow runs and exits
# Next check happens on next scheduled run
```

### Step 4: Verify

```bash
# Test polling flow
prefect flow-run create --flow check-s3-and-trigger

# Check automations
prefect automation ls
```

---

## Playbook: Dataset/Asset Migration

**When to use:** Your DAG uses `Dataset` (Airflow 2.4+) or `Asset` (Airflow 2.10+) for data-aware scheduling.

### Step 1: Identify Dataset Patterns

```python
# Airflow
from airflow.datasets import Dataset

orders_dataset = Dataset("s3://bucket/orders")

@dag(schedule=[orders_dataset])  # Triggered when orders_dataset updates
def process_orders():
    ...

@task(outlets=[orders_dataset])  # Produces orders_dataset
def write_orders():
    ...
```

### Step 2: Map to Prefect Events

| Airflow | Prefect |
|---------|---------|
| `Dataset(uri)` | Event with resource |
| `@dag(schedule=[dataset])` | Event trigger automation |
| `@task(outlets=[dataset])` | `emit_event()` call |

### Step 3: Implement Event Emission

```python
from prefect import flow, task
from prefect.events import emit_event

@task
def write_orders(data):
    # Write to S3...
    s3.put_object(...)

    # Emit event (replaces Dataset outlet)
    emit_event(
        "orders-updated",
        resource={"uri": "s3://bucket/orders", "rows": len(data)}
    )

@flow
def orders_etl():
    data = extract()
    write_orders(data)
```

### Step 4: Configure Event Trigger

```yaml
# prefect.yaml
deployments:
  - name: process-orders
    entrypoint: flows/process_orders.py:process_orders
    triggers:
      - type: event
        match:
          prefect.resource.name: orders-updated
```

### Step 5: Verify

```bash
# Trigger manually
python -c "from prefect.events import emit_event; emit_event('orders-updated', resource={'uri': 's3://bucket/orders'})"

# Check event in UI
# Verify downstream deployment triggered
```

---

## Playbook: Callback to Automation

**When to use:** Your DAG uses `on_success_callback`, `on_failure_callback`, `sla_miss_callback`.

### Step 1: Identify Callbacks

```python
# Airflow
def alert_on_failure(context):
    send_slack(f"DAG {context['dag'].dag_id} failed")

with DAG("my_dag", on_failure_callback=alert_on_failure):
    ...
```

### Step 2: Choose Prefect Pattern

| Callback Type | Prefect Pattern |
|--------------|-----------------|
| `on_failure_callback` | State hooks or Automation |
| `on_success_callback` | State hooks or Automation |
| `sla_miss_callback` | Automation with time trigger |

### Step 3: Implement with Hooks (Simple)

```python
from prefect import flow
from prefect.blocks.notifications import SlackWebhook

def notify_failure(flow, flow_run, state):
    slack = SlackWebhook.load("alerts")
    slack.notify(f"Flow {flow.name} failed: {state.message}")

def notify_success(flow, flow_run, state):
    slack = SlackWebhook.load("alerts")
    slack.notify(f"Flow {flow.name} completed successfully")

@flow(
    on_failure=[notify_failure],
    on_completion=[notify_success]  # Runs on any completion
)
def my_dag():
    ...
```

### Step 4: Implement with Automations (Production)

For centralized alerting across all flows:

**Via Prefect UI:**
1. Navigate to Automations
2. Create new automation
3. Trigger: "Flow run enters state Failed"
4. Action: "Send notification" → Select Slack block

**Via CLI:**
```bash
prefect automation create \
  --name "Alert on failure" \
  --trigger '{"type": "event", "match": {"prefect.resource.id": "prefect.flow-run.*"}, "expect": ["prefect.flow-run.Failed"]}' \
  --action '{"type": "send-notification", "block_document_id": "your-slack-block-id"}'
```

### Step 5: Migrate SLA Callbacks

```python
# Airflow
with DAG("my_dag", sla_miss_callback=sla_alert):
    task = PythonOperator(..., sla=timedelta(hours=2))

# Prefect: Use automation with time-based trigger
# Create automation that fires if flow hasn't completed within expected time
```

**Automation for SLA:**
```yaml
name: SLA Alert
trigger:
  type: compound
  require: all
  triggers:
    - type: event
      match:
        prefect.resource.name: my-dag
      expect:
        - prefect.flow-run.Running
      within: 7200  # 2 hours in seconds
    - type: event
      match:
        prefect.resource.name: my-dag
      expect:
        - prefect.flow-run.Completed
      posture: Reactive
      threshold: 0
actions:
  - type: send-notification
    block_document_id: slack-alerts
```

---

## Playbook: Connection to Block Migration

**When to use:** Your DAG uses Airflow Connections via Hooks.

### Step 1: List Connections Used

```python
# Airflow
from airflow.providers.postgres.hooks.postgres import PostgresHook

hook = PostgresHook(postgres_conn_id="my_postgres")
```

### Step 2: Create Prefect Block

**Via UI:**
1. Blocks → Add Block → SqlAlchemyConnector
2. Configure connection details
3. Save as "my-postgres"

**Via CLI:**
```python
from prefect_sqlalchemy import SqlAlchemyConnector, ConnectionComponents

connector = SqlAlchemyConnector(
    connection_info=ConnectionComponents(
        driver="postgresql+psycopg2",
        host="localhost",
        port=5432,
        database="mydb",
        username="user",
        password="secret"  # Or use Secret reference
    )
)
connector.save("my-postgres", overwrite=True)
```

### Step 3: Update Code

```python
from prefect_sqlalchemy import SqlAlchemyConnector

@task
def query_database():
    connector = SqlAlchemyConnector.load("my-postgres")
    return connector.fetch_all("SELECT * FROM users")
```

### Step 4: Install Package

```bash
pip install prefect-sqlalchemy
prefect block register -m prefect_sqlalchemy
```

### Step 5: Test Connectivity

```python
# Quick test
connector = SqlAlchemyConnector.load("my-postgres")
result = connector.fetch_one("SELECT 1")
print(f"Connection works: {result}")
```

---

## Quick Reference: Common Patterns

| Airflow | Prefect | Playbook |
|---------|---------|----------|
| `schedule_interval` | `.serve(cron=...)` or deployment | [Schedule](#playbook-schedule-migration) |
| `FileSensor` | Polling flow | [Sensor](#playbook-sensor-to-event-driven) |
| `Dataset` outlet | `emit_event()` | [Dataset](#playbook-datasetasset-migration) |
| `Dataset` schedule | Event trigger | [Dataset](#playbook-datasetasset-migration) |
| `on_failure_callback` | `@flow(on_failure=[...])` | [Callback](#playbook-callback-to-automation) |
| `PostgresHook` | `SqlAlchemyConnector` | [Connection](#playbook-connection-to-block-migration) |
| `Variable.get("secret")` | `Secret.load("x")` | [Variables](conversion/variables.md) |

## See Also

- [Convert Response Reference](convert-reference.md) — Understanding tool output
- [Operator Mapping](operator-mapping.md) — Complete operator reference
- [Troubleshooting](troubleshooting.md) — Common issues
