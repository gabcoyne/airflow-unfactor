# CLAUDE.md — airflow-unfactor

## Project Overview

An MCP server for LLM-assisted conversion of Apache Airflow DAGs to Prefect flows. The LLM reads raw DAG source code directly and generates complete Prefect flows using pre-compiled translation knowledge.

**Key Insight**: Deterministic code templating is brittle for DAG conversion. Instead, we provide raw source code + translation knowledge compiled from live sources, and the LLM generates the code.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Build Time (Colin)                        │
│  colin/models/*.md  →  colin run  →  colin/output/*.json        │
│  (GitHub source, Prefect MCP docs, LLM summarization)           │
└─────────────────────────────┬───────────────────────────────────┘
                              │ compiled JSON
┌─────────────────────────────▼───────────────────────────────────┐
│                     MCP Server (Runtime)                         │
│                                                                  │
│  1. read_dag         → Raw DAG source code for LLM to read      │
│  2. lookup_concept   → Translation rules from Colin output       │
│  3. search_prefect_docs → Live Prefect docs for gaps            │
│  4. LLM generates complete Prefect flow code                    │
│  5. validate         → Syntax check + both sources for review   │
│  6. scaffold         → Project directory structure               │
└─────────────────────────────────────────────────────────────────┘
```

**We provide raw code, translation knowledge, and validation. The LLM generates the code.**

## MCP Tools

| Tool | Purpose |
|------|---------|
| `read_dag` | Read a DAG file, return raw source + metadata (path, size, line count) |
| `lookup_concept` | Query Airflow→Prefect translation knowledge (operators, patterns, connections) |
| `search_prefect_docs` | Search live Prefect documentation via Prefect MCP server |
| `validate` | Return both sources + syntax check for LLM comparison |
| `scaffold` | Generate Prefect project directory structure (not code) |

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
uv sync

# Run tests
uv run pytest

# Lint
uv run ruff check --fix

# Run MCP server
uv run airflow-unfactor

# Compile translation knowledge (requires colin)
cd colin && colin run
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
| `src/airflow_unfactor/server.py` | MCP server entry point, tool registration |
| `src/airflow_unfactor/tools/read_dag.py` | Raw DAG source reader |
| `src/airflow_unfactor/tools/lookup.py` | Knowledge lookup tool |
| `src/airflow_unfactor/tools/search_docs.py` | Prefect docs search tool |
| `src/airflow_unfactor/tools/validate.py` | Source comparison + syntax validation |
| `src/airflow_unfactor/tools/scaffold.py` | Project scaffolding |
| `src/airflow_unfactor/knowledge.py` | Knowledge loader (Colin output + fallback) |
| `src/airflow_unfactor/external_mcp.py` | Prefect MCP HTTP client |
| `src/airflow_unfactor/validation.py` | Python syntax validation utility |
| `colin/` | Colin project for compiling translation knowledge |

## External MCP Integration

The server queries the Prefect MCP server for live documentation:

- **Prefect MCP**: `https://docs.prefect.io/mcp` (SearchPrefect tool)

Configure via environment variables:
```bash
MCP_PREFECT_ENABLED=true
MCP_PREFECT_URL=https://docs.prefect.io/mcp
```

When Prefect MCP is unavailable, `lookup_concept` still works using Colin-compiled or fallback knowledge.

## Testing

- Every feature has tests
- Tests use fixtures from `tests/fixtures/astronomer-2-9/`
- 60 tests currently passing

## Important Conventions

1. **Don't generate code** — The MCP tools provide raw source + knowledge; LLMs generate code
2. **No AST intermediary** — The LLM reads raw DAG source directly
3. **Colin for knowledge** — Translation rules compiled from live Airflow source + Prefect docs
4. **Prefect patterns** — Output should follow prefecthq/flows structure
5. **Validation** — Always validate generated code against original structure
