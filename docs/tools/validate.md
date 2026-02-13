---
title: Validation Tool
---

# Validation Tool

Verify that converted flows maintain behavioral equivalence with original DAGs.

## Overview

The `validate` tool compares your original Airflow DAG with the converted Prefect flow to ensure the migration preserves:

- **Task count** — Same number of meaningful tasks (excluding DummyOperator/EmptyOperator)
- **Dependencies** — Task execution order is preserved
- **Data flow** — XCom patterns are converted to return/parameter passing
- **Confidence scoring** — Automated assessment of conversion reliability

## Usage

### Via MCP

```python
result = await validate(
    original_dag="path/to/dag.py",
    converted_flow="path/to/flow.py"
)
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `original_dag` | string | Yes | Path to the original Airflow DAG file |
| `converted_flow` | string | Yes | Path to the converted Prefect flow file |

## Output Format

```json
{
  "is_valid": true,
  "task_count_match": true,
  "dependency_preserved": true,
  "confidence_score": 85,
  "issues": [],
  "dag_tasks": ["extract", "transform", "load"],
  "flow_tasks": ["extract", "transform", "load"],
  "dag_edges": [["extract", "transform"], ["transform", "load"]],
  "flow_edges": [["extract", "transform"], ["transform", "load"]]
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `is_valid` | boolean | Overall pass/fail status |
| `task_count_match` | boolean | Whether task counts match |
| `dependency_preserved` | boolean | Whether dependencies match |
| `confidence_score` | integer | 0-100 confidence rating |
| `issues` | array | List of specific mismatches found |
| `dag_tasks` | array | Tasks extracted from DAG |
| `flow_tasks` | array | Tasks extracted from flow |
| `dag_edges` | array | Dependencies in DAG |
| `flow_edges` | array | Dependencies in flow |

## Understanding Results

### Confidence Scores

| Score Range | Interpretation |
|-------------|----------------|
| 80-100 | High confidence — conversion is reliable |
| 60-79 | Medium confidence — review recommended |
| 40-59 | Low confidence — manual review required |
| 0-39 | Very low — significant manual work needed |

Factors that affect confidence:

- **Task complexity** — More tasks = lower confidence
- **Unknown operators** — Custom operators reduce confidence
- **Dynamic patterns** — Variable task_ids, computed values
- **Partial matches** — Some but not all dependencies verified

### Common Issues

**Task count mismatch:**
```json
{"issues": ["Task count mismatch: DAG has 5 tasks, flow has 4 tasks"]}
```

DummyOperator and EmptyOperator are excluded from counts. Other mismatches indicate missing task implementations.

**Dependency mismatch:**
```json
{"issues": ["Dependency mismatch: edge (extract, transform) not found in flow"]}
```

Check that tasks are called in the correct order and data is passed between them.

**XCom pattern not converted:**
```json
{"issues": ["XCom pattern 'ti.xcom_pull(task_ids=\"extract\")' not converted to parameter"]}
```

Ensure the converted task receives data as a function parameter.

## Examples

### Simple ETL DAG

**Original DAG:**
```python
with DAG("etl") as dag:
    extract = PythonOperator(task_id="extract", python_callable=extract_fn)
    transform = PythonOperator(task_id="transform", python_callable=transform_fn)
    load = PythonOperator(task_id="load", python_callable=load_fn)
    extract >> transform >> load
```

**Converted Flow:**
```python
@flow(name="etl")
def etl():
    data = extract()
    transformed = transform(data)
    load(transformed)
```

**Validation Result:**
```json
{
  "is_valid": true,
  "task_count_match": true,
  "dependency_preserved": true,
  "confidence_score": 95,
  "issues": []
}
```

### DAG with DummyOperator

**Original DAG:**
```python
with DAG("with_dummy") as dag:
    start = DummyOperator(task_id="start")
    process = PythonOperator(task_id="process", python_callable=process_fn)
    end = DummyOperator(task_id="end")
    start >> process >> end
```

**Converted Flow:**
```python
@flow(name="with_dummy")
def with_dummy():
    result = process()
    return result
```

**Validation Result:**
```json
{
  "is_valid": true,
  "task_count_match": true,
  "dependency_preserved": true,
  "confidence_score": 90,
  "issues": []
}
```

Note: DummyOperator tasks are correctly excluded from the comparison.

## Troubleshooting

See [Troubleshooting — Validation Issues](../troubleshooting.md#validation-issues) for detailed guidance on resolving validation failures.

## Best Practices

1. **Run validation after every conversion** — Catch issues early
2. **Address all issues before deployment** — Don't ignore warnings
3. **Use validation in CI/CD** — Automate verification
4. **Review low-confidence conversions** — Manual inspection is valuable
5. **Test with real data** — Validation checks structure, not runtime behavior
