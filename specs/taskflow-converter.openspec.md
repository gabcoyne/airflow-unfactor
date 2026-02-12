# OpenSpec: TaskFlow API Converter

## Overview
Convert Airflow TaskFlow API patterns (@dag, @task decorators) to equivalent Prefect flows.

## Requirements

### R1: Detect TaskFlow Patterns
- `@dag` decorated functions → `@flow`
- `@task` decorated functions → `@task`
- `@task.bash` → `@task` + subprocess
- `@task.branch` → native Python if/else
- `@task.short_circuit` → conditional returns

### R2: Parameter Mapping
| Airflow @task | Prefect @task |
|---------------|---------------|
| `retries=3` | `retries=3` |
| `retry_delay=timedelta(minutes=5)` | `retry_delay_seconds=300` |
| `task_id="name"` | `name="name"` |
| `multiple_outputs=True` | (automatic in Prefect) |
| `trigger_rule="all_success"` | (N/A - Prefect uses exceptions) |

### R3: DAG Parameter Mapping
| Airflow @dag | Prefect @flow |
|--------------|---------------|
| `dag_id="name"` | `name="name"` |
| `schedule="@daily"` | (external: Prefect deployment) |
| `catchup=False` | (external: deployment config) |
| `max_active_runs=1` | `task_runner=` config |
| `default_args={"retries": 2}` | (apply to each task) |

### R4: XCom Elimination
TaskFlow already passes data via return values → Prefect does the same.
No conversion needed for basic XCom.

### R5: Output Code Structure
```python
from prefect import flow, task

@task(name="original_task_id")
def my_task(arg1, arg2):
    # Original function body
    return result

@flow(name="original_dag_id")
def my_flow():
    # Call tasks in order
    result = my_task(arg1, arg2)
    return result
```

## Test Cases

### TC1: Simple TaskFlow DAG
Input:
```python
from airflow.decorators import dag, task

@dag(schedule="@daily")
def my_dag():
    @task
    def extract():
        return {"data": [1,2,3]}
    
    @task
    def transform(data):
        return [x * 2 for x in data["data"]]
    
    transform(extract())

my_dag()
```

Output:
```python
from prefect import flow, task

@task(name="extract")
def extract():
    return {"data": [1,2,3]}

@task(name="transform")
def transform(data):
    return [x * 2 for x in data["data"]]

@flow(name="my_dag")
def my_dag():
    result_extract = extract()
    result_transform = transform(result_extract)
    return result_transform
```

### TC2: @task.bash Conversion
Input:
```python
@task.bash
def run_script():
    return "echo hello"
```

Output:
```python
import subprocess

@task(name="run_script")
def run_script():
    cmd = "echo hello"
    result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
    return result.stdout
```

## Implementation Location
`src/airflow_unfactor/converters/taskflow.py`
