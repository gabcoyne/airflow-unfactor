## ADDED Requirements

### Requirement: Detect TaskGroup patterns
The system SHALL detect `@task_group` decorated functions and `TaskGroup` context managers.

#### Scenario: Detect task_group decorator
- **WHEN** DAG contains `@task_group` or `@task_group()` decorated function
- **THEN** system identifies TaskGroup with its name and contained tasks

#### Scenario: Detect TaskGroup context manager
- **WHEN** DAG contains `with TaskGroup("name") as group:`
- **THEN** system identifies TaskGroup with its name and contained tasks

### Requirement: Convert TaskGroup to subflow
The system SHALL convert `@task_group` to `@flow` decorator, creating a Prefect subflow.

#### Scenario: Simple TaskGroup conversion
- **WHEN** Airflow code has `@task_group def process_data(): ...`
- **THEN** generated Prefect code has `@flow def process_data(): ...`

#### Scenario: Preserve task organization
- **WHEN** TaskGroup contains multiple tasks with internal dependencies
- **THEN** generated subflow preserves task call order and data flow

### Requirement: Handle TaskGroup expand with wrapper
The system SHALL generate a wrapper task when TaskGroup uses `.expand()`, since Prefect subflows don't support native mapping.

#### Scenario: TaskGroup expand conversion
- **WHEN** Airflow code has `my_task_group.expand(param=[1,2,3])`
- **THEN** generated code includes wrapper `@task` that calls subflow, mapped over values

#### Scenario: Educational comment for wrapper
- **WHEN** wrapper task is generated for TaskGroup expand
- **THEN** comment explains Prefect subflows don't have `.expand()`, wrapper is workaround
