"""Convert Airflow TaskFlow API to Prefect flows.

See specs/taskflow-converter.openspec.md for specification.
"""

import ast
import re
import textwrap
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskInfo:
    """Information about a detected task."""
    name: str
    function_name: str
    decorator: str  # @task, @task.bash, etc.
    parameters: dict[str, Any] = field(default_factory=dict)
    body_source: str = ""
    args: list[str] = field(default_factory=list)  # Function arguments
    line_number: int = 0
    is_bash: bool = False
    is_branch: bool = False


@dataclass
class DagInfo:
    """Information about a detected DAG."""
    name: str
    function_name: str
    parameters: dict[str, Any] = field(default_factory=dict)
    tasks: list[TaskInfo] = field(default_factory=list)
    body_source: str = ""
    default_args: dict[str, Any] = field(default_factory=dict)


class TaskFlowVisitor(ast.NodeVisitor):
    """AST visitor to extract TaskFlow patterns."""
    
    def __init__(self, source_lines: list[str]):
        self.source_lines = source_lines
        self.source = "\n".join(source_lines)
        self.dags: list[DagInfo] = []
        self.standalone_tasks: list[TaskInfo] = []
        self.current_dag: DagInfo | None = None
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        for decorator in node.decorator_list:
            dec_str = ast.unparse(decorator)
            
            # Check for @dag decorator
            if self._is_dag_decorator(decorator):
                dag_info = self._extract_dag_info(node, decorator)
                self.dags.append(dag_info)
                # Visit children to find nested tasks
                old_dag = self.current_dag
                self.current_dag = dag_info
                self.generic_visit(node)
                self.current_dag = old_dag
                return
            
            # Check for @task decorator
            if self._is_task_decorator(decorator):
                task_info = self._extract_task_info(node, decorator)
                if self.current_dag:
                    self.current_dag.tasks.append(task_info)
                else:
                    self.standalone_tasks.append(task_info)
                return
        
        self.generic_visit(node)
    
    def _is_dag_decorator(self, decorator: ast.expr) -> bool:
        dec_str = ast.unparse(decorator)
        return dec_str.startswith("dag") or dec_str.startswith("dag(")
    
    def _is_task_decorator(self, decorator: ast.expr) -> bool:
        dec_str = ast.unparse(decorator)
        return (
            dec_str.startswith("task") or 
            dec_str.startswith("task(") or
            dec_str.startswith("task.")
        )
    
    def _extract_dag_info(self, node: ast.FunctionDef, decorator: ast.expr) -> DagInfo:
        params = self._extract_decorator_params(decorator)
        
        # Get dag_id from params or function name
        dag_id = params.get("dag_id", node.name)
        
        # Extract default_args if present
        default_args = {}
        if "default_args" in params:
            default_args = params.pop("default_args")
        
        return DagInfo(
            name=dag_id,
            function_name=node.name,
            parameters=params,
            default_args=default_args,
            body_source=self._get_function_body(node),
        )
    
    def _extract_task_info(self, node: ast.FunctionDef, decorator: ast.expr) -> TaskInfo:
        dec_str = ast.unparse(decorator)
        params = self._extract_decorator_params(decorator)
        
        # Determine task type
        is_bash = ".bash" in dec_str
        is_branch = ".branch" in dec_str
        
        # Get task_id from params or function name
        task_id = params.get("task_id", node.name)
        
        # Get function arguments
        args = [arg.arg for arg in node.args.args]
        
        return TaskInfo(
            name=task_id,
            function_name=node.name,
            decorator=dec_str,
            parameters=params,
            body_source=self._get_function_body(node),
            args=args,
            line_number=node.lineno,
            is_bash=is_bash,
            is_branch=is_branch,
        )
    
    def _extract_decorator_params(self, decorator: ast.expr) -> dict[str, Any]:
        """Extract parameters from decorator call."""
        params = {}
        
        if isinstance(decorator, ast.Call):
            for keyword in decorator.keywords:
                if keyword.arg:
                    try:
                        params[keyword.arg] = ast.literal_eval(keyword.value)
                    except (ValueError, TypeError):
                        params[keyword.arg] = ast.unparse(keyword.value)
        
        return params
    
    def _get_function_body(self, node: ast.FunctionDef) -> str:
        """Extract function body source code using ast.get_source_segment."""
        # Get the entire function body
        if not node.body:
            return "pass"
        
        # Get line range
        start_line = node.body[0].lineno - 1
        end_line = node.body[-1].end_lineno
        
        # Extract lines
        body_lines = self.source_lines[start_line:end_line]
        
        if not body_lines:
            return "pass"
        
        # Find minimum indentation
        non_empty = [l for l in body_lines if l.strip()]
        if not non_empty:
            return "pass"
        
        min_indent = min(len(l) - len(l.lstrip()) for l in non_empty)
        
        # Dedent
        dedented = [l[min_indent:] if len(l) > min_indent else l.lstrip() for l in body_lines]
        
        return "\n".join(dedented)


def extract_taskflow_info(dag_code: str) -> tuple[list[DagInfo], list[TaskInfo]]:
    """Extract TaskFlow DAGs and tasks from source code.
    
    Args:
        dag_code: Source code of the DAG file
        
    Returns:
        Tuple of (dags, standalone_tasks)
    """
    try:
        tree = ast.parse(dag_code)
    except SyntaxError:
        return [], []
    
    source_lines = dag_code.splitlines()
    visitor = TaskFlowVisitor(source_lines)
    visitor.visit(tree)
    
    return visitor.dags, visitor.standalone_tasks


def convert_taskflow_to_prefect(
    dag_code: str,
    include_comments: bool = True,
) -> dict[str, Any]:
    """Convert TaskFlow DAG to Prefect flow.
    
    Args:
        dag_code: Source code of the Airflow DAG
        include_comments: Include educational comments
        
    Returns:
        Dictionary with flow_code, warnings, mapping
    """
    dags, standalone_tasks = extract_taskflow_info(dag_code)
    
    if not dags and not standalone_tasks:
        return {
            "flow_code": "",
            "warnings": ["No TaskFlow patterns detected"],
            "mapping": {},
        }
    
    lines = []
    warnings = []
    mapping = {}
    
    # Imports
    lines.append("from prefect import flow, task")
    
    # Check if we need subprocess for @task.bash
    needs_subprocess = any(
        t.is_bash 
        for dag in dags for t in dag.tasks
    ) or any(t.is_bash for t in standalone_tasks)
    
    if needs_subprocess:
        lines.append("import subprocess")
    
    lines.append("")
    
    # Add header comment
    if include_comments and dags:
        lines.append(f'"""Prefect flow converted from Airflow TaskFlow DAG: {dags[0].name}')
        lines.append("")
        lines.append("\u2728 Converted by airflow-unfactor")
        lines.append("")
        lines.append("TaskFlow API maps naturally to Prefect:")
        lines.append("- @dag \u2192 @flow")
        lines.append("- @task \u2192 @task")
        lines.append("- Return values pass data between tasks (same as Prefect)")
        lines.append('"""')
        lines.append("")
    
    # Convert standalone tasks first
    for task in standalone_tasks:
        task_code = _convert_task(task, include_comments)
        lines.extend(task_code)
        lines.append("")
        mapping[task.name] = task.function_name
    
    # Convert DAGs
    for dag in dags:
        # Convert nested tasks first
        for task in dag.tasks:
            task_code = _convert_task(task, include_comments)
            lines.extend(task_code)
            lines.append("")
            mapping[task.name] = task.function_name
        
        # Convert DAG to flow
        flow_code = _convert_dag_to_flow(dag, include_comments)
        lines.extend(flow_code)
        mapping[dag.name] = dag.function_name
        
        # Check for unconvertible parameters
        if dag.parameters.get("schedule"):
            warnings.append(
                f"Schedule '{dag.parameters['schedule']}' not converted. "
                "Use Prefect deployments for scheduling."
            )
        if dag.default_args:
            warnings.append(
                "default_args not automatically applied. "
                "Consider adding retry config to individual tasks."
            )
    
    # Add main block
    if dags:
        lines.append("")
        lines.append("")
        lines.append('if __name__ == "__main__":')
        lines.append(f"    {dags[0].function_name}()")
    
    return {
        "flow_code": "\n".join(lines),
        "warnings": warnings,
        "mapping": mapping,
    }


def _convert_task(task: TaskInfo, include_comments: bool) -> list[str]:
    """Convert a single task to Prefect."""
    lines = []
    
    # Build decorator params
    params = []
    if task.name != task.function_name:
        params.append(f'name="{task.name}"')
    
    # Convert Airflow params to Prefect
    if "retries" in task.parameters:
        params.append(f"retries={task.parameters['retries']}")
    if "retry_delay" in task.parameters:
        # Convert timedelta to seconds if needed
        delay = task.parameters["retry_delay"]
        if isinstance(delay, str) and "timedelta" in delay:
            lines.append(f"# TODO: Convert {delay} to retry_delay_seconds")
        else:
            params.append(f"retry_delay_seconds={delay}")
    
    # Build decorator
    if params:
        decorator = f"@task({', '.join(params)})"
    else:
        decorator = "@task"
    
    lines.append(decorator)
    
    # Build function signature
    if task.args:
        args_str = ", ".join(task.args)
        lines.append(f"def {task.function_name}({args_str}):")
    else:
        lines.append(f"def {task.function_name}():")
    
    # Handle @task.bash specially
    if task.is_bash:
        if include_comments:
            lines.append("    # Converted from @task.bash")
            lines.append("    # The function returns a bash command string which is then executed")
        
        # Indent the original body
        body_lines = task.body_source.splitlines()
        for line in body_lines:
            lines.append(f"    {line}")
        
        # The original function returns a command string, we need to execute it
        # But since we can't know where the return is without parsing,
        # add a wrapper note
        lines.append("")
        lines.append("    # Note: In Airflow @task.bash, the returned string is executed as bash.")
        lines.append("    # In Prefect, use: subprocess.run(cmd, shell=True, check=True)")
    else:
        # Regular task - preserve body with proper indentation
        body_lines = task.body_source.splitlines()
        if not body_lines or (len(body_lines) == 1 and not body_lines[0].strip()):
            lines.append("    pass")
        else:
            for line in body_lines:
                lines.append(f"    {line}")
    
    return lines


def _convert_dag_to_flow(dag: DagInfo, include_comments: bool) -> list[str]:
    """Convert DAG function to flow."""
    lines = []
    
    # Build flow decorator
    params = [f'name="{dag.name}"']
    
    decorator = f"@flow({', '.join(params)})"
    lines.append(decorator)
    lines.append(f"def {dag.function_name}():")
    
    if include_comments:
        lines.append("    # Task orchestration converted from Airflow DAG")
    
    # Add task calls or pass
    has_calls = False
    if dag.tasks:
        for task in dag.tasks:
            if not task.args:
                lines.append(f"    {task.function_name}()")
                has_calls = True
            else:
                # Task needs arguments - add as comment
                lines.append(f"    # TODO: {task.function_name}({', '.join(task.args)})")
    
    # Always ensure there's a valid statement
    if not has_calls:
        lines.append("    pass")
    
    return lines
