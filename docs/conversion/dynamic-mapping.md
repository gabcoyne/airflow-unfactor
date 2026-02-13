---
layout: page
title: Dynamic Task Mapping
permalink: /conversion/dynamic-mapping/
---

# Dynamic Task Mapping

Convert Airflow's `.expand()` and `.partial().expand()` patterns to Prefect's `.map()`.

## What We Detect

| Pattern | Description |
|---------|-------------|
| `task.expand(param=iterable)` | TaskFlow dynamic mapping |
| `Operator.partial(fixed=val).expand(param=iterable)` | Operator partial + expand |
| `task.expand_kwargs(list_of_dicts)` | Keyword args expansion |
| `map_index_template` | UI naming template (Airflow only) |

## What We Generate

### Simple Expand

```python
# Airflow
@task
def process(item):
    return item * 2

process.expand(item=get_items())

# Prefect (converted)
@task
def process(item):
    return item * 2

process.map(get_items())  # Returns list of results
```

### Partial + Expand

```python
# Airflow
MyOperator.partial(conn_id="db", retries=3).expand(query=queries)

# Prefect (converted)
@task(retries=3)
def my_task(query):
    connector = SqlAlchemyConnector.load("db")
    return connector.execute(query)

my_task.map(queries)
```

### Expand Kwargs

```python
# Airflow
@task
def greet(name, greeting):
    return f"{greeting}, {name}!"

greet.expand_kwargs([
    {"name": "Alice", "greeting": "Hello"},
    {"name": "Bob", "greeting": "Hi"},
])

# Prefect (converted)
@task
def greet(name, greeting):
    return f"{greeting}, {name}!"

# expand_kwargs becomes list comprehension with submit
kwargs_list = [
    {"name": "Alice", "greeting": "Hello"},
    {"name": "Bob", "greeting": "Hi"},
]
results = [greet.submit(**kwargs) for kwargs in kwargs_list]
```

## Known Deltas

| Airflow Feature | Prefect Behavior | Notes |
|-----------------|------------------|-------|
| `map_index_template` | No equivalent | Warning emitted; UI-only feature |
| Mapped task instance isolation | Shared memory | Prefect maps run in same process |
| `max_active_tis_per_dag` | Work pool concurrency | Configure at infrastructure level |

## Manual Follow-up

1. **Review mapped task concurrency** — Prefect's `.map()` runs tasks concurrently by default. Use `task_runner` for process isolation if needed.

2. **Check data serialization** — Airflow serializes mapped inputs to XCom. Prefect passes in-memory. Large objects work better in Prefect.

3. **Update UI expectations** — No `map_index_template` equivalent for naming individual mapped runs.

## Example: Real-World ETL

```python
# Airflow - Process files in parallel
@task
def extract_file(path: str) -> dict:
    return load_json(path)

@task
def transform(data: dict) -> dict:
    return process(data)

@dag
def etl():
    files = list_files()
    extracted = extract_file.expand(path=files)
    transformed = transform.expand(data=extracted)

# Prefect (converted)
@task
def extract_file(path: str) -> dict:
    return load_json(path)

@task
def transform(data: dict) -> dict:
    return process(data)

@flow
def etl():
    files = list_files()
    extracted = extract_file.map(files)
    transformed = transform.map(extracted)
    return transformed
```
