## ADDED Requirements

### Requirement: DAG to Flow mapping
The system SHALL document the mapping from Airflow DAG concepts to Prefect flow concepts.

#### Scenario: DAG class maps to flow decorator
- **WHEN** user asks about DAG equivalent
- **THEN** system explains: Airflow `DAG()` context manager → Prefect `@flow` decorated function

#### Scenario: DAG default_args map to decorator parameters
- **WHEN** DAG has default_args with retries, retry_delay
- **THEN** system maps to `@task(retries=N, retry_delay_seconds=M)` parameters

### Requirement: Operator to Task mapping
The system SHALL document the mapping from Airflow operators to Prefect tasks.

#### Scenario: PythonOperator maps to task decorator
- **WHEN** user has PythonOperator
- **THEN** system explains: extract callable, apply `@task` decorator directly

#### Scenario: BashOperator maps to subprocess task
- **WHEN** user has BashOperator
- **THEN** system explains: create `@task` using `subprocess.run()` for execution

#### Scenario: Custom operators require manual mapping
- **WHEN** user has custom or provider-specific operators
- **THEN** system explains: use underlying Python libraries directly in `@task` function

### Requirement: XCom to return value mapping
The system SHALL document the fundamental difference in data passing models.

#### Scenario: XCom push/pull eliminated
- **WHEN** user asks about XCom equivalent
- **THEN** system explains: Prefect tasks return values directly; no database intermediate

#### Scenario: XCom keys map to multiple returns
- **WHEN** Airflow task pushes multiple keys
- **THEN** system explains: return dict/tuple from Prefect task, destructure in caller

### Requirement: Scheduling model mapping
The system SHALL document that scheduling is decoupled in Prefect.

#### Scenario: schedule_interval maps to deployment
- **WHEN** DAG has schedule_interval or timetable
- **THEN** system explains: configure via deployment YAML or `flow.serve(cron=...)`, not in flow code

#### Scenario: catchup behavior differs
- **WHEN** DAG has catchup=True/False
- **THEN** system explains: Prefect deployments don't backfill by default; use automation for catchup

### Requirement: Sensor to event mapping
The system SHALL document sensor replacement strategies.

#### Scenario: Polling sensors map to retry tasks
- **WHEN** user has S3KeySensor, HttpSensor, etc.
- **THEN** system explains: convert to `@task(retries=N)` with polling logic, or use event triggers

#### Scenario: ExternalTaskSensor maps to events/automations
- **WHEN** user has ExternalTaskSensor for cross-DAG deps
- **THEN** system explains: use Prefect events, automations, or API-based triggering

### Requirement: Connection to Block mapping
The system SHALL document credential management differences.

#### Scenario: Airflow connections map to Blocks
- **WHEN** user has Airflow connections (conn_id)
- **THEN** system explains: create Prefect Blocks for typed, encrypted credential storage

#### Scenario: Variables map to Blocks or env vars
- **WHEN** user has Airflow Variables
- **THEN** system explains: use Prefect Variables, JSON Blocks, or environment variables

### Requirement: Execution model differences
The system SHALL document the fundamental execution model difference.

#### Scenario: Task isolation differs
- **WHEN** user asks about task execution
- **THEN** system explains: Airflow runs each task in separate process/pod; Prefect runs all tasks in same environment within a flow run

#### Scenario: Worker model differs
- **WHEN** user asks about workers/executors
- **THEN** system explains: Airflow executors → Prefect work pools + workers; resource control at flow-run level
