---
layout: home
title: Home
---

# airflow-unfactor 🛫➡️🌊

> *"Airflow is for airports. Welcome to modern orchestration."*

**airflow-unfactor** is an MCP server that converts Apache Airflow DAGs to Prefect flows. Built with [FastMCP](https://github.com/jlowin/fastmcp).

## Features

- 🔄 **Complete Conversion** — Handles all operators, not just the easy ones
- 📚 **Educational** — Comments explain *why* Prefect does it better
- ✅ **Test Generation** — Every converted flow comes with pytest tests
- 🤖 **AI-Assisted** — Smart analysis of complex DAG patterns
- 📦 **Batch Support** — Convert entire projects at once

## Quick Start

### 1. Install

```bash
uv pip install airflow-unfactor
```

### 2. Add to Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "airflow-unfactor": {
      "command": "uvx",
      "args": ["airflow-unfactor"]
    }
  }
}
```

### 3. Convert!

Ask Claude:
> "Convert the DAG in `dags/my_etl.py` to a Prefect flow"

## The Key Differentiator: Tests

Every conversion generates:
- The converted Prefect flow
- pytest tests that verify the migration works
- Migration verification (task count, no XCom references)

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

# ✨ Prefect Advantage: Direct Data Passing
# No XCom - data flows in-memory between tasks.

@task
def extract():
    return {"users": [1, 2, 3]}

@task
def transform(data):
    return {"users": [u * 2 for u in data["users"]]}

@flow(name="my_etl")
def my_etl():
    data = extract()      # Direct return
    result = transform(data)  # Direct parameter
    return result
```

## Learn More

- [Getting Started](getting-started.md) — Installation and setup
- [Examples](examples.md) — Real conversions from [Astronomer DAGs](https://github.com/astronomer/2-9-example-dags)
- [Operator Mapping](operator-mapping.md) — Complete Airflow → Prefect reference
- [Testing](testing.md) — How to verify your migrations

---

Made with 💙 by [Prefect](https://prefect.io)