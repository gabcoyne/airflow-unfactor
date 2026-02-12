---
layout: page
title: Getting Started
permalink: /getting-started/
---

# Getting Started with airflow-unfactor

## Installation

```bash
# Using uv (recommended)
uv pip install airflow-unfactor

# Using pip
pip install airflow-unfactor
```

## Usage

### As an MCP Server

Add to your Claude Desktop or Cursor config:

```json
{
  "mcpServers": {
    "airflow-unfactor": {
      "command": "uv",
      "args": ["run", "airflow-unfactor"]
    }
  }
}
```

Then ask Claude to convert your DAGs:

> "Convert the DAG in `dags/my_etl.py` to a Prefect flow"

### CLI Usage

```bash
# Analyze a DAG (without converting)
airflow-unfactor analyze my_dag.py

# Convert a single DAG
airflow-unfactor convert my_dag.py -o my_flow.py

# Convert with tests
airflow-unfactor convert my_dag.py -o my_flow.py --with-tests

# Batch convert a directory
airflow-unfactor batch ./dags/ -o ./flows/
```

## MCP Tools

### `analyze_dag`
Analyze a DAG without converting. Returns:
- Operators used
- Task dependencies
- XCom usage patterns
- Complexity score

### `convert_dag`
Convert a DAG to a Prefect flow. Generates:
- Clean, idiomatic Prefect code
- Educational comments explaining Prefect advantages
- pytest tests for the converted flow

### `validate_conversion`
Verify a conversion maintains behavioral equivalence.

### `explain_concept`
Learn about Airflow concepts and their Prefect equivalents:
- XCom → Return values
- Sensors → Triggers / polling flows
- Executors → Work pools
- Hooks → Blocks
- Connections → Blocks / env vars
- Variables → Parameters / Blocks

### `batch_convert`
Convert multiple DAGs at once with a migration report.

## Next Steps

- See [Examples](examples.md) for real-world conversions
- Learn the [Operator Mapping](operator-mapping.md)
- Understand [Testing](testing.md) your migrations