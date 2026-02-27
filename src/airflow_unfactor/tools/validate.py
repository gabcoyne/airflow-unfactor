"""Validate DAG to flow conversions.

Returns both source files for LLM comparison plus syntax validation.
Structural comparison is done by the LLM, not AST.
"""

import json
from pathlib import Path

from airflow_unfactor.validation import validate_python_syntax


async def validate_conversion(
    original_dag: str,
    converted_flow: str,
) -> str:
    """Validate a converted flow against the original DAG.

    Returns both source files for the LLM to compare, plus a syntax
    check on the generated code.

    Args:
        original_dag: Path or content of original DAG
        converted_flow: Path or content of converted flow

    Returns:
        JSON with original_source, converted_source, syntax_valid,
        syntax_errors, and comparison_guidance.
    """
    # Load content if paths provided (short strings without newlines might be paths)
    original_source = original_dag
    if "\n" not in original_dag and len(original_dag) < 1024 and Path(original_dag).exists():
        original_source = Path(original_dag).read_text()

    converted_source = converted_flow
    if "\n" not in converted_flow and len(converted_flow) < 1024 and Path(converted_flow).exists():
        converted_source = Path(converted_flow).read_text()

    # Syntax check the generated code
    syntax_result = validate_python_syntax(converted_source)

    syntax_errors = None
    if not syntax_result.valid:
        syntax_errors = [
            {
                "line": syntax_result.line,
                "column": syntax_result.column,
                "message": syntax_result.error,
            }
        ]

    guidance = (
        "Compare the original Airflow DAG with the generated Prefect flow. Verify:\n"
        "1. All tasks from the DAG are represented in the flow\n"
        "2. Task dependencies are preserved (>> chains become function call order)\n"
        "3. XCom push/pull is replaced with task return values and parameters\n"
        "4. Connections are mapped to Prefect blocks\n"
        "5. Variables are mapped to Prefect variables or environment config\n"
        "6. Schedule, retries, and other DAG config is carried over\n"
        "7. Sensors are converted to polling tasks with retries or event triggers\n"
        "8. TaskGroups are converted to subflows\n"
        "9. Trigger rules are handled with state inspection"
    )

    # Append operator-specific guidance based on DAG content
    extras = []

    if "KubernetesPodOperator" in original_source:
        extras.append(
            "Kubernetes: verify a Kubernetes work pool is configured and that"
            " image, namespace, and env_vars map to the Prefect infrastructure block"
        )

    if any(
        x in original_source
        for x in ("DatabricksSubmitRunOperator", "DatabricksRunNowOperator")
    ):
        extras.append(
            "Databricks: verify prefect-databricks is installed,"
            " DatabricksCredentials block is configured, and job parameters are mapped"
        )

    if any(
        x in original_source
        for x in (
            "AzureDataFactoryRunPipelineOperator",
            "WasbOperator",
            "WasbDeleteOperator",
        )
    ):
        extras.append(
            "Azure: verify prefect-azure is installed and"
            " AzureBlobStorageCredentials or AzureDataFactoryCredentials block is configured"
        )

    if "DbtCloudRunJobOperator" in original_source:
        extras.append(
            "dbt Cloud: verify prefect-dbt is installed,"
            " DbtCloudCredentials block is set, and job ID and account ID are passed"
        )

    if any(x in original_source for x in ("SimpleHttpOperator", "HttpOperator")):
        extras.append(
            "HTTP: verify httpx is used (no prefect-http package exists),"
            " connection ID maps to base_url, and headers/auth are passed explicitly"
        )

    if "SSHOperator" in original_source:
        extras.append(
            "SSH: verify paramiko or fabric is used, SSH credentials are in a"
            " Prefect Secret block, and host/user/key are not hardcoded"
        )

    if extras:
        guidance += "\n" + "\n".join(extras)

    return json.dumps(
        {
            "original_source": original_source,
            "converted_source": converted_source,
            "syntax_valid": syntax_result.valid,
            "syntax_errors": syntax_errors,
            "comparison_guidance": guidance,
        },
        indent=2,
    )
