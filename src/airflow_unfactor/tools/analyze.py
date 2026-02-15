"""Analyze Airflow DAGs."""

import json
from pathlib import Path

from airflow_unfactor.analysis.complexity import calculate_complexity
from airflow_unfactor.analysis.dependencies import extract_dependencies
from airflow_unfactor.analysis.parser import parse_dag
from airflow_unfactor.analysis.version import detect_airflow_version
from airflow_unfactor.external_mcp import ExternalMCPClient


async def analyze_dag(
    path: str | None = None,
    content: str | None = None,
    include_external_context: bool = True,
) -> str:
    """Analyze an Airflow DAG.

    Args:
        path: Path to DAG file
        content: DAG code content
        include_external_context: Enrich with external MCP context

    Returns:
        JSON with DAG analysis
    """
    if content is None and path:
        content = Path(path).read_text()

    if content is None:
        return json.dumps({"error": "No DAG content provided"})

    external_context = {}

    try:
        analysis = parse_dag(content)
        dependencies = extract_dependencies(content)
        complexity_score = calculate_complexity(analysis)
        version = detect_airflow_version(content)

        result = {
            "dag_id": analysis.get("dag_id"),
            "operators": analysis.get("operators", []),
            "task_ids": analysis.get("task_ids", []),
            "dependencies": dependencies,
            "xcom_usage": analysis.get("xcom_usage", []),
            "notes": analysis.get("notes", []),
            "imports": analysis.get("imports", []),
            "complexity_score": complexity_score,
            "airflow_version": {
                "version": version.version_string,
                "features": {
                    "taskflow": version.has_taskflow,
                    "datasets": version.has_datasets,
                    "assets": version.has_assets,
                },
                "confidence": version.confidence,
            },
        }

        if include_external_context:
            client = ExternalMCPClient.from_env()
            external_context["prefect"] = await client.call_prefect_search(
                f"Analyze Airflow DAG. Operators: {len(analysis.get('operators', []))}"
            )
            external_context["astronomer"] = await client.call_astronomer_migration(
                "Airflow 2 to 3 migration: operator changes, datasets->assets"
            )

        if external_context:
            result["external_context"] = external_context

        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "external_context": external_context})
