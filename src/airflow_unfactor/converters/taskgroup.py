"""Convert Airflow TaskGroups to Prefect subflows.

TaskGroups in Airflow provide visual grouping and organization of tasks. In Prefect,
the equivalent pattern is a subflow - a flow called from within another flow.

Key conversions:
- @task_group decorated functions -> @flow decorated functions (subflows)
- TaskGroup context managers -> @flow decorated functions
- TaskGroup.expand() -> Wrapper @task that calls the subflow in a loop

Educational context:
TaskGroups are one of the cleanest patterns to convert because Prefect's subflows
provide the same organizational benefits plus:
- Native retry and error handling at the subflow level
- Better observability (each subflow run is tracked separately)
- Natural data passing between parent and child flows
"""

import ast
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskGroupInfo:
    """Information about a detected TaskGroup."""

    # The name/group_id of the TaskGroup
    name: str

    # The function name (for @task_group) or variable name (for context manager)
    function_name: str

    # Tasks defined within this TaskGroup
    tasks: list[str] = field(default_factory=list)

    # Whether .expand() is called on this TaskGroup
    has_expand: bool = False

    # Parameters passed to .expand() if present
    expand_params: dict[str, str] = field(default_factory=dict)

    # Source line number
    line_number: int = 0

    # Whether this is from @task_group decorator (True) or context manager (False)
    is_decorator: bool = True

    # Function arguments (for @task_group decorated functions)
    args: list[str] = field(default_factory=list)

    # The body source code
    body_source: str = ""

    # Decorator parameters like group_id, tooltip, etc.
    decorator_params: dict[str, Any] = field(default_factory=dict)


class TaskGroupVisitor(ast.NodeVisitor):
    """AST visitor to detect TaskGroup patterns.

    Detects both:
    - @task_group decorated functions
    - `with TaskGroup("name") as group:` context manager patterns
    """

    def __init__(self, source_lines: list[str]):
        self.source_lines = source_lines
        self.source = "\n".join(source_lines)
        self.task_groups: list[TaskGroupInfo] = []
        self._expand_calls: dict[str, dict[str, str]] = {}  # func_name -> expand params

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Check for @task_group decorated functions."""
        for decorator in node.decorator_list:
            if self._is_task_group_decorator(decorator):
                group_info = self._extract_task_group_from_decorator(node, decorator)
                self.task_groups.append(group_info)
                # Visit children to find nested tasks
                self.generic_visit(node)
                return

        self.generic_visit(node)

    def visit_With(self, node: ast.With):
        """Check for `with TaskGroup(...) as group:` patterns."""
        for item in node.items:
            if self._is_task_group_context(item.context_expr):
                group_info = self._extract_task_group_from_context(node, item)
                if group_info:
                    self.task_groups.append(group_info)
                    # Visit children to find nested tasks
                    self.generic_visit(node)
                    return

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Detect .expand() calls on TaskGroup functions."""
        if isinstance(node.func, ast.Attribute) and node.func.attr == "expand":
            # Get the name of what's being expanded
            func_name = self._get_callee_name(node.func.value)
            if func_name:
                # Extract expand parameters
                expand_params = {}
                for kw in node.keywords:
                    if kw.arg:
                        expand_params[kw.arg] = ast.unparse(kw.value)
                self._expand_calls[func_name] = expand_params

        self.generic_visit(node)

    def _is_task_group_decorator(self, decorator: ast.expr) -> bool:
        """Check if decorator is @task_group or @task_group(...)."""
        dec_str = ast.unparse(decorator)
        return dec_str == "task_group" or dec_str.startswith("task_group(")

    def _is_task_group_context(self, expr: ast.expr) -> bool:
        """Check if expression is TaskGroup(...)."""
        if isinstance(expr, ast.Call):
            func_name = self._get_func_name(expr)
            return func_name == "TaskGroup"
        return False

    def _get_func_name(self, node: ast.expr) -> str:
        """Get the function name from a call expression."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        elif isinstance(node, ast.Call):
            return self._get_func_name(node.func)
        return ""

    def _get_callee_name(self, node: ast.expr) -> str:
        """Get the name of what's being called (for method chains)."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            return self._get_func_name(node.func)
        return ""

    def _extract_task_group_from_decorator(
        self, node: ast.FunctionDef, decorator: ast.expr
    ) -> TaskGroupInfo:
        """Extract TaskGroup info from @task_group decorated function."""
        params = self._extract_decorator_params(decorator)

        # Get group_id from params or use function name
        group_id = params.pop("group_id", node.name)

        # Get function arguments
        args = [arg.arg for arg in node.args.args]

        # Extract tasks from function body
        tasks = self._extract_tasks_from_body(node)

        return TaskGroupInfo(
            name=group_id,
            function_name=node.name,
            tasks=tasks,
            has_expand=False,  # Will be updated in finalize()
            expand_params={},  # Will be updated in finalize()
            line_number=node.lineno,
            is_decorator=True,
            args=args,
            body_source=self._get_function_body(node),
            decorator_params=params,
        )

    def _extract_task_group_from_context(
        self, with_node: ast.With, item: ast.withitem
    ) -> TaskGroupInfo | None:
        """Extract TaskGroup info from context manager pattern."""
        call = item.context_expr
        if not isinstance(call, ast.Call):
            return None

        # Get the variable name (as group:)
        var_name = ""
        if isinstance(item.optional_vars, ast.Name):
            var_name = item.optional_vars.id

        # Extract parameters from TaskGroup call
        params = {}
        group_id = var_name  # Default to variable name

        # First positional arg is often the group_id
        if call.args:
            try:
                group_id = ast.literal_eval(call.args[0])
            except (ValueError, TypeError):
                group_id = ast.unparse(call.args[0])

        for kw in call.keywords:
            if kw.arg == "group_id":
                try:
                    group_id = ast.literal_eval(kw.value)
                except (ValueError, TypeError):
                    group_id = ast.unparse(kw.value)
            elif kw.arg:
                try:
                    params[kw.arg] = ast.literal_eval(kw.value)
                except (ValueError, TypeError):
                    params[kw.arg] = ast.unparse(kw.value)

        # Extract tasks from the with block body
        tasks = self._extract_tasks_from_statements(with_node.body)

        return TaskGroupInfo(
            name=group_id,
            function_name=var_name or group_id,
            tasks=tasks,
            has_expand=False,
            expand_params={},
            line_number=with_node.lineno,
            is_decorator=False,
            args=[],
            body_source=self._get_statements_source(with_node.body),
            decorator_params=params,
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

    def _extract_tasks_from_body(self, node: ast.FunctionDef) -> list[str]:
        """Extract task function names from a function body."""
        tasks = []
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef):
                # Check if it's a @task decorated function
                for dec in stmt.decorator_list:
                    dec_str = ast.unparse(dec)
                    if dec_str.startswith("task"):
                        tasks.append(stmt.name)
                        break
        return tasks

    def _extract_tasks_from_statements(self, stmts: list[ast.stmt]) -> list[str]:
        """Extract task names from a list of statements."""
        tasks = []
        for stmt in stmts:
            # Look for task assignments or calls
            if isinstance(stmt, ast.Assign):
                if isinstance(stmt.value, ast.Call):
                    # Check if it's an Operator call
                    func_name = self._get_func_name(stmt.value)
                    if "Operator" in func_name or func_name.endswith("Task"):
                        if stmt.targets and isinstance(stmt.targets[0], ast.Name):
                            tasks.append(stmt.targets[0].id)
            elif isinstance(stmt, ast.Expr):
                # Task calls without assignment
                if isinstance(stmt.value, ast.Call):
                    func_name = self._get_func_name(stmt.value)
                    if func_name:
                        tasks.append(func_name)
        return tasks

    def _get_function_body(self, node: ast.FunctionDef) -> str:
        """Extract function body source code."""
        if not node.body:
            return "pass"

        start_line = node.body[0].lineno - 1
        end_line = node.body[-1].end_lineno

        body_lines = self.source_lines[start_line:end_line]
        if not body_lines:
            return "pass"

        # Dedent
        non_empty = [line for line in body_lines if line.strip()]
        if not non_empty:
            return "pass"

        min_indent = min(len(line) - len(line.lstrip()) for line in non_empty)
        dedented = [
            line[min_indent:] if len(line) > min_indent else line.lstrip() for line in body_lines
        ]

        return "\n".join(dedented)

    def _get_statements_source(self, stmts: list[ast.stmt]) -> str:
        """Extract source code for a list of statements."""
        if not stmts:
            return "pass"

        start_line = stmts[0].lineno - 1
        end_line = stmts[-1].end_lineno

        body_lines = self.source_lines[start_line:end_line]
        if not body_lines:
            return "pass"

        non_empty = [line for line in body_lines if line.strip()]
        if not non_empty:
            return "pass"

        min_indent = min(len(line) - len(line.lstrip()) for line in non_empty)
        dedented = [
            line[min_indent:] if len(line) > min_indent else line.lstrip() for line in body_lines
        ]

        return "\n".join(dedented)

    def finalize(self):
        """Update TaskGroups with expand information after full traversal."""
        for group in self.task_groups:
            if group.function_name in self._expand_calls:
                group.has_expand = True
                group.expand_params = self._expand_calls[group.function_name]


def extract_task_groups(dag_code: str) -> list[TaskGroupInfo]:
    """Extract TaskGroup patterns from DAG source code.

    Args:
        dag_code: Source code of the DAG file

    Returns:
        List of detected TaskGroup patterns
    """
    try:
        tree = ast.parse(dag_code)
    except SyntaxError:
        return []

    source_lines = dag_code.splitlines()
    visitor = TaskGroupVisitor(source_lines)
    visitor.visit(tree)
    visitor.finalize()

    return visitor.task_groups


def convert_task_group(info: TaskGroupInfo, include_comments: bool = True) -> tuple[str, list[str]]:
    """Convert a TaskGroup to Prefect subflow code.

    Args:
        info: TaskGroup information
        include_comments: Include educational comments

    Returns:
        Tuple of (generated_code, warnings)
    """
    warnings = []
    lines = []

    if include_comments:
        lines.append(f"# Converted from Airflow TaskGroup: {info.name}")
        lines.append("# ")
        lines.append(
            "# In Prefect, subflows provide the same organizational benefits as TaskGroups,"
        )
        lines.append("# plus better observability and native retry handling at the subflow level.")
        lines.append("")

    # Generate the subflow
    if info.has_expand:
        # TaskGroup with .expand() needs a wrapper task
        lines.extend(_generate_expanded_task_group(info, include_comments, warnings))
    else:
        # Regular TaskGroup -> subflow
        lines.extend(_generate_subflow(info, include_comments, warnings))

    return "\n".join(lines), warnings


def _generate_subflow(
    info: TaskGroupInfo, include_comments: bool, warnings: list[str]
) -> list[str]:
    """Generate a simple subflow from TaskGroup."""
    lines = []

    # Build decorator parameters
    params = [f'name="{info.name}"']

    # Build the decorator
    decorator = f"@flow({', '.join(params)})"
    lines.append(decorator)

    # Build function signature
    if info.args:
        args_str = ", ".join(info.args)
        lines.append(f"def {info.function_name}({args_str}):")
    else:
        lines.append(f"def {info.function_name}():")

    # Add docstring
    lines.append(f'    """Subflow converted from TaskGroup \'{info.name}\'."""')

    # Add body or placeholder
    if info.body_source and info.body_source.strip() != "pass":
        if include_comments:
            lines.append("    # Original TaskGroup body:")
        for line in info.body_source.splitlines():
            lines.append(f"    {line}")
    else:
        lines.append("    pass")

    if not info.is_decorator:
        warnings.append(
            f"TaskGroup '{info.name}' used context manager pattern. "
            "Review the generated subflow structure."
        )

    return lines


def _generate_expanded_task_group(
    info: TaskGroupInfo, include_comments: bool, warnings: list[str]
) -> list[str]:
    """Generate code for TaskGroup with .expand() call.

    Airflow's TaskGroup.expand() creates multiple instances of the group.
    In Prefect, we generate:
    1. The subflow (same as regular TaskGroup)
    2. A wrapper @task that calls the subflow for each item
    """
    lines = []

    if include_comments:
        lines.append("# TaskGroup.expand() Pattern")
        lines.append("# ")
        lines.append("# In Airflow, TaskGroup.expand() creates multiple task group instances.")
        lines.append("# In Prefect, we use a wrapper task that calls the subflow for each item.")
        lines.append("# This preserves the same execution semantics with better observability.")
        lines.append("")

    # First, generate the subflow
    subflow_lines = _generate_subflow(info, include_comments=False, warnings=warnings)
    lines.extend(subflow_lines)
    lines.append("")

    # Then generate the wrapper task
    expand_param_names = list(info.expand_params.keys())
    expand_param_values = list(info.expand_params.values())

    if expand_param_names:
        wrapper_name = f"{info.function_name}_expanded"
        primary_param = expand_param_names[0]
        primary_value = expand_param_values[0]

        if include_comments:
            lines.append(f"# Wrapper task to map over {primary_value}")

        lines.append("@task")
        lines.append(f"def {wrapper_name}({primary_param}):")
        lines.append(f'    """Wrapper to run {info.function_name} subflow for each item."""')
        lines.append(f"    return {info.function_name}({primary_param})")
        lines.append("")

        if include_comments:
            lines.append(f"# Usage: {wrapper_name}.map({primary_value})")
            lines.append(
                f"# This replaces: {info.function_name}.expand({primary_param}={primary_value})"
            )
    else:
        warnings.append(f"TaskGroup '{info.name}' uses .expand() but no parameters were detected.")

    warnings.append(
        f"TaskGroup.expand() for '{info.name}' converted to wrapper task pattern. "
        "Call the wrapper with .map() instead of .expand()."
    )

    return lines


def convert_all_task_groups(
    dag_code: str,
    include_comments: bool = True,
) -> dict[str, Any]:
    """Convert all TaskGroups in a DAG file.

    Args:
        dag_code: Source code of the DAG file
        include_comments: Include educational comments

    Returns:
        Dictionary with conversions, summary, and warnings
    """
    task_groups = extract_task_groups(dag_code)

    if not task_groups:
        return {
            "conversions": [],
            "summary": "No TaskGroup patterns detected",
            "warnings": [],
            "prefect_code": "",
        }

    conversions = []
    all_warnings = []
    all_code = []

    for group in task_groups:
        code, warnings = convert_task_group(group, include_comments)
        conversions.append(
            {
                "task_group": group,
                "code": code,
                "warnings": warnings,
            }
        )
        all_warnings.extend(warnings)
        all_code.append(code)

    # Build summary
    decorator_count = sum(1 for g in task_groups if g.is_decorator)
    context_count = len(task_groups) - decorator_count
    expand_count = sum(1 for g in task_groups if g.has_expand)

    summary_parts = [f"Converted {len(task_groups)} TaskGroup(s)"]
    if decorator_count:
        summary_parts.append(f"{decorator_count} @task_group decorator(s)")
    if context_count:
        summary_parts.append(f"{context_count} context manager(s)")
    if expand_count:
        summary_parts.append(f"{expand_count} with .expand()")

    return {
        "conversions": conversions,
        "summary": ": ".join(summary_parts),
        "warnings": all_warnings,
        "prefect_code": "\n\n".join(all_code),
    }
