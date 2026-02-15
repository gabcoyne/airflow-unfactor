## ADDED Requirements

### Requirement: Parse and compare task graphs
The validation engine SHALL parse both original DAG and converted flow to extract task graphs for structural comparison.

#### Scenario: Extract tasks from DAG
- **WHEN** validation receives an Airflow DAG file
- **THEN** system extracts all task IDs and their dependencies

#### Scenario: Extract tasks from flow
- **WHEN** validation receives a Prefect flow file
- **THEN** system extracts all @task-decorated functions and their call relationships

### Requirement: Validate task count matches
The validation engine SHALL compare the number of tasks between original DAG and converted flow, accounting for expected differences.

#### Scenario: Task count matches
- **WHEN** original DAG has N operators and converted flow has N tasks
- **THEN** validation reports task_count_match: true

#### Scenario: Task count mismatch with explanation
- **WHEN** original DAG has 5 operators and converted flow has 4 tasks
- **THEN** validation reports task_count_match: false with list of missing tasks

#### Scenario: Expected differences ignored
- **WHEN** original DAG has DummyOperator/EmptyOperator tasks
- **THEN** these are excluded from count comparison (Prefect doesn't need them)

### Requirement: Validate dependency preservation
The validation engine SHALL verify that task dependencies are preserved in the converted flow.

#### Scenario: Dependencies match
- **WHEN** DAG has task_a >> task_b and flow calls task_b(task_a())
- **THEN** validation reports dependency_preserved: true

#### Scenario: Missing dependency detected
- **WHEN** DAG has task_a >> task_b but flow calls both without data passing
- **THEN** validation reports dependency_preserved: false with edge list

### Requirement: Validate data flow patterns
The validation engine SHALL detect XCom patterns in DAG and verify equivalent data passing in flow.

#### Scenario: XCom converted to return value
- **WHEN** DAG uses ti.xcom_push() and flow uses return
- **THEN** validation marks data flow as preserved

#### Scenario: XCom pull converted to parameter
- **WHEN** DAG uses ti.xcom_pull(task_ids="x") and flow passes x result as parameter
- **THEN** validation marks data flow as preserved

### Requirement: Generate validation report
The validation engine SHALL produce a structured report with pass/fail status and actionable diagnostics.

#### Scenario: All checks pass
- **WHEN** task count, dependencies, and data flow all match
- **THEN** report shows is_valid: true with summary

#### Scenario: Some checks fail
- **WHEN** one or more validation checks fail
- **THEN** report shows is_valid: false with specific issues and remediation suggestions

### Requirement: Calculate confidence score
The validation engine SHALL calculate a confidence score based on pattern complexity and coverage.

#### Scenario: Simple DAG high confidence
- **WHEN** DAG has only PythonOperators with simple XCom
- **THEN** confidence_score >= 90

#### Scenario: Complex DAG lower confidence
- **WHEN** DAG has trigger rules, dynamic mapping, custom operators
- **THEN** confidence_score reflects uncertainty in automated validation
