# OpenSpec: Airflow Version Detection

## Overview
Detect Airflow version (1.x, 2.x, 3.x) from DAG source code by analyzing imports and patterns.

## Requirements

### R1: Version Detection from Imports
- Detect Airflow 1.x: `from airflow.operators.python_operator import PythonOperator`
- Detect Airflow 2.x: `from airflow.operators.python import PythonOperator`
- Detect Airflow 2.x TaskFlow: `from airflow.decorators import dag, task`
- Detect Airflow 2.4+: `from airflow.datasets import Dataset`
- Detect Airflow 3.x: `from airflow.assets import Asset`

### R2: Feature Flags
Return which features are available based on detected version:

| Feature | Airflow 1.x | Airflow 2.0+ | Airflow 2.4+ | Airflow 2.9+ | Airflow 3.x |
|---------|-------------|--------------|--------------|--------------|-------------|
| TaskFlow API | ❌ | ✅ | ✅ | ✅ | ✅ |
| EmptyOperator | ❌ | ✅ | ✅ | ✅ | ✅ |
| Datasets | ❌ | ❌ | ✅ | ✅ | ❌ (renamed) |
| @task.bash | ❌ | ❌ | ❌ | ✅ | ✅ |
| Assets | ❌ | ❌ | ❌ | ❌ | ✅ |
| Dynamic Task Mapping | ❌ | ❌ | ✅ | ✅ | ✅ |

### R3: API Surface
```python
@dataclass
class AirflowVersion:
    major: int  # 1, 2, or 3
    minor: int | None  # e.g., 9 for 2.9
    
    # Feature flags
    has_taskflow: bool
    has_datasets: bool
    has_assets: bool
    has_task_bash: bool
    has_dynamic_task_mapping: bool
    has_empty_operator: bool
    
    # Confidence
    confidence: float  # 0.0-1.0
    evidence: list[str]  # What patterns were found

def detect_airflow_version(dag_code: str) -> AirflowVersion:
    """Detect Airflow version from DAG source code."""
```

### R4: Pattern Detection
Beyond imports, detect version from patterns:
- `DummyOperator` → Airflow 1.x (deprecated in 2.x)
- `@dag` decorator on function → Airflow 2.x+
- `@task.bash` → Airflow 2.9+
- `schedule_interval` → older style (1.x/early 2.x)
- `schedule=` → modern style (2.x+)
- `Dataset("...")` in schedule → Airflow 2.4+
- `Asset("...")` → Airflow 3.x

### R5: Confidence Scoring
- Single import match: confidence = 0.6
- Multiple consistent signals: confidence = 0.8
- Explicit version comment/import: confidence = 1.0
- Conflicting signals: return lowest compatible version, confidence = 0.4

## Test Cases

### TC1: Airflow 1.x Detection
```python
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.dummy_operator import DummyOperator
```
Expected: `AirflowVersion(major=1, has_taskflow=False, ...)`

### TC2: Airflow 2.x TaskFlow Detection
```python
from airflow.decorators import dag, task

@dag(schedule=None)
def my_dag():
    @task
    def hello():
        return "world"
```
Expected: `AirflowVersion(major=2, has_taskflow=True, ...)`

### TC3: Airflow 2.9+ Detection
```python
from airflow.decorators import dag, task

@dag()
def my_dag():
    @task.bash
    def run_script():
        return "echo hello"
```
Expected: `AirflowVersion(major=2, minor=9, has_task_bash=True, ...)`

### TC4: Airflow 3.x Detection
```python
from airflow.assets import Asset
from airflow.decorators import dag, task

my_asset = Asset("s3://bucket/data")

@dag(schedule=[my_asset])
def asset_dag():
    pass
```
Expected: `AirflowVersion(major=3, has_assets=True, has_datasets=False, ...)`

## Implementation Location
`src/airflow_unfactor/analysis/version.py`

## Dependencies
- None (pure AST analysis)
