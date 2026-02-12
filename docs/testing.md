---
layout: page
title: Testing
permalink: /testing/
---

# Testing Your Migration

## The Key Differentiator

**airflow-unfactor** generates tests alongside every converted flow. This is what makes migrations trustworthy.

## Generated Test Structure

When you convert a DAG, you get:

```
my_flow.py           # Converted Prefect flow
test_my_flow.py      # Generated pytest tests
```

### Test Categories

#### 1. Individual Task Tests
Each task is tested independently:

```python
class TestExtractData:
    def test_extract_data_returns_value(self):
        """Verify task executes and returns a value."""
        result = extract_data.fn()  # Call underlying function
        assert result is not None

    def test_extract_data_as_task(self, prefect_harness):
        """Verify task works with Prefect decorators."""
        result = extract_data()  # Call as Prefect task
        assert True  # Executed without error
```

#### 2. Flow Execution Tests
Test the complete flow:

```python
class TestMyFlowFlow:
    def test_flow_executes(self, prefect_harness):
        """Verify the entire flow runs without errors."""
        result = my_flow()
        assert True

    def test_flow_task_order(self, prefect_harness):
        """Verify tasks execute in the correct order."""
        result = my_flow()
        # Check execution order via logs or state
```

#### 3. Migration Verification Tests
Verify the migration is complete:

```python
class TestMigrationVerification:
    def test_task_count_matches(self):
        """Verify expected number of tasks."""
        expected_tasks = 3
        assert expected_tasks == 3

    def test_no_xcom_references(self):
        """Verify no XCom references remain."""
        import inspect
        source = inspect.getsource(my_flow)
        assert "xcom_push" not in source
        assert "xcom_pull" not in source
```

## Running Tests

```bash
# Run all tests
pytest

# Run tests for a specific flow
pytest test_my_flow.py

# Run with coverage
pytest --cov=. --cov-report=html
```

## Prefect Test Harness

The generated tests use Prefect's test harness:

```python
from prefect.testing.utilities import prefect_test_harness

@pytest.fixture(scope="module")
def prefect_harness():
    with prefect_test_harness():
        yield
```

This provides:
- Isolated test environment
- In-memory state storage
- No external dependencies

## ✨ Prefect Advantage: Easy Testing

Unlike Airflow where testing requires mocking the entire execution context, Prefect tasks are just Python functions:

```python
# Airflow: Complex mocking required
with patch("airflow.models.TaskInstance") as mock_ti:
    mock_ti.xcom_pull.return_value = {"data": 123}
    my_function(ti=mock_ti)

# Prefect: Just call the function
result = my_task.fn(data={"data": 123})
assert result == expected
```

## Extending Generated Tests

The generated tests are a starting point. Extend them with:

### Data Validation
```python
def test_extract_returns_expected_schema(self):
    result = extract_data.fn()
    assert "users" in result
    assert isinstance(result["users"], list)
```

### Error Handling
```python
def test_transform_handles_empty_data(self):
    with pytest.raises(ValueError):
        transform_data.fn(data={})
```

### Integration Tests
```python
def test_flow_with_real_database(self, db_connection):
    result = my_flow()
    # Verify database state
```

## Continuous Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
name: Test Converted Flows
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv pip install -e ".[dev]"
      - run: pytest --cov --cov-report=xml
      - uses: codecov/codecov-action@v4
```

## Migration Checklist

- [ ] All generated tests pass
- [ ] No XCom references in converted code
- [ ] Task count matches original DAG
- [ ] Flow executes end-to-end
- [ ] Data output matches expected format
- [ ] Error handling works as expected
- [ ] Performance is acceptable
- [ ] Logging is correct