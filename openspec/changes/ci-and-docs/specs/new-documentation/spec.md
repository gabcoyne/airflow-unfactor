## ADDED Requirements

### Requirement: Validation tool documentation
The docs SHALL include comprehensive validation tool documentation.

#### Scenario: docs/tools/validate.md exists
- **WHEN** user navigates to validation docs
- **THEN** page explains validation purpose and features
- **AND** includes usage examples via MCP

#### Scenario: Validation features documented
- **WHEN** user reads validation docs
- **THEN** explains task count comparison with DummyOperator exclusion
- **AND** explains dependency graph isomorphism check
- **AND** explains XCom data flow validation
- **AND** explains confidence scoring

#### Scenario: Validation output documented
- **WHEN** user reads validation docs
- **THEN** documents JSON output format
- **AND** explains is_valid, issues, and confidence_score fields
- **AND** provides example output

#### Scenario: Validation troubleshooting included
- **WHEN** user reads validation docs
- **THEN** includes common issues and solutions
- **AND** links to main troubleshooting page

### Requirement: Metrics module documentation
The docs SHALL include comprehensive metrics module documentation.

#### Scenario: docs/tools/metrics.md exists
- **WHEN** user navigates to metrics docs
- **THEN** page explains metrics purpose and features

#### Scenario: Enabling metrics documented
- **WHEN** user reads metrics docs
- **THEN** explains AIRFLOW_UNFACTOR_METRICS environment variable
- **AND** shows how to enable with "1", "true", or "yes"

#### Scenario: Recording conversions documented
- **WHEN** user reads metrics docs
- **THEN** explains record_conversion() function
- **AND** documents all available parameters

#### Scenario: Aggregate statistics documented
- **WHEN** user reads metrics docs
- **THEN** explains get_aggregate_stats() function
- **AND** documents success_rate, operator_coverage, warning_frequency

#### Scenario: Export functions documented
- **WHEN** user reads metrics docs
- **THEN** explains export_json() and export_to_file()
- **AND** provides example JSON output

### Requirement: Enterprise migration guide
The docs SHALL include guidance for large-scale migrations.

#### Scenario: docs/guides/enterprise-migration.md exists
- **WHEN** user navigates to enterprise migration guide
- **THEN** page provides patterns for large DAG portfolios

#### Scenario: Assessment phase documented
- **WHEN** user reads enterprise migration guide
- **THEN** explains DAG inventory analysis
- **AND** discusses complexity scoring
- **AND** covers dependency mapping

#### Scenario: Phased migration documented
- **WHEN** user reads enterprise migration guide
- **THEN** explains pilot → batch → full migration approach
- **AND** discusses parallel operation strategies

#### Scenario: Batch conversion documented
- **WHEN** user reads enterprise migration guide
- **THEN** explains using batch tool for multiple DAGs
- **AND** discusses scaffold tool for project structure

#### Scenario: Validation at scale documented
- **WHEN** user reads enterprise migration guide
- **THEN** explains using validate tool systematically
- **AND** discusses metrics for tracking progress

### Requirement: Prefect Cloud integration guide
The docs SHALL include Prefect Cloud-specific guidance.

#### Scenario: docs/guides/prefect-cloud.md exists
- **WHEN** user navigates to Prefect Cloud guide
- **THEN** page covers Cloud-specific features

#### Scenario: Work pools documented
- **WHEN** user reads Prefect Cloud guide
- **THEN** explains work pool types (process, docker, kubernetes)
- **AND** shows configuration examples from runbook

#### Scenario: Automations documented
- **WHEN** user reads Prefect Cloud guide
- **THEN** explains automation setup for callback replacement
- **AND** covers SLA, failure, and success automations
- **AND** shows EventTrigger configuration

#### Scenario: Blocks and secrets documented
- **WHEN** user reads Prefect Cloud guide
- **THEN** explains Block setup for connections
- **AND** covers Secret blocks for sensitive data
- **AND** references runbook Block CLI commands

#### Scenario: Concurrency management documented
- **WHEN** user reads Prefect Cloud guide
- **THEN** explains concurrency limits
- **AND** covers work pool concurrency settings
- **AND** references pool/pool_slots migration warnings
