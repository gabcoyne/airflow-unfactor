## ADDED Requirements

### Requirement: Detect dynamic task mapping patterns
The system SHALL detect Airflow dynamic task mapping patterns including `.expand()` calls on tasks and `.partial().expand()` chains.

#### Scenario: Detect TaskFlow expand
- **WHEN** DAG contains `@task` decorated function called with `.expand(param=iterable)`
- **THEN** system detects dynamic mapping with parameter name and source

#### Scenario: Detect partial expand chain
- **WHEN** DAG contains `Operator.partial(fixed=value).expand(dynamic=iterable)`
- **THEN** system detects both partial (fixed) and expand (dynamic) parameters

#### Scenario: Detect expand_kwargs
- **WHEN** DAG contains `.expand_kwargs(list_of_dicts)`
- **THEN** system detects kwargs expansion pattern

### Requirement: Convert expand to Prefect map
The system SHALL convert Airflow `.expand()` to Prefect `.map()` with equivalent parameter mapping.

#### Scenario: Simple expand conversion
- **WHEN** Airflow code is `my_task.expand(item=get_items())`
- **THEN** generated Prefect code is `my_task.map(item=get_items())`

#### Scenario: Partial expand conversion
- **WHEN** Airflow code is `MyOperator.partial(conn_id="db").expand(query=queries)`
- **THEN** generated Prefect code passes fixed params normally and maps dynamic params

### Requirement: Warn on map_index_template
The system SHALL emit a warning when `map_index_template` parameter is detected, noting it has no Prefect equivalent (UI-only feature).

#### Scenario: Map index template warning
- **WHEN** DAG contains `.expand(..., map_index_template="...")`
- **THEN** warning is emitted explaining this is Airflow UI naming only
