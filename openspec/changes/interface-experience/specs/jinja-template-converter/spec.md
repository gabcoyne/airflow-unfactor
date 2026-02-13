## ADDED Requirements

### Requirement: Detect Jinja2 template patterns
The system SHALL detect Jinja2 template variables in string literals (`{{ variable }}`).

#### Scenario: Detect ds variable
- **WHEN** string contains `{{ ds }}` or `{{ ds_nodash }}`
- **THEN** system identifies date formatting template

#### Scenario: Detect timestamp variables
- **WHEN** string contains `{{ ts }}` or `{{ ts_nodash }}`
- **THEN** system identifies timestamp template

#### Scenario: Detect data interval variables
- **WHEN** string contains `{{ data_interval_start }}` or `{{ data_interval_end }}`
- **THEN** system identifies data interval template

#### Scenario: Detect params access
- **WHEN** string contains `{{ params.name }}`
- **THEN** system identifies parameter reference

#### Scenario: Detect macros
- **WHEN** string contains `{{ macros.ds_add(ds, N) }}`
- **THEN** system identifies macro call with arguments

### Requirement: Convert date templates to runtime context
The system SHALL convert Airflow date templates to Prefect `runtime.flow_run.scheduled_start_time` with appropriate formatting.

#### Scenario: Convert ds to strftime
- **WHEN** template contains `{{ ds }}`
- **THEN** converted code uses `runtime.flow_run.scheduled_start_time.strftime('%Y-%m-%d')`

#### Scenario: Convert ds_nodash
- **WHEN** template contains `{{ ds_nodash }}`
- **THEN** converted code uses `.strftime('%Y%m%d')`

#### Scenario: Convert ts to isoformat
- **WHEN** template contains `{{ ts }}`
- **THEN** converted code uses `.isoformat()`

### Requirement: Convert params to flow parameters
The system SHALL convert `{{ params.x }}` references to flow function parameters.

#### Scenario: Params become flow args
- **WHEN** template contains `{{ params.config_value }}`
- **THEN** flow signature includes `config_value` parameter and f-string uses it

### Requirement: Convert macros to Python equivalents
The system SHALL convert Airflow macros to Python stdlib equivalents.

#### Scenario: Convert ds_add macro
- **WHEN** template contains `{{ macros.ds_add(ds, 7) }}`
- **THEN** converted code uses `(scheduled_start_time + timedelta(days=7)).strftime('%Y-%m-%d')`

### Requirement: Generate f-string output
The system SHALL convert Jinja2 template strings to Python f-strings.

#### Scenario: Full template conversion
- **WHEN** Airflow string is `"process_{{ ds }}_{{ params.env }}"`
- **THEN** Prefect code is f-string with runtime context and parameters

### Requirement: Warn on unrecognized templates
The system SHALL emit warnings for Jinja2 patterns not in the recognized set.

#### Scenario: Unknown template warning
- **WHEN** string contains `{{ custom_var }}` not in known patterns
- **THEN** warning emitted with original template preserved in comment

### Requirement: Add runtime import
The system SHALL add `from prefect import runtime` when Jinja2 templates are converted.

#### Scenario: Runtime import added
- **WHEN** any Jinja2 date/time template is converted
- **THEN** imports include `from prefect import runtime`
