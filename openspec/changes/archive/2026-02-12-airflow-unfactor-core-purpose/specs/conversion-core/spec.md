## ADDED Requirements

### Requirement: Dependency graph extraction
The system SHALL extract task dependencies from Airflow DAG code by parsing `>>` and `<<` operators, `set_upstream()`, and `set_downstream()` method calls.

#### Scenario: Extract simple linear dependencies
- **WHEN** DAG contains `extract >> transform >> load`
- **THEN** system extracts dependencies: extract→transform, transform→load

#### Scenario: Extract parallel fan-out dependencies
- **WHEN** DAG contains `start >> [branch_a, branch_b] >> end`
- **THEN** system extracts: start→branch_a, start→branch_b, branch_a→end, branch_b→end

#### Scenario: Extract method-based dependencies
- **WHEN** DAG contains `transform.set_upstream(extract)`
- **THEN** system extracts dependency: extract→transform

### Requirement: Topological execution ordering
The system SHALL generate flow code that respects the original DAG execution order using topological sort.

#### Scenario: Sequential tasks use data passing
- **WHEN** task B depends only on task A
- **THEN** generated code passes A's result as argument to B: `b_result = task_b(a_result)`

#### Scenario: Multi-upstream tasks use wait_for
- **WHEN** task C depends on both task A and task B
- **THEN** generated code uses wait_for: `c_result = task_c.submit(wait_for=[a_result, b_result])`

#### Scenario: Parallel tasks grouped by level
- **WHEN** tasks have same execution level (no dependencies between them)
- **THEN** generated code groups them with explanatory comments

### Requirement: XCom to return value conversion
The system SHALL convert Airflow XCom patterns to Prefect's direct data passing model.

#### Scenario: Simple xcom_pull conversion
- **WHEN** function contains `ti.xcom_pull(task_ids="extract")`
- **THEN** system replaces with parameter `extract_data` and passes upstream result

#### Scenario: xcom_push to return conversion
- **WHEN** function contains `ti.xcom_push(key="result", value=data)`
- **THEN** system converts to `return data`

#### Scenario: Complex XCom patterns flagged for review
- **WHEN** function contains dynamic task_ids like `ti.xcom_pull(task_ids=task_list)`
- **THEN** system generates warning and TODO comment in output

### Requirement: Operator to task conversion
The system SHALL convert Airflow operators to Prefect @task decorated functions.

#### Scenario: PythonOperator conversion
- **WHEN** DAG contains PythonOperator with python_callable
- **THEN** system generates @task function preserving callable logic

#### Scenario: BashOperator conversion
- **WHEN** DAG contains BashOperator with bash_command
- **THEN** system generates @task function using subprocess.run

#### Scenario: Sensor conversion
- **WHEN** DAG contains a Sensor operator
- **THEN** system generates @task with retries and warns about event-driven alternatives

### Requirement: Generated code validation
The system SHALL validate all generated Python code compiles before returning to user.

#### Scenario: Valid code passes validation
- **WHEN** generated flow code has correct syntax
- **THEN** system returns code without syntax warnings

#### Scenario: Invalid code reports error location
- **WHEN** generated code has syntax error
- **THEN** system reports error message, line number, and column in warnings

### Requirement: Flow structure generation
The system SHALL generate a complete Prefect flow module with proper structure.

#### Scenario: Flow includes required imports
- **WHEN** conversion completes
- **THEN** generated code includes `from prefect import flow, task` and any operator-specific imports

#### Scenario: Flow includes main block
- **WHEN** conversion completes
- **THEN** generated code includes `if __name__ == "__main__":` block for direct execution

#### Scenario: Flow preserves DAG identity
- **WHEN** DAG has dag_id "my_etl_pipeline"
- **THEN** generated flow has `@flow(name="my_etl_pipeline")` decorator
