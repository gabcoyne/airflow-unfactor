# Testing Patterns

**Analysis Date:** 2026-02-26

## Test Framework

**Runner:**
- pytest (>= 8.0.0)
- Config: `pyproject.toml` under `[tool.pytest.ini_options]`

**Async Support:**
- pytest-asyncio (>= 0.23.0)
- Config: `asyncio_default_fixture_loop_scope = "function"`

**Coverage:**
- pytest-cov (>= 4.1.0)
- Run: `pytest --cov=src/airflow_unfactor`
- Source: `src/airflow_unfactor`
- Branch coverage enabled

**Run Commands:**
```bash
pytest                              # Run all tests
pytest -v                          # Verbose output
pytest --cov                       # Run with coverage report
pytest tests/test_validation.py    # Run specific file
pytest -k "test_valid"             # Run tests matching pattern
```

## Test File Organization

**Location:** `tests/` directory at project root

**Naming:**
- Test files: `test_*.py` (e.g., `test_validation.py`, `test_read_dag.py`)
- Test classes: `Test*` (e.g., `TestValidatePythonSyntax`)
- Test methods: `test_*` (e.g., `test_valid_code`)

**Structure:**
```
tests/
├── conftest.py                 # Pytest fixtures and configuration
├── fixtures/                   # Test data files
│   ├── simple_etl.py
│   ├── snapshots/              # Snapshot golden files
│   └── astronomer-2-9/         # Astronomer reference DAGs
└── test_*.py                   # Test modules (8 files)
```

## Test Structure

**Suite Organization (from `test_validation.py`):**
```python
class TestValidatePythonSyntax:
    """Tests for validate_python_syntax function."""

    def test_valid_code(self):
        """Valid Python code should pass validation."""
        code = """..."""
        result = validate_python_syntax(code)
        assert result.valid is True
```

**Patterns:**
- One test class per main function or feature
- Descriptive class docstrings with focused test purpose
- Individual test methods with one assertion focus
- Test docstrings describe the specific behavior being tested

**Setup/Teardown:**
- No explicit setup/teardown used (tests are stateless)
- Fixtures from `conftest.py` for shared data
- Temporary directories via `tmp_path` fixture (pytest built-in)

**Example from `test_scaffold.py`:**
```python
class TestScaffoldProject:
    """Tests for scaffold_project function."""

    def test_scaffold_creates_directory_structure(self, tmp_path):
        """Test scaffolding creates basic directory structure."""
        output_dir = tmp_path / "output"

        result_json = asyncio.run(
            scaffold_project(output_directory=str(output_dir))
        )
        result = json.loads(result_json)

        assert output_dir.exists()
        assert (output_dir / "deployments").exists()
```

## Async Testing

**Pattern:**
- Use `asyncio.run()` to execute async functions in tests
- No special decorators needed (pytest-asyncio handles compatibility)
- Example from `test_read_dag.py`:
```python
def test_read_by_path(self, tmp_path):
    """Read a DAG file by path returns source and metadata."""
    dag_file = tmp_path / "my_dag.py"
    dag_file.write_text("from airflow import DAG\n...")

    result = json.loads(asyncio.run(read_dag(path=str(dag_file))))

    assert result["source"] == "from airflow import DAG\n..."
```

## Mocking

**Framework:** unittest.mock (standard library)

**Patterns:**
- Use `@patch` decorator for external dependencies
- `AsyncMock` for async functions
- `MagicMock` for sync functions and complex objects

**Example from `test_external_mcp.py`:**
```python
from unittest.mock import AsyncMock, MagicMock, patch

def _mock_call_tool_result(texts: list[str]):
    """Create a mock CallToolResult with text content items."""
    result = MagicMock()
    items = []
    for text in texts:
        item = MagicMock()
        item.text = text
        items.append(item)
    result.content = items
    return result

class TestSearchPrefectMCP:
    """Tests for search_prefect_mcp function."""

    def test_success_returns_results(self, monkeypatch):
        """Successful call returns search results."""
        monkeypatch.setenv("MCP_PREFECT_ENABLED", "true")

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.call_tool = AsyncMock(
            return_value=_mock_call_tool_result(["Title: Prefect Flows\n..."])
        )

        with patch("airflow_unfactor.external_mcp.Client", return_value=mock_client):
            result = asyncio.run(search_prefect_mcp("Prefect flows"))

        assert "results" in result
        assert len(result["results"]) == 1
        mock_client.call_tool.assert_called_once_with("SearchPrefect", {"query": "Prefect flows"})
```

**What to Mock:**
- External I/O: `Client` connections, file system (use `tmp_path` instead)
- Environment variables: use `monkeypatch.setenv()`
- External services: HTTP clients, MCP servers

**What NOT to Mock:**
- Core logic functions (validate_python_syntax, lookup, etc.)
- JSON parsing and serialization
- Simple utility functions
- Built-in types and operations

## Fixtures

**Test Data (from `conftest.py`):**
```python
FIXTURES_DIR = Path(__file__).parent / "fixtures"
ASTRONOMER_TOYS = FIXTURES_DIR / "astronomer-2-9" / "dags" / "toys"
SNAPSHOTS_DIR = FIXTURES_DIR / "snapshots"

@pytest.fixture
def simple_etl_dag():
    return (FIXTURES_DIR / "simple_etl.py").read_text()

@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR

@pytest.fixture
def astronomer_toys_dir():
    return ASTRONOMER_TOYS

@pytest.fixture
def snapshots_dir():
    return SNAPSHOTS_DIR
```

**Location:**
- Shared fixtures in `tests/conftest.py`
- Test data (DAG files) in `tests/fixtures/`
- Snapshot golden files in `tests/fixtures/snapshots/`

**Snapshot Mode:**
- Custom pytest option: `--snapshot-update`
- Fixture `snapshot_update` checks if update mode enabled
- Used for comparing generated output against golden files

## Coverage

**Requirements:** No minimum enforced, but coverage tracking enabled

**View Coverage:**
```bash
pytest --cov --cov-report=html
# Opens htmlcov/index.html in browser
```

**Excluded Patterns (from `pyproject.toml`):**
```
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

**Current Stats:**
- 768 lines of test code across 8 test modules
- 60 tests currently passing
- Tests cover: validation, knowledge lookup, reading DAGs, scaffolding, external MCP

## Test Types

**Unit Tests (Primary):**
- Test single functions in isolation
- Examples: `test_valid_code()`, `test_syntax_error()`, `test_exact_match()`
- Mock external dependencies

**Integration Tests:**
- Test multiple functions working together
- Example: `test_scaffold_creates_directory_structure()` — creates directories, reads files, verifies output
- Use real file system (via `tmp_path`)

**E2E Tests:**
- Not currently implemented
- Could test entire DAG→Flow conversion flow end-to-end

## Common Test Patterns

**Error Response Testing:**
```python
def test_missing_args(self):
    """Neither path nor content returns error."""
    result = json.loads(asyncio.run(read_dag()))

    assert result["error"] == "Either path or content must be provided"
```

**File I/O Testing:**
```python
def test_read_by_path(self, tmp_path):
    """Read a DAG file by path returns source and metadata."""
    dag_file = tmp_path / "my_dag.py"
    dag_file.write_text("from airflow import DAG\ndag = DAG('test')\n")

    result = json.loads(asyncio.run(read_dag(path=str(dag_file))))

    assert result["file_path"] == str(dag_file.resolve())
    assert result["file_size_bytes"] == dag_file.stat().st_size
```

**JSON Validation Testing:**
```python
def test_scaffold_with_project_name(self, tmp_path):
    """Test scaffolding with custom project name."""
    output_dir = tmp_path / "output"

    result_json = asyncio.run(
        scaffold_project(
            output_directory=str(output_dir),
            project_name="my_custom_project",
        )
    )
    result = json.loads(result_json)

    assert result["project_name"] == "my_custom_project"
```

**Case-Insensitive Matching:**
```python
def test_case_insensitive_match(self):
    """Case-insensitive match works."""
    knowledge = {"PythonOperator": {"concept_type": "operator"}}
    result = lookup("pythonoperator", knowledge)
    assert result["status"] == "found"
```

## Test Data

**Sources:**
- `tests/fixtures/simple_etl.py` — simple test DAG
- `tests/fixtures/astronomer-2-9/` — Astronomer reference DAGs (excluded from ruff linting)
- `tests/fixtures/snapshots/` — golden output files (excluded from ruff linting)

**Usage:**
- DAG content fixtures passed to tools for testing conversion logic
- Snapshot files for comparing generated code against expected output

---

*Testing analysis: 2026-02-26*
