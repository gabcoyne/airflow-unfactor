# airflow-unfactor 🛫➡️🌊

> *"Airflow is for airports. Welcome to modern orchestration."*

An MCP (Model Context Protocol) server that converts Apache Airflow DAGs to Prefect flows using AI-assisted analysis.

## Features

- 🔍 **Analyze** — Understand DAG complexity before converting
- 🔄 **Convert** — Transform Airflow DAGs to idiomatic Prefect flows
- ✅ **Validate** — Verify conversions maintain behavioral equivalence  
- 📚 **Educate** — Learn Prefect advantages through helpful comments
- 📦 **Batch** — Convert entire projects at once

## Installation

```bash
uv pip install -e ".[dev]"
```

## Usage

### As MCP Server

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

### CLI

```bash
# Analyze a DAG
airflow-unfactor analyze my_dag.py

# Convert a DAG
airflow-unfactor convert my_dag.py -o my_flow.py

# Batch convert
airflow-unfactor batch ./dags/ -o ./flows/
```

## Development

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Task tracking with Beads
bd ready  # See available tasks
bd create "New feature" -p 1
```

## License

MIT