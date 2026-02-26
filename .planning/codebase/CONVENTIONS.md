# Coding Conventions

**Analysis Date:** 2026-02-26

## Naming Patterns

**Files:**
- All lowercase with underscores: `read_dag.py`, `validation.py`, `external_mcp.py`
- Test files: `test_*.py` format (e.g., `test_validation.py`, `test_read_dag.py`)
- Package directories: lowercase with underscores (e.g., `airflow_unfactor/tools/`)

**Functions:**
- Snake case for all functions: `read_dag()`, `lookup_concept()`, `validate_python_syntax()`
- All async functions use `async def` with explicit return type hints
- Private helper functions prefixed with underscore: `_write_pyproject_toml()`, `_mock_call_tool_result()`

**Variables:**
- Snake case throughout: `output_directory`, `syntax_result`, `created_files`
- Type hints required on function parameters and returns (enforced by pyright)
- Union types use `|` syntax: `str | None`, `list[str] | None`

**Classes:**
- PascalCase for all classes: `ValidationResult`
- Dataclasses used for simple data containers with `@dataclass` decorator
- All dataclass fields have type hints

## Code Style

**Formatting:**
- Line length: 100 characters (enforced by ruff)
- Indentation: 4 spaces (enforced by ruff-format)
- Tool: ruff via pre-commit hooks

**Linting:**
- Tool: ruff (v0.5.0)
- Enabled rule sets: E, F, I, UP, B, SIM, TCH
- Disabled rules: E501 (line length, handled by formatter), SIM102, SIM103, SIM108, SIM118
- Type checking: pyright (v1.1.390) enforced via pre-commit

## Import Organization

**Order:**
1. Standard library imports (`json`, `os`, `pathlib`)
2. Third-party imports (`fastmcp`, `pytest`)
3. Local imports (`from airflow_unfactor...`)

Enforced by ruff's isort plugin.

**Path Aliases:**
- First-party imports defined as `airflow_unfactor` in ruff config
- All relative imports converted to absolute: `from airflow_unfactor.tools.read_dag import read_dag`

**Example pattern from `server.py`:**
```python
from fastmcp import FastMCP

from airflow_unfactor.tools.lookup import lookup_concept as _lookup_concept
from airflow_unfactor.tools.read_dag import read_dag as _read_dag
```

## Error Handling

**Pattern: Explicit JSON error responses**
- All tool functions return JSON strings (never raise exceptions)
- Error responses include `"error"` key with descriptive message
- Example from `read_dag.py`:
```python
if not path and not content:
    return json.dumps({"error": "Either path or content must be provided"})

if not file.exists():
    return json.dumps({"error": f"File not found: {path}", "source": None})
```

**Pattern: Validation and error collection**
- `ValidationResult` dataclass wraps validation outcome with optional error details
- `validate_python_syntax()` catches `SyntaxError` and extracts line/column info
- `validate_generated_code()` returns list of warning strings (never throws)

**Pattern: MCP failures return explicit error dicts**
- `search_prefect_mcp()` catches all exceptions, categorizes by type (connection, timeout, generic)
- Returns `{"error": "..."}` dict structure for all failures
- Provides actionable advice in error messages

## Logging

**Framework:** No logging framework; uses `json.dumps()` for structured output

**Patterns:**
- All tool functions return JSON-serialized results
- Errors are JSON objects with `"error"` key
- Status indicators: `"status": "found"` or `"status": "not_found"` in lookup results
- Success includes source attribution: `"source": "colin"` or `"source": "fallback"`

## Comments

**When to Comment:**
- Module-level docstrings (present on all .py files)
- Function docstrings with Args, Returns, and description
- Complex logic (rare — code is intentionally straightforward)

**JSDoc/TSDoc:**
- Uses Python docstring format (three-quote strings)
- All public functions have docstrings
- Args and Returns documented in all tool functions
- Example from `read_dag.py`:
```python
async def read_dag(
    path: str | None = None,
    content: str | None = None,
) -> str:
    """Read a DAG file and return raw source with metadata.

    Accepts a file path or inline content. Returns the source code,
    file path, size, and line count. The LLM reads the code directly.

    Args:
        path: Path to a DAG file on disk.
        content: Inline DAG source code.

    Returns:
        JSON with source, file_path, file_size_bytes, line_count — or error.
    """
```

## Function Design

**Size:**
- Functions kept small and focused (most under 50 lines)
- MCP tool registration functions are thin wrappers that delegate to implementation functions
- Helper functions prefixed with underscore (e.g., `_write_pyproject_toml()`)

**Parameters:**
- Optional parameters use `| None` union syntax with default values
- Type hints required on all parameters
- Maximum 4-5 parameters; complex cases use overloads (rarely needed)

**Return Values:**
- All public tool functions return JSON strings (`-> str`)
- Internal functions return typed values (dicts, bools, lists)
- JSON return for tools ensures MCP compatibility

**Example from `validation.py`:**
```python
def validate_python_syntax(code: str) -> ValidationResult:
    """Validate that code is syntactically valid Python.

    Args:
        code: Python source code to validate

    Returns:
        ValidationResult with valid=True if code parses,
        or valid=False with error details
    """
    try:
        ast.parse(code)
        return ValidationResult(valid=True)
    except SyntaxError as e:
        return ValidationResult(
            valid=False,
            error=e.msg,
            line=e.lineno,
            column=e.offset,
        )
```

## Module Design

**Exports:**
- All files explicitly export their public API
- Tools exported from `airflow_unfactor.server` for MCP registration
- Tool implementations exported from `airflow_unfactor.tools.*`

**Barrel Files:**
- `__init__.py` files minimal (mostly empty or docstring only)
- Tool registration happens in `server.py` via `@mcp.tool` decorators

**File Organization:**
- `tools/` directory: all MCP tool implementations
- Core utilities in root: `validation.py`, `knowledge.py`, `external_mcp.py`
- Each tool is independent, takes no dependencies on other tools

## Type Safety

**Requirements:**
- All function signatures must have type hints
- pyright configured to enforce (pre-commit hook)
- Union types use `|` operator (PEP 604): `str | None`
- Generic types explicit: `list[str]`, `dict[str, Any]`

**Example:**
```python
def lookup(concept: str, knowledge: dict[str, Any]) -> dict[str, Any]:
    """Look up a concept in the knowledge base."""
```

---

*Convention analysis: 2026-02-26*
