## ADDED Requirements

### Requirement: Detect Airflow connection usage
The system SHALL detect Airflow connection references including hook instantiation and BaseHook calls.

#### Scenario: Detect hook with conn_id
- **WHEN** code contains `PostgresHook(postgres_conn_id="mydb")`
- **THEN** system detects connection "mydb" of type postgres

#### Scenario: Detect BaseHook get_connection
- **WHEN** code contains `BaseHook.get_connection("conn_name")`
- **THEN** system detects connection reference by name

#### Scenario: Detect operator conn_id parameter
- **WHEN** operator has `conn_id="aws_default"` or similar parameter
- **THEN** system detects connection reference

### Requirement: Map connection types to Prefect Blocks
The system SHALL map Airflow connection types to equivalent Prefect Block types.

#### Scenario: Postgres to SqlAlchemyConnector
- **WHEN** connection type is postgres or mysql
- **THEN** recommended Block is `SqlAlchemyConnector` from `prefect-sqlalchemy`

#### Scenario: S3 to AwsCredentials
- **WHEN** connection type is aws or s3
- **THEN** recommended Blocks are `AwsCredentials` and `S3Bucket` from `prefect-aws`

#### Scenario: BigQuery to GcpCredentials
- **WHEN** connection type is google_cloud or bigquery
- **THEN** recommended Block is `BigQueryCredentials` from `prefect-gcp`

#### Scenario: Snowflake to SnowflakeConnector
- **WHEN** connection type is snowflake
- **THEN** recommended Block is `SnowflakeConnector` from `prefect-snowflake`

### Requirement: Generate Block scaffold code
The system SHALL generate scaffold code showing Block loading pattern.

#### Scenario: Block scaffold generation
- **WHEN** postgres connection detected
- **THEN** scaffold shows `SqlAlchemyConnector.load("block-name")` pattern

#### Scenario: No secrets in scaffold
- **WHEN** Block scaffold is generated
- **THEN** no credentials or secrets appear in generated code

### Requirement: Generate Block setup instructions
The system SHALL include setup instructions for creating Blocks in Prefect.

#### Scenario: Setup instructions in runbook
- **WHEN** connections are detected
- **THEN** runbook includes steps to create Blocks via UI or CLI

#### Scenario: Package requirements noted
- **WHEN** Block requires prefect integration package
- **THEN** runbook notes required `pip install prefect-<integration>`

### Requirement: Warn on unknown connection types
The system SHALL warn when connection type cannot be mapped to a known Block.

#### Scenario: Unknown connection warning
- **WHEN** connection type is not in mapping (e.g., custom hook)
- **THEN** warning emitted with generic Block scaffold suggestion
