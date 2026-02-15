# PROJECT.md — airflow-unfactor

> *"Airflow is for airports. Welcome to modern orchestration."*

## Overview

An MCP (Model Context Protocol) server that provides **rich analysis payloads** for LLM-assisted conversion of Apache Airflow DAGs to Prefect flows.

**Philosophy**: Deterministic code templating is too brittle for DAG conversion. Airflow and Prefect are architecturally dissimilar. Instead, we provide comprehensive analysis that enables LLMs to generate complete, functional Prefect flows using their knowledge of Python and Prefect patterns.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Client (LLM)                           │
├─────────────────────────────────────────────────────────────────┤
│  1. analyze(dag_code) → Rich structured payload                 │
│  2. get_context(features) → Prefect docs & patterns             │
│  3. LLM generates complete Prefect flow                         │
│  4. validate(original, generated) → Verify correctness          │
└─────────────────────────────────────────────────────────────────┘
```

**We analyze. The LLM generates. We validate.**

## Philosophy

- **Liberation, not migration** — Help users escape Airflow's complexity
- **LLM-native** — Provide rich payloads, let LLMs generate idiomatic code
- **Educational** — Migration notes explain *why* Prefect does it better
- **Complete** — Analyze all operators, patterns, and configurations
- **Validated** — Verify generated code matches original structure

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | Match Prefect's target |
| MCP Framework | FastMCP | Fast, Pythonic MCP server |
| Task Tracking | Beads (`bd`) | Dependency-aware issue tracking |
| Testing | pytest | 678+ tests |
| Package Manager | uv | Fast, modern Python tooling |

## MCP Tools

### Analysis Tools

#### `analyze`
Comprehensive DAG analysis with structure, patterns, and migration guidance.

**Returns:**
```json
{
  "dag_id": "example_dag",
  "airflow_version": {"detected": "2.7+", "features": {...}},
  "structure": {
    "operators": [...],
    "dependencies": [...],
    "task_groups": [...]
  },
  "patterns": {
    "xcom_usage": [...],
    "sensors": [...],
    "trigger_rules": [...],
    "connections": [...],
    "variables": [...]
  },
  "dag_config": {
    "schedule": "0 * * * *",
    "catchup": false,
    "default_args": {...}
  },
  "complexity": {"score": 7, "factors": [...]},
  "migration_notes": [...],
  "original_code": "..."
}
```

### Context Tools

#### `get_context`
Fetch Prefect documentation and patterns relevant to detected features.

#### `operator_mapping`
Get Prefect equivalent pattern for a specific Airflow operator.

#### `connection_mapping`
Map Airflow connection ID to Prefect block type.

### Validation Tools

#### `validate`
Verify generated Prefect code matches the original DAG structure.

### Scaffolding Tools

#### `scaffold`
Generate project directory structure following `prefecthq/flows` conventions.

## Target Output

Generated flows should follow this structure:

```
deployments/<workspace>/<flow-name>/
├── flow.py
├── Dockerfile
├── requirements.txt

prefect.yaml
```

## Development

```bash
# Setup
uv sync --all-extras
pre-commit install

# Test
uv run pytest

# Run server
uv run airflow-unfactor
```

## References

- [ARCHITECTURE.md](./ARCHITECTURE.md) — Detailed architecture documentation
- [Prefect Migration Guide](https://docs.prefect.io/v3/how-to-guides/migrate/airflow)
- [prefecthq/flows](https://github.com/PrefectHQ/flows) — Target output patterns
- [MCP Protocol Spec](https://modelcontextprotocol.io/)
