# CLAUDE.md — airflow-unfactor

## Project Overview

An MCP server that provides **rich analysis payloads** for LLM-assisted conversion of Apache Airflow DAGs to Prefect flows.

**Key Insight**: Deterministic code templating is brittle for DAG conversion because Airflow and Prefect are architecturally dissimilar. Instead, this tool provides comprehensive analysis payloads that enable LLMs to generate complete, functional, tested Prefect flows.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Client (LLM)                           │
│                                                                  │
│  1. analyze() → Get rich structured DAG payload                 │
│  2. get_context() → Fetch Prefect docs/patterns                 │
│  3. LLM generates complete Prefect flow code                    │
│  4. validate() → Verify structural correctness                  │
└─────────────────────────────────────────────────────────────────┘
```

**We provide analysis, context, and validation. The LLM generates the code.**

## MCP Tools

### Primary Tools (New Architecture)

| Tool | Purpose |
|------|---------|
| `analyze` | Comprehensive DAG analysis with structure, patterns, config, migration notes |
| `get_context` | Fetch Prefect docs based on detected features |
| `operator_mapping` | Get Prefect equivalent for specific Airflow operator |
| `connection_mapping` | Map Airflow connection to Prefect block type |
| `validate` | Verify generated code matches original structure |
| `scaffold` | Generate project directory structure (not code) |

### Deprecated Tools (Template-Based)

| Tool | Status |
|------|--------|
| `convert` | Deprecated - uses brittle templates |
| `batch` | Deprecated - uses brittle templates |

## Target Output Structure

Generated flows should follow `prefecthq/flows` conventions:

```
deployments/<workspace>/<flow-name>/
├── flow.py           # Main flow code
├── Dockerfile        # If custom dependencies
├── requirements.txt  # Python dependencies

prefect.yaml          # Deployment configuration
```

## Development

```bash
# Environment
uv sync --all-extras

# Run tests
uv run pytest

# Type check
uv run pyright

# Lint
uv run ruff check --fix

# Run MCP server
uv run airflow-unfactor

# Run with wizard UI
uv run airflow-unfactor --ui
```

## Task Tracking

Use beads (`bd`) for issue tracking:

```bash
bd ready              # Find available work
bd show <id>          # View details
bd update <id> --status in_progress
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Key Files

| Path | Description |
|------|-------------|
| `src/airflow_unfactor/server.py` | MCP server entry point |
| `src/airflow_unfactor/tools/analyze.py` | DAG analysis tool |
| `src/airflow_unfactor/tools/context.py` | Prefect context/docs tools |
| `src/airflow_unfactor/tools/validate.py` | Validation tool |
| `src/airflow_unfactor/analysis/` | AST parsing and analysis |
| `ARCHITECTURE.md` | Detailed architecture documentation |

## External MCP Integration

The server can call external MCP servers for enriched context:

- **Prefect MCP**: `https://docs.prefect.io/mcp` (SearchPrefect tool)
- **Astronomer MCP**: Airflow 2→3 migration guidance

Configure via environment variables:
```bash
MCP_PREFECT_ENABLED=true
MCP_PREFECT_URL=https://docs.prefect.io/mcp
```

## Testing Philosophy

- Every feature should have tests
- Tests use fixtures from `tests/fixtures/astronomer-2-9/`
- Property-based testing with hypothesis where appropriate
- 678 tests currently passing

## Important Conventions

1. **Don't generate code** - The MCP tools provide analysis; LLMs generate code
2. **Rich payloads** - Include everything an LLM needs for accurate generation
3. **Prefect patterns** - Output should follow prefecthq/flows structure
4. **Validation** - Always validate generated code against original structure
