"""Explain Airflow concepts and Prefect equivalents."""

import json
from airflow_unfactor.external_mcp import ExternalMCPClient

CONCEPT_EXPLANATIONS = {
    "xcom": {
        "airflow_concept": "XCom",
        "airflow_description": "Key-value store for passing data between tasks via the metadata database",
        "prefect_equivalent": "Return values / Artifacts",
        "prefect_advantages": [
            "Direct in-memory passing - no database round-trip",
            "Type-safe with Python's native types", 
            "No size limits (Airflow XCom has DB constraints)",
            "Automatic serialization of complex objects",
        ],
        "code_example": {
            "airflow": """ti.xcom_push(key='data', value=result)
data = ti.xcom_pull(task_ids='extract', key='data')""",
            "prefect": """return result  # Just return it!
data = extract()  # Call returns the value directly""",
        },
    },
    "sensor": {
        "airflow_concept": "Sensor",
        "airflow_description": "Operator that waits for a condition, consuming a worker slot while polling",
        "prefect_equivalent": "Triggers / Polling flows / Events",
        "prefect_advantages": [
            "Event-driven triggers don't consume resources while waiting",
            "Polling flows can be lightweight scheduled checks",
            "Native webhook support for push-based workflows",
            "No worker slot blocked during wait periods",
        ],
        "code_example": {
            "airflow": "S3KeySensor(task_id='wait_for_file', bucket='my-bucket', key='data.csv')",
            "prefect": """# Option 1: Polling flow
@flow
def check_s3():
    if s3_file_exists('my-bucket', 'data.csv'):
        run_deployment('process-data')

# Option 2: Event trigger via Prefect automation""",
        },
    },
    "executor": {
        "airflow_concept": "Executor",
        "airflow_description": "Component that determines how tasks are run (Local, Celery, Kubernetes)",
        "prefect_equivalent": "Work Pools / Workers / Task Runners",
        "prefect_advantages": [
            "Flows run in a single execution context (not task-by-task pods)",
            "Direct in-memory data passing between tasks",
            "Simpler infrastructure - no separate scheduler/worker split",
            "DaskTaskRunner for parallelism within a flow",
        ],
        "code_example": {
            "airflow": """# airflow.cfg
executor = KubernetesExecutor""",
            "prefect": """# Create a work pool
prefect work-pool create k8s-pool --type kubernetes

# Deploy flow to it
flow.deploy(work_pool_name='k8s-pool')""",
        },
    },
    "hook": {
        "airflow_concept": "Hook",
        "airflow_description": "Interface to external services, configured via Airflow Connections",
        "prefect_equivalent": "Blocks",
        "prefect_advantages": [
            "Blocks are versioned and can be shared across flows",
            "UI for managing credentials and configuration",
            "Type-safe with Pydantic models",
            "Can be loaded by name or created in code",
        ],
        "code_example": {
            "airflow": """from airflow.providers.amazon.aws.hooks.s3 import S3Hook
hook = S3Hook(aws_conn_id='my_aws_conn')""",
            "prefect": """from prefect_aws import S3Bucket
s3 = S3Bucket.load('my-s3-bucket')
# or
s3 = S3Bucket(bucket_name='my-bucket', credentials=...)""",
        },
    },
    "connection": {
        "airflow_concept": "Connection",
        "airflow_description": "Stored credentials in the metadata database, referenced by conn_id",
        "prefect_equivalent": "Blocks / Environment Variables / Secret Blocks",
        "prefect_advantages": [
            "Blocks provide typed, validated credential storage",
            "Secret blocks for sensitive values",
            "Environment variables for simple cases",
            "No dependency on a metadata database",
        ],
        "code_example": {
            "airflow": """# In Airflow UI or CLI:
airflow connections add my_pg --conn-type postgres --host localhost""",
            "prefect": """# Create a block in UI or code:
from prefect_sqlalchemy import SqlAlchemyConnector
conn = SqlAlchemyConnector(connection_info=...)
conn.save('my-postgres')""",
        },
    },
    "variable": {
        "airflow_concept": "Variable",
        "airflow_description": "Key-value store for runtime configuration, stored in metadata DB",
        "prefect_equivalent": "Environment Variables / Blocks / Parameters",
        "prefect_advantages": [
            "Environment variables for simple config",
            "JSON blocks for complex configuration",
            "Flow parameters for runtime inputs",
            "No database dependency",
        ],
        "code_example": {
            "airflow": """from airflow.models import Variable
value = Variable.get('my_var')""",
            "prefect": """import os
value = os.environ['MY_VAR']
# or
from prefect.blocks.system import JSON
config = JSON.load('my-config')""",
        },
    },
}


async def explain_concept(concept: str, include_external_context: bool = True) -> str:
    """Explain an Airflow concept and its Prefect equivalent.

    Args:
        concept: Airflow concept name
        include_external_context: Enrich with external MCP context

    Returns:
        JSON with explanation and examples
    """
    key = concept.lower().strip()
    external_context = {}

    if key in CONCEPT_EXPLANATIONS:
        result = CONCEPT_EXPLANATIONS[key]
        if include_external_context:
            client = ExternalMCPClient.from_env()
            external_context["prefect"] = await client.call_prefect_search(
                f"{concept} in Prefect"
            )
        if external_context:
            result = {**result, "external_context": external_context}
        return json.dumps(result, indent=2)

    return json.dumps({
        "error": f"Unknown concept: {concept}",
        "available": list(CONCEPT_EXPLANATIONS.keys()),
    }, indent=2)
