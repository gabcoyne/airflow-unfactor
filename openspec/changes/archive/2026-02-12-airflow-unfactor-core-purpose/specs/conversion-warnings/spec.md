## ADDED Requirements

### Requirement: Jinja2 template detection
The system SHALL detect Jinja2 templates in Airflow code and warn users they will not render in Prefect.

#### Scenario: Detect execution context templates
- **WHEN** bash_command contains `{{ ds }}`, `{{ execution_date }}`, `{{ ts }}`
- **THEN** system adds warning with Prefect runtime context equivalent

#### Scenario: Detect task context templates
- **WHEN** code contains `{{ task.task_id }}`, `{{ dag.dag_id }}`
- **THEN** system adds warning with Prefect task_run/flow_run equivalents

#### Scenario: Detect variable templates
- **WHEN** code contains `{{ var.value.X }}`, `{{ conn.X }}`
- **THEN** system adds warning recommending Prefect Blocks

#### Scenario: Add inline comments for templates
- **WHEN** Jinja2 template detected in generated code
- **THEN** system adds warning comment above the line with suggested replacement

### Requirement: Dynamic XCom detection
The system SHALL detect XCom patterns that cannot be statically converted.

#### Scenario: Detect variable task_ids
- **WHEN** xcom_pull uses variable like `ti.xcom_pull(task_ids=task_list)`
- **THEN** system adds warning: "Dynamic task_ids requires manual conversion"

#### Scenario: Detect custom XCom keys
- **WHEN** xcom_pull uses key parameter like `ti.xcom_pull(task_ids="x", key="schema")`
- **THEN** system adds warning: "Custom key requires restructuring - Prefect tasks return single value"

#### Scenario: Detect list task_ids
- **WHEN** xcom_pull uses list like `ti.xcom_pull(task_ids=["a", "b"])`
- **THEN** system adds warning: "Multi-task xcom_pull requires manual conversion"

### Requirement: Unsupported operator detection
The system SHALL warn about operators that cannot be automatically converted.

#### Scenario: Unknown operator warning
- **WHEN** DAG contains operator not in mapping registry
- **THEN** system adds warning: "Operator 'X' requires manual review" and generates stub

#### Scenario: Provider operator partial support
- **WHEN** DAG contains provider operator (SparkSubmitOperator, KubernetesPodOperator)
- **THEN** system adds warning with available mapping or manual implementation guidance

### Requirement: Trigger rule detection
The system SHALL warn about Airflow trigger rules that have no direct Prefect equivalent.

#### Scenario: Non-default trigger rule
- **WHEN** task has trigger_rule other than "all_success"
- **THEN** system adds warning: "Trigger rule 'X' requires custom control flow in Prefect"

#### Scenario: one_failed or one_success rules
- **WHEN** task has trigger_rule="one_failed" or "one_success"
- **THEN** system adds warning with suggested Prefect state handling pattern

### Requirement: Sensor mode detection
The system SHALL warn about sensor mode implications.

#### Scenario: Reschedule mode detected
- **WHEN** sensor has mode="reschedule"
- **THEN** system adds warning: "Reschedule mode frees worker slot - consider Prefect task runner configuration"

#### Scenario: Poke mode with long timeout
- **WHEN** sensor has mode="poke" with timeout > 300 seconds
- **THEN** system adds warning: "Long-running poke blocks worker - consider event-driven approach"

### Requirement: TaskGroup detection
The system SHALL warn about TaskGroups which have no direct Prefect equivalent.

#### Scenario: TaskGroup detected
- **WHEN** DAG uses TaskGroup context manager
- **THEN** system adds warning: "TaskGroup should be converted to nested flow (subflow) for organization"

### Requirement: Dynamic task mapping detection
The system SHALL warn about Airflow 2.3+ dynamic task mapping.

#### Scenario: expand() or map() detected
- **WHEN** DAG uses task.expand() or task.map() patterns
- **THEN** system adds warning: "Dynamic task mapping - use Prefect task.map() with appropriate task runner"

### Requirement: Warning aggregation
The system SHALL aggregate warnings in the conversion result for user review.

#### Scenario: Warnings included in response
- **WHEN** conversion completes with warnings
- **THEN** response includes `warnings` array with all detected issues

#### Scenario: Warnings categorized by severity
- **WHEN** warnings generated
- **THEN** critical issues (will break at runtime) distinguished from advisories (may need review)
