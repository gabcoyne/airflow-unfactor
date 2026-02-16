# Design: Clean Up Deprecated Template-Based Code

## Architecture Decision Record

### Context

The project underwent a fundamental architecture shift from **deterministic template-based code generation** to **LLM-assisted code generation**. The old approach attempted to programmatically convert Airflow DAGs to Prefect flows using templates and pattern matching. The new approach provides rich analysis payloads that inform an LLM to generate idiomatic Prefect code.

### Previous Architecture (Deprecated)

```
┌─────────────────────────────────────────────────────────────┐
│                    airflow-unfactor                          │
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │  analyze()  │───►│  convert()  │───►│  validate() │      │
│  │             │    │             │    │             │      │
│  │ Parse DAG   │    │ Template    │    │ Compare     │      │
│  │ Extract     │    │ Generation  │    │ Structure   │      │
│  │ Structure   │    │ (base.py)   │    │             │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│                           │                                  │
│                           ▼                                  │
│                    ┌─────────────┐                          │
│                    │ flow_code   │  Deterministic output    │
│                    │ test_code   │  (often incorrect/       │
│                    │ runbook     │   non-idiomatic)         │
│                    └─────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

**Problems with this approach:**
1. Template-based generation produced non-idiomatic Prefect code
2. Could not handle complex patterns (dynamic tasks, custom operators, etc.)
3. Generated code often required significant manual fixes
4. Test generation was placeholder-only
5. Maintenance burden of keeping templates up-to-date

### New Architecture (Current)

```
┌─────────────────────────────────────────────────────────────┐
│                    airflow-unfactor                          │
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │  analyze()  │    │get_context()│    │  validate() │      │
│  │             │    │             │    │             │      │
│  │ Rich JSON   │    │ Prefect     │    │ Structural  │      │
│  │ Payload:    │    │ Docs &      │    │ Comparison  │      │
│  │ - structure │    │ Patterns    │    │             │      │
│  │ - patterns  │    │ - mappings  │    │             │      │
│  │ - config    │    │ - examples  │    │             │      │
│  │ - runbook   │    │             │    │             │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│         │                  │                                 │
│         └────────┬─────────┘                                │
│                  ▼                                          │
│         ┌─────────────────┐                                 │
│         │   LLM Context   │                                 │
│         │   for Code Gen  │                                 │
│         └─────────────────┘                                 │
│                  │                                          │
│                  ▼                                          │
│         ┌─────────────────┐                                 │
│         │  LLM generates  │  Idiomatic, context-aware      │
│         │  Prefect code   │  output tailored to DAG        │
│         └─────────────────┘                                 │
└─────────────────────────────────────────────────────────────┘
```

**Benefits of new approach:**
1. LLM generates idiomatic Prefect code naturally
2. Rich context enables handling of complex patterns
3. Migration runbook provides human-readable guidance
4. Operator/connection mappings guide the LLM
5. No code generation = no maintenance of templates

## What Was Removed

### Deleted Files

| File | Purpose | Reason for Removal |
|------|---------|-------------------|
| `tools/convert.py` | MCP tool wrapping template conversion | Deprecated - replaced by analyze + LLM |
| `tools/batch.py` | Batch conversion of multiple DAGs | Deprecated - never fully implemented |
| `converters/base.py` | `convert_dag_to_flow()` template engine | Core of old approach - now obsolete |
| `converters/test_generator.py` | Placeholder test scaffolding | Never worked properly |
| `.ralph/examples/basic_conversion.py` | Example using old API | Referenced deleted code |

### Updated Files

| File | Change |
|------|--------|
| `server.py` | Removed `convert` and `batch` tool registrations |
| `http_server.py` | Removed `/api/convert` endpoint |
| `converters/__init__.py` | Removed `convert_dag_to_flow` export |
| `tools/scaffold.py` | Simplified to directory-only scaffolding |

### Test Files Removed/Updated

| File | Action |
|------|--------|
| `tests/test_convert.py` | Deleted |
| `tests/test_convert_tool.py` | Deleted |
| `tests/test_conversion_core_p3.py` | Deleted |
| `tests/test_dag_settings_parser.py` | Removed `TestRunbookSpecificity` class |
| `tests/test_astronomer_fixtures.py` | Removed conversion tests |
| `tests/test_http_server.py` | Removed convert endpoint tests |
| `tests/test_scaffold.py` | Updated for new simplified API |

## What Was Preserved

The following extraction/analysis code remains as it feeds the `analyze` tool:

- `converters/taskflow.py` - TaskFlow pattern extraction
- `converters/sensors.py` - Sensor detection and pattern conversion
- `converters/taskgroup.py` - TaskGroup extraction
- `converters/trigger_rules.py` - Trigger rule detection
- `converters/connections.py` - Connection detection
- `converters/variables.py` - Variable detection
- `converters/jinja.py` - Jinja template detection
- `converters/dynamic_mapping.py` - Dynamic task mapping detection
- `converters/custom_operators.py` - Custom operator detection
- `converters/datasets.py` - Dataset/Asset detection
- `converters/runbook.py` - Migration runbook generation
- `converters/provider_mappings.py` - Operator to Prefect mappings

These converters now focus on **extraction and analysis**, producing rich data structures that feed into the analysis payload. Any "convert" functions in these modules generate code **snippets for the runbook**, not complete flow code.

## API Changes

### Before

```python
# Old API - deterministic conversion
from airflow_unfactor.tools.convert import convert_dag

result = await convert_dag(path="/path/to/dag.py")
# Returns: { flow_code: "...", test_code: "...", ... }
```

### After

```python
# New API - analysis for LLM
from airflow_unfactor.tools.analyze import analyze_dag

result = await analyze_dag(path="/path/to/dag.py")
# Returns: {
#   dag_id, operators, imports, patterns,
#   migration_notes, conversion_runbook_md,
#   original_code, ...
# }
# LLM uses this to generate idiomatic code
```

### Scaffold API Change

```python
# Before - scaffold converted DAGs into project
await scaffold_project(
    dags_directory="/path/to/dags",
    output_directory="/path/to/output",
)

# After - scaffold empty project structure only
await scaffold_project(
    output_directory="/path/to/output",
    project_name="my_project",
)
# LLM generates flow code using analyze() output
```

## Migration Path for Users

Users of the old `convert` tool should:

1. Use `analyze()` to get rich DAG analysis
2. Use `get_context()` to fetch Prefect patterns
3. Pass both to an LLM to generate Prefect code
4. Use `validate()` to verify the generated code

The new workflow produces better results because:
- LLM understands context and generates idiomatic code
- Migration runbook provides human-readable guidance
- Operator mappings are suggestions, not rigid templates

## Future Considerations

1. **Runbook Enhancement**: The `conversion_runbook_md` in the analyze payload could be expanded with more specific guidance based on detected patterns.

2. **Example Generation**: Rather than generating complete flow code, we could generate small example snippets that demonstrate key patterns.

3. **Validation Improvements**: The validate tool could be enhanced to check not just structure but also semantic equivalence.
