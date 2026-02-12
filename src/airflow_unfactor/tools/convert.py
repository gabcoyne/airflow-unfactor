"""Convert Airflow DAGs to Prefect flows."""

import json
from pathlib import Path
from typing import Optional

from airflow_unfactor.analysis.parser import parse_dag
from airflow_unfactor.analysis.version import detect_airflow_version
from airflow_unfactor.converters.base import convert_dag_to_flow
from airflow_unfactor.converters.test_generator import generate_flow_tests, generate_test_filename
from airflow_unfactor.external_mcp import ExternalMCPClient


async def convert_dag(
    path: Optional[str] = None,
    content: Optional[str] = None,
    include_comments: bool = True,
    generate_tests: bool = True,
    include_external_context: bool = True,
) -> str:
    """Convert an Airflow DAG to a Prefect flow.

    Args:
        path: Path to DAG file
        content: DAG code content
        include_comments: Include educational comments
        generate_tests: Generate pytest tests for the converted flow
        include_external_context: Enrich with external MCP context

    Returns:
        JSON with converted code, tests, and metadata
    """
    if content is None and path:
        content = Path(path).read_text()

    if content is None:
        return json.dumps({"error": "No DAG content provided"})

    external_context = {}

    try:
        dag_info = parse_dag(content)
        version = detect_airflow_version(content)

        result = convert_dag_to_flow(
            dag_info,
            original_code=content,
            include_comments=include_comments,
        )

        # Generate tests alongside the flow
        if generate_tests:
            dag_id = dag_info.get("dag_id", "converted_flow")
            flow_name = dag_id.replace("-", "_").replace(" ", "_")
            task_mapping = result.get("original_to_new_mapping", {})

            test_code = generate_flow_tests(
                dag_info=dag_info,
                flow_name=flow_name,
                task_mapping=task_mapping,
            )
            result["test_code"] = test_code
            result["test_filename"] = generate_test_filename(dag_id)

        # External MCP enrichment (best-effort)
        if include_external_context:
            client = ExternalMCPClient.from_env()
            external_context["prefect"] = await client.call_prefect_search(
                f"Convert Airflow DAG to Prefect flow. TaskFlow={version.has_taskflow}, Datasets={version.has_datasets}"
            )
            external_context["astronomer"] = await client.call_astronomer_migration(
                "Airflow 2 to 3 migration: datasets to assets, operator changes"
            )

        if external_context:
            result["external_context"] = external_context

        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "external_context": external_context})
