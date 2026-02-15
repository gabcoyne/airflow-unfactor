"""Parse Airflow DAG files using AST."""

import ast
from typing import Any

AIRFLOW_OPERATORS = {
    "PythonOperator",
    "BashOperator",
    "BranchPythonOperator",
    "DummyOperator",
    "EmptyOperator",
    "TriggerDagRunOperator",
    "ShortCircuitOperator",
    "PythonSensor",
    "ExternalTaskSensor",
    "FileSensor",
    "S3KeySensor",
    "HttpSensor",
    "SqlSensor",
    "TaskGroup",
    # Provider operators
    "S3CreateObjectOperator",
    "S3DeleteObjectsOperator",
    "BigQueryInsertJobOperator",
    "BigQueryExecuteQueryOperator",
    "GCSCreateBucketOperator",
    "PostgresOperator",
    "MySqlOperator",
    "SlackWebhookOperator",
    "EmailOperator",
    "SimpleHttpOperator",
}


class DAGVisitor(ast.NodeVisitor):
    """AST visitor to extract DAG information."""

    def __init__(self):
        self.dag_id = None
        self.operators = []
        self.xcom_usage = []
        self.notes = []
        self.imports = []
        self.task_ids = set()
        self.dag_settings = {}

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            for alias in node.names:
                self.imports.append(f"{node.module}.{alias.name}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Check for DAG instantiation
        func_name = self._get_call_name(node)

        if func_name == "DAG":
            self._extract_dag_id(node)
        elif func_name in AIRFLOW_OPERATORS:
            self._extract_operator(node, func_name)

        # Check for XCom usage
        if func_name in ("xcom_push", "xcom_pull"):
            self._extract_xcom(node, func_name)

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definitions to check for @dag decorator."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                func_name = self._get_call_name(decorator)
                if func_name == "dag":
                    self._extract_dag_id(decorator)
                    # If dag_id wasn't in decorator args, use function name
                    if not self.dag_id:
                        self.dag_id = node.name
            elif isinstance(decorator, ast.Name) and decorator.id == "dag":
                # Handle bare @dag decorator without arguments
                if not self.dag_id:
                    self.dag_id = node.name
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        # Check for ti.xcom_push/pull
        if node.attr in ("xcom_push", "xcom_pull"):
            self.xcom_usage.append(f"Uses {node.attr}")
        self.generic_visit(node)

    def _get_call_name(self, node: ast.Call) -> str:
        """Get the name of a function call."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    def _extract_dag_id(self, node: ast.Call):
        """Extract DAG ID and settings from DAG() call or @dag decorator."""
        # Extract dag_id
        for keyword in node.keywords:
            if keyword.arg == "dag_id" and isinstance(keyword.value, ast.Constant):
                self.dag_id = keyword.value.value
                break
        # First positional arg might be dag_id
        if not self.dag_id and node.args and isinstance(node.args[0], ast.Constant):
            self.dag_id = node.args[0].value

        # Extract DAG-level settings
        self._extract_dag_settings(node)

    def _extract_operator(self, node: ast.Call, op_type: str):
        """Extract operator information."""
        task_id = None
        retries = None
        retry_delay = None
        retry_exponential_backoff = None
        max_retry_delay = None
        pool = None
        pool_slots = None

        for keyword in node.keywords:
            if keyword.arg == "task_id" and isinstance(keyword.value, ast.Constant):
                task_id = keyword.value.value
            elif keyword.arg == "retries":
                retries = self._extract_value(keyword.value)
            elif keyword.arg == "retry_delay":
                retry_delay = self._extract_value(keyword.value)
            elif keyword.arg == "retry_exponential_backoff":
                retry_exponential_backoff = self._extract_value(keyword.value)
            elif keyword.arg == "max_retry_delay":
                max_retry_delay = self._extract_value(keyword.value)
            elif keyword.arg == "pool":
                pool = self._extract_value(keyword.value)
            elif keyword.arg == "pool_slots":
                pool_slots = self._extract_value(keyword.value)

        operator_info = {
            "type": op_type,
            "task_id": task_id,
            "line": node.lineno,
        }

        # Add task-level retry settings if present
        if retries is not None:
            operator_info["retries"] = retries
        if retry_delay is not None:
            operator_info["retry_delay"] = retry_delay
        if retry_exponential_backoff is not None:
            operator_info["retry_exponential_backoff"] = retry_exponential_backoff
        if max_retry_delay is not None:
            operator_info["max_retry_delay"] = max_retry_delay
        if pool is not None:
            operator_info["pool"] = pool
        if pool_slots is not None:
            operator_info["pool_slots"] = pool_slots

        self.operators.append(operator_info)

        if task_id:
            self.task_ids.add(task_id)

        # Add notes for complex operators
        if "Sensor" in op_type:
            self.notes.append(f"Has sensor: {op_type} (consider Prefect triggers)")
        elif op_type == "BranchPythonOperator":
            self.notes.append("Has branching logic (convert to Python if/else)")
        elif op_type == "TaskGroup":
            self.notes.append("Has TaskGroup (convert to subflow)")

        # Add notes for retry/pool configurations
        if retry_exponential_backoff:
            self.notes.append(
                f"Task '{task_id}' uses exponential_backoff - Prefect uses different backoff mechanism"
            )
        if pool:
            self.notes.append(
                f"Task '{task_id}' uses pool '{pool}' - configure Prefect work pool concurrency"
            )
        if pool_slots and pool_slots > 1:
            self.notes.append(
                f"Task '{task_id}' uses pool_slots={pool_slots} - review Prefect concurrency limits"
            )

    def _extract_xcom(self, node: ast.Call, func_name: str):
        """Extract XCom usage information."""
        self.xcom_usage.append(f"Uses {func_name}")
        self.notes.append(f"Uses XCom {func_name} (convert to return values)")

    def _extract_dag_settings(self, node: ast.Call):
        """Extract DAG-level configuration settings."""
        settings = {}

        for keyword in node.keywords:
            arg_name = keyword.arg

            # Extract schedule settings
            if arg_name in ("schedule", "schedule_interval"):
                value = self._extract_value(keyword.value)
                if value is not None:
                    settings[arg_name] = value

            # Extract boolean flags
            elif arg_name == "catchup":
                value = self._extract_value(keyword.value)
                if value is not None:
                    settings["catchup"] = value

            # Extract max_active_runs
            elif arg_name == "max_active_runs":
                value = self._extract_value(keyword.value)
                if value is not None:
                    settings["max_active_runs"] = value

            # Extract max_consecutive_failed_dag_runs
            elif arg_name == "max_consecutive_failed_dag_runs":
                value = self._extract_value(keyword.value)
                if value is not None:
                    settings["max_consecutive_failed_dag_runs"] = value

            # Extract tags
            elif arg_name == "tags":
                value = self._extract_value(keyword.value)
                if value is not None:
                    settings["tags"] = value

            # Extract default_args
            elif arg_name == "default_args":
                default_args = self._extract_default_args(keyword.value)
                if default_args:
                    settings["default_args"] = default_args

            # Extract callbacks
            elif arg_name in (
                "on_success_callback",
                "on_failure_callback",
                "on_retry_callback",
                "sla_miss_callback",
            ):
                # Just record that callback is present
                if "callbacks" not in settings:
                    settings["callbacks"] = []
                settings["callbacks"].append(arg_name)

        self.dag_settings = settings

    def _extract_value(self, node: ast.AST) -> Any:
        """Extract value from an AST node."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.List):
            return [self._extract_value(elt) for elt in node.elts]
        elif isinstance(node, ast.Str):  # Python 3.7 compatibility
            return node.s
        elif isinstance(node, ast.Num):  # Python 3.7 compatibility
            return node.n
        elif isinstance(node, ast.Name):
            # Return the variable name as a string representation
            return f"<variable: {node.id}>"
        elif isinstance(node, ast.Attribute):
            # Handle things like datetime.timedelta or Dataset()
            return self._format_attribute(node)
        elif isinstance(node, ast.Call):
            # Handle function calls like timedelta(), Dataset(), etc.
            return self._format_call(node)
        return None

    def _format_attribute(self, node: ast.Attribute) -> str:
        """Format an attribute access like datetime.timedelta."""
        parts = []
        current = node
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

    def _extract_default_args(self, node: ast.AST) -> dict[str, Any] | str:
        """Extract default_args dictionary or variable reference."""
        if isinstance(node, ast.Name):
            # It's a variable reference
            return f"<variable: {node.id}>"
        elif not isinstance(node, ast.Dict):
            return {}

        default_args = {}
        for key, value in zip(node.keys, node.values, strict=False):
            if isinstance(key, ast.Constant):
                key_str = key.value
                # Focus on retries and retry_delay as per requirements
                if key_str in (
                    "retries",
                    "retry_delay",
                    "owner",
                    "email",
                    "email_on_failure",
                    "email_on_retry",
                ):
                    extracted_value = self._extract_value(value)
                    if extracted_value is not None:
                        default_args[key_str] = extracted_value

        return default_args


def parse_dag(content: str) -> dict[str, Any]:
    """Parse an Airflow DAG file.

    Args:
        content: DAG file content

    Returns:
        Dictionary with DAG information including DAG-level settings
    """
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}"}

    visitor = DAGVisitor()
    visitor.visit(tree)

    result = {
        "dag_id": visitor.dag_id or "unknown",
        "operators": visitor.operators,
        "xcom_usage": list(set(visitor.xcom_usage)),
        "notes": list(set(visitor.notes)),
        "imports": visitor.imports,
        "task_ids": list(visitor.task_ids),
        "dag_settings": visitor.dag_settings,
    }

    # Flatten DAG settings into result for easier access
    settings = visitor.dag_settings
    if "schedule" in settings:
        result["schedule"] = settings["schedule"]
    elif "schedule_interval" in settings:
        result["schedule"] = settings["schedule_interval"]

    if "catchup" in settings:
        result["catchup"] = settings["catchup"]

    if "max_active_runs" in settings:
        result["max_active_runs"] = settings["max_active_runs"]

    if "max_consecutive_failed_dag_runs" in settings:
        result["max_consecutive_failed_dag_runs"] = settings["max_consecutive_failed_dag_runs"]

    if "tags" in settings:
        result["tags"] = settings["tags"]

    if "default_args" in settings:
        result["default_args"] = settings["default_args"]

    if "callbacks" in settings:
        result["has_failure_callback"] = "on_failure_callback" in settings["callbacks"]
        result["has_success_callback"] = "on_success_callback" in settings["callbacks"]
        result["has_retry_callback"] = "on_retry_callback" in settings["callbacks"]
        result["has_sla_callback"] = "sla_miss_callback" in settings["callbacks"]
        result["callbacks"] = settings["callbacks"]

    return result
