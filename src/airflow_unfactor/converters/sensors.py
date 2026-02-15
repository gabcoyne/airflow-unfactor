"""Convert Airflow Sensors to Prefect polling tasks and triggers.

See specs/sensor-trigger-converter.openspec.md for specification.
"""

import ast
from dataclasses import dataclass, field
from typing import Any

# Known sensor types and their conversion strategies
SENSOR_STRATEGIES = {
    "ExternalTaskSensor": {
        "approach": "event",
        "description": "Use Prefect events or flow.wait_for() for flow dependencies",
        "event_type": "prefect.flow-run.completed",
    },
    "S3KeySensor": {
        "approach": "event_or_poll",
        "description": "Use S3 event notifications (SNS/SQS) or polling task",
        "event_type": "s3.object.created",
        "polling_import": "boto3",
    },
    "GCSObjectSensor": {
        "approach": "event_or_poll",
        "description": "Use GCS Pub/Sub notifications or polling task",
        "event_type": "gcs.object.finalize",
        "polling_import": "google.cloud.storage",
    },
    "HttpSensor": {
        "approach": "poll",
        "description": "Use webhook trigger or polling task",
        "polling_import": "httpx",
    },
    "FileSensor": {
        "approach": "poll",
        "description": "Use filesystem watch (watchdog) or polling task",
        "polling_import": "pathlib",
    },
    "SqlSensor": {
        "approach": "poll",
        "description": "Convert to polling task with database query",
    },
    "PythonSensor": {
        "approach": "direct",
        "description": "Convert poke function to @task with retry logic",
    },
    "TimeDeltaSensor": {
        "approach": "schedule",
        "description": "Use Prefect scheduling instead of waiting",
    },
    "DateTimeSensor": {
        "approach": "schedule",
        "description": "Use Prefect scheduling instead of waiting",
    },
}


@dataclass
class SensorInfo:
    """Information about a detected sensor."""

    sensor_type: str
    task_id: str
    parameters: dict[str, Any] = field(default_factory=dict)
    line_number: int = 0
    poke_interval: int = 60  # Default
    timeout: int = 3600  # Default
    mode: str = "poke"  # poke or reschedule


@dataclass
class SensorConversion:
    """Conversion result for a sensor."""

    sensor: SensorInfo
    polling_code: str
    event_suggestion: str
    warnings: list[str] = field(default_factory=list)


class SensorVisitor(ast.NodeVisitor):
    """AST visitor to extract sensor patterns."""

    def __init__(self):
        self.sensors: list[SensorInfo] = []

    def visit_Call(self, node: ast.Call):
        func_name = self._get_func_name(node)

        if func_name and "Sensor" in func_name:
            sensor = self._extract_sensor_info(node, func_name)
            if sensor:
                self.sensors.append(sensor)

        self.generic_visit(node)

    def _get_func_name(self, node: ast.Call) -> str:
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    def _extract_sensor_info(self, node: ast.Call, sensor_type: str) -> SensorInfo | None:
        params = {}
        task_id = "unknown_sensor"
        poke_interval = 60
        timeout = 3600
        mode = "poke"

        for kw in node.keywords:
            if kw.arg == "task_id" and isinstance(kw.value, ast.Constant):
                task_id = str(kw.value.value)
            elif kw.arg == "poke_interval" and isinstance(kw.value, ast.Constant):
                poke_interval = int(kw.value.value)  # type: ignore[arg-type]
            elif kw.arg == "timeout" and isinstance(kw.value, ast.Constant):
                timeout = int(kw.value.value)  # type: ignore[arg-type]
            elif kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                mode = str(kw.value.value)
            elif kw.arg:
                try:
                    params[kw.arg] = ast.literal_eval(kw.value)
                except (ValueError, TypeError):
                    params[kw.arg] = ast.unparse(kw.value)

        return SensorInfo(
            sensor_type=sensor_type,
            task_id=task_id,
            parameters=params,
            line_number=node.lineno,
            poke_interval=poke_interval,
            timeout=timeout,
            mode=mode,
        )


def detect_sensors(dag_code: str) -> list[SensorInfo]:
    """Detect sensors in DAG code.

    Args:
        dag_code: Source code of the DAG file

    Returns:
        List of detected sensors
    """
    try:
        tree = ast.parse(dag_code)
    except SyntaxError:
        return []

    visitor = SensorVisitor()
    visitor.visit(tree)
    return visitor.sensors


def convert_sensor(sensor: SensorInfo, include_comments: bool = True) -> SensorConversion:
    """Convert a single sensor to Prefect patterns.

    Args:
        sensor: Sensor information
        include_comments: Include educational comments

    Returns:
        SensorConversion with polling code and event suggestions
    """
    strategy = SENSOR_STRATEGIES.get(
        sensor.sensor_type,
        {
            "approach": "poll",
            "description": "Generic sensor - convert to polling task",
        },
    )

    warnings = []

    # Calculate retry count from timeout and poke_interval
    retries = max(1, sensor.timeout // sensor.poke_interval)

    # Generate polling code
    polling_lines = []

    if include_comments:
        polling_lines.append(f"# Converted from {sensor.sensor_type}")
        polling_lines.append(f"# {strategy['description']}")
        polling_lines.append("")

    # Sensor-specific conversions
    if sensor.sensor_type == "S3KeySensor":
        polling_lines.extend(_generate_s3_sensor(sensor, retries))
    elif sensor.sensor_type == "HttpSensor":
        polling_lines.extend(_generate_http_sensor(sensor, retries))
    elif sensor.sensor_type == "FileSensor":
        polling_lines.extend(_generate_file_sensor(sensor, retries))
    elif sensor.sensor_type == "SqlSensor":
        polling_lines.extend(_generate_sql_sensor(sensor, retries))
    elif sensor.sensor_type == "PythonSensor":
        polling_lines.extend(_generate_python_sensor(sensor, retries))
    elif sensor.sensor_type == "ExternalTaskSensor":
        polling_lines.extend(_generate_external_task_sensor(sensor))
        warnings.append("ExternalTaskSensor: Consider using Prefect events for flow dependencies")
    else:
        polling_lines.extend(_generate_generic_sensor(sensor, retries))
        warnings.append(f"Unknown sensor type: {sensor.sensor_type}")

    # Generate event suggestion
    event_suggestion = _generate_event_suggestion(sensor, strategy)

    if sensor.mode == "reschedule":
        warnings.append(
            "Sensor used 'reschedule' mode. In Prefect, use retries with "
            "retry_delay_seconds for similar behavior without blocking workers."
        )

    return SensorConversion(
        sensor=sensor,
        polling_code="\n".join(polling_lines),
        event_suggestion=event_suggestion,
        warnings=warnings,
    )


def _generate_s3_sensor(sensor: SensorInfo, retries: int) -> list[str]:
    bucket = sensor.parameters.get("bucket_name", sensor.parameters.get("bucket_key", "BUCKET"))
    key = sensor.parameters.get("bucket_key", "KEY")

    return [
        "import boto3",
        "from prefect import task",
        "",
        f"@task(retries={retries}, retry_delay_seconds={sensor.poke_interval})",
        f"def {sensor.task_id}():",
        '    """Wait for S3 object to exist."""',
        "    s3 = boto3.client('s3')",
        "    try:",
        f"        s3.head_object(Bucket='{bucket}', Key='{key}')",
        "        return True",
        "    except s3.exceptions.ClientError as e:",
        "        if e.response['Error']['Code'] == '404':",
        f"            raise Exception('S3 key not found: {key}')",
        "        raise",
    ]


def _generate_http_sensor(sensor: SensorInfo, retries: int) -> list[str]:
    endpoint = sensor.parameters.get("endpoint", "/health")
    http_conn_id = sensor.parameters.get("http_conn_id", "http_default")

    return [
        "import httpx",
        "from prefect import task",
        "",
        f"@task(retries={retries}, retry_delay_seconds={sensor.poke_interval})",
        f"def {sensor.task_id}():",
        '    """Wait for HTTP endpoint to return success."""',
        f"    # Configure base URL from connection: {http_conn_id}",
        f"    response = httpx.get('http://your-host{endpoint}')",
        "    if response.status_code != 200:",
        "        raise Exception(f'HTTP check failed: {response.status_code}')",
        "    return True",
    ]


def _generate_file_sensor(sensor: SensorInfo, retries: int) -> list[str]:
    filepath = sensor.parameters.get("filepath", "/path/to/file")

    return [
        "from pathlib import Path",
        "from prefect import task",
        "",
        f"@task(retries={retries}, retry_delay_seconds={sensor.poke_interval})",
        f"def {sensor.task_id}():",
        '    """Wait for file to exist."""',
        f"    path = Path('{filepath}')",
        "    if not path.exists():",
        "        raise Exception(f'File not found: {path}')",
        "    return True",
    ]


def _generate_sql_sensor(sensor: SensorInfo, retries: int) -> list[str]:
    sql = sensor.parameters.get("sql", "SELECT 1")
    conn_id = sensor.parameters.get("conn_id", "default")

    return [
        "from prefect import task",
        "# from prefect_sqlalchemy import SqlAlchemyConnector  # Optional integration",
        "",
        f"@task(retries={retries}, retry_delay_seconds={sensor.poke_interval})",
        f"def {sensor.task_id}():",
        '    """Wait for SQL query to return truthy result."""',
        f"    # Connection: {conn_id}",
        f'    sql = """{sql}"""',
        "    # Execute query and check result",
        "    # result = connector.fetch_one(sql)",
        "    # if not result or not result[0]:",
        "    #     raise Exception('SQL condition not met')",
        "    # return True",
        "    raise NotImplementedError('Configure database connection')",
    ]


def _generate_python_sensor(sensor: SensorInfo, retries: int) -> list[str]:
    python_callable = sensor.parameters.get("python_callable", "check_condition")

    return [
        "from prefect import task",
        "",
        f"@task(retries={retries}, retry_delay_seconds={sensor.poke_interval})",
        f"def {sensor.task_id}():",
        '    """Converted from PythonSensor."""',
        f"    # Original callable: {python_callable}",
        "    result = check_condition()  # Replace with actual logic",
        "    if not result:",
        "        raise Exception('Condition not met')",
        "    return result",
    ]


def _generate_external_task_sensor(sensor: SensorInfo) -> list[str]:
    external_dag = sensor.parameters.get("external_dag_id", "upstream_dag")
    external_task = sensor.parameters.get("external_task_id", None)

    return [
        "from prefect import flow, task",
        "from prefect.events import emit_event",
        "",
        "# Option 1: Use Prefect events for flow dependencies",
        f"# The upstream flow '{external_dag}' should emit an event on completion:",
        "# emit_event(event='flow.completed', resource={'flow': '" + external_dag + "'})",
        "",
        "# Option 2: Use flow.wait_for() if running in same deployment",
        "# upstream_state = upstream_flow.wait_for()",
        "",
        f"# Original: Wait for {external_dag}" + (f".{external_task}" if external_task else ""),
        f"def {sensor.task_id}():",
        '    """Dependency on external flow."""',
        "    # Configure via Prefect automation triggers",
        "    pass",
    ]


def _generate_generic_sensor(sensor: SensorInfo, retries: int) -> list[str]:
    return [
        "from prefect import task",
        "",
        f"@task(retries={retries}, retry_delay_seconds={sensor.poke_interval})",
        f"def {sensor.task_id}():",
        f'    """Converted from {sensor.sensor_type}."""',
        "    # TODO: Implement poke logic",
        "    condition_met = False  # Replace with actual check",
        "    if not condition_met:",
        "        raise Exception('Condition not met')",
        "    return True",
    ]


def _generate_event_suggestion(sensor: SensorInfo, strategy: dict) -> str:
    """Generate event-driven alternative suggestion."""
    if strategy.get("approach") not in ("event", "event_or_poll"):
        return ""

    event_type = strategy.get("event_type", "custom.event")

    return f"""# ✨ Recommended: Event-driven approach
# Instead of polling, configure your deployment with a trigger:
#
# prefect.yaml:
# deployments:
#   - name: {sensor.task_id}_flow
#     triggers:
#       - match:
#           prefect.resource.id: "your-resource"
#         expect:
#           - "{event_type}"
#
# This eliminates polling and reacts instantly to events.
"""


def convert_all_sensors(
    dag_code: str,
    include_comments: bool = True,
) -> dict[str, Any]:
    """Convert all sensors in a DAG file.

    Args:
        dag_code: Source code of the DAG file
        include_comments: Include educational comments

    Returns:
        Dictionary with conversions, summary, warnings
    """
    sensors = detect_sensors(dag_code)

    if not sensors:
        return {
            "conversions": [],
            "summary": "No sensors detected",
            "warnings": [],
            "polling_code": "",
        }

    conversions = [convert_sensor(s, include_comments) for s in sensors]
    all_warnings = []
    all_code = []

    for conv in conversions:
        all_warnings.extend(conv.warnings)
        all_code.append(conv.polling_code)
        if conv.event_suggestion:
            all_code.append(conv.event_suggestion)

    return {
        "conversions": conversions,
        "summary": f"Converted {len(sensors)} sensor(s): {', '.join(s.sensor_type for s in sensors)}",
        "warnings": all_warnings,
        "polling_code": "\n\n".join(all_code),
    }
