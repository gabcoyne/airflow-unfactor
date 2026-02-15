# OpenSpec: Provider Operator Mappings

## Overview
Map common Airflow provider operators to Prefect integrations and patterns.

## Requirements

### R1: AWS Operators
| Airflow Operator | Prefect Equivalent |
|------------------|--------------------|
| S3CreateObjectOperator | prefect-aws: s3_upload |
| S3DeleteObjectsOperator | prefect-aws: s3_delete |
| S3CopyObjectOperator | prefect-aws: s3_copy |
| GlueJobOperator | boto3 + prefect task |
| AthenaOperator | boto3 + prefect task |
| LambdaInvokeFunctionOperator | boto3 + prefect task |

### R2: GCP Operators  
| Airflow Operator | Prefect Equivalent |
|------------------|--------------------|
| GCSCreateBucketOperator | prefect-gcp: GcsBucket.create |
| BigQueryInsertJobOperator | prefect-gcp: bigquery_query |
| BigQueryExecuteQueryOperator | prefect-gcp: bigquery_query |
| DataprocSubmitJobOperator | google-cloud-dataproc + task |

### R3: Database Operators
| Airflow Operator | Prefect Equivalent |
|------------------|--------------------|
| PostgresOperator | prefect-sqlalchemy or psycopg |
| MySqlOperator | prefect-sqlalchemy or pymysql |
| SnowflakeOperator | prefect-snowflake |
| RedshiftSQLOperator | prefect-aws or psycopg |

### R4: Notification Operators
| Airflow Operator | Prefect Equivalent |
|------------------|--------------------|
| SlackWebhookOperator | prefect-slack: send_message |
| EmailOperator | smtplib or prefect-email |
| MsTeamsWebhookOperator | httpx POST |

### R5: Output Format
For each operator, generate:
- Prefect integration import (if available)
- Equivalent task code
- Required pip packages
- Connection migration notes

## Implementation Location
`src/airflow_unfactor/converters/providers.py`
