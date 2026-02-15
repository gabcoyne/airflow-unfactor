"""Convert Airflow DAGs to Prefect flows."""

import json
import time
from pathlib import Path

from airflow_unfactor.analysis.parser import parse_dag
from airflow_unfactor.analysis.version import detect_airflow_version
from airflow_unfactor.converters.base import convert_dag_to_flow
from airflow_unfactor.converters.connections import convert_all_connections, extract_connections
from airflow_unfactor.converters.custom_operators import (
    convert_custom_operators,
    extract_custom_operators,
)
from airflow_unfactor.converters.datasets import analyze_datasets, generate_event_code
from airflow_unfactor.converters.dynamic_mapping import (
    convert_all_dynamic_mappings,
    extract_dynamic_mapping,
)
from airflow_unfactor.converters.jinja import analyze_jinja_in_code, has_jinja_patterns
from airflow_unfactor.converters.runbook import extract_dag_settings, generate_runbook
from airflow_unfactor.converters.taskgroup import convert_all_task_groups, extract_task_groups
from airflow_unfactor.converters.test_generator import generate_flow_tests, generate_test_filename
from airflow_unfactor.converters.trigger_rules import convert_trigger_rules, detect_trigger_rules
from airflow_unfactor.converters.variables import convert_all_variables, extract_variables
from airflow_unfactor.external_mcp import ExternalMCPClient
from airflow_unfactor.metrics import metrics_enabled, record_conversion
from airflow_unfactor.validation import validate_generated_code


async def convert_dag(
    path: str | None = None,
    content: str | None = None,
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
    start_time = time.time() if metrics_enabled() else None

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

        # Extract enhanced features
        connections = extract_connections(content)
        variables = extract_variables(content)
        dag_settings = extract_dag_settings(content)
        dynamic_mappings = extract_dynamic_mapping(content)
        task_groups = extract_task_groups(content)
        trigger_rules = detect_trigger_rules(content)
        custom_ops = extract_custom_operators(content)
        has_jinja = has_jinja_patterns(content)

        # Add feature detection to result
        result["features"] = {
            "has_taskflow": version.has_taskflow,
            "has_datasets": version.has_datasets,
            "has_sensors": any("Sensor" in str(op.get("type", "")) for op in dag_info.get("operators", [])),
            "has_dynamic_mapping": len(dynamic_mappings) > 0,
            "has_task_groups": len(task_groups) > 0,
            "has_trigger_rules": len(trigger_rules) > 0,
            "has_jinja_templates": has_jinja,
            "has_connections": len(connections) > 0,
            "has_variables": len(variables) > 0,
            "has_custom_operators": len(custom_ops) > 0,
        }

        # Generate enhanced scaffolds
        if connections:
            conn_result = convert_all_connections(content)
            result["block_scaffolds"] = conn_result.get("scaffolds", {})
            result.setdefault("warnings", []).extend(conn_result.get("warnings", []))

        if variables:
            var_result = convert_all_variables(content, include_comments=include_comments)
            result["variable_scaffolds"] = {
                v.name: var_result["scaffolds"].get(v.name, ("", "", []))[0]
                for v in variables
            }
            result.setdefault("warnings", []).extend(var_result.get("all_warnings", []))

        if dynamic_mappings:
            dm_result = convert_all_dynamic_mappings(content)
            result["dynamic_mapping_code"] = dm_result.get("prefect_code", "")
            result.setdefault("warnings", []).extend(dm_result.get("warnings", []))

        if task_groups:
            tg_result = convert_all_task_groups(content, include_comments=include_comments)
            result["task_group_code"] = tg_result.get("prefect_code", "")
            result.setdefault("warnings", []).extend(tg_result.get("warnings", []))

        if trigger_rules:
            tr_result = convert_trigger_rules(content, include_comments=include_comments)
            result["trigger_rule_code"] = tr_result.get("code_snippets", {})
            result.setdefault("warnings", []).extend(tr_result.get("warnings", []))

        if custom_ops:
            co_result = convert_custom_operators(content, include_comments=include_comments)
            result["custom_operator_stubs"] = co_result.get("stubs", {})
            result.setdefault("warnings", []).extend(co_result.get("warnings", []))

        if has_jinja:
            jinja_result = analyze_jinja_in_code(content)
            result["jinja_analysis"] = jinja_result
            result.setdefault("warnings", []).extend(
                [f"Jinja2 template detected: {note}" for note in jinja_result.get("conversion_notes", [])]
            )

        # Generate enhanced runbook using new module
        result["conversion_runbook_md"] = generate_runbook(
            settings=dag_settings,
            connections=connections,
            variables=variables,
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

        # Validate generated code compiles
        validation_warnings = validate_generated_code(
            flow_code=result.get("flow_code"),
            test_code=result.get("test_code"),
        )
        if validation_warnings:
            result.setdefault("warnings", []).extend(validation_warnings)

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

        # Record metrics if enabled
        if metrics_enabled():
            operators = dag_info.get("operators", [])
            total_ops = len(operators)
            # Count converted operators (those with supported types)
            from airflow_unfactor.converters.provider_mappings import get_operator_mapping
            converted_ops = sum(1 for op in operators if get_operator_mapping(str(op.get("type", ""))) is not None)
            unknown_ops = total_ops - converted_ops

            # Collect detected features
            features = [k for k, v in result.get("features", {}).items() if v]

            execution_time_ms = (time.time() - start_time) * 1000 if start_time else None

            record_conversion(
                dag_id=dag_info.get("dag_id", "unknown"),
                success=True,
                operators_total=total_ops,
                operators_converted=converted_ops,
                operators_unknown=unknown_ops,
                warnings=result.get("warnings", []),
                features_detected=features,
                execution_time_ms=execution_time_ms,
            )

        return json.dumps(result, indent=2)
    except Exception as e:
        # Record failed conversion metrics
        if metrics_enabled() and start_time:
            execution_time_ms = (time.time() - start_time) * 1000
            record_conversion(
                dag_id="unknown",
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time_ms,
            )
        return json.dumps({"error": str(e), "external_context": external_context})


def _build_conversion_runbook(
    dag_id: str,
    version: str,
    operators: list[dict[str, str | int | None]],
    warnings: list[str],
    dataset_conversion: dict[str, object],
    dag_settings: dict[str, object] | None = None,
) -> str:
    """Build an operational migration runbook for post-conversion steps."""
    dag_settings = dag_settings or {}
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
    ]

    # Add DAG Configuration section if settings are present
    if dag_settings:
        lines.append("## DAG Configuration")
        lines.append("")

        # Schedule information
        schedule = dag_settings.get("schedule") or dag_settings.get("schedule_interval")
        if schedule:
            lines.append(f"**Schedule**: `{schedule}`")
            lines.append("  - Configure via deployment schedule or `flow.serve(cron=...)`")
            lines.append("")

        # Catchup setting
        if "catchup" in dag_settings:
            catchup = dag_settings["catchup"]
            lines.append(f"**Catchup**: `{catchup}`")
            if not catchup:
                lines.append("  - Catchup disabled - Prefect deployments skip past schedule times by default")
            lines.append("")

        # Concurrency settings
        if "max_active_runs" in dag_settings:
            max_runs = dag_settings["max_active_runs"]
            lines.append(f"**Max Active Runs**: `{max_runs}`")
            lines.append("  - Configure concurrency limit in deployment settings")
            lines.append("")

        # Auto-pause settings
        if "max_consecutive_failed_dag_runs" in dag_settings:
            max_failed = dag_settings["max_consecutive_failed_dag_runs"]
            lines.append(f"**Auto-pause**: `max_consecutive_failed_dag_runs={max_failed}`")
            lines.append(f"  - Airflow 2.9+ auto-pauses DAG after {max_failed} consecutive failures")
            lines.append("  - In Prefect: Create automation to pause deployment after consecutive failures")
            lines.append("")

        # Retry configuration
        default_args = dag_settings.get("default_args", {})
        if isinstance(default_args, dict) and ("retries" in default_args or "retry_delay" in default_args):
            lines.append("**Retry Configuration**:")
            if "retries" in default_args:
                lines.append(f"  - Retries: `{default_args['retries']}`")
            if "retry_delay" in default_args:
                lines.append(f"  - Retry delay: `{default_args['retry_delay']}`")
            lines.append("  - Configure via `@flow(retries=...)` and `@task(retries=...)` decorators")
            lines.append("")

        # Tags
        tags = dag_settings.get("tags", [])
        if tags:
            tags_str = ", ".join([f"`{tag}`" for tag in tags])
            lines.append(f"**Tags**: {tags_str}")
            lines.append("  - Add tags via `@flow(tags=[...])` decorator")
            lines.append("")

        # Callbacks
        callbacks = dag_settings.get("callbacks", [])
        if callbacks:
            lines.append("**Callbacks Detected**:")
            for callback in callbacks:
                lines.append(f"  - `{callback}`: Use Prefect state handlers or notification blocks")
            lines.append("")

    lines.extend([
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
    ])

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
