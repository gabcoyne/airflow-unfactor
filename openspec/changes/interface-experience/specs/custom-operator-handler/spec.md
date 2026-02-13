## ADDED Requirements

### Requirement: Detect custom operators
The system SHALL detect operators not in the provider mapping as custom operators.

#### Scenario: Unknown operator detection
- **WHEN** code uses operator class not in provider mappings
- **THEN** system identifies it as custom operator requiring manual review

#### Scenario: Distinguish from known operators
- **WHEN** code uses PythonOperator, BashOperator, or mapped provider operator
- **THEN** system does NOT flag as custom (uses standard conversion)

### Requirement: Extract execute method context
The system SHALL attempt to extract the `execute()` method body from custom operator classes defined in the same file or importable.

#### Scenario: Inline custom operator
- **WHEN** custom operator class is defined in the DAG file
- **THEN** system extracts `execute()` method body for context

#### Scenario: Imported custom operator
- **WHEN** custom operator is imported from another module
- **THEN** system notes the import path for user reference

### Requirement: Generate refactoring prompt
The system SHALL generate a TODO block with context to help users refactor custom operators to Prefect tasks.

#### Scenario: Prompt with execute body
- **WHEN** execute() method extracted
- **THEN** generated code includes commented execute() body with refactoring guidance

#### Scenario: Prompt without execute body
- **WHEN** execute() method not extractable
- **THEN** generated code includes TODO with operator class name and import path

### Requirement: Include operator parameters in prompt
The system SHALL include the operator's instantiation parameters in the refactoring prompt.

#### Scenario: Parameters captured
- **WHEN** custom operator instantiated with `MyOperator(param1=x, param2=y)`
- **THEN** prompt shows these parameters for reference in task signature

### Requirement: Generate stub task
The system SHALL generate a stub `@task` function for the custom operator.

#### Scenario: Stub task generation
- **WHEN** custom operator detected
- **THEN** generated code includes `@task def <task_id>(): ...` with TODO body

#### Scenario: Preserve task_id
- **WHEN** custom operator has `task_id="my_task"`
- **THEN** stub function is named `my_task` with `@task(name="my_task")`
