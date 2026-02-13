---
layout: home
title: Home
---

# airflow-unfactor

> *"Airflow is for airports. Welcome to modern orchestration."*

**airflow-unfactor** is an MCP server that helps you migrate Apache Airflow DAGs to Prefect flows. Built with [FastMCP](https://github.com/jlowin/fastmcp).

## Features

- **Complete Migration** — Handles operators, TaskFlow, sensors, datasets, dynamic mapping, TaskGroups, trigger rules, and Jinja2 templates
- **Educational** — Comments explain *why* Prefect does it better
- **Test Generation** — Every migrated flow comes with pytest tests
- **Migration Runbooks** — DAG-specific guidance for schedule, callbacks, connections, and variables
- **AI-Assisted** — Smart analysis with external MCP enrichment from Prefect and Astronomer docs

## What Gets Converted

| Airflow Pattern | Prefect Equivalent |
|----------------|-------------------|
| `@dag` / `@task` | `@flow` / `@task` |
| `.expand()` dynamic mapping | `.map()` |
| `@task_group` | `@flow` (subflow) |
| `trigger_rule="all_done"` | `return_state=True` + state checks |
| `{{ ds }}` Jinja2 | `runtime.flow_run.scheduled_start_time` |
| `PostgresHook(conn_id="x")` | `SqlAlchemyConnector.load("x")` scaffold |
| `Variable.get("api_key")` | Prefect Secret/Variable scaffold |
| Sensors | Polling tasks + event trigger suggestions |
| Datasets/Assets | Prefect Events + automation triggers |

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

with DAG("my_etl", schedule="@daily", catchup=False) as dag:
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
    data = extract()
    result = transform(data)
    return result
```

**Plus:**
- Generated pytest tests
- Migration runbook with schedule configuration guidance
- Block/Variable scaffolds for any detected connections

## Learn More

### Getting Started
- [Installation & Setup](getting-started.md)
- [Examples](examples.md) — Real conversions from Astronomer DAGs
- [Operator Mapping](operator-mapping.md) — Complete reference

### Conversion Guides
- [Dynamic Task Mapping](conversion/dynamic-mapping.md) — `.expand()` to `.map()`
- [TaskGroups](conversion/taskgroups.md) — Groups to subflows
- [Trigger Rules](conversion/trigger-rules.md) — State-based patterns
- [Jinja2 Templates](conversion/jinja-templates.md) — Runtime context
- [Connections & Blocks](conversion/connections.md) — Credential management
- [Variables & Secrets](conversion/variables.md) — Configuration patterns

### Reference
- [Migration Playbooks](playbooks.md) — Step-by-step guides for common patterns
- [Convert Response Reference](convert-reference.md) — Complete output documentation
- [Testing](testing.md) — Verify your migrations
- [Troubleshooting](troubleshooting.md) — Common issues

---

Made with love by [Prefect](https://prefect.io)
