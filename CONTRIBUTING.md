# Contributing to airflow-unfactor

Thanks for your interest in contributing to airflow-unfactor! This guide covers the development workflow, from spec to implementation to testing.

## Development Setup

```bash
# Clone and install
git clone https://github.com/prefecthq/airflow-unfactor.git
cd airflow-unfactor
uv pip install -e ".[dev]"

# Run tests
pytest

# Run specific test file
pytest tests/test_convert_tool.py -v
```

## Project Structure

```
airflow-unfactor/
├── src/airflow_unfactor/
│   ├── server.py              # MCP server entrypoint
│   ├── tools/                 # MCP tool implementations
│   │   ├── convert.py         # Main convert tool
│   │   ├── analyze.py         # DAG analysis
│   │   ├── validate.py        # Conversion validation
│   │   ├── batch.py           # Batch conversion
│   │   └── scaffold.py        # Project skeleton generator
│   ├── converters/            # Pattern-specific converters
│   │   ├── base.py            # Core DAG→flow conversion
│   │   ├── dynamic_mapping.py # .expand() → .map()
│   │   ├── taskgroup.py       # TaskGroup → subflow
│   │   ├── trigger_rules.py   # Trigger rules → state checks
│   │   ├── jinja.py           # Jinja2 → runtime context
│   │   ├── connections.py     # Hooks → Blocks
│   │   ├── variables.py       # Variables → Secrets/params
│   │   └── runbook.py         # Migration runbook generation
│   ├── analysis/              # DAG parsing and analysis
│   └── external_mcp.py        # External MCP client
├── tests/                     # Test suite
├── docs/                      # Jekyll documentation
├── schemas/                   # JSON schemas
└── openspec/                  # OpenSpec change tracking
```

## The OpenSpec Workflow

We use OpenSpec to track changes from proposal through implementation. This ensures docs, specs, and code stay aligned.

### 1. Starting a New Change

```bash
# Create a new change
openspec new change "my-feature"

# This creates:
# openspec/changes/my-feature/
#   ├── proposal.md      # Why this change?
#   ├── design.md        # How will it work?
#   ├── specs/           # Detailed specifications
#   └── tasks.md         # Implementation tasks
```

### 2. Writing Artifacts

**proposal.md** — The "why"
- What problem does this solve?
- Who benefits?
- What are the acceptance criteria?

**design.md** — The "how"
- Architecture decisions
- API design
- Trade-offs considered

**specs/** — The details
- One spec per capability
- Include examples and edge cases
- Define the output contract

**tasks.md** — The work
- Ordered implementation steps
- Check off as you complete

### 3. Implementation

Follow the tasks in order. For each task:

1. **Write tests first** — Define expected behavior
2. **Implement the feature** — Make tests pass
3. **Update docs** — Keep docs in sync with code
4. **Check the task** — Mark complete in tasks.md

### 4. Archiving

When complete:
```bash
openspec archive change "my-feature"
```

This moves specs to the main specs directory and closes the change.

## Adding a New Converter

To add support for a new Airflow pattern:

### 1. Create the Spec

```bash
# Create spec file
touch openspec/changes/my-change/specs/new-pattern.openspec.md
```

Define:
- What patterns are detected
- What output is generated
- Edge cases and limitations

### 2. Write Tests

```python
# tests/test_new_pattern_converter.py

class TestNewPatternDetection:
    def test_detects_pattern(self):
        code = '''
        # Airflow code with pattern
        '''
        result = extract_new_pattern(code)
        assert len(result) == 1
        assert result[0].name == "expected"

class TestNewPatternConversion:
    def test_converts_simple_case(self):
        code = '''...'''
        result = convert_new_pattern(code)
        assert "expected_output" in result["prefect_code"]
```

### 3. Implement the Converter

```python
# src/airflow_unfactor/converters/new_pattern.py

from dataclasses import dataclass

@dataclass
class NewPatternInfo:
    """Detected pattern information."""
    name: str
    # ... other fields

def extract_new_pattern(code: str) -> list[NewPatternInfo]:
    """Extract patterns from Airflow code."""
    patterns = []
    # Parse and extract
    return patterns

def convert_new_pattern(
    code: str,
    include_comments: bool = True,
) -> dict[str, object]:
    """Convert patterns to Prefect equivalent."""
    patterns = extract_new_pattern(code)
    # Generate Prefect code
    return {
        "prefect_code": generated_code,
        "warnings": warnings,
    }
```

### 4. Integrate with Convert Tool

```python
# src/airflow_unfactor/tools/convert.py

from airflow_unfactor.converters.new_pattern import (
    extract_new_pattern,
    convert_new_pattern,
)

# In convert_dag():
patterns = extract_new_pattern(content)
if patterns:
    pattern_result = convert_new_pattern(content)
    result["new_pattern_code"] = pattern_result.get("prefect_code", "")
    result.setdefault("warnings", []).extend(pattern_result.get("warnings", []))
```

### 5. Update Documentation

- Add section to relevant conversion guide in `docs/conversion/`
- Update `docs/operator-mapping.md` if adding operator support
- Add examples to `docs/examples.md`

## Output Contract Changes

When changing the convert tool output:

### 1. Update JSON Schema

Edit `schemas/conversion-output.json`:

```json
{
  "properties": {
    "new_field": {
      "type": "string",
      "description": "Description of the new field"
    }
  }
}
```

### 2. Update Response Reference

Edit `docs/convert-reference.md` to document the new field.

### 3. Update Tests

Add tests for the new output:

```python
def test_convert_includes_new_field(self):
    result_json = asyncio.run(convert_dag(content=dag_code))
    result = json.loads(result_json)
    assert "new_field" in result
    assert result["new_field"] == expected_value
```

## Testing Guidelines

### Test Organization

```
tests/
├── test_convert_tool.py       # Integration tests for convert
├── test_analyze_tool.py       # Analysis tests
├── test_*_converter.py        # Converter-specific tests
├── test_external_mcp.py       # External client tests
└── fixtures/                  # Test DAG files
```

### Test Patterns

**Pattern detection tests:**
```python
def test_detects_pattern(self):
    code = '''...'''
    result = extract_pattern(code)
    assert len(result) == expected_count
```

**Conversion tests:**
```python
def test_converts_to_prefect(self):
    code = '''...'''
    result = convert_pattern(code)
    assert "expected_output" in result["prefect_code"]
```

**Edge case tests:**
```python
def test_handles_edge_case(self):
    code = '''...'''
    result = convert_pattern(code)
    assert "warning" in result["warnings"][0].lower()
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov --cov-report=html

# Specific file
pytest tests/test_convert_tool.py -v

# Specific test
pytest tests/test_convert_tool.py::TestConvertDAG::test_simple_dag -v
```

## Code Style

- Python 3.11+ features are welcome
- Use type hints
- Keep functions focused (single responsibility)
- Prefer dataclasses for structured data
- Use descriptive variable names

## Pull Request Process

1. **Create a branch** from `main`
2. **Write tests** before implementing
3. **Ensure all tests pass** (`pytest`)
4. **Update documentation** if needed
5. **Create PR** with clear description
6. **Address review feedback**

## Questions?

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- Tag maintainers for urgent items

---

Made with love by [Prefect](https://prefect.io)
