---
layout: page
title: TaskGroups
permalink: /conversion/taskgroups/
---

# TaskGroups

Convert Airflow TaskGroups to Prefect subflows for better organization and observability.

## What We Detect

| Pattern | Description |
|---------|-------------|
| `@task_group` decorator | TaskFlow-style task groups |
| `with TaskGroup("name"):` | Context manager style |
| `task_group.expand(param=[...])` | Dynamic task group mapping |

## What We Generate

### Simple TaskGroup

```python
# Airflow
from airflow.decorators import task_group

@task_group
def data_processing():
    @task
    def extract():
        return {"data": [1, 2, 3]}

    @task
    def transform(data):
        return [x * 2 for x in data["data"]]

    transform(extract())

@dag
def my_dag():
    data_processing()

# Prefect (converted)
@task
def extract():
    return {"data": [1, 2, 3]}

@task
def transform(data):
    return [x * 2 for x in data["data"]]

@flow(name="data_processing")
def data_processing():
    """Subflow - provides better observability than TaskGroups."""
    data = extract()
    result = transform(data)
    return result

@flow(name="my_dag")
def my_dag():
    data_processing()  # Subflow call
```

### TaskGroup with Expand

```python
# Airflow
@task_group
def process_region(region: str):
    @task
    def fetch(r):
        return get_data(r)

    @task
    def analyze(data):
        return compute(data)

    analyze(fetch(region))

@dag
def regional_analysis():
    process_region.expand(region=["us", "eu", "asia"])

# Prefect (converted)
@task
def fetch(region: str):
    return get_data(region)

@task
def analyze(data):
    return compute(data)

@flow(name="process_region")
def process_region(region: str):
    """Subflow for processing a single region."""
    data = fetch(region)
    result = analyze(data)
    return result

@task
def run_process_region(region: str):
    """Wrapper task for mapping subflow calls."""
    return process_region(region)

@flow(name="regional_analysis")
def regional_analysis():
    # Subflows don't have native .expand()
    # Use wrapper task with .map() instead
    regions = ["us", "eu", "asia"]
    results = run_process_region.map(regions)
    return results
```

## Known Deltas

| Airflow Feature | Prefect Behavior | Notes |
|-----------------|------------------|-------|
| TaskGroup UI grouping | Subflow as separate run | Better observability, separate logs |
| TaskGroup tooltip | Flow docstring | Use docstrings for descriptions |
| Group-level prefix | Flow name | Configure via `name` parameter |
| `group_id` | `name` parameter | Passed to `@flow` decorator |

## Manual Follow-up

1. **Review subflow parameters** — TaskGroups implicitly capture variables from parent scope. Subflows need explicit parameters.

2. **Check retry behavior** — Subflows can have independent retry config via `@flow(retries=...)`.

3. **Consider parallel execution** — Subflow calls are sequential by default. Use the wrapper task pattern with `.map()` for parallel execution.

## Subflow Advantages Over TaskGroups

| Benefit | Description |
|---------|-------------|
| **Independent deployment** | Subflows can be deployed separately |
| **Separate runs** | Each subflow call is a distinct run with its own logs |
| **Retry isolation** | Retry only the failed subflow, not the parent |
| **Reusability** | Import and call subflows from multiple parent flows |
| **Parameter validation** | Type hints and Pydantic models work naturally |

## Example: Data Pipeline with Stages

```python
# Prefect - Organized with subflows
@flow
def bronze_stage(source: str):
    """Raw data ingestion."""
    raw = extract_raw(source)
    validated = validate_schema(raw)
    return save_bronze(validated)

@flow
def silver_stage(bronze_path: str):
    """Cleaned and transformed data."""
    data = load_bronze(bronze_path)
    cleaned = clean_data(data)
    return save_silver(cleaned)

@flow
def gold_stage(silver_path: str):
    """Aggregated business metrics."""
    data = load_silver(silver_path)
    metrics = compute_metrics(data)
    return save_gold(metrics)

@flow(name="medallion_pipeline")
def medallion_pipeline(source: str):
    bronze = bronze_stage(source)
    silver = silver_stage(bronze)
    gold = gold_stage(silver)
    return gold
```
