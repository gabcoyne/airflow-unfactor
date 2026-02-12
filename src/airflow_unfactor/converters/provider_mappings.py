"""Map Airflow provider operators to Prefect integrations.

See specs/provider-operators.openspec.md for specification.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OperatorMapping:
    """Mapping from Airflow operator to Prefect equivalent."""
    airflow_operator: str
    prefect_integration: str | None  # e.g., "prefect-aws"
    prefect_function: str  # e.g., "s3_upload"
    pip_packages: list[str] = field(default_factory=list)
    import_statement: str = ""
    code_template: str = ""
    notes: str = ""


# Operator mappings registry
OPERATOR_MAPPINGS: dict[str, OperatorMapping] = {
    # AWS Operators
    "S3CreateObjectOperator": OperatorMapping(
        airflow_operator="S3CreateObjectOperator",
        prefect_integration="prefect-aws",
        prefect_function="s3_upload",
        pip_packages=["prefect-aws"],
        import_statement="from prefect_aws import S3Bucket",
        code_template="""@task
def upload_to_s3(data: bytes, key: str):
    s3_bucket = S3Bucket.load("my-bucket")  # Configure in Prefect UI
    s3_bucket.upload_from_bytes(data, key)""",
        notes="Configure S3Bucket block in Prefect UI with credentials",
    ),
    "S3DeleteObjectsOperator": OperatorMapping(
        airflow_operator="S3DeleteObjectsOperator",
        prefect_integration="prefect-aws",
        prefect_function="s3_delete",
        pip_packages=["prefect-aws"],
        import_statement="from prefect_aws import S3Bucket",
        code_template="""@task
def delete_s3_objects(keys: list[str]):
    import boto3
    s3 = boto3.client('s3')
    s3.delete_objects(Bucket='bucket', Delete={'Objects': [{'Key': k} for k in keys]})""",
    ),
    "LambdaInvokeFunctionOperator": OperatorMapping(
        airflow_operator="LambdaInvokeFunctionOperator",
        prefect_integration="prefect-aws",
        prefect_function="lambda_invoke",
        pip_packages=["prefect-aws", "boto3"],
        import_statement="from prefect_aws.lambda_function import LambdaFunction",
        code_template="""@task
def invoke_lambda(function_name: str, payload: dict):
    import boto3
    import json
    client = boto3.client('lambda')
    response = client.invoke(
        FunctionName=function_name,
        Payload=json.dumps(payload),
    )
    return json.loads(response['Payload'].read())""",
    ),
    
    # GCP Operators
    "BigQueryInsertJobOperator": OperatorMapping(
        airflow_operator="BigQueryInsertJobOperator",
        prefect_integration="prefect-gcp",
        prefect_function="bigquery_query",
        pip_packages=["prefect-gcp"],
        import_statement="from prefect_gcp.bigquery import bigquery_query",
        code_template="""@task
def run_bigquery_job(query: str):
    from prefect_gcp import GcpCredentials
    from google.cloud import bigquery
    
    credentials = GcpCredentials.load("my-gcp-creds")
    client = bigquery.Client(credentials=credentials.get_credentials_from_service_account())
    job = client.query(query)
    return job.result()""",
        notes="Configure GcpCredentials block in Prefect UI",
    ),
    "BigQueryExecuteQueryOperator": OperatorMapping(
        airflow_operator="BigQueryExecuteQueryOperator",
        prefect_integration="prefect-gcp",
        prefect_function="bigquery_query",
        pip_packages=["prefect-gcp"],
        import_statement="from prefect_gcp.bigquery import bigquery_query",
        code_template="""@task
def execute_bigquery(sql: str):
    from prefect_gcp import GcpCredentials
    from google.cloud import bigquery
    
    credentials = GcpCredentials.load("my-gcp-creds")
    client = bigquery.Client(credentials=credentials.get_credentials_from_service_account())
    return list(client.query(sql).result())""",
    ),
    "GCSCreateBucketOperator": OperatorMapping(
        airflow_operator="GCSCreateBucketOperator",
        prefect_integration="prefect-gcp",
        prefect_function="create_gcs_bucket",
        pip_packages=["prefect-gcp"],
        import_statement="from prefect_gcp import GcsBucket",
        code_template="""@task
def create_gcs_bucket(bucket_name: str, location: str = "US"):
    from google.cloud import storage
    client = storage.Client()
    bucket = client.create_bucket(bucket_name, location=location)
    return bucket.name""",
    ),
    
    # Database Operators
    "PostgresOperator": OperatorMapping(
        airflow_operator="PostgresOperator",
        prefect_integration="prefect-sqlalchemy",
        prefect_function="execute_sql",
        pip_packages=["prefect-sqlalchemy", "psycopg2-binary"],
        import_statement="from prefect_sqlalchemy import SqlAlchemyConnector",
        code_template="""@task
def execute_postgres(sql: str):
    connector = SqlAlchemyConnector.load("postgres-conn")  # Configure in Prefect UI
    with connector.get_connection() as conn:
        conn.execute(sql)""",
        notes="Configure SqlAlchemyConnector block with PostgreSQL connection string",
    ),
    "MySqlOperator": OperatorMapping(
        airflow_operator="MySqlOperator",
        prefect_integration="prefect-sqlalchemy",
        prefect_function="execute_sql",
        pip_packages=["prefect-sqlalchemy", "pymysql"],
        import_statement="from prefect_sqlalchemy import SqlAlchemyConnector",
        code_template="""@task
def execute_mysql(sql: str):
    connector = SqlAlchemyConnector.load("mysql-conn")
    with connector.get_connection() as conn:
        conn.execute(sql)""",
    ),
    "SnowflakeOperator": OperatorMapping(
        airflow_operator="SnowflakeOperator",
        prefect_integration="prefect-snowflake",
        prefect_function="snowflake_query",
        pip_packages=["prefect-snowflake"],
        import_statement="from prefect_snowflake import SnowflakeConnector",
        code_template="""@task
def execute_snowflake(query: str):
    connector = SnowflakeConnector.load("snowflake-conn")
    return connector.fetch_all(query)""",
        notes="Configure SnowflakeConnector block in Prefect UI",
    ),
    
    # Notification Operators
    "SlackWebhookOperator": OperatorMapping(
        airflow_operator="SlackWebhookOperator",
        prefect_integration="prefect-slack",
        prefect_function="send_message",
        pip_packages=["prefect-slack"],
        import_statement="from prefect_slack import SlackWebhook",
        code_template="""@task
def send_slack_message(message: str):
    webhook = SlackWebhook.load("slack-webhook")  # Configure in Prefect UI
    webhook.notify(body=message)""",
        notes="Configure SlackWebhook block with webhook URL",
    ),
    "EmailOperator": OperatorMapping(
        airflow_operator="EmailOperator",
        prefect_integration="prefect-email",
        prefect_function="send_email",
        pip_packages=["prefect-email"],
        import_statement="from prefect_email import EmailServerCredentials, email_send_message",
        code_template="""@task
def send_email(to: list[str], subject: str, body: str):
    credentials = EmailServerCredentials.load("email-creds")
    email_send_message(
        email_server_credentials=credentials,
        subject=subject,
        msg=body,
        email_to=to,
    )""",
    ),
    
    # Generic/Utility Operators
    "SimpleHttpOperator": OperatorMapping(
        airflow_operator="SimpleHttpOperator",
        prefect_integration=None,
        prefect_function="http_request",
        pip_packages=["httpx"],
        import_statement="import httpx",
        code_template="""@task
def http_request(method: str, url: str, data: dict = None):
    response = httpx.request(method, url, json=data)
    response.raise_for_status()
    return response.json()""",
    ),
}


def get_operator_mapping(operator_name: str) -> OperatorMapping | None:
    """Get the Prefect mapping for an Airflow operator.
    
    Args:
        operator_name: Name of the Airflow operator
        
    Returns:
        OperatorMapping if found, None otherwise
    """
    return OPERATOR_MAPPINGS.get(operator_name)


def get_all_mappings() -> dict[str, OperatorMapping]:
    """Get all operator mappings."""
    return OPERATOR_MAPPINGS.copy()


def generate_conversion_code(
    operator_name: str,
    task_id: str,
    parameters: dict[str, Any],
    include_comments: bool = True,
) -> dict[str, Any]:
    """Generate Prefect code for an Airflow operator.
    
    Args:
        operator_name: Name of the Airflow operator
        task_id: The task_id from Airflow
        parameters: Operator parameters
        include_comments: Include educational comments
        
    Returns:
        Dictionary with code, imports, packages, notes
    """
    mapping = get_operator_mapping(operator_name)
    
    if not mapping:
        # Unknown operator - generate generic task
        return {
            "code": f"""@task
def {task_id}():
    \"\"\"Converted from {operator_name}.\"\"\"  
    # TODO: Implement operator logic
    # Original parameters: {parameters}
    raise NotImplementedError("Manual conversion needed for {operator_name}")""",
            "imports": ["from prefect import task"],
            "packages": [],
            "notes": [f"Unknown operator: {operator_name}. Manual conversion required."],
        }
    
    lines = []
    
    if include_comments:
        lines.append(f"# Converted from Airflow {operator_name}")
        if mapping.prefect_integration:
            lines.append(f"# Using Prefect integration: {mapping.prefect_integration}")
        if mapping.notes:
            lines.append(f"# Note: {mapping.notes}")
        lines.append("")
    
    lines.append(mapping.import_statement)
    lines.append("from prefect import task")
    lines.append("")
    
    # Customize code template with task_id
    code = mapping.code_template.replace("@task\ndef ", f"@task\ndef {task_id}_")
    lines.append(code)
    
    return {
        "code": "\n".join(lines),
        "imports": [mapping.import_statement, "from prefect import task"],
        "packages": mapping.pip_packages,
        "notes": [mapping.notes] if mapping.notes else [],
    }


def summarize_operator_support() -> str:
    """Generate a summary of supported operator conversions."""
    lines = ["# Supported Airflow Operator Conversions", ""]
    
    # Group by category
    categories = {
        "AWS": ["S3CreateObjectOperator", "S3DeleteObjectsOperator", "LambdaInvokeFunctionOperator"],
        "GCP": ["BigQueryInsertJobOperator", "BigQueryExecuteQueryOperator", "GCSCreateBucketOperator"],
        "Database": ["PostgresOperator", "MySqlOperator", "SnowflakeOperator"],
        "Notifications": ["SlackWebhookOperator", "EmailOperator"],
        "HTTP": ["SimpleHttpOperator"],
    }
    
    for category, operators in categories.items():
        lines.append(f"## {category}")
        for op in operators:
            mapping = OPERATOR_MAPPINGS.get(op)
            if mapping:
                integration = mapping.prefect_integration or "stdlib"
                lines.append(f"- {op} \u2192 {integration}: {mapping.prefect_function}")
        lines.append("")
    
    return "\n".join(lines)
