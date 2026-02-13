---
layout: page
title: Jinja2 Templates
permalink: /conversion/jinja-templates/
---

# Jinja2 Templates

Convert Airflow Jinja2 template variables to Prefect runtime context.

## What We Detect

| Pattern | Description |
|---------|-------------|
| `{{ ds }}` | Execution date as YYYY-MM-DD |
| `{{ ds_nodash }}` | Execution date as YYYYMMDD |
| `{{ ts }}` | Execution timestamp (ISO format) |
| `{{ ts_nodash }}` | Timestamp without dashes |
| `{{ execution_date }}` | Full datetime object |
| `{{ data_interval_start }}` | Start of data interval |
| `{{ data_interval_end }}` | End of data interval |
| `{{ params.name }}` | DAG run parameters |
| `{{ macros.ds_add(ds, N) }}` | Date arithmetic |
| `{{ prev_ds }}` / `{{ next_ds }}` | Previous/next execution date |

## What We Generate

### Date Variables

```python
# Airflow
bash_command = "echo Processing data for {{ ds }}"

# Prefect (converted)
from prefect import runtime

@task
def run_command():
    ds = runtime.flow_run.scheduled_start_time.strftime('%Y-%m-%d')
    cmd = f"echo Processing data for {ds}"
    subprocess.run(cmd, shell=True, check=True)
```

### Timestamp Variables

```python
# Airflow
file_path = "s3://bucket/data_{{ ts_nodash }}.parquet"

# Prefect (converted)
from prefect import runtime

@task
def process_file():
    ts_nodash = runtime.flow_run.scheduled_start_time.strftime('%Y%m%dT%H%M%S')
    file_path = f"s3://bucket/data_{ts_nodash}.parquet"
    # ...
```

### Parameters

```python
# Airflow
@task
def process(env="{{ params.environment }}"):
    return f"Processing in {env}"

# Prefect (converted)
@task
def process(environment: str):  # Parameter becomes function argument
    return f"Processing in {environment}"

@flow
def my_flow(environment: str = "prod"):  # Default at flow level
    process(environment)
```

### Date Arithmetic

```python
# Airflow
yesterday = "{{ macros.ds_add(ds, -1) }}"
next_week = "{{ macros.ds_add(ds, 7) }}"

# Prefect (converted)
from datetime import timedelta
from prefect import runtime

@task
def compute_dates():
    scheduled = runtime.flow_run.scheduled_start_time
    yesterday = (scheduled - timedelta(days=1)).strftime('%Y-%m-%d')
    next_week = (scheduled + timedelta(days=7)).strftime('%Y-%m-%d')
    return {"yesterday": yesterday, "next_week": next_week}
```

## Complete Mapping Table

| Airflow Template | Prefect Equivalent |
|-----------------|-------------------|
| `{{ ds }}` | `runtime.flow_run.scheduled_start_time.strftime('%Y-%m-%d')` |
| `{{ ds_nodash }}` | `.strftime('%Y%m%d')` |
| `{{ ts }}` | `.isoformat()` |
| `{{ ts_nodash }}` | `.strftime('%Y%m%dT%H%M%S')` |
| `{{ ts_nodash_with_tz }}` | `.strftime('%Y%m%dT%H%M%S%z')` |
| `{{ execution_date }}` | `runtime.flow_run.scheduled_start_time` |
| `{{ data_interval_start }}` | `runtime.flow_run.scheduled_start_time` |
| `{{ data_interval_end }}` | Computed from schedule |
| `{{ prev_ds }}` | `(scheduled - timedelta(days=1)).strftime('%Y-%m-%d')` |
| `{{ next_ds }}` | `(scheduled + timedelta(days=1)).strftime('%Y-%m-%d')` |
| `{{ params.x }}` | Flow parameter `x` |
| `{{ macros.ds_add(ds, N) }}` | `(scheduled + timedelta(days=N)).strftime('%Y-%m-%d')` |
| `{{ macros.ds_format(ds, fmt) }}` | `.strftime(fmt)` |

## Known Deltas

| Airflow Feature | Prefect Behavior | Notes |
|-----------------|------------------|-------|
| Runtime templating | Build-time f-strings | Templates resolved when task runs |
| `data_interval_end` | Needs schedule info | Compute based on schedule interval |
| `{{ var.value.name }}` | `Variable.get()` | See Variables conversion |
| `{{ conn.my_conn }}` | Block.load() | See Connections conversion |

## Manual Follow-up

1. **Review f-string escaping** — If your templates contain literal braces, update to `{{` or `}}` in f-strings.

2. **Check timezone handling** — Prefect uses UTC by default. If your DAG used local time, adjust accordingly.

3. **Verify schedule alignment** — `scheduled_start_time` is when the flow was scheduled, not when it actually runs.

## Example: Data Pipeline with Date Partitioning

```python
# Airflow
@task
def extract():
    return f"s3://raw/{{ ds }}/data.json"

@task.bash
def transform(path):
    return f"spark-submit transform.py --input {path} --output s3://processed/{{ ds }}/"

# Prefect (converted)
from prefect import flow, task, runtime
from datetime import timedelta
import subprocess

@task
def extract():
    ds = runtime.flow_run.scheduled_start_time.strftime('%Y-%m-%d')
    return f"s3://raw/{ds}/data.json"

@task
def transform(path: str):
    ds = runtime.flow_run.scheduled_start_time.strftime('%Y-%m-%d')
    cmd = f"spark-submit transform.py --input {path} --output s3://processed/{ds}/"
    subprocess.run(cmd, shell=True, check=True)

@flow(name="daily_etl")
def daily_etl():
    path = extract()
    transform(path)
```

## Handling Unrecognized Templates

Unknown Jinja2 patterns generate warnings:

```
Warning: Unknown Jinja2 pattern: {{ custom_macro() }}
```

Convert manually by:
1. Identifying what the macro returns
2. Implementing equivalent Python logic
3. Using f-strings with the computed value
