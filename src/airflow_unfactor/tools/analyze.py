"""Analyze Airflow DAGs - provide rich structured payloads for LLM-assisted conversion."""

import json
from pathlib import Path
from typing import Any

from airflow_unfactor.analysis.complexity import calculate_complexity
from airflow_unfactor.analysis.dependencies import extract_dependencies
from airflow_unfactor.analysis.parser import parse_dag
from airflow_unfactor.analysis.version import detect_airflow_version
from airflow_unfactor.converters.connections import extract_connections
from airflow_unfactor.converters.custom_operators import extract_custom_operators
from airflow_unfactor.converters.datasets import analyze_datasets
from airflow_unfactor.converters.dynamic_mapping import extract_dynamic_mapping
from airflow_unfactor.converters.jinja import analyze_jinja_in_code, has_jinja_patterns
from airflow_unfactor.converters.runbook import extract_dag_settings
from airflow_unfactor.converters.taskgroup import extract_task_groups
from airflow_unfactor.converters.trigger_rules import detect_trigger_rules
from airflow_unfactor.converters.variables import extract_variables
from airflow_unfactor.external_mcp import ExternalMCPClient


async def analyze_dag(
    path: str | None = None,
    content: str | None = None,
    include_external_context: bool = True,
) -> str:
    """Analyze an Airflow DAG and return a rich structured payload.

    This tool provides comprehensive analysis for LLM-assisted code generation.
    It extracts all relevant information from the DAG without generating any code.

    Args:
        path: Path to DAG file
        content: DAG code content
        include_external_context: Enrich with external MCP context

    Returns:
        JSON with comprehensive DAG analysis including:
        - Structure (operators, dependencies, task groups)
        - Patterns (XCom, sensors, branching, trigger rules)
        - Configuration (schedule, catchup, default_args)
        - Complexity assessment and migration notes
        - Original code for LLM reference
    """
    if content is None and path:
        content = Path(path).read_text()

    if content is None:
        return json.dumps({"error": "No DAG content provided"})

    external_context = {}

    try:
        # Core parsing
        analysis = parse_dag(content)
        dependencies = extract_dependencies(content)
        complexity_score = calculate_complexity(analysis)
        version = detect_airflow_version(content)

        # Enhanced pattern detection
        connections = extract_connections(content)
        variables = extract_variables(content)
        dag_settings = extract_dag_settings(content)
        dynamic_mappings = extract_dynamic_mapping(content)
        task_groups = extract_task_groups(content)
        trigger_rules = detect_trigger_rules(content)
        custom_ops = extract_custom_operators(content)
        has_jinja = has_jinja_patterns(content)
        jinja_analysis = analyze_jinja_in_code(content) if has_jinja else {}
        dataset_analysis = analyze_datasets(content)

        # Build comprehensive result
        result: dict[str, Any] = {
            # Basic info
            "dag_id": analysis.get("dag_id"),
            "source_file": path,

            # Airflow version detection
            "airflow_version": {
                "detected": version.version_string,
                "features": {
                    "taskflow": version.has_taskflow,
                    "datasets": version.has_datasets,
                    "assets": version.has_assets,
                },
                "confidence": version.confidence,
            },

            # DAG structure
            "structure": {
                "operators": _enrich_operators(analysis.get("operators", [])),
                "task_ids": analysis.get("task_ids", []),
                "dependencies": dependencies,
                "task_groups": [
                    {
                        "name": tg.name,
                        "function_name": tg.function_name,
                        "tasks": tg.tasks,
                        "has_expand": tg.has_expand,
                    }
                    for tg in task_groups
                ],
                "imports": analysis.get("imports", []),
            },

            # Detected patterns (what needs special handling)
            "patterns": {
                "xcom_usage": analysis.get("xcom_usage", []),
                "sensors": [
                    op for op in analysis.get("operators", [])
                    if "Sensor" in str(op.get("type", ""))
                ],
                "trigger_rules": [
                    {
                        "task_id": tr.task_id,
                        "rule": tr.rule,
                        "line": tr.line_number,
                    }
                    for tr in trigger_rules
                ],
                "dynamic_mapping": [
                    {
                        "task_name": dm.task_name,
                        "mapping_type": dm.mapping_type.value,
                        "mapped_iterable": dm.mapped_iterable,
                    }
                    for dm in dynamic_mappings
                ],
                "branching": [
                    op for op in analysis.get("operators", [])
                    if op.get("type") in ("BranchPythonOperator", "ShortCircuitOperator")
                ],
                "connections": [c.name for c in connections],
                "variables": [v.name for v in variables],
                "custom_operators": [
                    {
                        "class_name": co.class_name,
                        "task_id": co.task_id,
                        "base_classes": co.base_classes,
                        "import_path": co.import_path,
                    }
                    for co in custom_ops
                ],
                "jinja_templates": jinja_analysis if has_jinja else None,
                "datasets": {
                    "dataset_uris": [d.uri for d in dataset_analysis.datasets],
                    "producers": [p.task_name for p in dataset_analysis.producers],
                    "consumers": [c.dag_name for c in dataset_analysis.consumers],
                },
            },

            # DAG configuration (maps to prefect.yaml)
            "dag_config": {
                "schedule": dag_settings.schedule if dag_settings else None,
                "catchup": dag_settings.catchup if dag_settings else None,
                "max_active_runs": dag_settings.max_active_runs if dag_settings else None,
                "max_consecutive_failed_dag_runs": dag_settings.max_consecutive_failed_dag_runs if dag_settings else None,
                "tags": dag_settings.tags if dag_settings else [],
                "default_args": dag_settings.default_args if dag_settings else {},
                "callbacks": [cb.callback_type for cb in dag_settings.callbacks] if dag_settings else [],
            },

            # Complexity assessment
            "complexity": {
                "score": complexity_score,
                "factors": _get_complexity_factors(analysis, version, trigger_rules, dynamic_mappings),
            },

            # Migration guidance
            "migration_notes": _generate_migration_notes(
                analysis, version, connections, variables, trigger_rules,
                dynamic_mappings, custom_ops, has_jinja
            ),

            # Original code (for LLM reference)
            "original_code": content,
        }

        # External MCP enrichment (best-effort)
        if include_external_context:
            client = ExternalMCPClient.from_env()

            # Build search query based on detected features
            features = []
            if version.has_taskflow:
                features.append("TaskFlow")
            if version.has_datasets:
                features.append("Datasets")
            if any("Sensor" in str(op.get("type", "")) for op in analysis.get("operators", [])):
                features.append("Sensors")
            if trigger_rules:
                features.append("TriggerRules")
            if dynamic_mappings:
                features.append("DynamicMapping")

            search_query = f"Convert Airflow DAG to Prefect flow. Features: {', '.join(features) or 'standard'}"

            external_context["prefect"] = await client.call_prefect_search(search_query)
            external_context["astronomer"] = await client.call_astronomer_migration(
                "Airflow 2 to 3 migration: datasets to assets, operator changes"
            )

        if external_context:
            result["external_context"] = external_context

        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "external_context": external_context})


def _enrich_operators(operators: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Enrich operator info with conversion hints."""
    enriched = []
    for op in operators:
        op_type = str(op.get("type", ""))
        enriched_op = dict(op)

        # Add conversion hints
        if op_type == "PythonOperator":
            enriched_op["conversion_hint"] = "Convert to @task decorated function"
        elif op_type == "BashOperator":
            enriched_op["conversion_hint"] = "Use prefect_shell.ShellOperation or subprocess"
        elif op_type == "BranchPythonOperator":
            enriched_op["conversion_hint"] = "Use Python if/else with task references"
        elif op_type in ("DummyOperator", "EmptyOperator"):
            enriched_op["conversion_hint"] = "Not needed - Prefect uses task dependencies directly"
        elif "Sensor" in op_type:
            enriched_op["conversion_hint"] = "Use polling with retries or event triggers"
        elif op_type == "TriggerDagRunOperator":
            enriched_op["conversion_hint"] = "Use run_deployment or subflow"
        elif op_type == "TaskGroup":
            enriched_op["conversion_hint"] = "Convert to subflow"
        else:
            enriched_op["conversion_hint"] = "Check prefect integrations or implement as @task"

        enriched.append(enriched_op)

    return enriched


def _get_complexity_factors(
    analysis: dict[str, Any],
    version: Any,
    trigger_rules: list,
    dynamic_mappings: list,
) -> list[str]:
    """Generate list of complexity factors."""
    factors = []

    # Check for XCom usage
    if analysis.get("xcom_usage"):
        factors.append("Uses XCom for data passing (convert to return values)")

    # Check for sensors
    sensors = [
        op for op in analysis.get("operators", [])
        if "Sensor" in str(op.get("type", ""))
    ]
    if sensors:
        factors.append(f"Has {len(sensors)} sensor(s) (convert to polling/triggers)")

    # Check for branching
    branching = [
        op for op in analysis.get("operators", [])
        if op.get("type") in ("BranchPythonOperator", "ShortCircuitOperator")
    ]
    if branching:
        factors.append("Has branching logic (convert to Python if/else)")

    # Check for trigger rules
    non_default_rules = [tr for tr in trigger_rules if tr.rule != "all_success"]
    if non_default_rules:
        factors.append(f"Has {len(non_default_rules)} non-default trigger rule(s)")

    # Check for dynamic mapping
    if dynamic_mappings:
        factors.append(f"Has {len(dynamic_mappings)} dynamic mapping(s) (use Prefect .map())")

    # Check for datasets
    if version.has_datasets:
        factors.append("Uses Datasets (convert to Prefect events/automations)")

    return factors


def _generate_migration_notes(
    analysis: dict[str, Any],
    version: Any,
    connections: list,
    variables: list,
    trigger_rules: list,
    dynamic_mappings: list,
    custom_ops: list,
    has_jinja: bool,
) -> list[str]:
    """Generate actionable migration notes."""
    notes = []

    # XCom notes
    if analysis.get("xcom_usage"):
        notes.append(
            "XCom: Replace xcom_push/pull with function return values. "
            "Tasks automatically share data through return values in Prefect."
        )

    # Sensor notes
    sensors = [
        op for op in analysis.get("operators", [])
        if "Sensor" in str(op.get("type", ""))
    ]
    for sensor in sensors:
        sensor_type = sensor.get("type", "")
        if "S3" in sensor_type:
            notes.append(
                f"{sensor_type}: Consider S3 event notifications with Prefect automations, "
                "or use polling with @task(retries=N, retry_delay_seconds=M)"
            )
        elif "External" in sensor_type:
            notes.append(
                f"{sensor_type}: Use Prefect deployment triggers or automations "
                "for cross-flow dependencies"
            )
        else:
            notes.append(
                f"{sensor_type}: Implement as polling task with retries, "
                "or use event-driven triggers if available"
            )

    # Connection notes
    if connections:
        conn_names = [c.name for c in connections]
        notes.append(
            f"Connections ({', '.join(conn_names)}): Configure as Prefect blocks. "
            "Check prefect integrations for matching block types."
        )

    # Variable notes
    if variables:
        var_names = [v.name for v in variables]
        notes.append(
            f"Variables ({', '.join(var_names)}): Use Prefect Variables or environment variables. "
            "Secrets should use Secret blocks."
        )

    # Trigger rule notes
    non_default = [tr for tr in trigger_rules if tr.rule != "all_success"]
    for tr in non_default:
        if tr.rule == "all_done":
            notes.append(
                f"Task '{tr.task_id}' uses all_done: Use try/except or state handlers "
                "to run regardless of upstream success"
            )
        elif tr.rule == "one_success":
            notes.append(
                f"Task '{tr.task_id}' uses one_success: Use wait_for with return_when=FIRST_COMPLETED "
                "or conditional logic"
            )
        else:
            notes.append(
                f"Task '{tr.task_id}' uses {tr.rule}: Implement equivalent logic "
                "using state handlers or conditional execution"
            )

    # Dynamic mapping notes
    if dynamic_mappings:
        notes.append(
            "Dynamic mapping: Use .map() method on tasks. "
            "Example: task.map(items=my_list)"
        )

    # Custom operator notes
    if custom_ops:
        op_names = [co.class_name for co in custom_ops]
        notes.append(
            f"Custom operators ({', '.join(op_names)}): Implement logic in @task functions. "
            "Consider creating reusable task functions."
        )

    # Jinja notes
    if has_jinja:
        notes.append(
            "Jinja templates: Replace with Python f-strings or .format(). "
            "Prefect uses standard Python string formatting."
        )

    # Dataset notes
    if version.has_datasets:
        notes.append(
            "Datasets: Convert to Prefect events and automations. "
            "Use emit_event() for producers, deployment triggers for consumers."
        )

    return notes
