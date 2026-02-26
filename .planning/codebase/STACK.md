# Technology Stack

**Analysis Date:** 2026-02-26

## Languages

**Primary:**
- Python 3.11+ - MCP server and CLI tools
- Python 3.12, 3.13 - Supported versions (defined in `pyproject.toml`)

**Secondary:**
- Markdown - Colin model templates for knowledge compilation
- JSON - Knowledge base output format
- YAML - Configuration files

## Runtime

**Environment:**
- Python 3.11 (pinned in `.python-version`)

**Package Manager:**
- uv (UV package manager) - Primary dependency management
- Lockfile: `uv.lock` (present)

## Frameworks

**Core:**
- FastMCP 2.14.0+ - MCP (Model Context Protocol) server framework for exposing tools to LLMs
  - Location: `src/airflow_unfactor/server.py`
  - Provides tool registration and stdio-based MCP transport
  - Used to build async tools for DAG reading, knowledge lookup, validation

**Development/Build:**
- Ruff 0.5.0+ - Linter and code formatter
- Pre-commit 3.7.0+ - Git hook framework for code quality checks
- Pyright 1.1.390+ - Static type checker (via pre-commit hook)
- Hatchling - Python package builder

**Testing:**
- pytest 8.0.0+ - Test framework
- pytest-asyncio 0.23.0+ - Async test support
- pytest-cov 4.1.0+ - Code coverage measurement

## Key Dependencies

**Critical:**
- fastmcp 2.14.0+ - MCP server framework for tool exposure
  - Handles async tool registration and MCP protocol communication
- pydantic 2.0.0+ (via pre-commit) - Data validation for FastMCP
- anyio 4.12.1+ - Async I/O abstraction library (transitive)
- httpx or requests (transitive) - HTTP client for external MCP calls

**Infrastructure:**
- authlib 1.6.7+ - OAuth/JWT support (potential use for future auth providers)

**Development:**
- ruff 0.5.0+ - Fast Python linter/formatter
- pyright - Static type checking
- pre-commit 3.7.0+ - Git hooks management

## Configuration

**Environment:**
- Python version: `.python-version` (pinned to 3.11)
- MCP server configuration: `.mcp.json`
  - Defines MCP server entry points
  - Registers `airflow-unfactor` command via `uv run`
  - Optional: Supabase MCP integration (HTTP transport)

**Build:**
- `pyproject.toml` - Project metadata, dependencies, tool configuration
  - Ruff settings: line-length=100, target-version=py311
  - Pytest configuration: asyncio_default_fixture_loop_scope=function
  - Coverage thresholds and exclusions
- `colin.toml` - Knowledge compilation configuration (in `colin/` subdirectory)
  - Defines providers: GitHub (Apache Airflow source), MCP (Prefect docs), LLM (Claude Sonnet 4.5)
  - Output target: local JSON files

**Pre-commit Hooks:**
- Ruff check and format
- Pyright type checking (with pydantic, prefect, fastmcp dependencies)
- Prettier for YAML/JSON formatting

## External Integrations (Configuration)

**MCP Servers:**
- `airflow-unfactor` - Self (via `uv run` command)
- `supabase` (optional) - HTTP-based MCP for database integration

**Environment Variables:**
- `MCP_PREFECT_ENABLED` - Enable/disable Prefect docs MCP search (default: true)
- `MCP_PREFECT_URL` - URL for Prefect MCP server (default: https://docs.prefect.io/mcp)
- `GITHUB_TOKEN` - GitHub API token for Colin's Airflow source fetching (optional, for colin run)

## CLI Entry Points

**Command:**
- `airflow-unfactor` - Runs MCP server over stdio (entry point: `airflow_unfactor.server:main`)

**Development Commands:**
```bash
uv sync              # Install dependencies
uv run pytest        # Run tests
uv run ruff check .  # Lint
uv run ruff format . # Format
```

## Platform Requirements

**Development:**
- macOS, Linux, or Windows (Unix-compatible shell)
- Python 3.11+
- uv package manager

**Production (MCP Server):**
- Python 3.11+
- Any system capable of running Python
- Used as stdio-based MCP server (embedded in Claude Desktop, Cursor, or compatible clients)

---

*Stack analysis: 2026-02-26*
