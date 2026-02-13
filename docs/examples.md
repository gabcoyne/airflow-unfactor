---
layout: page
title: Examples
permalink: /examples/
---

# Migration Examples

Real-world examples of migrating Airflow DAGs to Prefect flows. Based on [Astronomer's 2.9 Example DAGs](https://github.com/astronomer/2-9-example-dags).

## TaskFlow with @task.bash

### Original Airflow DAG
```python
from airflow.decorators import dag, task

@dag(start_date=None, schedule=None, catchup=False)
def toy_taskflow_bash():
    @task
    def upstream_task():
        return {"names": ["Trevor", "Grant"], "dogs": [1, 0]}

    @task.bash
    def bash_task(dog_owner_data):
        # Returns bash command to execute
        return f'echo "Someone needs a dog!"'

    bash_task(dog_owner_data=upstream_task())

toy_taskflow_bash()
```

### Converted Prefect Flow
```python
from prefect import flow, task
import subprocess

# ✨ Prefect Advantage: TaskFlow API works similarly!
# Prefect's @task decorator is inspired by Airflow's TaskFlow.
# The main difference: no @task.bash - just use subprocess.

@task
def upstream_task():
    return {"names": ["Trevor", "Grant"], "dogs": [1, 0]}

@task
def bash_task(dog_owner_data):
    """Execute bash command based on data."""
    # In Prefect, just run bash directly - no special decorator needed
    cmd = f'echo "Someone needs a dog!"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout

@flow(name="toy_taskflow_bash")
def toy_taskflow_bash():
    data = upstream_task()
    result = bash_task(data)
    return result
```

---

## XCom Patterns

### Original Airflow DAG
```python
from airflow import DAG
from airflow.operators.python import PythonOperator

def push_small_xcom(ti):
    ti.xcom_push(key="small_data", value={"count": 42})

def pull_xcom(ti):
    data = ti.xcom_pull(task_ids="push_task", key="small_data")
    print(f"Got: {data}")

with DAG("xcom_example", ...) as dag:
    push_task = PythonOperator(task_id="push_task", python_callable=push_small_xcom)
    pull_task = PythonOperator(task_id="pull_task", python_callable=pull_xcom)
    push_task >> pull_task
```

### Converted Prefect Flow
```python
from prefect import flow, task

# ✨ Prefect Advantage: Direct Data Passing
# No more ti.xcom_push() / ti.xcom_pull()!
# Data flows in-memory between tasks - faster, simpler, no size limits.

@task
def push_task():
    """Just return the data - no xcom_push needed."""
    return {"count": 42}

@task
def pull_task(data):
    """Receive data as a parameter - no xcom_pull needed."""
    print(f"Got: {data}")
    return data

@flow(name="xcom_example")
def xcom_example():
    data = push_task()  # Returns directly
    result = pull_task(data)  # Receives as parameter
    return result
```

---

## Complex DAG Structure

### Original Airflow DAG (simplified)
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

with DAG("complex_dag", ...) as dag:
    start = PythonOperator(task_id="start", python_callable=lambda: "start")

    with TaskGroup("processing") as processing_group:
        task_a = PythonOperator(task_id="task_a", python_callable=lambda: "a")
        task_b = PythonOperator(task_id="task_b", python_callable=lambda: "b")
        task_a >> task_b

    end = PythonOperator(task_id="end", python_callable=lambda: "end")

    start >> processing_group >> end
```

### Converted Prefect Flow
```python
from prefect import flow, task

# ✨ Prefect Advantage: Subflows replace TaskGroups
# Subflows are more powerful - they can be deployed independently,
# have their own retry logic, and can be reused across flows.

@task
def start():
    return "start"

@task
def task_a():
    return "a"

@task
def task_b(upstream):
    return "b"

@flow(name="processing")
def processing():
    """Subflow replacing TaskGroup."""
    a_result = task_a()
    b_result = task_b(a_result)
    return b_result

@task
def end(upstream):
    return "end"

@flow(name="complex_dag")
def complex_dag():
    s = start()
    p = processing()  # Subflow call
    e = end(p)
    return e
```

---

## Data Engineering: ETL Pipeline

### Original Airflow DAG
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator

with DAG("earnings_report", ...) as dag:
    extract = PythonOperator(task_id="extract", python_callable=extract_data)
    transform = PythonOperator(task_id="transform", python_callable=transform_data)
    load = SnowflakeOperator(task_id="load", sql="INSERT INTO ...")
    notify = PythonOperator(task_id="notify", python_callable=send_slack)

    extract >> transform >> load >> notify
```

### Converted Prefect Flow
```python
from prefect import flow, task
from prefect_snowflake import SnowflakeConnector
from prefect.blocks.notifications import SlackWebhook

# ✨ Prefect Advantage: Blocks replace Hooks/Connections
# Blocks are typed, versioned, and can be managed in the UI.

@task
def extract_data():
    # Your extract logic
    return raw_data

@task
def transform_data(data):
    # Your transform logic
    return transformed_data

@task
def load_to_snowflake(data):
    """Load data using Snowflake Block."""
    connector = SnowflakeConnector.load("my-snowflake")
    connector.execute("INSERT INTO ...", data=data)

@task
def send_notification():
    """Send Slack notification using Block."""
    slack = SlackWebhook.load("my-slack")
    slack.notify("🚀 Earnings report complete!")

@flow(name="earnings_report")
def earnings_report():
    raw = extract_data()
    transformed = transform_data(raw)
    load_to_snowflake(transformed)
    send_notification()
```

---

## More Examples

See the [tests/fixtures/astronomer](https://github.com/prefect/airflow-unfactor/tree/main/tests/fixtures/astronomer) directory for more migration examples from production-style DAGs.