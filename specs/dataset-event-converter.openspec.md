# OpenSpec: Dataset to Event Converter

## Overview
Convert Airflow Datasets (2.4+) and Assets (3.x) to Prefect Events for data-driven orchestration.

## Requirements

### R1: Detect Dataset Patterns
- `from airflow.datasets import Dataset`
- `Dataset("uri")` instantiation
- `schedule=[dataset1, dataset2]` in @dag
- `outlets=[dataset]` in task

### R2: Mapping Strategy
| Airflow Concept | Prefect Equivalent |
|-----------------|--------------------|
| Dataset("s3://bucket/path") | Event name: "dataset.s3.bucket.path" |
| schedule=[dataset] | Automation trigger on event |
| outlets=[dataset] | emit_event() at task end |
| Dataset dependencies | Event-driven deployment |

### R3: Generated Code Pattern

**Producer task (outlets):**
```python
from prefect.events import emit_event

@task
def produce_data():
    # ... do work ...
    emit_event(
        event="dataset.s3.bucket.data.updated",
        resource={"prefect.resource.id": "s3://bucket/data"}
    )
```

**Consumer flow (schedule=[dataset]):**
```python
# Deployment config (not in code):
# triggers:
#   - match: {"prefect.resource.id": "s3://bucket/data"}
#     expect: ["dataset.s3.bucket.data.updated"]
```

### R4: Output Structure
Return:
- `events`: List of detected datasets as event names
- `producers`: Tasks that update datasets (outlets)
- `consumers`: DAGs triggered by datasets
- `deployment_config`: YAML for Prefect deployment triggers

## Test Cases

### TC1: Detect Dataset Import
```python
from airflow.datasets import Dataset
my_data = Dataset("s3://my-bucket/data.csv")
```
Expected: `events=["dataset.s3.my-bucket.data.csv"]`

### TC2: Detect Producer Task
```python
@task(outlets=[my_data])
def write_data():
    pass
```
Expected: `producers=[{"task": "write_data", "dataset": "my_data"}]`

## Implementation Location
`src/airflow_unfactor/converters/datasets.py`
