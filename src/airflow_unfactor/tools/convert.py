"""Convert Airflow DAGs to Prefect flows."""

import json
from pathlib import Path
from typing import Optional

from airflow_unfactor.analysis.parser import parse_dag
from airflow_unfactor.analysis.version import detect_airflow_version
from airflow_unfactor.converters.base import convert_dag_to_flow
from airflow_unfactor.converters.datasets import analyze_datasets, generate_event_code
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
        dataset_analysis = analyze_datasets(content)
        result["dataset_conversion"] = generate_event_code(
            dataset_analysis,
            include_comments=include_comments,
        )
        result["conversion_runbook_md"] = _build_conversion_runbook(
            dag_id=dag_info.get("dag_id", "unknown"),
            version=version.version_string,
            operators=dag_info.get("operators", []),
            warnings=result.get("warnings", []),
            dataset_conversion=result["dataset_conversion"],
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


def _build_conversion_runbook(
    dag_id: str,
    version: str,
    operators: list[dict[str, str | int | None]],
    warnings: list[str],
    dataset_conversion: dict[str, object],
) -> str:
    """Build an operational migration runbook for post-conversion steps."""
    operator_types = sorted({str(op.get("type", "Unknown")) for op in operators})
    operators_line = ", ".join(operator_types) if operator_types else "None detected"

    events = dataset_conversion.get("events", [])
    event_count = len(events) if isinstance(events, list) else 0
    assets = dataset_conversion.get("assets", [])
    asset_count = len(assets) if isinstance(assets, list) else 0
    has_deployment_triggers = bool(dataset_conversion.get("deployment_yaml"))

    lines = [
        f"# Conversion Runbook: `{dag_id}`",
        "",
        "## Summary",
        f"- Airflow version detected: `{version}`",
        f"- Operator types detected: {operators_line}",
        f"- Dataset/Asset events detected: {event_count}",
        f"- Airflow assets detected: {asset_count}",
        "",
        "## Server/API Configuration Checklist",
        "- Configure deployment schedules and pause state in Prefect server/cloud.",
        "- Configure retries, concurrency, and execution infrastructure at deployment/work pool level.",
        "- Configure credentials and connections as Prefect blocks, variables, or environment settings.",
        "- Configure event automations and triggers in Prefect for event-driven workflows.",
        "- Review notification, SLA, and alerting behavior that was previously Airflow-managed.",
        "",
        "## Generated Artifacts",
        "- `flow_code`: converted flow implementation scaffold",
        "- `test_code`: generated tests (if enabled)",
        "- `dataset_conversion.producer_code`: event emission helpers",
        "- `dataset_conversion.deployment_yaml`: trigger snippets for deployment config",
        "- `dataset_conversion.materialization_code`: asset materialization scaffold",
        "",
        "## Migration Notes",
    ]

    if has_deployment_triggers:
        lines.append(
            "- Event-based scheduling detected. Apply `deployment_yaml` trigger snippets in deployment config."
        )
    if asset_count:
        lines.append(
            "- Airflow Assets detected. Complete generated `@materialize(...)` functions with concrete asset logic."
        )
    if not has_deployment_triggers and not asset_count:
        lines.append("- No dataset/asset orchestration patterns detected.")

    if warnings:
        lines.append("")
        lines.append("## Manual Review Required")
        for warning in warnings:
            lines.append(f"- {warning}")

    lines.extend(
        [
            "",
            "## Next Steps",
            "1. Fill TODOs in generated flow/task/materialization code.",
            "2. Configure Prefect deployment, work pool, and infrastructure.",
            "3. Configure triggers/automations for event-driven dependencies.",
            "4. Run generated tests and validate behavior against Airflow runs.",
        ]
    )
    return "\n".join(lines)
