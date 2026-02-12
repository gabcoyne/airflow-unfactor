---
layout: home
title: Home
---

# airflow-unfactor 🛫➡️🌊

> *"Airflow is for airports. Welcome to modern orchestration."*

**airflow-unfactor** is an MCP (Model Context Protocol) server that converts Apache Airflow DAGs to Prefect flows using AI-assisted analysis.

## Why airflow-unfactor?

- **🔄 Complete Conversion** — Handles all operators, not just the easy ones
- **📚 Educational** — Comments explain *why* Prefect does it better
- **✅ Test Generation** — Every converted flow comes with pytest tests
- **🤖 AI-Assisted** — Smart analysis of complex DAG patterns
- **📦 Batch Support** — Convert entire projects at once

## Quick Start

```bash
# Install
uv pip install airflow-unfactor

# Convert a DAG
airflow-unfactor convert my_dag.py -o my_flow.py

# Or use as an MCP server with Claude/Cursor
```

## The Key Differentiator: Tests

Every conversion generates:
- The converted Prefect flow
- pytest tests that verify the migration works
- Migration verification tests (task count, no XCom references)

**Migrations you can trust.**

## Example

**Airflow DAG:**
```python
from airflow import DAG
from airflow.operators.python import PythonOperator

def extract_fn():
    return {"users": [1, 2, 3]}

def transform_fn(ti):
    data = ti.xcom_pull(task_ids="extract")
    return {"users": [u * 2 for u in data["users"]]}

with DAG("my_etl", ...) as dag:
    extract = PythonOperator(task_id="extract", python_callable=extract_fn)
    transform = PythonOperator(task_id="transform", python_callable=transform_fn)
    extract >> transform
```

**Converted Prefect Flow:**
```python
from prefect import flow, task

@task
def extract():
    return {"users": [1, 2, 3]}

@task
def transform(data):
    return {"users": [u * 2 for u in data["users"]]}

@flow(name="my_etl")
def my_etl():
    data = extract()      # Direct return, not xcom_push
    result = transform(data)  # Direct parameter, not xcom_pull
    return result
```

## Learn More

- [Getting Started](getting-started.md)
- [Examples](examples.md) (from [Astronomer example DAGs](https://github.com/astronomer/2-9-example-dags))
- [Operator Mapping](operator-mapping.md)
- [Testing](testing.md)