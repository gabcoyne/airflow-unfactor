## ADDED Requirements

### Requirement: Collect conversion statistics
The metrics module SHALL collect statistics during each conversion operation.

#### Scenario: Track operator counts
- **WHEN** convert tool processes a DAG
- **THEN** metrics records operators_total, operators_converted, operators_stubbed

#### Scenario: Track warning counts
- **WHEN** convert tool generates warnings
- **THEN** metrics records warnings_count by category

#### Scenario: Track timing
- **WHEN** convert tool completes
- **THEN** metrics records elapsed_ms for the operation

### Requirement: Store metrics in memory
The metrics module SHALL maintain in-memory storage of conversion metrics.

#### Scenario: Accumulate across conversions
- **WHEN** multiple DAGs are converted in a session
- **THEN** metrics are accumulated and queryable

#### Scenario: Clear on demand
- **WHEN** metrics.clear() is called
- **THEN** all accumulated metrics are reset

### Requirement: Export metrics to JSON
The metrics module SHALL support exporting metrics to JSON format.

#### Scenario: Export single conversion
- **WHEN** export_json(conversion_id) is called
- **THEN** returns JSON with that conversion's metrics

#### Scenario: Export all conversions
- **WHEN** export_all_json() is called
- **THEN** returns JSON array of all conversion metrics

### Requirement: Calculate aggregate statistics
The metrics module SHALL calculate aggregate statistics across conversions.

#### Scenario: Calculate success rate
- **WHEN** get_aggregate_stats() is called
- **THEN** returns success_rate = conversions_passed / conversions_total

#### Scenario: Calculate operator coverage
- **WHEN** get_aggregate_stats() is called
- **THEN** returns operator_coverage = unique_operators_seen / known_operators

#### Scenario: Calculate warning frequency
- **WHEN** get_aggregate_stats() is called
- **THEN** returns warning_frequency by category

### Requirement: Metrics disabled by default
The metrics module SHALL be disabled by default to avoid overhead.

#### Scenario: No collection when disabled
- **WHEN** AIRFLOW_UNFACTOR_METRICS is not set
- **THEN** no metrics are collected (no-op functions)

#### Scenario: Enable via environment
- **WHEN** AIRFLOW_UNFACTOR_METRICS=1 is set
- **THEN** metrics collection is enabled

### Requirement: Optional export adapters
The metrics module SHALL support optional export to external systems.

#### Scenario: JSON file export
- **WHEN** metrics.export_to_file(path) is called
- **THEN** writes metrics to specified JSON file

#### Scenario: Future adapter interface
- **WHEN** new export adapter is needed
- **THEN** can implement MetricsExporter protocol with export(metrics) method
