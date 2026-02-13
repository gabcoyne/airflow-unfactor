## ADDED Requirements

### Requirement: AWS operator mappings
The provider registry SHALL include mappings for common AWS operators.

#### Scenario: S3 operators mapped
- **WHEN** DAG uses S3CopyObjectOperator, S3ListOperator, S3ToRedshiftOperator
- **THEN** convert generates prefect-aws S3Bucket-based tasks

#### Scenario: ECS/EKS operators mapped
- **WHEN** DAG uses EcsRunTaskOperator, EksCreateClusterOperator
- **THEN** convert generates prefect-aws or boto3-based task scaffolds

#### Scenario: Glue operators mapped
- **WHEN** DAG uses GlueJobOperator, GlueCrawlerOperator
- **THEN** convert generates boto3 glue client task scaffolds

#### Scenario: Redshift operators mapped
- **WHEN** DAG uses RedshiftSQLOperator, RedshiftDataOperator
- **THEN** convert generates prefect-sqlalchemy or boto3 task scaffolds

### Requirement: GCP operator mappings
The provider registry SHALL include mappings for common GCP operators.

#### Scenario: Cloud Storage operators mapped
- **WHEN** DAG uses GCSToGCSOperator, GCSDeleteObjectsOperator
- **THEN** convert generates prefect-gcp GcsBucket-based tasks

#### Scenario: Dataproc operators mapped
- **WHEN** DAG uses DataprocSubmitJobOperator, DataprocCreateClusterOperator
- **THEN** convert generates google-cloud-dataproc task scaffolds

#### Scenario: Pub/Sub operators mapped
- **WHEN** DAG uses PubSubPublishMessageOperator, PubSubCreateSubscriptionOperator
- **THEN** convert generates google-cloud-pubsub task scaffolds

### Requirement: Azure operator mappings
The provider registry SHALL include mappings for common Azure operators.

#### Scenario: Blob Storage operators mapped
- **WHEN** DAG uses AzureBlobStorageToAzureBlobStorageOperator
- **THEN** convert generates prefect-azure AzureBlobStorageCredentials tasks

#### Scenario: Data Factory operators mapped
- **WHEN** DAG uses AzureDataFactoryRunPipelineOperator
- **THEN** convert generates azure-mgmt-datafactory task scaffolds

### Requirement: Databricks operator mappings
The provider registry SHALL include mappings for Databricks operators.

#### Scenario: Job operators mapped
- **WHEN** DAG uses DatabricksRunNowOperator, DatabricksSubmitRunOperator
- **THEN** convert generates databricks-sdk task scaffolds

#### Scenario: SQL operators mapped
- **WHEN** DAG uses DatabricksSqlOperator
- **THEN** convert generates prefect-databricks or databricks-sql task scaffolds

### Requirement: dbt operator mappings
The provider registry SHALL include mappings for dbt operators.

#### Scenario: dbt Cloud operators mapped
- **WHEN** DAG uses DbtCloudRunJobOperator
- **THEN** convert generates prefect-dbt dbt_cloud_run_job tasks

#### Scenario: dbt Core operators mapped
- **WHEN** DAG uses DbtRunOperator (cosmos)
- **THEN** convert generates prefect-dbt DbtCoreOperation tasks

### Requirement: Generate integration scaffold code
Each operator mapping SHALL include working code template with proper imports.

#### Scenario: Code template includes imports
- **WHEN** operator mapping is applied
- **THEN** generated code includes necessary import statements

#### Scenario: Code template includes Block references
- **WHEN** operator requires credentials
- **THEN** generated code references appropriate Prefect Block type

#### Scenario: Code template includes pip packages
- **WHEN** operator needs additional packages
- **THEN** mapping.pip_packages lists required packages
