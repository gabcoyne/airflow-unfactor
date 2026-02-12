"""Parse Airflow DAG files using AST."""

import ast
import re
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
        """Extract DAG ID from DAG() call."""
        for keyword in node.keywords:
            if keyword.arg == "dag_id" and isinstance(keyword.value, ast.Constant):
                self.dag_id = keyword.value.value
                return
        # First positional arg might be dag_id
        if node.args and isinstance(node.args[0], ast.Constant):
            self.dag_id = node.args[0].value

    def _extract_operator(self, node: ast.Call, op_type: str):
        """Extract operator information."""
        task_id = None
        for keyword in node.keywords:
            if keyword.arg == "task_id" and isinstance(keyword.value, ast.Constant):
                task_id = keyword.value.value
                break

        self.operators.append({
            "type": op_type,
            "task_id": task_id,
            "line": node.lineno,
        })

        if task_id:
            self.task_ids.add(task_id)

        # Add notes for complex operators
        if "Sensor" in op_type:
            self.notes.append(f"Has sensor: {op_type} (consider Prefect triggers)")
        elif op_type == "BranchPythonOperator":
            self.notes.append("Has branching logic (convert to Python if/else)")
        elif op_type == "TaskGroup":
            self.notes.append("Has TaskGroup (convert to subflow)")

    def _extract_xcom(self, node: ast.Call, func_name: str):
        """Extract XCom usage information."""
        self.xcom_usage.append(f"Uses {func_name}")
        self.notes.append(f"Uses XCom {func_name} (convert to return values)")


def parse_dag(content: str) -> dict[str, Any]:
    """Parse an Airflow DAG file.

    Args:
        content: DAG file content

    Returns:
        Dictionary with DAG information
    """
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}"}

    visitor = DAGVisitor()
    visitor.visit(tree)

    return {
        "dag_id": visitor.dag_id or "unknown",
        "operators": visitor.operators,
        "xcom_usage": list(set(visitor.xcom_usage)),
        "notes": list(set(visitor.notes)),
        "imports": visitor.imports,
        "task_ids": list(visitor.task_ids),
    }