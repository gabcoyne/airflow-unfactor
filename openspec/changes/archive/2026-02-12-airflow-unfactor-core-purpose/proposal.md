## Why

airflow-unfactor exists to help teams refactor Airflow DAG code into Prefect flow code through AI-assisted analysis and transformation. A deep audit revealed fundamental gaps between the tool's aspirations and its actual capabilities: task dependencies were lost, XCom patterns failed silently, Jinja2 templates caused runtime errors, and generated code was never validated. The tool was selling "liberation, not migration" but delivering broken scaffolds. This change establishes the core purpose, documents the architectural differences between Airflow and Prefect that inform correct conversion, and ensures the tool produces working, idiomatic Prefect code.

## What Changes

- **Establish authoritative documentation** of Airflow-to-Prefect conceptual mappings based on current Prefect 3.x architecture
- **Fix critical conversion bugs**: dependency tracking, XCom handling, Jinja2 detection, code validation (completed in P0 sprint)
- **Define clear tool boundaries**: what converts correctly, what requires manual review, what cannot be automated
- **Improve generated code quality**: preserve execution order, use Prefect idioms (data passing, wait_for), add actionable warnings
- **Create runbook specificity**: DAG-level settings, callbacks, SLA semantics mapped to Prefect equivalents

## Capabilities

### New Capabilities

- `conversion-core`: Core conversion engine that transforms Airflow operators to Prefect tasks while preserving dependencies, handling XCom patterns, and validating output
- `conceptual-mapping`: Authoritative reference for Airflow→Prefect concept translation (DAG→flow, Operator→task, XCom→return values, Sensors→events, Connections→Blocks)
- `conversion-warnings`: Detection and reporting system for patterns that require manual intervention (Jinja2 templates, dynamic XCom, custom operators, trigger rules)
- `runbook-generation`: DAG-specific migration guidance including schedule conversion, retry configuration, callback mapping, and infrastructure setup

### Modified Capabilities

<!-- No existing specs to modify - this is establishing the foundational specs -->

## Impact

**Code affected:**
- `src/airflow_unfactor/converters/base.py` - dependency graph, execution ordering
- `src/airflow_unfactor/converters/operators/python.py` - XCom detection and conversion
- `src/airflow_unfactor/converters/operators/bash.py` - Jinja2 template detection
- `src/airflow_unfactor/validation.py` - generated code syntax validation
- `src/airflow_unfactor/analysis/dependencies.py` - DAG dependency extraction
- `src/airflow_unfactor/tools/convert.py` - orchestration of conversion pipeline

**APIs affected:**
- `convert` MCP tool response now includes `dependencies`, `execution_groups`, and enhanced `warnings`
- Operator converter functions return result objects with `code`, `warnings`, and detection info

**Documentation affected:**
- README messaging changed from "conversion" to "refactoring"
- Docs need comprehensive limitations guide
- Need contributor guide for OpenSpec-to-implementation workflow

**Dependencies:**
- Prefect 3.x API compatibility (validated against current docs)
- No new external dependencies added
