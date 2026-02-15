---
layout: page
title: Getting Started
permalink: /getting-started/
---

# Getting Started

## Installation

### Using uv (recommended)

```bash
uv pip install airflow-unfactor
```

### Using pip

```bash
pip install airflow-unfactor
```

### From source

```bash
git clone https://github.com/prefecthq/airflow-unfactor.git
cd airflow-unfactor
uv pip install -e ".[dev]"
```

## Setup with Claude Desktop

Add to your Claude Desktop config:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

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

Restart Claude Desktop. You should see the airflow-unfactor tools available.

## Setup with Cursor

Add to your Cursor MCP config (`~/.cursor/mcp.json` or via Cursor settings):

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

## Usage

### With an AI Assistant

Once configured, ask your AI assistant:

> "Analyze the DAG in `dags/my_etl.py`"

> "Migrate `dags/my_dag.py` to a Prefect flow"

> "Explain what XCom is and how Prefect handles data passing"

> "Migrate all DAGs in the `dags/` directory"

### Standalone

Run the MCP server directly:

```bash
# Using uvx (no install needed)
uvx airflow-unfactor

# Or if installed
airflow-unfactor
```

## Available Tools

### `analyze`
Analyze a DAG without converting.

```
Inputs:
  - path: Path to DAG file
  - content: DAG code (alternative to path)

Returns:
  - dag_id, operators, dependencies
  - XCom usage, complexity score
  - Conversion notes
```

### `convert`
Migrate a DAG to a Prefect flow.

```
Inputs:
  - path: Path to DAG file
  - content: DAG code (alternative to path)
  - include_comments: Add educational comments (default: true)
  - generate_tests: Generate pytest tests (default: true)
  - include_external_context: Enrich with external MCP context (default: true)

Returns:
  - flow_code: Converted Prefect flow
  - test_code: pytest tests for the flow
  - warnings: Conversion warnings
  - original_to_new_mapping: Original → converted task names
  - dataset_conversion: Dataset/asset conversion outputs
    - events: List of detected dataset events
    - producer_code: Event emission helpers
    - deployment_yaml: Trigger snippets for deployment config
    - materialization_code: Asset materialization scaffolds
  - conversion_runbook_md: Step-by-step migration guide with:
    - DAG-specific configuration mapping (schedule, retries, tags, etc.)
    - Server/API configuration checklist
    - Deployment guidance based on extracted DAG settings
```

### `validate`
Verify a migration is correct.

```
Inputs:
  - original_dag: Original DAG path/content
  - converted_flow: Converted flow path/content

Returns:
  - valid: Boolean
  - issues: List of problems
  - test_suggestions: Recommended tests
```

### `explain`
Learn Airflow concepts and Prefect equivalents.

```
Inputs:
  - concept: XCom, Sensor, Executor, Hook, Connection, or Variable

Returns:
  - Explanation with code examples
  - Prefect advantages
```

### `batch`
Migrate multiple DAGs at once.

```
Inputs:
  - directory: Directory with DAG files
  - output_directory: Where to write flows (optional)

Returns:
  - Migration report (success/fail counts)
  - Migration runbook file
```

### `scaffold`
Generate a clean project skeleton with migrated flows.

```
Inputs:
  - dags_directory: Directory containing Airflow DAG files
  - output_directory: Where to create the new project
  - project_name: Project name (optional)
  - include_docker: Include Dockerfile (default: true)
  - include_github_actions: Include CI workflow (default: true)

Returns:
  - Scaffold report with project structure
```

**Generated structure:**
```
your-project/
├── flows/              # Prefect flow entrypoints
├── tasks/              # Reusable task functions
├── deployments/        # Deployment configurations
├── infrastructure/     # Work pool configs
├── tests/              # pytest tests
├── migration/
│   ├── airflow_sources/    # Original DAGs (read-only)
│   └── conversion_notes/   # Migration runbooks
├── prefect.yaml        # Deployment config
├── Dockerfile          # Container build
└── docker-compose.yml  # Local development
```

## Next Steps

- See [Examples](examples.md) for real-world conversions
- Review the [Operator Mapping](operator-mapping.md)
- Learn about [Testing](testing.md) your migrations