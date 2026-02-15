## ADDED Requirements

### Requirement: Detect Airflow Variable usage
The system SHALL detect `Variable.get()` and `Variable.set()` calls.

#### Scenario: Detect Variable.get
- **WHEN** code contains `Variable.get("var_name")`
- **THEN** system detects variable read with name

#### Scenario: Detect Variable.get with default
- **WHEN** code contains `Variable.get("var_name", default_var="value")`
- **THEN** system detects variable with default value

#### Scenario: Detect Variable.set
- **WHEN** code contains `Variable.set("var_name", value)`
- **THEN** system detects variable write (requires Prefect Variable, not parameter)

### Requirement: Classify variables by sensitivity
The system SHALL classify variables as sensitive or non-sensitive based on naming patterns.

#### Scenario: Sensitive name detection
- **WHEN** variable name contains "key", "password", "secret", "token", "credential", or "auth"
- **THEN** system classifies as sensitive, recommends Prefect Secret

#### Scenario: Non-sensitive classification
- **WHEN** variable name does not match sensitive patterns
- **THEN** system classifies as non-sensitive, recommends Variable or parameter

### Requirement: Generate multiple scaffold options
The system SHALL generate scaffold code for all valid Prefect patterns with recommendations.

#### Scenario: Sensitive variable scaffold
- **WHEN** variable classified as sensitive
- **THEN** scaffold shows `Secret.load("name")` as recommended option

#### Scenario: Config variable scaffold
- **WHEN** variable has default value and is read-only
- **THEN** scaffold shows flow parameter as recommended, Variable as alternative

#### Scenario: Dynamic variable scaffold
- **WHEN** variable uses both get and set
- **THEN** scaffold shows `Variable.get()`/`Variable.set()` as only valid option

### Requirement: Generate setup instructions
The system SHALL include instructions for creating Variables and Secrets in Prefect.

#### Scenario: Secret setup instructions
- **WHEN** Secret scaffold generated
- **THEN** runbook includes `prefect secret create` or UI instructions

#### Scenario: Variable setup instructions
- **WHEN** Variable scaffold generated
- **THEN** runbook includes `prefect variable create` or UI instructions

### Requirement: Warn on dynamic variable patterns
The system SHALL warn when Variable.set() is detected, as this requires runtime Prefect Variable (not deployment-time config).

#### Scenario: Dynamic variable warning
- **WHEN** Variable.set() is detected
- **THEN** warning explains this requires Prefect Variable block, not flow parameter
