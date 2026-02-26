# Codebase Structure

**Analysis Date:** 2026-02-26

## Directory Layout

```
airflow-unfactor/
├── src/airflow_unfactor/           # Main package
│   ├── __init__.py                 # Package marker
│   ├── server.py                   # MCP server entry point + tool registration
│   ├── knowledge.py                # Knowledge loading and lookup logic
│   ├── validation.py               # Python syntax validation utilities
│   ├── external_mcp.py             # Prefect MCP HTTP client
│   └── tools/                      # Tool implementations
│       ├── __init__.py
│       ├── read_dag.py             # Read Airflow DAG source code
│       ├── lookup.py               # Look up translation knowledge
│       ├── search_docs.py          # Search Prefect documentation
│       ├── validate.py             # Validate conversions
│       └── scaffold.py             # Generate project structure
├── tests/                          # Test suite
│   ├── conftest.py                 # pytest configuration + fixtures
│   ├── __init__.py
│   ├── test_read_dag.py
│   ├── test_lookup.py
│   ├── test_search_docs.py
│   ├── test_validate.py
│   ├── test_validation.py
│   ├── test_external_mcp.py
│   ├── test_scaffold.py
│   ├── test_knowledge.py
│   └── fixtures/                   # Test data
│       ├── simple_etl.py           # Simple test DAG
│       ├── astronomer-2-9/         # Large fixture set from Astronomer
│       │   └── dags/toys/          # Example DAGs for testing
│       └── snapshots/              # Golden file snapshots for comparison
├── colin/                          # Knowledge compilation project
│   ├── models/                     # Knowledge models and prompts
│   ├── output/                     # Colin compilation output (JSON)
│   └── ...                         # Colin configuration
├── pyproject.toml                  # Python project configuration
├── .mcp.json                       # MCP configuration (tool descriptions)
├── main.py                         # CLI entry point (wrapper)
└── README.md                       # Project documentation
```

## Directory Purposes

**src/airflow_unfactor/:**
- Purpose: Main package code for the MCP server
- Contains: Server, tools, knowledge system, validation
- Key files: `server.py` (entry point), `tools/` (tool implementations)

**src/airflow_unfactor/tools/:**
- Purpose: Individual tool implementations exposed to LLM
- Contains: Five async functions, each returning JSON
- Key files: All tools return JSON directly, no shared utilities in this directory

**tests/:**
- Purpose: Pytest test suite for all components
- Contains: Unit tests, async test patterns, mocked external calls
- Key files: `conftest.py` for shared fixtures, `test_*.py` for unit tests

**tests/fixtures/:**
- Purpose: Test data and example DAGs
- Contains: Simple test DAGs, large Astronomer fixture set, snapshot golden files
- Key files: `simple_etl.py` (minimal), `astronomer-2-9/dags/toys/` (comprehensive)

**tests/fixtures/snapshots/:**
- Purpose: Golden files for snapshot-based testing
- Contains: Expected output snapshots (e.g., expected converted flows)
- Generated: Via `--snapshot-update` pytest option

**colin/:**
- Purpose: Knowledge compilation system (external project)
- Contains: Models, prompts, output directory with JSON mappings
- Relationship: Generates JSON that `knowledge.py` loads; optional but recommended

## Key File Locations

**Entry Points:**
- `main.py`: Minimal CLI wrapper (calls `server.main()`)
- `src/airflow_unfactor/server.py::main()`: MCP server startup over stdio
- `airflow-unfactor`: Console script entry point defined in `pyproject.toml`

**Configuration:**
- `pyproject.toml`: Python package config, dependencies, tools (ruff, pytest)
- `.mcp.json`: MCP server configuration (optional)
- `pyproject.toml::tool.ruff`: Linting config (line-length=100, select rules)
- `pyproject.toml::tool.pytest`: Test config (asyncio mode, paths)

**Core Logic:**
- `src/airflow_unfactor/server.py`: Tool registration and MCP server
- `src/airflow_unfactor/knowledge.py`: Knowledge loading and lookup algorithm
- `src/airflow_unfactor/tools/read_dag.py`: DAG source reading
- `src/airflow_unfactor/tools/lookup.py`: Knowledge lookup wrapper
- `src/airflow_unfactor/tools/search_docs.py`: Prefect docs search wrapper
- `src/airflow_unfactor/tools/validate.py`: Conversion validation
- `src/airflow_unfactor/tools/scaffold.py`: Project scaffolding
- `src/airflow_unfactor/external_mcp.py`: Prefect MCP HTTP client
- `src/airflow_unfactor/validation.py`: Python syntax validation via AST

**Testing:**
- `tests/conftest.py`: Shared fixtures (simple_etl_dag, fixtures_dir, snapshots_dir)
- `tests/test_*.py`: Unit tests for each module
- `tests/fixtures/simple_etl.py`: Minimal Airflow DAG for basic tests
- `tests/fixtures/astronomer-2-9/`: Comprehensive real-world DAG examples

## Naming Conventions

**Files:**
- Source files: lowercase with underscores (e.g., `read_dag.py`, `external_mcp.py`)
- Test files: `test_<module>.py` (e.g., `test_read_dag.py`)
- Config files: `pyproject.toml`, `.mcp.json`, `.pre-commit-config.yaml`

**Directories:**
- Package: lowercase with underscores (e.g., `airflow_unfactor`)
- Tools directory: `tools/` (plural, grouping related tools)
- Tests directory: `tests/` (plural, grouping all tests)
- Fixtures: `fixtures/` (descriptive, co-located with tests)

**Functions:**
- Async tools: `async def <concept>(...) -> str:` (always return JSON string)
- Utility functions: lowercase_with_underscores (e.g., `load_knowledge()`, `validate_python_syntax()`)
- Internal helpers: prefixed with `_` (e.g., `_write_pyproject_toml()`)

**Classes:**
- Data structures: PascalCase (e.g., `ValidationResult`)
- Test classes: `Test<Feature>` (e.g., `TestLookupConcept`)

**Variables:**
- Constants: UPPERCASE_WITH_UNDERSCORES (e.g., `DEFAULT_PREFECT_URL`, `FALLBACK_KNOWLEDGE`)
- Local: lowercase_with_underscores
- Fixtures: lowercase (e.g., `simple_etl_dag`, `astronomer_toys_dir`)

## Where to Add New Code

**New Tool/Feature:**
- Create async function in `src/airflow_unfactor/tools/<tool_name>.py`
- Register with `@mcp.tool` decorator in `src/airflow_unfactor/server.py`
- Return JSON string with consistent structure
- Add test file: `tests/test_<tool_name>.py`

**New Validation Function:**
- Add to `src/airflow_unfactor/validation.py`
- Return `ValidationResult` dataclass
- Test in `tests/test_validation.py`

**New Knowledge Mappings:**
- For temporary/fallback: Add to `FALLBACK_KNOWLEDGE` dict in `src/airflow_unfactor/knowledge.py`
- For permanent: Implement in Colin (`colin/models/`), then `colin run` generates JSON

**New Test Fixture:**
- DAG fixture: Add to `tests/fixtures/` (separate .py file)
- Snapshot: Auto-generated via `pytest --snapshot-update`
- Register in `tests/conftest.py` if reused across multiple tests

**Utility Functions:**
- General utilities: `src/airflow_unfactor/validation.py` (or new module if distinct domain)
- Tool-specific helpers: Keep in tool's own file (e.g., `_write_dockerfile()` in `scaffold.py`)

## Special Directories

**src/airflow_unfactor/tools/:**
- Purpose: MCP tool implementations
- Pattern: Each file contains one async function (sometimes with internal `_helper()` functions)
- All return JSON strings (serialization happens in each tool, not centrally)

**tests/fixtures/astronomer-2-9/:**
- Purpose: Real-world Airflow DAG examples from Astronomer
- Large fixture set for comprehensive testing
- Not committed to repository (in .gitignore based on ruff exclusions)
- Installed separately or generated via test setup

**tests/fixtures/snapshots/:**
- Purpose: Golden files for snapshot-based testing
- Generated: Run tests with `--snapshot-update` to generate
- Pattern: Compare actual output to golden; update when behavior is intentional
- Committed: Yes (provides version control for expected outputs)

**colin/output/:**
- Purpose: Colin-compiled translation knowledge in JSON format
- Generated: Via `colin run` command
- Format: JSON files indexed by concept name
- Fallback: `knowledge.py` has hardcoded FALLBACK_KNOWLEDGE if this directory is missing or empty

**.planning/codebase/:**
- Purpose: Architecture and structure documentation (generated by /gsd:map-codebase)
- Contains: ARCHITECTURE.md, STRUCTURE.md, and other analysis documents
- Not committed: Typically .gitignored (working directory for analysis)

---

*Structure analysis: 2026-02-26*
