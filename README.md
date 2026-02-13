# airflow-unfactor 🛫➡️🌊

> *"Airflow is for airports. Welcome to modern orchestration."*

[![Tests](https://github.com/prefect/airflow-unfactor/actions/workflows/test.yml/badge.svg)](https://github.com/prefect/airflow-unfactor/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/airflow-unfactor)](https://pypi.org/project/airflow-unfactor/)
[![License](https://img.shields.io/github/license/prefect/airflow-unfactor)](LICENSE)

An MCP server that refactors Apache Airflow DAG code into Prefect flow code with AI assistance. Built with [FastMCP](https://github.com/jlowin/fastmcp).

## Features

- 🔄 **Refactor-Focused** — Translates Airflow DAG patterns into maintainable Prefect flow patterns
- 📚 **Educational** — Comments explain *why* Prefect does it better
- ✅ **Test Generation** — Every converted flow comes with pytest tests
- 🤖 **AI-Assisted** — Smart analysis of complex DAG patterns
- 📦 **Batch Support** — Refactor entire DAG projects at once

## Installation

```bash
# Using uv (recommended)
uv pip install airflow-unfactor

# Using pip
pip install airflow-unfactor

# From source (for development)
git clone https://github.com/prefect/airflow-unfactor.git
cd airflow-unfactor
uv pip install -e ".[dev]"
```

## Quick Start

### Use with Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "airflow-unfactor": {
      "command": "uvx",
      "args": ["airflow-unfactor"]
    }
  }
}
```

Then ask Claude:
> "Refactor the DAG in `dags/my_etl.py` into a Prefect flow"

### Use with Cursor

Add to your Cursor MCP config:

```json
{
  "mcpServers": {
    "airflow-unfactor": {
      "command": "uvx",
      "args": ["airflow-unfactor"]
    }
  }
}
```

### Run Standalone

```bash
# Start the MCP server
airflow-unfactor

# Or with uv
uvx airflow-unfactor
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `analyze` | Analyze a DAG's structure, operators, and complexity |
| `convert` | Refactor a DAG into a Prefect flow with tests |
| `validate` | Verify refactoring maintains behavioral equivalence |
| `explain` | Learn Airflow concepts and Prefect equivalents |
| `batch` | Refactor multiple DAGs at once |
| `scaffold` | Generate a complete Prefect project from DAG directory |

### Validating Conversions

The `validate` tool compares your original DAG with the converted flow to ensure behavioral equivalence:

```python
# Via MCP
result = await validate(
    original_dag="path/to/dag.py",
    converted_flow="path/to/flow.py"
)

# Returns JSON with:
# - is_valid: Overall pass/fail
# - task_count_match: Whether task counts match
# - dependency_preserved: Whether dependencies are preserved
# - confidence_score: 0-100 confidence rating
# - issues: Specific mismatches found
```

The validator:
- Extracts task graphs from both files
- Ignores DummyOperator/EmptyOperator (not needed in Prefect)
- Detects XCom patterns and verifies they're converted to return values
- Reports actionable issues when mismatches are found

## Recommended Target Layout (New Prefect Project)

When refactoring Airflow DAGs into a new codebase, keep generated output organized instead of dropping files into a single folder.

Suggested structure (inspired by `prefecthq/flows` style):

```text
your-project/
  flows/                  # Prefect flow entrypoints
  tasks/                  # Reusable task functions
  deployments/            # deployment.yaml / deployment scripts
  infrastructure/         # work pool / worker config helpers
  tests/
    flows/
    tasks/
  migration/
    airflow_sources/      # original DAGs kept read-only for reference
    conversion_notes/     # runbook outputs and manual TODOs
```

This helps keep migration work auditable and reduces long-term repo clutter.

## Example

**Airflow DAG:**
```python
from airflow import DAG
from airflow.operators.python import PythonOperator

def extract():
    return {"users": [1, 2, 3]}

def transform(ti):
    data = ti.xcom_pull(task_ids="extract")
    return [u * 2 for u in data["users"]]

with DAG("my_etl", ...) as dag:
    t1 = PythonOperator(task_id="extract", python_callable=extract)
    t2 = PythonOperator(task_id="transform", python_callable=transform)
    t1 >> t2
```

**Converted Prefect Flow:**
```python
from prefect import flow, task

# ✨ Prefect Advantage: Direct Data Passing
# No XCom push/pull - data flows in-memory between tasks.

@task
def extract():
    return {"users": [1, 2, 3]}

@task
def transform(data):
    return [u * 2 for u in data["users"]]

@flow(name="my_etl")
def my_etl():
    data = extract()  # Direct return
    result = transform(data)  # Direct parameter
    return result
```

**Plus generated tests!** See [Testing](https://prefect.github.io/airflow-unfactor/testing/) for details.

## Documentation

Full documentation: [prefect.github.io/airflow-unfactor](https://prefect.github.io/airflow-unfactor)

- [Getting Started](https://prefect.github.io/airflow-unfactor/getting-started/)
- [Examples](https://prefect.github.io/airflow-unfactor/examples/)
- [Operator Mapping](https://prefect.github.io/airflow-unfactor/operator-mapping/)
- [Testing](https://prefect.github.io/airflow-unfactor/testing/)

## Development

```bash
# Clone and install
git clone https://github.com/prefect/airflow-unfactor.git
cd airflow-unfactor
uv pip install -e ".[dev]"

# Run tests
pytest

# Task tracking with Beads
bd ready
```

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT - see [LICENSE](LICENSE).

---

Made with 💙 by [Prefect](https://prefect.io)
