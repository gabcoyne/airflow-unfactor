# OpenSpec: Dataset to Event Converter

## Overview
Convert Airflow Datasets (2.4+) and Assets (3.x) to Prefect Events for data-driven orchestration.

## Requirements

### R1: Detect Dataset/Asset Patterns
- `from airflow.datasets import Dataset`
- `Dataset("uri")` instantiation
- `from airflow.assets import Asset`
- `Asset("uri")` instantiation
- `schedule=[dataset1, dataset2]` in @dag
- `outlets=[dataset]` in task
- `schedule=[asset1, asset2]` in @dag (Airflow 3.x)
- `outlets=[asset]` in task (Airflow 3.x)

### R2: Mapping Strategy
| Airflow Concept | Prefect Equivalent |
|-----------------|--------------------|
| Dataset("s3://bucket/path") | Event name: "dataset.s3.bucket.path" |
| Asset("s3://bucket/path") | Prefect Asset + event for automation |
| schedule=[dataset] | Automation trigger on event |
| outlets=[dataset] | emit_event() at task end |
| Dataset dependencies | Event-driven deployment |
| Asset dependencies | Prefect asset materialization + event-driven deployment |

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

**Asset materialization (Airflow 3.x):**
```python
# Pseudocode-level target pattern (exact API may vary by Prefect version):
# from prefect.assets import materialize
#
# @flow
# def refresh_assets():
#     materialize("s3://bucket/data")
#
# Use materialization to represent production of an Asset and
# keep emit_event for automation/trigger compatibility.
```

### R4: Output Structure
Return:
- `events`: List of detected datasets/assets as event names
- `assets`: List of detected Airflow Assets and their Prefect materialization hints
- `producers`: Tasks that update datasets/assets (outlets)
- `consumers`: DAGs triggered by datasets/assets
- `deployment_config`: YAML for Prefect deployment triggers
- `materialization_code`: Optional generated scaffold for Prefect asset materialization

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

### TC3: Detect Asset Import (Airflow 3.x)
```python
from airflow.assets import Asset
sales_asset = Asset("s3://sales/daily")
```
Expected:
- Asset detected
- event generated for automation
- materialization hint generated for Prefect

### TC4: Detect Asset Producer (Airflow 3.x)
```python
@task(outlets=[sales_asset])
def build_sales():
    pass
```
Expected:
- producer mapped
- `materialization_code` includes asset materialization scaffold

## Migration Delta Documentation (Required)
Create/update docs that explain the Airflow-to-Prefect behavior delta:
- File: `docs-site/src/app/docs/conversion/datasets/page.mdx`
- Include:
  - Dataset (Airflow 2.4+) vs Asset (Airflow 3.x) differences
  - Why both event emission and asset materialization are produced
  - What remains manual (naming, ownership metadata, storage/lineage conventions)
  - A concrete before/after example

## Implementation Location
`src/airflow_unfactor/converters/datasets.py`
