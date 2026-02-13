---
layout: page
title: Convert Response Reference
permalink: /convert-reference/
---

# Convert Response Reference

Complete reference for the `convert` tool response. Use this to understand what you get back and how to use each field.

## Quick Summary

```
convert(path="dag.py") returns:
├── flow_code           # Generated Prefect flow
├── test_code           # pytest tests for the flow
├── conversion_runbook_md   # Migration runbook
├── warnings            # Issues to address
├── original_to_new_mapping # Task ID → function name
├── features            # What patterns were detected
├── block_scaffolds     # Connection → Block code
├── variable_scaffolds  # Variable → Secret/Variable code
├── dataset_conversion  # Event/trigger scaffolds
└── external_context    # External MCP enrichment (optional)
```

## Response Fields

### `flow_code`

**Type:** `string`

The generated Prefect flow as Python source code. Ready to write to a `.py` file.

```python
# Example output
from prefect import flow, task

@task
def extract():
    return {"users": [1, 2, 3]}

@task
def transform(data):
    return [u * 2 for u in data["users"]]

@flow(name="my_etl")
def my_etl():
    data = extract()
    result = transform(data)
    return result
```

**When empty:** Error during parsing or conversion. Check `warnings` for details.

**Edge cases:**
- XCom patterns are converted to direct return/parameter passing
- Jinja2 templates generate `# TODO: Replace runtime template` comments
- Custom operators generate stub functions with TODOs

---

### `test_code`

**Type:** `string`

Generated pytest tests for the converted flow.

```python
# Example output
import pytest
from prefect.testing.utilities import prefect_test_harness

@pytest.fixture(scope="module")
def prefect_harness():
    with prefect_test_harness():
        yield

class TestExtract:
    def test_extract_returns_value(self):
        from my_flow import extract
        result = extract.fn()
        assert result is not None

class TestMyEtlFlow:
    def test_flow_executes(self, prefect_harness):
        from my_flow import my_etl
        result = my_etl()
        assert True  # Flow completed
```

**When absent:** `generate_tests=False` was passed.

**Test categories:**
1. **Task unit tests** — Each task tested independently via `.fn()`
2. **Flow execution tests** — Full flow execution with harness
3. **Migration verification** — Task count, no XCom references

---

### `conversion_runbook_md`

**Type:** `string`

DAG-specific migration runbook in Markdown format. Contains:

```markdown
# Migration Runbook: `my_etl`

## Migration Checklist
- [ ] Configure schedule via deployment or `.serve(cron="...")`
- [ ] Create required Prefect Blocks for connections
- [ ] Set up Variables/Secrets for credentials
- [ ] Configure retries and concurrency
- [ ] Set up notifications and automations

## Schedule Migration
| Airflow | Prefect |
|---------|---------|
| `@daily` | `cron: "0 0 * * *"` or `.serve(cron="0 0 * * *")` |

## Connections Required
| Connection ID | Prefect Block | Package |
|--------------|---------------|---------|
| `my_postgres` | `SqlAlchemyConnector` | `prefect-sqlalchemy` |

## Variables Required
| Variable | Recommendation |
|----------|---------------|
| `api_key` | `Secret.load("api-key")` |

## Warnings
- Jinja2 template `{{ ds }}` requires runtime context migration
```

**Sections include:**
- Migration Checklist — Step-by-step setup tasks
- Schedule Migration — How to configure Prefect schedule
- Connections Required — Block setup instructions
- Variables Required — Secret/Variable setup
- Warnings — Items needing manual review

---

### `warnings`

**Type:** `array[string]`

Issues detected during conversion that may need manual attention.

```json
[
  "Jinja2 template detected: {{ ds }} - use runtime.flow_run.scheduled_start_time",
  "Dynamic XCom pattern: ti.xcom_pull(task_ids=variable) - cannot statically convert",
  "Unknown operator: CustomOperator - stub generated",
  "Trigger rule 'all_done' detected - review state handling pattern"
]
```

**Warning categories:**

| Category | Example | Action |
|----------|---------|--------|
| Jinja2 | `{{ ds }}` detected | Review runtime context migration |
| XCom | Dynamic task ID | Manual refactoring needed |
| Operator | Unknown operator | Complete stub implementation |
| Trigger Rule | Non-default rule | Review state handling code |
| Connection | Missing block | Create Prefect Block |
| Validation | Syntax error | Fix generated code |

---

### `original_to_new_mapping`

**Type:** `object`

Maps Airflow task IDs to generated Prefect function names.

```json
{
  "extract_data": "extract_data",
  "transform-data": "transform_data",
  "load_to_warehouse": "load_to_warehouse"
}
```

**Use cases:**
- Verify all tasks were converted
- Map logs/metrics from old to new
- Update downstream references

**Note:** Task IDs with hyphens become underscored function names.

---

### `features`

**Type:** `object`

Flags indicating which Airflow patterns were detected.

```json
{
  "has_taskflow": true,
  "has_datasets": false,
  "has_sensors": false,
  "has_dynamic_mapping": true,
  "has_task_groups": false,
  "has_trigger_rules": false,
  "has_jinja_templates": true,
  "has_connections": true,
  "has_variables": true,
  "has_custom_operators": false
}
```

**Use for:**
- Estimating migration complexity
- Identifying which conversion guides to reference
- Planning manual review areas

---

### `block_scaffolds`

**Type:** `object`

Generated Prefect Block scaffold code for each detected connection.

```json
{
  "my_postgres": "connector = SqlAlchemyConnector.load(\"my-postgres\")\nresult = connector.fetch_all(\"SELECT * FROM table\")",
  "aws_default": "s3 = S3Bucket.load(\"aws-default\")\ndata = s3.read_path(\"data.json\")"
}
```

**Next steps:**
1. Install required package (`prefect-sqlalchemy`, `prefect-aws`, etc.)
2. Create Block in Prefect UI or via CLI
3. Replace placeholder code with actual usage

---

### `variable_scaffolds`

**Type:** `object`

Generated code for migrating Airflow Variables.

```json
{
  "api_key": "Secret.load(\"api-key\").get()",
  "max_retries": "# Flow parameter: max_retries: int = 3",
  "last_processed_id": "Variable.get(\"last-processed-id\", default=\"0\")"
}
```

**Recommendation logic:**
- Contains `key`, `password`, `secret`, `token`, `credential` → Secret
- Has default value, read-only → Flow parameter
- Dynamic read/write → Prefect Variable

---

### `dataset_conversion`

**Type:** `object`

Scaffolds for Airflow Dataset/Asset patterns.

```json
{
  "events": [
    {"name": "orders_updated", "uri": "s3://bucket/orders"}
  ],
  "producer_code": "from prefect.events import emit_event\n\ndef emit_orders_updated():\n    emit_event(\"orders-updated\", resource={\"uri\": \"s3://bucket/orders\"})",
  "deployment_yaml": "triggers:\n  - type: event\n    match:\n      prefect.resource.name: orders-updated",
  "materialization_code": "# Asset materialization scaffold..."
}
```

**Subfields:**

| Field | Description |
|-------|-------------|
| `events` | Detected dataset events |
| `producer_code` | Event emission helpers |
| `deployment_yaml` | Trigger configuration snippets |
| `materialization_code` | Asset materialization scaffolds |

---

### `external_context`

**Type:** `object` (optional)

Enrichment from external MCP tools (when `include_external_context=True`).

```json
{
  "prefect": {
    "ok": true,
    "tool": "prefect_search",
    "query": "Convert Airflow DAG to Prefect flow. TaskFlow=true",
    "elapsed_ms": 1250,
    "result": "Prefect documentation excerpt..."
  },
  "astronomer": {
    "ok": true,
    "tool": "astronomer_migration",
    "query": "Airflow 2 to 3 migration",
    "elapsed_ms": 890,
    "result": "Migration guidance..."
  }
}
```

**When disabled:** Pass `include_external_context=False` for faster conversion without external calls.

**Failure handling:** If external calls fail, `ok=false` and `error` contains the message. Conversion still succeeds.

---

## Complete Example

```python
# Input DAG
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

def extract(ti):
    api_key = Variable.get("api_key")
    return {"users": [1, 2, 3]}

def transform(ti):
    data = ti.xcom_pull(task_ids="extract")
    return [u * 2 for u in data["users"]]

with DAG("my_etl", schedule="@daily") as dag:
    t1 = PythonOperator(task_id="extract", python_callable=extract)
    t2 = PythonOperator(task_id="transform", python_callable=transform)
    t1 >> t2
```

```json
// Output (abbreviated)
{
  "flow_code": "from prefect import flow, task\nfrom prefect.blocks.system import Secret\n\n@task\ndef extract():\n    api_key = Secret.load(\"api-key\").get()\n    return {\"users\": [1, 2, 3]}\n\n@task\ndef transform(data):\n    return [u * 2 for u in data[\"users\"]]\n\n@flow(name=\"my_etl\")\ndef my_etl():\n    data = extract()\n    result = transform(data)\n    return result",
  "test_code": "...",
  "conversion_runbook_md": "# Migration Runbook: `my_etl`\n...",
  "warnings": [
    "Variable 'api_key' appears sensitive - use Secret block"
  ],
  "original_to_new_mapping": {
    "extract": "extract",
    "transform": "transform"
  },
  "features": {
    "has_taskflow": false,
    "has_variables": true,
    "has_connections": false
  },
  "variable_scaffolds": {
    "api_key": "Secret.load(\"api-key\").get()"
  }
}
```

## Error Response

When conversion fails:

```json
{
  "error": "Failed to parse DAG: invalid syntax at line 15",
  "external_context": {}
}
```

Check for:
- Python syntax errors in input
- Unsupported Airflow 1.x patterns
- Missing `with DAG()` context or `@dag` decorator

## See Also

- [Getting Started](getting-started.md) — Tool overview
- [Operator Mapping](operator-mapping.md) — How operators convert
- [Variables & Secrets](conversion/variables.md) — Variable migration details
- [Connections & Blocks](conversion/connections.md) — Connection migration details
- [Troubleshooting](troubleshooting.md) — Common issues
