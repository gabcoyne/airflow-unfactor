# PROJECT.md — airflow-unfactor

> *"Airflow is for airports. Welcome to modern orchestration."*

## Overview

An MCP (Model Context Protocol) server that converts Apache Airflow DAGs to Prefect flows using AI-assisted analysis. Educates users on Prefect's advantages while producing clean, idiomatic Python code.

## Philosophy

- **Liberation, not migration** — Help users escape Airflow's complexity
- **Educational** — Comments explain *why* Prefect does it better, not just *what* changed  
- **Complete** — Handle all operators, not just the easy ones
- **TDD** — Every feature starts with a failing test
- **Beads** — Task tracking with `bd` for structured, agent-friendly development

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | Match Prefect's target |
| Protocol | MCP SDK | Agent-native interface |
| Task Tracking | Beads (`bd`) | Dependency-aware graph for AI agents |
| Testing | pytest + hypothesis | TDD with property-based testing |
| AI Backend | Model-agnostic | Claude, GPT, or local models |
| Package Manager | uv | Fast, modern Python tooling |

## MCP Tools

### `analyze_dag`
Analyze an Airflow DAG file without converting.

**Input:**
```json
{
  "path": "string (file path or '-' for stdin)",
  "content": "string (optional, raw DAG code)"
}
```

**Output:**
```json
{
  "dag_id": "string",
  "operators": [{"type": "PythonOperator", "task_id": "...", "count": 1}],
  "dependencies": [["task_a", "task_b"]],
  "xcom_usage": ["task_a pushes", "task_b pulls"],
  "complexity_score": 42,
  "conversion_notes": ["Uses dynamic task mapping", "Has 3 sensors"]
}
```

### `convert_dag`
Convert an Airflow DAG to a Prefect flow.

**Input:**
```json
{
  "path": "string",
  "content": "string (optional)",
  "options": {
    "prefect_version": "3",
    "include_comments": true,
    "comment_style": "educational"
  }
}
```

**Output:**
```json
{
  "flow_code": "string (Python code)",
  "imports": ["from prefect import flow, task"],
  "warnings": ["Sensor converted to polling - consider Prefect triggers"],
  "original_to_new_mapping": {"extract_task": "extract_data"}
}
```

### `validate_conversion`
Validate that a converted flow matches the original DAG's behavior.

### `explain_concept`
Explain an Airflow concept and its Prefect equivalent.

### `batch_convert`
Convert multiple DAGs in a directory.

## Operator Mapping

See docs/operator_mapping.md for complete table.

## TDD Workflow with Beads

```bash
bd create "Convert PythonOperator to @task" -p 1
# Write failing test
bd update <id> --claim
# Implement
bd update <id> --done
```

## References

- [Prefect Migration Guide](https://docs.prefect.io/v3/how-to-guides/migrate/airflow)
- [MCP Protocol Spec](https://modelcontextprotocol.io/)
- [Beads Documentation](https://github.com/steveyegge/beads)
