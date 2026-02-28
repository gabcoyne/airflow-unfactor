# airflow-unfactor

[![Tests](https://github.com/gabcoyne/airflow-unfactor/actions/workflows/test.yml/badge.svg)](https://github.com/gabcoyne/airflow-unfactor/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/airflow-unfactor)](https://pypi.org/project/airflow-unfactor/)
[![License](https://img.shields.io/github/license/gabcoyne/airflow-unfactor)](LICENSE)

An MCP server that converts Apache Airflow DAGs into Prefect flows. Point it at a DAG, and the LLM generates idiomatic Prefect code. Not a template with TODOs — working code. Built with [FastMCP](https://github.com/jlowin/fastmcp).

## How It Works

The server exposes five tools over MCP. The LLM reads raw DAG source code, looks up translation knowledge, and generates the Prefect flow.

| Tool | What It Does |
|------|-------------|
| `read_dag` | Returns raw DAG source code with metadata (path, size, line count) |
| `lookup_concept` | Airflow→Prefect translation knowledge — operators, patterns, connections |
| `validate` | Syntax-checks generated code and returns both sources for comparison |
| `search_prefect_docs` | Searches live Prefect docs for anything not in the pre-compiled knowledge |
| `scaffold` | Creates a Prefect project directory structure (not code) |

No AST parsing. No template engine. The LLM reads the code directly, just like a developer would.

## Installation

```bash
# From PyPI
pip install airflow-unfactor

# Or with uv
uv pip install airflow-unfactor
```

## Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

### Claude Code

Add to `.mcp.json` in your project:

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

### Cursor

Add to your Cursor MCP settings:

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

Then ask your LLM: *"Convert the DAG in `dags/my_etl.py` to a Prefect flow."*

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

**Generated Prefect flow:**
```python
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

The `>>` dependency chain becomes explicit data passing through return values. XCom is gone. It's just Python.

## Translation Knowledge

The server ships with 78 pre-compiled Airflow→Prefect translation entries covering operators, patterns, connections, and core concepts. These are compiled by Colin from live Airflow source and Prefect documentation.

When the pre-compiled knowledge doesn't cover something, `search_prefect_docs` queries the Prefect documentation MCP server at docs.prefect.io in real time.

## Documentation

Full docs: [gabcoyne.github.io/airflow-unfactor](https://gabcoyne.github.io/airflow-unfactor)

## Development

```bash
git clone https://github.com/gabcoyne/airflow-unfactor.git
cd airflow-unfactor
uv sync

# Run tests
uv run pytest

# Lint
uv run ruff check --fix

# Compile translation knowledge
cd colin && colin run
```

## License

MIT — see [LICENSE](LICENSE).
