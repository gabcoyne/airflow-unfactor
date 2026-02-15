"""Fetch Prefect context and documentation for LLM-assisted code generation."""

import json
from typing import Any

from airflow_unfactor.external_mcp import ExternalMCPClient

# Operator mapping: Airflow operator → Prefect equivalent pattern
OPERATOR_MAPPINGS: dict[str, dict[str, Any]] = {
    "PythonOperator": {
        "prefect_pattern": "@task decorated function",
        "example": """
@task
def my_task(param: str) -> dict:
    # Your Python code here
    return {"result": value}
""",
        "notes": [
            "Return values replace XCom push",
            "Function arguments replace op_kwargs",
            "Type hints recommended for clarity",
        ],
    },
    "BashOperator": {
        "prefect_pattern": "prefect_shell.ShellOperation or subprocess",
        "example": """
from prefect_shell import ShellOperation

@task
def run_bash_command():
    result = ShellOperation(commands=["echo 'hello'"]).run()
    return result
""",
        "notes": [
            "Use prefect_shell for shell commands",
            "Can also use subprocess directly",
            "Consider security implications of shell commands",
        ],
    },
    "BranchPythonOperator": {
        "prefect_pattern": "Python if/else with task references",
        "example": """
@flow
def branching_flow():
    condition = check_condition()
    if condition:
        result = branch_a()
    else:
        result = branch_b()
    return result
""",
        "notes": [
            "Use native Python control flow",
            "Tasks can be called conditionally",
            "Return values determine execution path",
        ],
    },
    "DummyOperator": {
        "prefect_pattern": "Not needed - use task dependencies",
        "example": "# Simply chain tasks: task_a() >> task_b()",
        "notes": [
            "Prefect doesn't need placeholder tasks",
            "Use task return values for dependencies",
        ],
    },
    "EmptyOperator": {
        "prefect_pattern": "Not needed - use task dependencies",
        "example": "# Simply chain tasks: task_a() >> task_b()",
        "notes": ["Same as DummyOperator - not needed in Prefect"],
    },
    "TriggerDagRunOperator": {
        "prefect_pattern": "run_deployment or subflow",
        "example": """
from prefect.deployments import run_deployment

@task
def trigger_other_flow():
    run_deployment(name="other-flow/deployment-name")
""",
        "notes": [
            "Use run_deployment for deployed flows",
            "Use subflows for inline execution",
            "Can pass parameters to triggered flows",
        ],
    },
    "ShortCircuitOperator": {
        "prefect_pattern": "raise SKIP or conditional execution",
        "example": """
from prefect.states import Completed

@task
def maybe_skip(condition: bool):
    if not condition:
        return Completed(message="Skipped")
    return do_work()
""",
        "notes": [
            "Return early to skip downstream",
            "Use state handlers for complex skip logic",
        ],
    },
    "ExternalTaskSensor": {
        "prefect_pattern": "Deployment triggers or polling",
        "example": """
from prefect import flow
from prefect.events import DeploymentEventTrigger

# Option 1: Event-driven trigger in prefect.yaml
# Option 2: Polling
@task(retries=60, retry_delay_seconds=60)
def wait_for_external():
    # Poll for condition
    if not check_condition():
        raise Exception("Not ready")
""",
        "notes": [
            "Prefer event-driven triggers",
            "Use automations for cross-flow dependencies",
            "Polling with retries as fallback",
        ],
    },
    "FileSensor": {
        "prefect_pattern": "Polling with retries or file events",
        "example": """
from pathlib import Path

@task(retries=60, retry_delay_seconds=60)
def wait_for_file(path: str):
    if not Path(path).exists():
        raise Exception("File not found")
    return path
""",
        "notes": [
            "Use cloud provider events when possible",
            "Polling with retries for simple cases",
        ],
    },
    "S3KeySensor": {
        "prefect_pattern": "prefect-aws S3 with polling or S3 events",
        "example": """
from prefect_aws import S3Bucket

@task(retries=60, retry_delay_seconds=60)
def wait_for_s3_key(bucket_name: str, key: str):
    s3 = S3Bucket.load("my-bucket")
    # Check if object exists
    try:
        s3.read_path(key)
        return True
    except:
        raise Exception("Key not found")
""",
        "notes": [
            "Consider S3 event notifications with Lambda/SNS",
            "Use automations to trigger on S3 events",
            "Polling as fallback",
        ],
    },
    "HttpSensor": {
        "prefect_pattern": "httpx with retries",
        "example": """
import httpx

@task(retries=60, retry_delay_seconds=60)
def wait_for_endpoint(url: str, expected_status: int = 200):
    response = httpx.get(url)
    if response.status_code != expected_status:
        raise Exception(f"Got {response.status_code}")
    return response.json()
""",
        "notes": [
            "Use httpx for HTTP requests",
            "Configure retries and delays",
            "Consider webhooks for event-driven approach",
        ],
    },
    "SqlSensor": {
        "prefect_pattern": "Database query with retries",
        "example": """
from prefect_sqlalchemy import SqlAlchemyConnector

@task(retries=60, retry_delay_seconds=60)
def wait_for_data(query: str):
    connector = SqlAlchemyConnector.load("my-db")
    result = connector.fetch_one(query)
    if not result:
        raise Exception("No data found")
    return result
""",
        "notes": [
            "Use prefect_sqlalchemy blocks",
            "Configure connection in Prefect blocks",
        ],
    },
    "PostgresOperator": {
        "prefect_pattern": "prefect_sqlalchemy SqlAlchemyConnector",
        "example": """
from prefect_sqlalchemy import SqlAlchemyConnector

@task
def run_postgres_query(sql: str):
    connector = SqlAlchemyConnector.load("postgres-conn")
    result = connector.execute(sql)
    return result
""",
        "notes": [
            "Use SqlAlchemyConnector block",
            "Supports transactions",
            "Configure credentials in block",
        ],
    },
    "BigQueryInsertJobOperator": {
        "prefect_pattern": "prefect_gcp BigQueryWarehouse",
        "example": """
from prefect_gcp.bigquery import BigQueryWarehouse

@task
def run_bigquery_job(query: str):
    bq = BigQueryWarehouse.load("my-bq")
    result = bq.execute(query)
    return result
""",
        "notes": [
            "Use prefect_gcp for BigQuery",
            "Configure GCP credentials in block",
        ],
    },
    "S3CreateObjectOperator": {
        "prefect_pattern": "prefect_aws S3Bucket",
        "example": """
from prefect_aws import S3Bucket

@task
def upload_to_s3(data: bytes, key: str):
    s3 = S3Bucket.load("my-bucket")
    s3.write_path(key, data)
""",
        "notes": [
            "Use prefect_aws for S3 operations",
            "Configure AWS credentials in block",
        ],
    },
    "SlackWebhookOperator": {
        "prefect_pattern": "prefect_slack or direct webhook",
        "example": """
from prefect_slack import SlackWebhook

@task
def send_slack_message(message: str):
    webhook = SlackWebhook.load("my-webhook")
    webhook.notify(body=message)
""",
        "notes": [
            "Use prefect_slack for Slack integration",
            "Can also use for failure notifications via automations",
        ],
    },
    "EmailOperator": {
        "prefect_pattern": "prefect_email EmailServerCredentials",
        "example": """
from prefect_email import EmailServerCredentials, email_send_message

@task
def send_email(to: str, subject: str, body: str):
    credentials = EmailServerCredentials.load("email-creds")
    email_send_message(
        email_server_credentials=credentials,
        subject=subject,
        msg=body,
        email_to=to,
    )
""",
        "notes": [
            "Use prefect_email for email sending",
            "Configure SMTP in block",
        ],
    },
    "TaskGroup": {
        "prefect_pattern": "Subflow",
        "example": """
@flow
def task_group_equivalent():
    # Group related tasks in a subflow
    result_a = task_a()
    result_b = task_b(result_a)
    return result_b

@flow
def main_flow():
    before = setup_task()
    group_result = task_group_equivalent()
    after = cleanup_task(group_result)
""",
        "notes": [
            "Subflows provide logical grouping",
            "Can be reused across flows",
            "Have their own run tracking",
        ],
    },
}

# Connection to Block mappings
CONNECTION_BLOCK_MAPPINGS: dict[str, dict[str, str]] = {
    "aws_default": {
        "block_type": "AwsCredentials",
        "package": "prefect_aws",
        "notes": "Use for S3, Lambda, EC2, etc.",
    },
    "google_cloud_default": {
        "block_type": "GcpCredentials",
        "package": "prefect_gcp",
        "notes": "Use for BigQuery, GCS, etc.",
    },
    "postgres_default": {
        "block_type": "SqlAlchemyConnector",
        "package": "prefect_sqlalchemy",
        "notes": "Use postgresql+psycopg2:// connection string",
    },
    "mysql_default": {
        "block_type": "SqlAlchemyConnector",
        "package": "prefect_sqlalchemy",
        "notes": "Use mysql+pymysql:// connection string",
    },
    "slack_default": {
        "block_type": "SlackWebhook",
        "package": "prefect_slack",
        "notes": "Configure webhook URL in block",
    },
    "http_default": {
        "block_type": "N/A - use httpx directly",
        "package": "httpx",
        "notes": "Use httpx for HTTP requests",
    },
}


async def get_prefect_context(
    topics: list[str] | None = None,
    detected_features: list[str] | None = None,
) -> str:
    """Fetch relevant Prefect documentation and patterns.

    Args:
        topics: Specific topics to fetch docs for (flows, tasks, blocks, deployments)
        detected_features: Features detected in DAG (taskflow, sensors, xcom, etc.)

    Returns:
        JSON with Prefect documentation and patterns relevant to the conversion
    """
    topics = topics or ["flows", "tasks"]
    detected_features = detected_features or []

    result: dict[str, Any] = {
        "documentation": {},
        "patterns": {},
        "blocks": {},
        "deployment_config": {},
    }

    # Build search queries based on topics and features
    queries = []

    # Base topics
    topic_queries = {
        "flows": "Prefect flow decorator best practices",
        "tasks": "Prefect task decorator retry configuration",
        "blocks": "Prefect blocks credentials configuration",
        "deployments": "Prefect deployment YAML configuration",
        "work_pools": "Prefect work pools kubernetes configuration",
        "events": "Prefect events automations triggers",
    }

    for topic in topics:
        if topic in topic_queries:
            queries.append(topic_queries[topic])

    # Feature-specific queries
    feature_queries = {
        "sensors": "Prefect polling retry pattern sensor equivalent",
        "xcom": "Prefect task return values data passing",
        "taskflow": "Prefect TaskFlow API migration",
        "datasets": "Prefect events automations data dependencies",
        "branching": "Prefect conditional task execution",
        "dynamic_mapping": "Prefect map dynamic task generation",
        "task_groups": "Prefect subflows task grouping",
        "connections": "Prefect blocks credentials secrets",
        "variables": "Prefect variables configuration",
    }

    for feature in detected_features:
        if feature in feature_queries:
            queries.append(feature_queries[feature])

    # Fetch from Prefect MCP
    client = ExternalMCPClient.from_env()
    for query in queries:
        doc_result = await client.call_prefect_search(query)
        if doc_result and "error" not in str(doc_result).lower():
            result["documentation"][query] = doc_result

    # Add static patterns for detected operators
    result["operator_patterns"] = OPERATOR_MAPPINGS
    result["connection_mappings"] = CONNECTION_BLOCK_MAPPINGS

    # Add deployment structure template
    result["deployment_template"] = get_deployment_template()

    return json.dumps(result, indent=2)


def get_deployment_template() -> dict[str, Any]:
    """Get the prefect.yaml deployment structure template."""
    return {
        "structure": {
            "name": "flows",
            "prefect-version": "3.0.0",
            "pull": [
                {
                    "prefect.deployments.steps.git_clone": {
                        "repository": "https://github.com/org/repo",
                        "branch": "main",
                        "access_token": "{{ prefect.blocks.secret.repo-pat }}",
                    }
                }
            ],
            "definitions": {
                "docker_build": "YAML anchors for reusable build steps",
                "work_pools": "YAML anchors for work pool configurations",
                "schedules": "YAML anchors for common schedules",
            },
            "deployments": [
                {
                    "name": "Deployment Name",
                    "description": "Description of what this flow does",
                    "entrypoint": "deployments/<workspace>/<flow>/flow.py:flow_name",
                    "schedules": ["cron or interval schedules"],
                    "parameters": {"param": "default_value"},
                    "work_pool": {"name": "work-pool-name", "job_variables": {}},
                    "build": ["Docker build steps if needed"],
                    "push": ["Docker push steps if needed"],
                }
            ],
        },
        "directory_structure": {
            "pattern": "deployments/<workspace>/<flow-name>/",
            "files": {
                "flow.py": "Main flow implementation",
                "Dockerfile": "Optional - if custom dependencies needed",
                "requirements.txt": "Python dependencies",
            },
        },
        "schedule_examples": {
            "cron_hourly": {"cron": "0 * * * *"},
            "cron_daily_8am": {"cron": "0 8 * * *", "timezone": "America/New_York"},
            "interval": {"interval": 3600},  # seconds
        },
        "work_pool_examples": {
            "kubernetes": {
                "name": "kubernetes-pool",
                "job_variables": {
                    "image": "{{ image }}",
                    "service_account_name": "flow-runner",
                },
            },
            "docker": {
                "name": "docker-pool",
                "job_variables": {"image": "{{ image }}"},
            },
        },
    }


async def get_operator_mapping(operator_type: str) -> str:
    """Get detailed mapping for a specific Airflow operator.

    Args:
        operator_type: The Airflow operator type (e.g., "PythonOperator")

    Returns:
        JSON with Prefect equivalent pattern, example code, and migration notes
    """
    if operator_type in OPERATOR_MAPPINGS:
        mapping = OPERATOR_MAPPINGS[operator_type]
        return json.dumps(
            {
                "operator": operator_type,
                "mapping": mapping,
                "status": "supported",
            },
            indent=2,
        )
    else:
        return json.dumps(
            {
                "operator": operator_type,
                "mapping": None,
                "status": "unsupported",
                "suggestion": "Use @task decorator with custom implementation",
                "notes": [
                    "This operator doesn't have a direct Prefect equivalent",
                    "Implement the logic directly in a @task function",
                    "Check if there's a prefect-* integration package",
                ],
            },
            indent=2,
        )


async def get_connection_mapping(connection_id: str) -> str:
    """Get Prefect block mapping for an Airflow connection.

    Args:
        connection_id: The Airflow connection ID

    Returns:
        JSON with Prefect block type and configuration guidance
    """
    # Try to match connection ID pattern
    connection_type = None
    for pattern in CONNECTION_BLOCK_MAPPINGS:
        if pattern in connection_id.lower():
            connection_type = pattern
            break

    if connection_type:
        mapping = CONNECTION_BLOCK_MAPPINGS[connection_type]
        return json.dumps(
            {
                "connection_id": connection_id,
                "matched_pattern": connection_type,
                "prefect_block": mapping,
                "status": "mapped",
            },
            indent=2,
        )
    else:
        return json.dumps(
            {
                "connection_id": connection_id,
                "matched_pattern": None,
                "prefect_block": None,
                "status": "unknown",
                "suggestions": [
                    "Check prefect integrations catalog for matching block type",
                    "Use Secret block for credentials",
                    "Use JSON block for complex configuration",
                ],
            },
            indent=2,
        )
