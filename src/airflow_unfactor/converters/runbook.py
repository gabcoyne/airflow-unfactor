"""Generate migration runbooks from DAG settings extraction.

This module provides comprehensive extraction of DAG-level settings from both
DAG() constructor calls and @dag decorator patterns, then generates actionable
markdown runbooks with Prefect equivalents for each setting.
"""

import ast
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CallbackInfo:
    """Information about a detected callback function."""

    callback_type: str  # on_failure_callback, on_success_callback, etc.
    function_name: str  # Name or representation of the callback function
    line_number: int = 0


@dataclass
class DAGSettings:
    """Extracted DAG-level configuration settings."""

    dag_id: str = ""
    schedule: str | None = None  # schedule_interval or schedule
    catchup: bool | None = None
    default_args: dict[str, Any] = field(default_factory=dict)
    max_active_runs: int | None = None
    max_consecutive_failed_dag_runs: int | None = None
    tags: list[str] = field(default_factory=list)
    callbacks: list[CallbackInfo] = field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    doc_md: str | None = None
    is_paused_upon_creation: bool | None = None
    concurrency: int | None = None
    dagrun_timeout: str | None = None
    sla_miss_callback: str | None = None
    # Source information
    source_type: str = "unknown"  # "DAG()" or "@dag"
    line_number: int = 0


# Mapping of Airflow schedule presets to human-readable descriptions
SCHEDULE_PRESETS: dict[str, str] = {
    "@once": "Run once",
    "@hourly": "Every hour (0 * * * *)",
    "@daily": "Every day at midnight (0 0 * * *)",
    "@weekly": "Every Sunday at midnight (0 0 * * 0)",
    "@monthly": "First day of month at midnight (0 0 1 * *)",
    "@yearly": "First day of year at midnight (0 0 1 1 *)",
    "@annually": "First day of year at midnight (0 0 1 1 *)",
}


class DAGSettingsVisitor(ast.NodeVisitor):
    """AST visitor to extract DAG settings from both DAG() and @dag patterns."""

    def __init__(self, source_lines: list[str]):
        self.source_lines = source_lines
        self.settings: DAGSettings | None = None
        self._current_function_name: str | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions to check for @dag decorator."""
        self._current_function_name = node.name

        for decorator in node.decorator_list:
            if self._is_dag_decorator(decorator):
                self.settings = self._extract_from_decorator(node, decorator)
                return

        self.generic_visit(node)
        self._current_function_name = None

    def visit_With(self, node: ast.With) -> None:
        """Visit with statements to check for DAG context manager."""
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                func_name = self._get_call_name(item.context_expr)
                if func_name == "DAG":
                    self.settings = self._extract_from_call(item.context_expr)
                    return

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Visit calls to detect DAG() instantiation outside context manager."""
        func_name = self._get_call_name(node)
        if func_name == "DAG" and self.settings is None:
            self.settings = self._extract_from_call(node)
            return

        self.generic_visit(node)

    def _is_dag_decorator(self, decorator: ast.expr) -> bool:
        """Check if a decorator is @dag or @dag(...)."""
        if isinstance(decorator, ast.Name):
            return decorator.id == "dag"
        elif isinstance(decorator, ast.Call):
            return self._get_call_name(decorator) == "dag"
        return False

    def _get_call_name(self, node: ast.Call) -> str:
        """Get the name of a function call."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    def _extract_from_decorator(
        self, func_node: ast.FunctionDef, decorator: ast.expr
    ) -> DAGSettings:
        """Extract settings from @dag decorator."""
        settings = DAGSettings(
            source_type="@dag",
            line_number=decorator.lineno,
        )

        # Default dag_id to function name
        settings.dag_id = func_node.name

        # Extract parameters if decorator has arguments
        if isinstance(decorator, ast.Call):
            self._extract_keywords(decorator, settings)

        return settings

    def _extract_from_call(self, node: ast.Call) -> DAGSettings:
        """Extract settings from DAG() constructor call."""
        settings = DAGSettings(
            source_type="DAG()",
            line_number=node.lineno,
        )

        # First positional arg is often dag_id
        if node.args and isinstance(node.args[0], ast.Constant):
            settings.dag_id = str(node.args[0].value)

        self._extract_keywords(node, settings)

        return settings

    def _extract_keywords(self, node: ast.Call, settings: DAGSettings) -> None:
        """Extract keyword arguments into settings."""
        for keyword in node.keywords:
            arg_name = keyword.arg
            if not arg_name:
                continue

            value = self._extract_value(keyword.value)

            if arg_name == "dag_id" and value:
                settings.dag_id = str(value)

            elif arg_name in ("schedule", "schedule_interval"):
                settings.schedule = str(value) if value is not None else None

            elif arg_name == "catchup":
                settings.catchup = bool(value) if value is not None else None

            elif arg_name == "max_active_runs":
                settings.max_active_runs = int(value) if value is not None else None

            elif arg_name == "max_consecutive_failed_dag_runs":
                settings.max_consecutive_failed_dag_runs = (
                    int(value) if value is not None else None
                )

            elif arg_name == "tags":
                if isinstance(value, list):
                    settings.tags = [str(t) for t in value]

            elif arg_name == "default_args":
                if isinstance(value, dict):
                    settings.default_args = value
                elif isinstance(value, str) and value.startswith("<variable:"):
                    settings.default_args = {"_variable_ref": value}

            elif arg_name == "start_date":
                settings.start_date = str(value) if value else None

            elif arg_name == "end_date":
                settings.end_date = str(value) if value else None

            elif arg_name == "description":
                settings.description = str(value) if value else None

            elif arg_name == "doc_md":
                settings.doc_md = str(value) if value else None

            elif arg_name == "is_paused_upon_creation":
                settings.is_paused_upon_creation = (
                    bool(value) if value is not None else None
                )

            elif arg_name == "concurrency":
                settings.concurrency = int(value) if value is not None else None

            elif arg_name == "dagrun_timeout":
                settings.dagrun_timeout = str(value) if value else None

            elif arg_name in (
                "on_failure_callback",
                "on_success_callback",
                "on_retry_callback",
                "sla_miss_callback",
            ):
                func_name = self._extract_callback_name(keyword.value)
                settings.callbacks.append(
                    CallbackInfo(
                        callback_type=arg_name,
                        function_name=func_name,
                        line_number=keyword.value.lineno,
                    )
                )

    def _extract_value(self, node: ast.AST) -> Any:
        """Extract a Python value from an AST node."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.List):
            return [self._extract_value(elt) for elt in node.elts]
        elif isinstance(node, ast.Dict):
            result = {}
            for key, val in zip(node.keys, node.values):
                if key and isinstance(key, ast.Constant):
                    result[key.value] = self._extract_value(val)
            return result
        elif isinstance(node, ast.Name):
            if node.id in ("True", "False", "None"):
                return {"True": True, "False": False, "None": None}[node.id]
            return f"<variable: {node.id}>"
        elif isinstance(node, ast.Attribute):
            return self._format_attribute(node)
        elif isinstance(node, ast.Call):
            return self._format_call(node)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            inner = self._extract_value(node.operand)
            if isinstance(inner, (int, float)):
                return -inner
        return None

    def _format_attribute(self, node: ast.Attribute) -> str:
        """Format an attribute access like datetime.timedelta."""
        parts = []
        current: ast.expr = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))

    def _format_call(self, node: ast.Call) -> str:
        """Format a function call as a string representation."""
        func_name = self._get_call_name(node)
        if isinstance(node.func, ast.Attribute):
            func_name = self._format_attribute(node.func)
        return f"<call: {func_name}(...)>"

    def _extract_callback_name(self, node: ast.AST) -> str:
        """Extract the name of a callback function."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._format_attribute(node)
        elif isinstance(node, ast.Lambda):
            return "<lambda>"
        elif isinstance(node, ast.Call):
            # Handle partial() or other wrapper calls
            return f"<wrapped: {self._get_call_name(node)}(...)>"
        return "<unknown>"


def extract_dag_settings(dag_code: str) -> DAGSettings:
    """Extract DAG settings from source code.

    Handles both DAG() constructor and @dag decorator patterns.

    Args:
        dag_code: Source code of the DAG file

    Returns:
        DAGSettings with all extracted configuration
    """
    try:
        tree = ast.parse(dag_code)
    except SyntaxError:
        return DAGSettings()

    source_lines = dag_code.splitlines()
    visitor = DAGSettingsVisitor(source_lines)
    visitor.visit(tree)

    return visitor.settings or DAGSettings()


def generate_runbook(
    settings: DAGSettings,
    connections: list[Any] | None = None,
    variables: list[Any] | None = None,
) -> str:
    """Generate an actionable migration runbook markdown document.

    Args:
        settings: Extracted DAG settings
        connections: List of detected connection usages (ConnectionInfo objects)
        variables: List of detected variable usages (VariableInfo objects)

    Returns:
        Markdown formatted runbook
    """
    connections = connections or []
    variables = variables or []

    lines = [
        f"# Migration Runbook: `{settings.dag_id or 'Unknown DAG'}`",
        "",
        "This runbook provides actionable guidance for migrating your Airflow DAG to Prefect.",
        "",
    ]

    # Summary section
    lines.extend(_generate_summary_section(settings))

    # Work pool recommendation (P3 enhancement 6.1)
    lines.extend(_generate_work_pool_section(settings))

    # Schedule configuration
    if settings.schedule is not None:
        lines.extend(_generate_schedule_section(settings))

    # Deployment configuration (P3 enhancement 6.3)
    lines.extend(_generate_deployment_config_section(settings, variables))

    # Catchup configuration
    if settings.catchup is not None:
        lines.extend(_generate_catchup_section(settings))

    # Retry configuration
    if settings.default_args:
        lines.extend(_generate_retry_section(settings))

    # Concurrency configuration
    if settings.max_active_runs is not None or settings.concurrency is not None:
        lines.extend(_generate_concurrency_section(settings))

    # Auto-pause configuration
    if settings.max_consecutive_failed_dag_runs is not None:
        lines.extend(_generate_autopause_section(settings))

    # Tags configuration
    if settings.tags:
        lines.extend(_generate_tags_section(settings))

    # Callbacks/Automation configuration (P3 enhancement 6.2)
    if settings.callbacks:
        lines.extend(_generate_callbacks_section(settings))
        lines.extend(_generate_automation_section(settings))

    # Timeout configuration
    if settings.dagrun_timeout:
        lines.extend(_generate_timeout_section(settings))

    # Connections section with Block CLI commands (P3 enhancement 6.4)
    if connections:
        lines.extend(_generate_connections_section(connections))
        lines.extend(_generate_block_setup_section(connections))

    # Variables section
    if variables:
        lines.extend(_generate_variables_section(variables))

    # Testing guidance (P3 enhancement 6.5)
    lines.extend(_generate_testing_section(settings))

    # Action checklist
    lines.extend(_generate_action_checklist(settings, connections, variables))

    return "\n".join(lines)


def _generate_work_pool_section(settings: DAGSettings) -> list[str]:
    """Generate work pool recommendation section (P3 6.1)."""
    dag_id = settings.dag_id or "my-flow"
    lines = [
        "## Work Pool Configuration",
        "",
        "Choose a work pool type based on your execution requirements:",
        "",
        "### Option 1: Process Work Pool (Recommended for simple flows)",
        "",
        "Best for: Local development, simple Python flows, no containerization needed.",
        "",
        "```bash",
        "# Create process work pool",
        f'prefect work-pool create "{dag_id}-pool" --type process',
        "",
        "# Start a worker",
        f'prefect worker start --pool "{dag_id}-pool"',
        "```",
        "",
        "### Option 2: Docker Work Pool (Recommended for production)",
        "",
        "Best for: Isolated execution, consistent environments, dependency management.",
        "",
        "```bash",
        "# Create Docker work pool",
        f'prefect work-pool create "{dag_id}-pool" --type docker',
        "",
        "# Start a worker",
        f'prefect worker start --pool "{dag_id}-pool"',
        "```",
        "",
        "```yaml",
        "# prefect.yaml - Docker configuration",
        "deployments:",
        f"  - name: {dag_id}",
        f'    work_pool: "{dag_id}-pool"',
        "    build:",
        "      - prefect_docker.deployments.steps.build_docker_image:",
        '          image_name: "my-registry/my-flow"',
        '          dockerfile: "Dockerfile"',
        "```",
        "",
        "### Option 3: Kubernetes Work Pool (For orchestrated environments)",
        "",
        "Best for: Kubernetes clusters, auto-scaling, cloud-native deployments.",
        "",
        "```bash",
        "# Create Kubernetes work pool",
        f'prefect work-pool create "{dag_id}-pool" --type kubernetes',
        "",
        "# Workers run as Kubernetes pods - deploy using:",
        "helm install prefect-worker prefect/prefect-worker \\",
        f'  --set worker.config.workPool="{dag_id}-pool"',
        "```",
        "",
    ]
    return lines


def _generate_deployment_config_section(
    settings: DAGSettings, variables: list[Any] | None = None
) -> list[str]:
    """Generate prefect.yaml configuration section (P3 6.3)."""
    variables = variables or []
    dag_id = settings.dag_id or "my-flow"
    flow_name = dag_id.replace("-", "_").replace(" ", "_")

    lines = [
        "## Deployment Configuration (prefect.yaml)",
        "",
        "Create a `prefect.yaml` file to configure your deployment:",
        "",
        "```yaml",
        "# prefect.yaml",
        f"name: {dag_id}",
        "",
        "deployments:",
        f"  - name: {dag_id}",
        f'    entrypoint: "flows/{flow_name}.py:{flow_name}"',
        '    work_pool:',
        f'      name: "{dag_id}-pool"',
    ]

    # Add schedule if present
    if settings.schedule:
        cron = _convert_schedule_to_cron(settings.schedule)
        if cron:
            lines.extend([
                "    schedules:",
                "      - cron: \"" + cron + "\"",
                "        timezone: \"UTC\"  # Adjust as needed",
            ])
        else:
            lines.extend([
                "    schedules:",
                f'      - cron: "{settings.schedule}"  # Verify cron expression',
                "        timezone: \"UTC\"",
            ])

    # Add parameters if variables detected
    if variables:
        lines.extend([
            "    parameters:",
        ])
        for var in variables:
            var_name = getattr(var, "name", str(var))
            lines.append(f'      {var_name}: "default_value"  # TODO: Set default')

    # Add tags if present
    if settings.tags:
        tags_yaml = ", ".join([f'"{t}"' for t in settings.tags])
        lines.extend([
            f"    tags: [{tags_yaml}]",
        ])

    lines.extend([
        "```",
        "",
        "### Deploy the flow",
        "",
        "```bash",
        "# Deploy using the prefect.yaml configuration",
        "prefect deploy --all",
        "",
        "# Or deploy a specific deployment",
        f'prefect deploy --name "{dag_id}"',
        "```",
        "",
    ])

    return lines


def _generate_automation_section(settings: DAGSettings) -> list[str]:
    """Generate automation setup guidance for callbacks (P3 6.2)."""
    callback_types = {c.callback_type for c in settings.callbacks}
    dag_id = settings.dag_id or "my-flow"

    lines = [
        "## Automation Setup",
        "",
        "Replace Airflow callbacks with Prefect Automations for robust alerting:",
        "",
    ]

    if "sla_miss_callback" in callback_types:
        lines.extend([
            "### SLA Monitoring Automation",
            "",
            "Create an automation to detect SLA breaches based on flow run duration:",
            "",
            "```python",
            "from datetime import timedelta",
            "from prefect.automations import Automation",
            "from prefect.events.schemas.automations import EventTrigger",
            "from prefect.events.actions import SendNotification",
            "",
            "# SLA automation - triggers when flow runs exceed expected duration",
            "sla_automation = Automation(",
            f'    name="{dag_id}-sla-monitor",',
            "    description=\"Alert when flow exceeds expected duration\",",
            "    trigger=EventTrigger(",
            '        match={"prefect.resource.id": "prefect.flow-run.*"},',
            '        expect=["prefect.flow-run.Running"],',
            "        posture=\"Proactive\",",
            "        threshold=1,",
            "        within=timedelta(hours=2),  # SLA threshold - adjust as needed",
            "    ),",
            "    actions=[",
            "        SendNotification(",
            '            block_document_id="your-slack-webhook-block-id",',
            "            subject=\"SLA Breach Warning\",",
            f'            body="Flow {dag_id} has been running longer than expected",',
            "        )",
            "    ],",
            ")",
            "```",
            "",
            "**Via Prefect UI:**",
            "1. Navigate to Automations → Create Automation",
            "2. Trigger: Flow run enters 'Running' state for > 2 hours",
            "3. Action: Send Slack/Email notification",
            "",
        ])

    if "on_failure_callback" in callback_types:
        lines.extend([
            "### Failure Notification Automation",
            "",
            "```python",
            "from prefect.automations import Automation",
            "from prefect.events.schemas.automations import EventTrigger",
            "from prefect.events.actions import SendNotification",
            "",
            "failure_automation = Automation(",
            f'    name="{dag_id}-failure-alert",',
            "    description=\"Alert on flow failures\",",
            "    trigger=EventTrigger(",
            '        match={"prefect.resource.id": "prefect.flow-run.*"},',
            '        expect=["prefect.flow-run.Failed"],',
            "        posture=\"Reactive\",",
            "        threshold=1,",
            "    ),",
            "    actions=[",
            "        SendNotification(",
            '            block_document_id="your-slack-webhook-block-id",',
            "            subject=\"Flow Failed\",",
            "            body=\"{{ flow_run.name }} has failed. Check logs for details.\",",
            "        )",
            "    ],",
            ")",
            "```",
            "",
        ])

    if "on_success_callback" in callback_types:
        lines.extend([
            "### Success Notification Automation",
            "",
            "```python",
            "from prefect.automations import Automation",
            "from prefect.events.schemas.automations import EventTrigger",
            "from prefect.events.actions import SendNotification",
            "",
            "success_automation = Automation(",
            f'    name="{dag_id}-success-alert",',
            "    description=\"Notify on successful completion\",",
            "    trigger=EventTrigger(",
            '        match={"prefect.resource.id": "prefect.flow-run.*"},',
            '        expect=["prefect.flow-run.Completed"],',
            "        posture=\"Reactive\",",
            "        threshold=1,",
            "    ),",
            "    actions=[",
            "        SendNotification(",
            '            block_document_id="your-slack-webhook-block-id",',
            "            subject=\"Flow Completed\",",
            "            body=\"{{ flow_run.name }} completed successfully.\",",
            "        )",
            "    ],",
            ")",
            "```",
            "",
        ])

    return lines


def _generate_block_setup_section(connections: list[Any]) -> list[str]:
    """Generate Block setup CLI commands (P3 6.4)."""
    lines = [
        "## Block Setup Commands",
        "",
        "Create Prefect Blocks to securely store connection credentials:",
        "",
    ]

    for conn in connections:
        conn_name = getattr(conn, "name", str(conn))
        conn_type = getattr(conn, "conn_type", "unknown") or "unknown"

        # Block setup based on connection type
        if conn_type in ("postgres", "postgresql"):
            lines.extend([
                f"### Database Block: `{conn_name}`",
                "",
                "```bash",
                "# Register the SqlAlchemy block type",
                "prefect block register -m prefect_sqlalchemy",
                "```",
                "",
                "```python",
                "from prefect_sqlalchemy import SqlAlchemyConnector, ConnectionComponents",
                "",
                f'{conn_name.replace("-", "_")}_block = SqlAlchemyConnector(',
                f'    connection_info=ConnectionComponents(',
                '        driver="postgresql+psycopg2",',
                '        host="your-host",',
                '        port=5432,',
                '        database="your-db",',
                '        username="your-user",',
                '        password="your-password",  # Use Secret block for production',
                "    )",
                ")",
                f'{conn_name.replace("-", "_")}_block.save("{conn_name}")',
                "```",
                "",
            ])
        elif conn_type in ("mysql",):
            lines.extend([
                f"### Database Block: `{conn_name}`",
                "",
                "```python",
                "from prefect_sqlalchemy import SqlAlchemyConnector, ConnectionComponents",
                "",
                f'{conn_name.replace("-", "_")}_block = SqlAlchemyConnector(',
                f'    connection_info=ConnectionComponents(',
                '        driver="mysql+pymysql",',
                '        host="your-host",',
                '        port=3306,',
                '        database="your-db",',
                '        username="your-user",',
                '        password="your-password",',
                "    )",
                ")",
                f'{conn_name.replace("-", "_")}_block.save("{conn_name}")',
                "```",
                "",
            ])
        elif conn_type in ("aws", "s3"):
            lines.extend([
                f"### AWS Credentials Block: `{conn_name}`",
                "",
                "```bash",
                "# Register AWS block types",
                "prefect block register -m prefect_aws",
                "```",
                "",
                "```python",
                "from prefect_aws import AwsCredentials",
                "",
                f'{conn_name.replace("-", "_")}_block = AwsCredentials(',
                '    aws_access_key_id="your-key-id",',
                '    aws_secret_access_key="your-secret-key",',
                '    region_name="us-east-1",',
                ")",
                f'{conn_name.replace("-", "_")}_block.save("{conn_name}")',
                "```",
                "",
            ])
        elif conn_type in ("google_cloud", "google_cloud_platform", "bigquery"):
            lines.extend([
                f"### GCP Credentials Block: `{conn_name}`",
                "",
                "```bash",
                "# Register GCP block types",
                "prefect block register -m prefect_gcp",
                "```",
                "",
                "```python",
                "from prefect_gcp import GcpCredentials",
                "",
                f'{conn_name.replace("-", "_")}_block = GcpCredentials(',
                '    service_account_file="/path/to/service-account.json",',
                "    # Or use service_account_info for inline JSON",
                ")",
                f'{conn_name.replace("-", "_")}_block.save("{conn_name}")',
                "```",
                "",
            ])
        elif conn_type in ("slack", "slack_webhook"):
            lines.extend([
                f"### Slack Webhook Block: `{conn_name}`",
                "",
                "```python",
                "from prefect.blocks.notifications import SlackWebhook",
                "",
                f'{conn_name.replace("-", "_")}_block = SlackWebhook(',
                '    url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"',
                ")",
                f'{conn_name.replace("-", "_")}_block.save("{conn_name}")',
                "```",
                "",
            ])
        elif conn_type == "snowflake":
            lines.extend([
                f"### Snowflake Block: `{conn_name}`",
                "",
                "```bash",
                "# Register Snowflake block types",
                "prefect block register -m prefect_snowflake",
                "```",
                "",
                "```python",
                "from prefect_snowflake import SnowflakeCredentials, SnowflakeConnector",
                "",
                f'{conn_name.replace("-", "_")}_creds = SnowflakeCredentials(',
                '    account="your-account",',
                '    user="your-user",',
                '    password="your-password",',
                ")",
                f'{conn_name.replace("-", "_")}_block = SnowflakeConnector(',
                f'    credentials={conn_name.replace("-", "_")}_creds,',
                '    database="your-db",',
                '    schema="your-schema",',
                '    warehouse="your-warehouse",',
                ")",
                f'{conn_name.replace("-", "_")}_block.save("{conn_name}")',
                "```",
                "",
            ])
        else:
            # Generic block guidance
            lines.extend([
                f"### Custom Block: `{conn_name}` (type: {conn_type})",
                "",
                "```python",
                "from prefect.blocks.core import Block",
                "",
                f"# Create a custom block or use appropriate prefect integration",
                f"# Check: https://prefecthq.github.io/prefect-{conn_type}/",
                "```",
                "",
            ])

    return lines


def _generate_testing_section(settings: DAGSettings) -> list[str]:
    """Generate testing guidance section (P3 6.5)."""
    dag_id = settings.dag_id or "my-flow"
    flow_name = dag_id.replace("-", "_").replace(" ", "_")

    lines = [
        "## Testing Guidance",
        "",
        "### Local Testing",
        "",
        "Run the flow locally to verify behavior before deployment:",
        "",
        "```bash",
        "# Run flow directly",
        f"python flows/{flow_name}.py",
        "",
        "# Or using pytest with the generated tests",
        f"pytest tests/test_{flow_name}.py -v",
        "```",
        "",
        "### Testing with Prefect",
        "",
        "```bash",
        "# Run with Prefect tracking (requires server connection)",
        f"prefect flow-run create {flow_name}",
        "```",
        "",
        "### Deployment Testing",
        "",
        "Trigger a deployment run to validate in your execution environment:",
        "",
        "```bash",
        "# Trigger deployment run via CLI",
        f'prefect deployment run "{dag_id}/{dag_id}"',
        "",
        "# Trigger with parameters",
        f'prefect deployment run "{dag_id}/{dag_id}" --param key=value',
        "",
        "# Watch the run",
        f'prefect flow-run watch $(prefect deployment run "{dag_id}/{dag_id}" --output-json | jq -r .id)',
        "```",
        "",
        "### Validating Against Airflow",
        "",
        "Compare outputs between your Airflow DAG and Prefect flow:",
        "",
        "1. Run the Airflow DAG with a specific execution_date",
        "2. Run the Prefect flow with the same parameters",
        "3. Compare task outputs/results",
        "4. Verify timing and retry behavior",
        "",
        "```python",
        "# Example validation script",
        f"from flows.{flow_name} import {flow_name}",
        "",
        "def validate_migration():",
        f"    result = {flow_name}()",
        "    # Compare with expected Airflow output",
        "    assert result == expected_airflow_output",
        "```",
        "",
    ]
    return lines


def _generate_summary_section(settings: DAGSettings) -> list[str]:
    """Generate the summary section."""
    source = f"`{settings.source_type}`" if settings.source_type != "unknown" else "unknown"
    lines = [
        "## Summary",
        "",
        f"| Setting | Value |",
        f"|---------|-------|",
        f"| DAG ID | `{settings.dag_id or 'unknown'}` |",
        f"| Source Pattern | {source} |",
    ]

    if settings.schedule is not None:
        lines.append(f"| Schedule | `{settings.schedule}` |")
    if settings.catchup is not None:
        lines.append(f"| Catchup | `{settings.catchup}` |")
    if settings.max_active_runs is not None:
        lines.append(f"| Max Active Runs | `{settings.max_active_runs}` |")
    if settings.tags:
        tags_str = ", ".join([f"`{t}`" for t in settings.tags])
        lines.append(f"| Tags | {tags_str} |")
    if settings.callbacks:
        callback_types = ", ".join([f"`{c.callback_type}`" for c in settings.callbacks])
        lines.append(f"| Callbacks | {callback_types} |")

    lines.append("")
    return lines


def _generate_schedule_section(settings: DAGSettings) -> list[str]:
    """Generate the schedule configuration section."""
    schedule = settings.schedule
    lines = [
        "## Schedule Configuration",
        "",
        f"**Airflow Setting**: `schedule_interval` / `schedule` = `{schedule}`",
        "",
    ]

    # Add description for presets
    if schedule in SCHEDULE_PRESETS:
        lines.append(f"This is the `{schedule}` preset: {SCHEDULE_PRESETS[schedule]}")
        lines.append("")

    lines.extend([
        "**Prefect Equivalent**:",
        "",
        "Option 1: Deployment with cron schedule",
        "```yaml",
        "# prefect.yaml",
        "deployments:",
        f"  - name: {settings.dag_id or 'my-flow'}",
        "    schedule:",
    ])

    # Convert Airflow preset to cron if possible
    cron_value = _convert_schedule_to_cron(schedule) if schedule else None
    if cron_value:
        lines.append(f'      cron: "{cron_value}"')
    else:
        lines.append(f'      cron: "{schedule}"  # Verify this cron expression')

    lines.extend([
        "```",
        "",
        "Option 2: Using `flow.serve()` for simple scheduling",
        "```python",
        "if __name__ == '__main__':",
    ])

    if cron_value:
        lines.append(f'    my_flow.serve(name="{settings.dag_id}", cron="{cron_value}")')
    else:
        lines.append(f'    my_flow.serve(name="{settings.dag_id}", cron="{schedule}")')

    lines.extend([
        "```",
        "",
        "Option 3: Using interval schedules",
        "```python",
        "from datetime import timedelta",
        "from prefect import flow",
        "",
        "@flow",
        "def my_flow():",
        "    pass",
        "",
        "if __name__ == '__main__':",
        "    my_flow.serve(",
        f'        name="{settings.dag_id}",',
        "        interval=timedelta(hours=1),  # Adjust as needed",
        "    )",
        "```",
        "",
    ])

    return lines


def _generate_catchup_section(settings: DAGSettings) -> list[str]:
    """Generate the catchup configuration section."""
    catchup = settings.catchup
    lines = [
        "## Catchup / Backfill Configuration",
        "",
        f"**Airflow Setting**: `catchup` = `{catchup}`",
        "",
    ]

    if catchup:
        lines.extend([
            "**Behavior**: Airflow will backfill runs for all missed schedule intervals.",
            "",
            "**Prefect Equivalent**:",
            "",
            "Prefect does not automatically backfill by default. To run backfills:",
            "",
            "1. **Manual backfill via CLI**:",
            "```bash",
            "# Run flow for a specific date",
            f'prefect deployment run "{settings.dag_id}/my-deployment" --param execution_date=2024-01-01',
            "```",
            "",
            "2. **Programmatic backfill**:",
            "```python",
            "from prefect.deployments import run_deployment",
            "from datetime import date, timedelta",
            "",
            "def backfill(start_date: date, end_date: date):",
            "    current = start_date",
            "    while current <= end_date:",
            '        run_deployment("my-flow/my-deployment", parameters={"execution_date": str(current)})',
            "        current += timedelta(days=1)",
            "```",
            "",
        ])
    else:
        lines.extend([
            "**Behavior**: Airflow skips missed schedule intervals (no backfill).",
            "",
            "**Prefect Equivalent**:",
            "",
            "This is Prefect's default behavior. No additional configuration needed.",
            "Prefect deployments only trigger for future scheduled times.",
            "",
        ])

    return lines


def _generate_retry_section(settings: DAGSettings) -> list[str]:
    """Generate the retry configuration section."""
    default_args = settings.default_args
    lines = [
        "## Retry Configuration",
        "",
        "**Airflow Setting**: `default_args`",
        "",
    ]

    retries = default_args.get("retries")
    retry_delay = default_args.get("retry_delay")
    email = default_args.get("email")
    email_on_failure = default_args.get("email_on_failure")
    email_on_retry = default_args.get("email_on_retry")

    if retries is not None:
        lines.append(f"- `retries`: `{retries}`")
    if retry_delay is not None:
        lines.append(f"- `retry_delay`: `{retry_delay}`")
    if email is not None:
        lines.append(f"- `email`: `{email}`")
    if email_on_failure is not None:
        lines.append(f"- `email_on_failure`: `{email_on_failure}`")
    if email_on_retry is not None:
        lines.append(f"- `email_on_retry`: `{email_on_retry}`")

    lines.append("")
    lines.extend([
        "**Prefect Equivalent**:",
        "",
        "```python",
        "from prefect import flow, task",
        "",
    ])

    # Build decorator args
    decorator_args = []
    if retries is not None:
        decorator_args.append(f"retries={retries}")
    if retry_delay is not None:
        # Convert to seconds if it looks like a timedelta
        if isinstance(retry_delay, int):
            decorator_args.append(f"retry_delay_seconds={retry_delay}")
        else:
            decorator_args.append(f"retry_delay_seconds=300  # TODO: Convert {retry_delay}")

    decorator_str = ", ".join(decorator_args) if decorator_args else ""

    lines.extend([
        "# Apply retries at task level",
        f"@task({decorator_str})" if decorator_str else "@task",
        "def my_task():",
        "    pass",
        "",
        "# Or at flow level (applies to all tasks)",
        f"@flow({decorator_str})" if decorator_str else "@flow",
        "def my_flow():",
        "    pass",
        "```",
        "",
    ])

    # Add email notification guidance if needed
    if email or email_on_failure or email_on_retry:
        lines.extend([
            "**Email Notifications**:",
            "",
            "In Prefect, use notification blocks or automations:",
            "",
            "```python",
            "from prefect.blocks.notifications import SlackWebhook",
            "",
            "# Or use Prefect Automations in the UI to:",
            "# 1. Trigger on flow/task state changes (Failed, Retrying)",
            "# 2. Send notifications via email, Slack, PagerDuty, etc.",
            "```",
            "",
        ])

    return lines


def _generate_concurrency_section(settings: DAGSettings) -> list[str]:
    """Generate the concurrency configuration section."""
    lines = [
        "## Concurrency Configuration",
        "",
    ]

    if settings.max_active_runs is not None:
        lines.extend([
            f"**Airflow Setting**: `max_active_runs` = `{settings.max_active_runs}`",
            "",
            "This limits concurrent DAG runs. In Prefect:",
            "",
        ])

    if settings.concurrency is not None:
        lines.extend([
            f"**Airflow Setting**: `concurrency` = `{settings.concurrency}`",
            "",
            "This limits concurrent tasks within the DAG. In Prefect:",
            "",
        ])

    max_runs = settings.max_active_runs or settings.concurrency or 1

    lines.extend([
        "**Prefect Equivalent**:",
        "",
        "Option 1: Global concurrency limit (Prefect Cloud/Server)",
        "```python",
        "from prefect import flow",
        "from prefect.concurrency.sync import concurrency",
        "",
        "@flow",
        "def my_flow():",
        f'    with concurrency("{settings.dag_id}-limit", occupy={max_runs}):',
        "        # Flow logic here",
        "        pass",
        "```",
        "",
        "Option 2: Create concurrency limit via CLI",
        "```bash",
        f'prefect concurrency-limit create "{settings.dag_id}-limit" {max_runs}',
        "```",
        "",
        "Option 3: Work pool concurrency (limits all flows in pool)",
        "```bash",
        f"prefect work-pool update my-pool --concurrency-limit {max_runs}",
        "```",
        "",
    ])

    return lines


def _generate_autopause_section(settings: DAGSettings) -> list[str]:
    """Generate the auto-pause configuration section."""
    max_failed = settings.max_consecutive_failed_dag_runs
    lines = [
        "## Auto-Pause on Consecutive Failures",
        "",
        f"**Airflow Setting**: `max_consecutive_failed_dag_runs` = `{max_failed}`",
        "",
        f"This pauses the DAG after {max_failed} consecutive failed runs.",
        "",
        "**Prefect Equivalent**:",
        "",
        "Create an automation in Prefect UI or via code:",
        "",
        "1. **Via Prefect UI**:",
        "   - Navigate to Automations > Create Automation",
        "   - Trigger: Flow run enters `Failed` state",
        f"   - Condition: Count >= {max_failed} within time window",
        "   - Action: Pause deployment",
        "",
        "2. **Via Python SDK**:",
        "```python",
        "from prefect.automations import Automation",
        "from prefect.events.schemas.automations import EventTrigger",
        "",
        "# Create automation to pause on consecutive failures",
        "automation = Automation(",
        f'    name="{settings.dag_id}-auto-pause",',
        "    trigger=EventTrigger(",
        '        expect=["prefect.flow-run.Failed"],',
        f"        threshold={max_failed},",
        '        within=timedelta(hours=24),  # Adjust window as needed',
        "    ),",
        "    actions=[",
        "        # Pause deployment action",
        "    ],",
        ")",
        "```",
        "",
    ]

    return lines


def _generate_tags_section(settings: DAGSettings) -> list[str]:
    """Generate the tags configuration section."""
    tags = settings.tags
    tags_str = ", ".join([f'"{t}"' for t in tags])
    lines = [
        "## Tags",
        "",
        f"**Airflow Setting**: `tags` = `{tags}`",
        "",
        "**Prefect Equivalent**:",
        "",
        "```python",
        "from prefect import flow",
        "",
        f"@flow(tags=[{tags_str}])",
        "def my_flow():",
        "    pass",
        "```",
        "",
        "Tags in Prefect enable:",
        "- Filtering flows/runs in the UI",
        "- Work pool routing (workers can filter by tags)",
        "- Automation triggers (react to tagged flow events)",
        "",
    ]

    return lines


def _generate_callbacks_section(settings: DAGSettings) -> list[str]:
    """Generate the callbacks configuration section."""
    lines = [
        "## Callbacks / Hooks",
        "",
        "**Airflow Setting**: Callbacks detected:",
        "",
    ]

    for callback in settings.callbacks:
        lines.append(f"- `{callback.callback_type}` -> `{callback.function_name}`")

    lines.extend([
        "",
        "**Prefect Equivalent**:",
        "",
        "Prefect uses state change hooks and automations:",
        "",
        "```python",
        "from prefect import flow",
        "from prefect.states import Failed, Completed",
        "",
    ])

    # Generate appropriate hook examples based on callback types
    callback_types = {c.callback_type for c in settings.callbacks}

    if "on_failure_callback" in callback_types:
        lines.extend([
            "def on_failure(flow, flow_run, state):",
            '    """Called when flow fails."""',
            "    # Your failure handling logic",
            '    print(f"Flow {flow.name} failed: {state.message}")',
            "",
        ])

    if "on_success_callback" in callback_types:
        lines.extend([
            "def on_success(flow, flow_run, state):",
            '    """Called when flow succeeds."""',
            "    # Your success handling logic",
            '    print(f"Flow {flow.name} completed successfully")',
            "",
        ])

    # Build hook list for decorator
    hooks = []
    if "on_failure_callback" in callback_types:
        hooks.append("on_failure=[on_failure]")
    if "on_success_callback" in callback_types:
        hooks.append("on_completion=[on_success]")

    if hooks:
        hooks_str = ", ".join(hooks)
        lines.extend([
            f"@flow({hooks_str})",
            "def my_flow():",
            "    pass",
            "```",
            "",
        ])
    else:
        lines.extend([
            "@flow",
            "def my_flow():",
            "    pass",
            "```",
            "",
        ])

    if "sla_miss_callback" in callback_types:
        lines.extend([
            "**SLA Miss Handling**:",
            "",
            "For SLA monitoring, use Prefect Automations:",
            "",
            "1. Create automation triggered by flow run duration",
            "2. Set threshold for SLA breach",
            "3. Action: Send notification or trigger remediation flow",
            "",
        ])

    return lines


def _generate_timeout_section(settings: DAGSettings) -> list[str]:
    """Generate the timeout configuration section."""
    lines = [
        "## Timeout Configuration",
        "",
        f"**Airflow Setting**: `dagrun_timeout` = `{settings.dagrun_timeout}`",
        "",
        "**Prefect Equivalent**:",
        "",
        "```python",
        "from prefect import flow",
        "from datetime import timedelta",
        "",
        "@flow(timeout_seconds=3600)  # Adjust based on original timeout",
        "def my_flow():",
        "    pass",
        "```",
        "",
        "Note: Convert your Airflow timeout to seconds for the Prefect decorator.",
        "",
    ]

    return lines


def _generate_connections_section(connections: list[Any]) -> list[str]:
    """Generate the connections section."""
    lines = [
        "## Connection Migration",
        "",
        "The following Airflow connections were detected:",
        "",
        "| Connection ID | Type | Prefect Block |",
        "|--------------|------|---------------|",
    ]

    for conn in connections:
        conn_name = getattr(conn, "name", str(conn))
        conn_type = getattr(conn, "conn_type", "unknown") or "unknown"

        # Map to Prefect block type
        block_mapping = {
            "postgres": "SqlAlchemyConnector",
            "postgresql": "SqlAlchemyConnector",
            "mysql": "SqlAlchemyConnector",
            "snowflake": "SnowflakeConnector",
            "bigquery": "BigQueryWarehouse",
            "google_cloud": "GcpCredentials",
            "google_cloud_platform": "GcpCredentials",
            "aws": "AwsCredentials",
            "s3": "S3Bucket",
            "slack": "SlackWebhook",
            "slack_webhook": "SlackWebhook",
        }
        block_type = block_mapping.get(conn_type, "Custom Block")

        lines.append(f"| `{conn_name}` | `{conn_type}` | `{block_type}` |")

    lines.extend([
        "",
        "See the generated `combined_code` in the conversion output for Block scaffolds.",
        "",
    ])

    return lines


def _generate_variables_section(variables: list[Any]) -> list[str]:
    """Generate the variables section."""
    lines = [
        "## Variable Migration",
        "",
        "The following Airflow Variables were detected:",
        "",
        "| Variable Name | Usage | Sensitive | Prefect Equivalent |",
        "|--------------|-------|-----------|-------------------|",
    ]

    for var in variables:
        var_name = getattr(var, "name", str(var))
        is_set = getattr(var, "is_set", False)
        is_sensitive = getattr(var, "is_sensitive", False)

        usage = "write" if is_set else "read"
        sensitive = "Yes" if is_sensitive else "No"

        if is_sensitive:
            prefect_equiv = "Secret Block"
        elif is_set:
            prefect_equiv = "Prefect Variable (API)"
        else:
            prefect_equiv = "Flow Parameter / Variable"

        lines.append(f"| `{var_name}` | {usage} | {sensitive} | {prefect_equiv} |")

    lines.extend([
        "",
        "See the generated scaffolds in the conversion output for implementation options.",
        "",
    ])

    return lines


def _generate_action_checklist(
    settings: DAGSettings,
    connections: list[Any],
    variables: list[Any],
) -> list[str]:
    """Generate the action checklist."""
    lines = [
        "## Migration Checklist",
        "",
        "### Pre-Migration",
        "",
    ]

    # Dynamic checklist based on detected features
    checklist_items = []

    if settings.schedule:
        checklist_items.append("- [ ] Verify schedule cron expression is correct")

    if connections:
        checklist_items.append("- [ ] Create Prefect Blocks for each connection")
        for conn in connections:
            conn_name = getattr(conn, "name", str(conn))
            checklist_items.append(f"  - [ ] `{conn_name}`")

    if variables:
        checklist_items.append("- [ ] Configure Prefect Variables/Secrets")
        for var in variables:
            var_name = getattr(var, "name", str(var))
            is_sensitive = getattr(var, "is_sensitive", False)
            var_type = "Secret" if is_sensitive else "Variable"
            checklist_items.append(f"  - [ ] `{var_name}` ({var_type})")

    if settings.callbacks:
        checklist_items.append("- [ ] Implement state change hooks or automations")

    if settings.max_consecutive_failed_dag_runs:
        checklist_items.append("- [ ] Create auto-pause automation")

    if not checklist_items:
        checklist_items.append("- [ ] Review generated flow code")

    lines.extend(checklist_items)

    lines.extend([
        "",
        "### Deployment",
        "",
        "- [ ] Create work pool for flow execution",
        "- [ ] Create deployment with schedule",
        "- [ ] Configure concurrency limits (if applicable)",
        "- [ ] Set up monitoring and alerting",
        "",
        "### Validation",
        "",
        "- [ ] Run generated tests",
        "- [ ] Compare output with Airflow DAG runs",
        "- [ ] Verify retry behavior",
        "- [ ] Verify notification/callback behavior",
        "",
        "### Cutover",
        "",
        "- [ ] Pause Airflow DAG",
        "- [ ] Activate Prefect deployment",
        "- [ ] Monitor first few scheduled runs",
        "- [ ] Archive Airflow DAG after validation period",
        "",
    ])

    return lines


def _convert_schedule_to_cron(schedule: str | None) -> str | None:
    """Convert Airflow schedule preset to cron expression."""
    if not schedule:
        return None

    preset_to_cron = {
        "@once": None,  # No cron equivalent
        "@hourly": "0 * * * *",
        "@daily": "0 0 * * *",
        "@weekly": "0 0 * * 0",
        "@monthly": "0 0 1 * *",
        "@yearly": "0 0 1 1 *",
        "@annually": "0 0 1 1 *",
    }

    if schedule in preset_to_cron:
        return preset_to_cron[schedule]

    # If it looks like a cron expression, return as-is
    if len(schedule.split()) == 5:
        return schedule

    return None
