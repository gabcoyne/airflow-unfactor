---
title: Troubleshooting
---

# Troubleshooting

Common issues and solutions when using airflow-unfactor.

## Parse Errors

### "SyntaxError: invalid syntax"

The DAG file has Python syntax errors. Fix them before conversion.

```bash
# Validate syntax
python -m py_compile your_dag.py
```

### "No DAG content provided"

Either `path` or `content` must be provided to the convert tool.

## Unsupported Patterns

### Custom Operators

Custom operators (not in the provider mappings) generate stub tasks with the original `execute()` method as context:

```python
@task(name="my_custom_task")
def my_custom_task():
    """TODO: Refactor from MyCustomOperator.

    Original execute() method:
    # ... extracted code ...
    """
    raise NotImplementedError("Refactor this custom operator")
```

**Solution**: Review the original `execute()` logic and implement as a Prefect task.

### Jinja2 Templates with Custom Variables

Templates using `{{ custom_var }}` that aren't in the standard set (`ds`, `ts`, `params.*`, `macros.*`) generate warnings:

```
Warning: Unknown Jinja2 pattern: {{ custom_var }}
```

**Solution**: Replace with Python f-strings using appropriate runtime context or flow parameters.

### Dynamic XCom Patterns

Patterns like `ti.xcom_pull(task_ids=some_variable)` where the task ID is dynamic cannot be statically migrated:

```
Warning: Dynamic XCom pattern detected - task_id is not a constant string
```

**Solution**: Refactor to pass data directly between tasks via function parameters.

## Trigger Rule Limitations

### Complex Trigger Rules

While `all_done`, `all_failed`, `one_failed`, `one_success`, and `none_failed` are migrated, the generated code may need review:

```python
# For trigger_rule="one_failed"
if any(s.is_failed() for s in [state1, state2]):
    downstream_task()
```

**Solution**: Review the generated state-checking logic and adjust for your specific use case.

## Connection/Block Issues

### Unknown Connection Type

```
Warning: Unknown connection type 'custom_conn'. Using generic Block scaffold.
```

**Solution**: Manually create the appropriate Prefect Block or use environment variables.

### Missing Prefect Integration Package

Generated Block scaffolds require Prefect integration packages:

```python
# Requires: pip install prefect-sqlalchemy
from prefect_sqlalchemy import SqlAlchemyConnector
```

**Solution**: Install the required package listed in the scaffold comments.

## External MCP Errors

### Timeout or Connection Errors

External MCP enrichment (Prefect docs, Astronomer migration guidance) is best-effort:

```json
{
  "external_context": {
    "prefect": {
      "ok": false,
      "error": "timeout"
    }
  }
}
```

**Solution**: Conversion proceeds without enrichment. Set `include_external_context=false` to skip external calls entirely.

## Validation Warnings

### Generated Code Syntax Errors

The converter validates that generated code compiles:

```
Warning: Generated flow code has syntax error: ...
```

**Solution**: This usually indicates a bug in the converter. Report the issue with your input DAG.

### Task Count Mismatch

```
Warning: Original DAG has 5 tasks, converted flow has 4 tasks
```

**Solution**: Review which tasks were skipped (usually `DummyOperator`/`EmptyOperator`) and verify this is expected.

## Validation Issues

The `validate` tool compares your original DAG with the converted flow to verify behavioral equivalence. Here are common issues:

### Task Count Mismatch (Validation)

```json
{
  "is_valid": false,
  "issues": ["Task count mismatch: DAG has 5 tasks, flow has 3 tasks"]
}
```

**Cause**: The validation excludes `DummyOperator`/`EmptyOperator` (not needed in Prefect), but other tasks may have been skipped.

**Solution**:
1. Check the conversion warnings for skipped operators
2. Verify custom operators were handled correctly
3. Review the generated flow for missing task implementations

### Dependency Graph Mismatch

```json
{
  "is_valid": false,
  "issues": ["Dependency mismatch: edge (extract, transform) not found in flow"]
}
```

**Cause**: The task dependency structure differs between DAG and flow.

**Solution**:
1. Check that tasks are called in the correct order in the flow
2. Verify `wait_for` or data passing preserves dependencies
3. Review complex patterns like fan-out/fan-in

### Data Flow Warnings

```json
{
  "issues": ["XCom pattern 'ti.xcom_pull(task_ids=\"extract\")' not converted to parameter"]
}
```

**Cause**: XCom pulls should become function parameters in Prefect.

**Solution**:
1. Ensure the converted task receives data as a parameter
2. Check that upstream tasks return values
3. For multi-task pulls, verify all sources are connected

### Low Confidence Scores

```json
{
  "confidence_score": 45,
  "is_valid": true
}
```

**Cause**: Confidence decreases with:
- Many tasks (complex DAGs)
- Custom/unknown operators
- Dynamic patterns that can't be statically analyzed
- Partial dependency matches

**Solution**:
1. Scores above 70 are generally reliable
2. Scores 50-70 warrant manual review
3. Scores below 50 indicate significant manual work needed
4. Focus on the specific `issues` rather than the score

### Validation Timeout

For very large DAGs, validation may timeout:

```json
{
  "error": "Validation timeout: DAG has 200+ tasks"
}
```

**Solution**: Consider splitting large DAGs into smaller flows, which is a Prefect best practice anyway.

## Getting Help

1. Check the [examples](examples.md) for similar patterns
2. Review the [operator mapping](operator-mapping.md) reference
3. Use the [validation tool](tools/validate.md) to verify conversions
4. File an issue at [github.com/prefecthq/airflow-unfactor](https://github.com/prefecthq/airflow-unfactor/issues)
