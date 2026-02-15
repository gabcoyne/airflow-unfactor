---
layout: page
title: Wizard Quickstart
permalink: /wizard/quickstart/
---

# Wizard Quickstart

Migrate your first DAG using the visual wizard.

## Prerequisites

- Python 3.11+
- airflow-unfactor with UI extras:

```bash
pip install airflow-unfactor[ui]
```

## Start the Wizard

```bash
airflow-unfactor --ui
```

This starts an HTTP server at `http://localhost:8765`.

To use a different port:
```bash
airflow-unfactor --ui --port 9000
```

## Step 1: Select DAGs

1. Enter the path to your DAG directory
2. The wizard lists all `.py` files that contain DAG definitions
3. Check the DAGs you want to migrate
4. Click **Analyze**

**Tip**: Start with a simple DAG to get familiar with the process.

## Step 2: Review Analysis

For each selected DAG, you'll see:

- **Operators**: Types and counts of Airflow operators used
- **Dependencies**: Task execution order
- **Complexity Score**: 0-100 rating based on patterns detected
- **Conversion Notes**: Patterns that may need attention

Review any warnings. Common issues:
- Custom operators (generate stubs, require manual work)
- Jinja2 templates (may need runtime context)
- Dynamic XCom patterns (may need refactoring)

## Step 3: Configure Conversion

Choose your conversion options:

### Include Comments
When enabled, the converted code includes educational comments explaining Prefect patterns:

```python
# ✨ Prefect Advantage: Direct Data Passing
# No XCom push/pull - data flows in-memory between tasks.
```

Recommended for learning. Disable for cleaner production code.

### Generate Tests
Creates pytest tests for each converted flow:

```python
def test_my_flow_runs():
    """Test that the flow executes without errors."""
    result = my_flow()
    assert result is not None
```

### Migration Runbook
Generates a markdown guide with:
- DAG-specific configuration notes
- Schedule migration instructions
- Connection setup checklist
- Manual TODO items

## Step 4: Validate

The wizard validates your conversions:

- **Task Count**: Same number of tasks (excluding DummyOperator)
- **Dependencies**: Execution order preserved
- **Data Flow**: XCom patterns converted to parameters

Review the **Confidence Score**:
- **70-100**: High confidence, minimal review needed
- **50-70**: Review flagged issues
- **Below 50**: Significant manual work expected

## Step 5: Configure Project

Set up your Prefect project structure:

- **Project Name**: Name for the generated project
- **Workspace**: Prefect workspace name
- **Include Dockerfile**: Add container configuration
- **Include GitHub Actions**: Add CI workflow

## Step 6: Configure Deployment

Set up Prefect deployment:

- **Work Pool**: Name of the work pool to use
- **Schedule**: Cron expression (if DAG had a schedule)
- **Tags**: Labels for the deployment

## Step 7: Export

Review and download your project:

1. Browse the generated file tree
2. Preview any file's contents
3. Click **Download ZIP** to get the complete project

## After Export

1. **Extract the ZIP** to your desired location
2. **Review the code** - check for TODO comments
3. **Install dependencies**: `pip install -e .`
4. **Run tests**: `pytest`
5. **Deploy**: `prefect deploy --all`

## Troubleshooting

### Server won't start
Make sure aiohttp is installed:
```bash
pip install airflow-unfactor[ui]
```

### DAGs not detected
Ensure your files contain valid DAG definitions with `from airflow import DAG` or `@dag` decorator.

### Low confidence scores
Review the specific issues flagged. Common causes:
- Custom operators
- Complex trigger rules
- Dynamic task generation

## Next Steps

- [Migration Examples](../examples.md)
- [Operator Mapping](../operator-mapping.md)
- [Testing Guide](../testing.md)
