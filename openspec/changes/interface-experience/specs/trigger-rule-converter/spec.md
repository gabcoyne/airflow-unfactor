## ADDED Requirements

### Requirement: Detect trigger_rule parameter
The system SHALL detect `trigger_rule` parameter on operators and TaskFlow tasks.

#### Scenario: Detect operator trigger rule
- **WHEN** operator has `trigger_rule="all_done"` or other valid rule
- **THEN** system captures the trigger rule for conversion

#### Scenario: Detect default trigger rule
- **WHEN** operator has no explicit trigger_rule
- **THEN** system assumes `all_success` (Airflow default)

### Requirement: Convert all_success trigger rule
The system SHALL convert `trigger_rule="all_success"` (default) to normal Prefect task calls where exceptions propagate.

#### Scenario: All success is default
- **WHEN** task has `trigger_rule="all_success"` or no trigger_rule
- **THEN** generated Prefect code uses normal task call (no special handling)

### Requirement: Convert all_done trigger rule
The system SHALL convert `trigger_rule="all_done"` using `return_state=True` to capture upstream states without blocking on failure.

#### Scenario: All done conversion
- **WHEN** task has `trigger_rule="all_done"`
- **THEN** generated code calls upstreams with `return_state=True` and passes states to downstream

#### Scenario: All done educational comment
- **WHEN** all_done pattern is generated
- **THEN** comment explains task runs regardless of upstream success/failure

### Requirement: Convert failure-based trigger rules
The system SHALL convert `all_failed`, `one_failed`, `one_success`, `none_failed` using `allow_failure` annotation and state checks.

#### Scenario: One failed conversion
- **WHEN** task has `trigger_rule="one_failed"`
- **THEN** generated code checks `any(s.is_failed() for s in states)` before execution

#### Scenario: All failed conversion
- **WHEN** task has `trigger_rule="all_failed"`
- **THEN** generated code checks `all(s.is_failed() for s in states)` before execution

#### Scenario: None failed conversion
- **WHEN** task has `trigger_rule="none_failed"`
- **THEN** generated code checks `not any(s.is_failed() for s in states)` before execution

### Requirement: Generate state checking imports
The system SHALL add necessary imports for state-based trigger rule conversion.

#### Scenario: State imports added
- **WHEN** any non-default trigger rule is converted
- **THEN** imports include `from prefect.states import State` and `allow_failure` if needed
