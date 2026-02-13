# Airflow Operator Coverage Matrix

This document lists all Airflow operators supported by airflow-unfactor and their
Prefect equivalents. Generated automatically from the operator registry.

## Quick Reference

| Status | Meaning |
|--------|---------|
| ✅ Supported | Full conversion with Prefect integration |
| 🔧 Scaffold | Generates working scaffold code |
| ⚠️ Manual | Requires manual review after conversion |

**Total Operators Supported: 35**

## AWS S3

| Airflow Operator | Prefect Function | Integration | Status |
|------------------|------------------|-------------|--------|
| `S3CreateObjectOperator` | `s3_upload` | prefect-aws | ✅ Supported |
| `S3DeleteObjectsOperator` | `s3_delete` | prefect-aws | ✅ Supported |
| `S3CopyObjectOperator` | `s3_copy` | prefect-aws | ✅ Supported |
| `S3ListOperator` | `s3_list` | prefect-aws | ✅ Supported |
| `S3FileTransformOperator` | `s3_transform` | prefect-aws | ✅ Supported |

## AWS Compute

| Airflow Operator | Prefect Function | Integration | Status |
|------------------|------------------|-------------|--------|
| `LambdaInvokeFunctionOperator` | `lambda_invoke` | prefect-aws | ✅ Supported |
| `EcsRunTaskOperator` | `ecs_run_task` | prefect-aws | ✅ Supported |
| `EksCreateClusterOperator` | `eks_create_cluster` | prefect-aws | ✅ Supported |
| `EksPodOperator` | `kubernetes_job` | prefect-kubernetes | ✅ Supported |

## AWS Data

| Airflow Operator | Prefect Function | Integration | Status |
|------------------|------------------|-------------|--------|
| `GlueJobOperator` | `glue_job` | prefect-aws | ✅ Supported |
| `GlueCrawlerOperator` | `glue_crawler` | prefect-aws | ✅ Supported |
| `RedshiftSQLOperator` | `redshift_query` | prefect-aws | ✅ Supported |

## GCP Storage & BigQuery

| Airflow Operator | Prefect Function | Integration | Status |
|------------------|------------------|-------------|--------|
| `BigQueryInsertJobOperator` | `bigquery_query` | prefect-gcp | ✅ Supported |
| `BigQueryExecuteQueryOperator` | `bigquery_query` | prefect-gcp | ✅ Supported |
| `GCSCreateBucketOperator` | `create_gcs_bucket` | prefect-gcp | ✅ Supported |
| `GCSToGCSOperator` | `gcs_copy` | prefect-gcp | ✅ Supported |
| `GCSDeleteObjectsOperator` | `gcs_delete` | prefect-gcp | ✅ Supported |
| `GCSFileTransformOperator` | `gcs_transform` | prefect-gcp | ✅ Supported |

## GCP Compute

| Airflow Operator | Prefect Function | Integration | Status |
|------------------|------------------|-------------|--------|
| `DataprocSubmitJobOperator` | `dataproc_job` | prefect-gcp | ✅ Supported |
| `DataprocCreateClusterOperator` | `dataproc_create_cluster` | prefect-gcp | ✅ Supported |

## GCP Messaging

| Airflow Operator | Prefect Function | Integration | Status |
|------------------|------------------|-------------|--------|
| `PubSubPublishMessageOperator` | `pubsub_publish` | prefect-gcp | ✅ Supported |
| `PubSubCreateSubscriptionOperator` | `pubsub_create_subscription` | prefect-gcp | ✅ Supported |

## Azure

| Airflow Operator | Prefect Function | Integration | Status |
|------------------|------------------|-------------|--------|
| `WasbBlobOperator` | `azure_blob` | prefect-azure | ✅ Supported |
| `AzureDataFactoryRunPipelineOperator` | `adf_run_pipeline` | prefect-azure | ✅ Supported |

## Databricks

| Airflow Operator | Prefect Function | Integration | Status |
|------------------|------------------|-------------|--------|
| `DatabricksRunNowOperator` | `databricks_run_now` | prefect-databricks | ✅ Supported |
| `DatabricksSubmitRunOperator` | `databricks_submit_run` | prefect-databricks | ✅ Supported |
| `DatabricksSqlOperator` | `databricks_sql` | prefect-databricks | ✅ Supported |

## dbt

| Airflow Operator | Prefect Function | Integration | Status |
|------------------|------------------|-------------|--------|
| `DbtCloudRunJobOperator` | `dbt_cloud_run_job` | prefect-dbt | ✅ Supported |
| `DbtRunOperator` | `dbt_run` | prefect-dbt | ✅ Supported |

## Database

| Airflow Operator | Prefect Function | Integration | Status |
|------------------|------------------|-------------|--------|
| `PostgresOperator` | `execute_sql` | prefect-sqlalchemy | ✅ Supported |
| `MySqlOperator` | `execute_sql` | prefect-sqlalchemy | ✅ Supported |
| `SnowflakeOperator` | `snowflake_query` | prefect-snowflake | ✅ Supported |

## Notifications

| Airflow Operator | Prefect Function | Integration | Status |
|------------------|------------------|-------------|--------|
| `SlackWebhookOperator` | `send_message` | prefect-slack | ✅ Supported |
| `EmailOperator` | `send_email` | prefect-email | ✅ Supported |

## HTTP & General

| Airflow Operator | Prefect Function | Integration | Status |
|------------------|------------------|-------------|--------|
| `SimpleHttpOperator` | `http_request` | stdlib | ✅ Supported |

## Required Packages

Below are the Prefect integration packages required for each provider:

| Provider | Package | Installation |
|----------|---------|--------------|
| AWS | prefect-aws | `pip install prefect-aws` |
| GCP | prefect-gcp | `pip install prefect-gcp` |
| Azure | prefect-azure | `pip install prefect-azure` |
| Databricks | prefect-databricks | `pip install prefect-databricks` |
| dbt | prefect-dbt | `pip install prefect-dbt` |
| Snowflake | prefect-snowflake | `pip install prefect-snowflake` |
| SQL | prefect-sqlalchemy | `pip install prefect-sqlalchemy` |
| Slack | prefect-slack | `pip install prefect-slack` |
| Email | prefect-email | `pip install prefect-email` |
| Kubernetes | prefect-kubernetes | `pip install prefect-kubernetes` |

## Adding New Operators

To add support for a new Airflow operator:

1. Add an `OperatorMapping` entry to `src/airflow_unfactor/converters/provider_mappings.py`
2. Add the operator to the appropriate category in `get_operators_by_category()`
3. Add tests in `tests/test_provider_operators.py`
4. Run `python scripts/generate_operator_docs.py` to regenerate this file

---

*Generated by airflow-unfactor*