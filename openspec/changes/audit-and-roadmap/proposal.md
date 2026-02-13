## Why

Two major development phases are complete: P0 (core conversion bugs) and P1 (interface-experience). The tool now has 8 converters, 524 passing tests, comprehensive docs, and a scaffold tool. Before starting the next sprint, we need to identify the highest-impact work. The audit reveals one critical gap (validate tool is a stub) and several opportunities to expand coverage (provider operators, complex patterns, observability).

## What Changes

### Critical Gap: Validation Tool

The `validate` tool is currently a stub with `# TODO: Implement validation logic`. This is the only feature advertised but not implemented. Users need confidence that converted flows are behaviorally equivalent to original DAGs.

### Coverage Expansion

- **Provider operator mappings**: Currently ~50 operators mapped; hundreds exist in AWS, GCP, Azure, Databricks providers
- **Complex XCom patterns**: Multi-task pulls, dynamic pulls have TODOs
- **Retry policies**: Only basic retries; no exponential backoff, jitter support
- **Pool/concurrency constraints**: Airflow pools have no direct Prefect equivalent—needs design

### Observability & Developer Experience

- **Conversion metrics**: No tracking of success rates, operator coverage, warning frequency
- **IDE integration**: No VS Code extension or language server features
- **Interactive mode**: Batch conversion provides no feedback during long runs

### Documentation Gaps

- **Operator coverage matrix**: No searchable reference for "is operator X supported?"
- **Enterprise patterns guide**: Large DAG migrations, multi-team coordination not documented
- **Prefect Cloud integration**: No guidance on cloud-specific features (automations, work pools)

## Capabilities

### New Capabilities

- `validation-engine`: Behavioral equivalence checking between original DAG and converted flow. Compare task graphs, detect missing tasks, validate data flow patterns. Report mismatches with actionable diagnostics.

- `provider-operator-expansion`: Expand operator mappings for AWS (30+), GCP (20+), Azure (15+), Databricks (10+) providers. Generate integration scaffolds with proper Block types.

- `conversion-metrics`: Track and report conversion statistics—operator coverage, warning frequency, success rates. Exportable for quality dashboards.

- `operator-coverage-matrix`: Searchable documentation of all known Airflow operators and their conversion status (supported, partial, unsupported, unknown).

### Modified Capabilities

- `conversion-core`: Add support for complex XCom patterns (multi-task, dynamic) and complete retry policy conversion
- `runbook-generation`: Add Prefect Cloud-specific guidance (work pools, automations, deployments)

## Impact

**Code changes:**
- `src/airflow_unfactor/tools/validate.py`: Complete implementation of behavioral validation
- `src/airflow_unfactor/converters/provider_mappings.py`: Expand operator registry
- `src/airflow_unfactor/metrics/`: New module for conversion tracking
- `src/airflow_unfactor/converters/base.py`: Complex XCom and retry policy support

**Documentation changes:**
- `docs/operator-coverage.md`: New—searchable operator matrix
- `docs/enterprise-migration.md`: New—large-scale migration patterns
- `docs/prefect-cloud.md`: New—cloud-specific integration guide

**External dependencies:**
- No new runtime dependencies
- Consider optional metrics export (prometheus-client, statsd)

**Prioritization recommendation:**
1. **P0**: Validation engine (critical gap—advertised but not implemented)
2. **P1**: Provider operator expansion (high user value, straightforward)
3. **P2**: Conversion metrics (quality improvement, can be incremental)
4. **P3**: Complex XCom/retry (edge cases, lower frequency)
