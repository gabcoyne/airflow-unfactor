## ADDED Requirements

### Requirement: Include Prefect Cloud work pool guidance
The runbook SHALL include guidance for configuring Prefect Cloud work pools.

#### Scenario: Work pool recommendation
- **WHEN** runbook is generated
- **THEN** includes section on choosing work pool type (process, docker, kubernetes)

#### Scenario: Worker deployment guidance
- **WHEN** runbook is generated
- **THEN** includes commands for starting workers with the flow's work pool

### Requirement: Include automation setup guidance
The runbook SHALL include guidance for Prefect automations replacing Airflow features.

#### Scenario: SLA callback migration
- **WHEN** DAG has sla_miss_callback
- **THEN** runbook includes automation setup for SLA monitoring

#### Scenario: Failure callback migration
- **WHEN** DAG has on_failure_callback
- **THEN** runbook includes automation setup for failure notifications

#### Scenario: Success callback migration
- **WHEN** DAG has on_success_callback
- **THEN** runbook includes automation setup for success notifications

### Requirement: Include deployment configuration guidance
The runbook SHALL include guidance for prefect.yaml deployment configuration.

#### Scenario: Schedule migration
- **WHEN** DAG has schedule_interval
- **THEN** runbook includes prefect.yaml schedule configuration snippet

#### Scenario: Parameter configuration
- **WHEN** DAG has params or Variable usage
- **THEN** runbook includes prefect.yaml parameters configuration

#### Scenario: Infrastructure configuration
- **WHEN** DAG has resource requirements
- **THEN** runbook includes work pool infrastructure overrides

### Requirement: Include Block setup commands
The runbook SHALL include CLI commands for creating required Blocks.

#### Scenario: Database Block setup
- **WHEN** DAG uses database connection
- **THEN** runbook includes prefect block register and Python Block creation code

#### Scenario: Cloud credential Block setup
- **WHEN** DAG uses cloud provider connection
- **THEN** runbook includes Block setup for appropriate credential type

### Requirement: Include testing guidance
The runbook SHALL include guidance for testing the migrated flow.

#### Scenario: Local testing
- **WHEN** runbook is generated
- **THEN** includes command to run flow locally with test harness

#### Scenario: Deployment testing
- **WHEN** runbook is generated
- **THEN** includes command to trigger deployment run for validation
