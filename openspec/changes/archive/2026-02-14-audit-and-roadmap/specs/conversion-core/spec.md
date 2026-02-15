## ADDED Requirements

### Requirement: Convert multi-task XCom pulls
The converter SHALL handle XCom pulls from multiple upstream tasks.

#### Scenario: Pull from multiple tasks
- **WHEN** DAG has `ti.xcom_pull(task_ids=["task_a", "task_b"])`
- **THEN** convert generates function that receives both results as parameters

#### Scenario: Pull with key from multiple tasks
- **WHEN** DAG has `ti.xcom_pull(task_ids=["task_a", "task_b"], key="data")`
- **THEN** convert generates appropriate parameter passing with warning about key access

### Requirement: Warn on dynamic XCom patterns
The converter SHALL detect and warn on dynamically-constructed XCom patterns.

#### Scenario: Variable task ID detected
- **WHEN** DAG has `ti.xcom_pull(task_ids=variable)`
- **THEN** convert generates warning and TODO comment for manual review

#### Scenario: Computed task ID detected
- **WHEN** DAG has `ti.xcom_pull(task_ids=f"task_{i}")`
- **THEN** convert generates warning about dynamic pattern

### Requirement: Convert retry policies with backoff
The converter SHALL convert Airflow retry configurations to Prefect equivalents.

#### Scenario: Basic retries converted
- **WHEN** DAG has `default_args={"retries": 3, "retry_delay": timedelta(minutes=5)}`
- **THEN** convert generates `@task(retries=3, retry_delay_seconds=300)`

#### Scenario: Exponential backoff detected
- **WHEN** DAG has `retry_exponential_backoff=True`
- **THEN** convert generates warning that Prefect uses different backoff mechanism

#### Scenario: Max retry delay converted
- **WHEN** DAG has `max_retry_delay=timedelta(hours=1)`
- **THEN** convert generates warning and suggests Prefect retry configuration

### Requirement: Convert task-level retry overrides
The converter SHALL handle task-specific retry configurations.

#### Scenario: Task overrides default
- **WHEN** task has `retries=5` overriding default_args
- **THEN** convert applies task-specific retry to generated task decorator

#### Scenario: Task disables retries
- **WHEN** task has `retries=0`
- **THEN** convert generates `@task(retries=0)` explicitly

### Requirement: Detect pool constraints
The converter SHALL detect and warn about Airflow pool usage.

#### Scenario: Pool parameter detected
- **WHEN** task has `pool="limited_resources"`
- **THEN** convert generates warning about Prefect work pool configuration

#### Scenario: Pool slots detected
- **WHEN** task has `pool_slots=2`
- **THEN** convert generates warning about concurrency management
