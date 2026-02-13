## 1. Dynamic Task Mapping Converter

- [x] 1.1 Create `src/airflow_unfactor/converters/dynamic_mapping.py` with AST visitor for `.expand()` detection
- [x] 1.2 Implement `.expand()` to `.map()` conversion logic
- [x] 1.3 Handle `.partial().expand()` chains
- [x] 1.4 Add warning for `map_index_template` parameter
- [x] 1.5 Write tests for dynamic mapping detection and conversion
- [x] 1.6 Integrate into main convert pipeline

## 2. TaskGroup Converter

- [x] 2.1 Create `src/airflow_unfactor/converters/taskgroup.py` with `@task_group` detection
- [x] 2.2 Implement TaskGroup to `@flow` subflow conversion
- [x] 2.3 Generate wrapper `@task` for TaskGroup `.expand()` patterns
- [x] 2.4 Add educational comments explaining subflow pattern
- [x] 2.5 Write tests for TaskGroup detection and conversion
- [x] 2.6 Integrate into main convert pipeline

## 3. Trigger Rule Converter

- [x] 3.1 Create `src/airflow_unfactor/converters/trigger_rules.py` with trigger_rule detection
- [x] 3.2 Implement `all_done` conversion using `return_state=True`
- [x] 3.3 Implement `all_failed`/`one_failed`/`one_success`/`none_failed` with `allow_failure` and state checks
- [x] 3.4 Generate appropriate imports (`allow_failure`, state methods)
- [x] 3.5 Add educational comments for each trigger rule pattern
- [x] 3.6 Write tests for all trigger rule conversions
- [x] 3.7 Integrate into main convert pipeline

## 4. Jinja2 Template Converter

- [x] 4.1 Create `src/airflow_unfactor/converters/jinja.py` with Jinja2 pattern detection
- [x] 4.2 Implement `{{ ds }}`, `{{ ds_nodash }}`, `{{ ts }}` conversion to runtime context
- [x] 4.3 Implement `{{ params.x }}` conversion to flow parameters
- [x] 4.4 Implement `{{ macros.ds_add() }}` conversion to timedelta
- [x] 4.5 Generate f-string replacements with runtime imports
- [x] 4.6 Add warning for unrecognized Jinja2 patterns
- [x] 4.7 Write tests for all Jinja2 template conversions
- [x] 4.8 Integrate into main convert pipeline

## 5. Connection to Block Converter

- [x] 5.1 Create `src/airflow_unfactor/converters/connections.py` with hook detection
- [x] 5.2 Build connection type to Block type mapping (Postgres→SqlAlchemy, S3→Aws, etc.)
- [x] 5.3 Generate Block scaffold code with `.load()` pattern
- [x] 5.4 Generate setup instructions for runbook (no secrets in code)
- [x] 5.5 Add warning for unknown connection types
- [x] 5.6 Write tests for connection detection and scaffold generation
- [x] 5.7 Integrate into runbook generation

## 6. Variable to Config Converter

- [x] 6.1 Create `src/airflow_unfactor/converters/variables.py` with Variable.get/set detection
- [x] 6.2 Implement sensitivity classification based on name patterns
- [x] 6.3 Generate multiple scaffold options (Secret, Variable, parameter) with recommendations
- [x] 6.4 Generate setup instructions for runbook
- [x] 6.5 Add warning for dynamic Variable.set() patterns
- [x] 6.6 Write tests for variable detection and classification
- [x] 6.7 Integrate into runbook generation

## 7. Custom Operator Handler

- [x] 7.1 Extend parser to detect operators not in provider mappings
- [x] 7.2 Implement `execute()` method extraction for inline custom operators
- [x] 7.3 Generate stub `@task` with TODO and original code context
- [x] 7.4 Include operator parameters in refactoring prompt
- [x] 7.5 Write tests for custom operator detection and stub generation
- [x] 7.6 Integrate into main convert pipeline

## 8. Runbook Generation Enhancement

- [x] 8.1 Extend parser to extract `DAG()` constructor settings (schedule, catchup, default_args)
- [x] 8.2 Extend parser to extract `@dag` decorator settings
- [x] 8.3 Extend parser to extract callbacks (on_failure, on_success, sla_miss)
- [x] 8.4 Generate actionable markdown checklist in runbook
- [x] 8.5 Map all settings to Prefect equivalents with guidance
- [x] 8.6 Write tests for setting extraction and runbook generation
- [x] 8.7 Update `conversion_runbook_md` generation in convert tool

## 9. Conversion Output Schema

- [x] 9.1 Create `schemas/conversion-output.json` with JSON Schema
- [x] 9.2 Define schema for analyze response
- [x] 9.3 Define schema for convert response (including runbook, warnings, external_context)
- [x] 9.4 Define schema for validate and explain responses
- [x] 9.5 Add version field and documentation
- [x] 9.6 Create example valid responses for each tool
- [x] 9.7 Add schema validation to tests

## 10. Integration and Documentation

- [x] 10.1 Update `docs/index.md` to reflect complete conversion capabilities
- [x] 10.2 Create `docs/troubleshooting.md` for common issues
- [x] 10.3 Update existing beads to reflect completed work
- [x] 10.4 Run full test suite and fix any integration issues
- [x] 10.5 Update README with new capabilities
