## ADDED Requirements

### Requirement: Extract DAG constructor settings
The system SHALL extract settings from `DAG()` constructor including schedule, catchup, default_args, and concurrency.

#### Scenario: Extract schedule_interval
- **WHEN** DAG has `schedule_interval="@daily"` or `schedule="0 0 * * *"`
- **THEN** runbook includes schedule with Prefect deployment equivalent

#### Scenario: Extract catchup setting
- **WHEN** DAG has `catchup=False`
- **THEN** runbook notes this is deployment-level config in Prefect

#### Scenario: Extract default_args
- **WHEN** DAG has `default_args={"retries": 3, "retry_delay": timedelta(minutes=5)}`
- **THEN** runbook maps each arg to Prefect task decorator equivalent

### Requirement: Extract @dag decorator settings
The system SHALL extract settings from `@dag` decorator for TaskFlow DAGs.

#### Scenario: Extract @dag schedule
- **WHEN** TaskFlow DAG has `@dag(schedule="@hourly")`
- **THEN** runbook includes schedule setting

#### Scenario: Extract @dag default_args
- **WHEN** TaskFlow DAG has `@dag(default_args={...})`
- **THEN** runbook maps default_args to Prefect equivalents

### Requirement: Extract callback definitions
The system SHALL extract DAG-level and task-level callbacks.

#### Scenario: Extract on_failure_callback
- **WHEN** DAG or task has `on_failure_callback=alert_function`
- **THEN** runbook maps to Prefect `on_failure` hook or automation

#### Scenario: Extract on_success_callback
- **WHEN** DAG or task has `on_success_callback=notify_function`
- **THEN** runbook maps to Prefect `on_completion` hook

#### Scenario: Extract sla_miss_callback
- **WHEN** DAG has `sla_miss_callback=escalate_function`
- **THEN** runbook maps to Prefect automation with duration trigger

### Requirement: Generate actionable checklist
The system SHALL generate a markdown checklist of manual follow-up items.

#### Scenario: Deployment checklist item
- **WHEN** schedule extracted
- **THEN** checklist includes "[ ] Create Prefect deployment with schedule: {schedule}"

#### Scenario: Block setup checklist item
- **WHEN** connections detected
- **THEN** checklist includes "[ ] Create Prefect Blocks for: {connection_names}"

#### Scenario: Automation checklist item
- **WHEN** callbacks detected
- **THEN** checklist includes "[ ] Configure Prefect automation/hooks for: {callback_types}"

### Requirement: Map settings to Prefect equivalents
The system SHALL provide mapping guidance for each Airflow setting.

#### Scenario: Concurrency mapping
- **WHEN** DAG has `max_active_runs=1` or `concurrency=4`
- **THEN** runbook explains Prefect work pool concurrency and task runner options

#### Scenario: Tags mapping
- **WHEN** DAG has `tags=["etl", "daily"]`
- **THEN** runbook shows Prefect flow/deployment tags equivalent

#### Scenario: Retries mapping
- **WHEN** default_args has `retries=3`
- **THEN** runbook shows `@task(retries=3)` equivalent
