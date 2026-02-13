## ADDED Requirements

### Requirement: DAG metadata extraction
The system SHALL extract DAG-level configuration for runbook generation.

#### Scenario: Extract schedule configuration
- **WHEN** DAG has schedule_interval, schedule, or timetable
- **THEN** runbook includes schedule value and Prefect deployment equivalent

#### Scenario: Extract retry configuration
- **WHEN** DAG or default_args has retries, retry_delay
- **THEN** runbook includes values and maps to @flow/@task decorator parameters

#### Scenario: Extract concurrency settings
- **WHEN** DAG has max_active_runs, max_active_tasks
- **THEN** runbook includes values and maps to Prefect concurrency limits

### Requirement: Callback mapping guidance
The system SHALL provide guidance for converting Airflow callbacks.

#### Scenario: on_failure_callback detected
- **WHEN** DAG has on_failure_callback
- **THEN** runbook explains: use Prefect state handlers or notification blocks

#### Scenario: on_success_callback detected
- **WHEN** DAG has on_success_callback
- **THEN** runbook explains: use Prefect state handlers or automations

#### Scenario: sla_miss_callback detected
- **WHEN** DAG has sla_miss_callback
- **THEN** runbook explains: use Prefect Cloud SLAs or custom automation

### Requirement: Infrastructure guidance
The system SHALL provide infrastructure migration guidance.

#### Scenario: Executor to work pool mapping
- **WHEN** runbook generated
- **THEN** includes guidance: "Configure Prefect work pool matching your Airflow executor type"

#### Scenario: Connection migration guidance
- **WHEN** DAG uses conn_id references
- **THEN** runbook includes: "Create Prefect Blocks for each Airflow connection"

### Requirement: Generated artifacts reference
The system SHALL document all generated artifacts in the runbook.

#### Scenario: List generated files
- **WHEN** conversion completes
- **THEN** runbook lists: flow_code, test_code, dataset_conversion outputs

#### Scenario: Explain artifact purposes
- **WHEN** runbook generated
- **THEN** explains purpose of each artifact and how to use it

### Requirement: Manual review checklist
The system SHALL include actionable checklist for post-conversion review.

#### Scenario: Include TODO items
- **WHEN** runbook generated
- **THEN** includes numbered checklist: fill TODOs, configure deployment, test, validate

#### Scenario: Highlight warnings
- **WHEN** conversion has warnings
- **THEN** runbook includes "Manual Review Required" section listing each warning

### Requirement: Deployment configuration guidance
The system SHALL provide Prefect deployment setup guidance.

#### Scenario: Deployment YAML template
- **WHEN** DAG has schedule
- **THEN** runbook includes deployment.yaml snippet with schedule configuration

#### Scenario: Work pool recommendation
- **WHEN** runbook generated
- **THEN** includes work pool type recommendations based on detected operator types

### Requirement: Testing guidance
The system SHALL provide testing recommendations.

#### Scenario: Test execution guidance
- **WHEN** test_code generated
- **THEN** runbook includes: "Run tests with: pytest test_<dag_id>_flow.py"

#### Scenario: Validation approach
- **WHEN** runbook generated
- **THEN** includes guidance for validating behavior matches original DAG

### Requirement: Event-driven migration guidance
The system SHALL provide guidance for converting to event-driven patterns.

#### Scenario: Dataset/Asset migration
- **WHEN** DAG uses Airflow Datasets or Assets
- **THEN** runbook explains Prefect event emission and automation triggers

#### Scenario: Sensor replacement guidance
- **WHEN** DAG uses sensors
- **THEN** runbook explains event-driven alternatives with webhook/SNS/EventBridge examples
