# airflow-unfactor

MCP server providing rich analysis payloads for LLM-assisted Airflow→Prefect conversion.

**Key insight**: We analyze DAGs; LLMs generate Prefect code.

## Quick Start

```bash
uv sync --all-extras
uv run airflow-unfactor
```

## Tools

| Tool | Purpose |
|------|---------|
| `analyze` | Comprehensive DAG analysis payload |
| `get_context` | Prefect docs & patterns |
| `validate` | Verify generated code |

See [PROJECT.md](./PROJECT.md) for details.
