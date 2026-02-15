"""Convert Airflow PythonOperator to Prefect @task."""

import ast
import re
import textwrap
from dataclasses import dataclass, field


@dataclass
class XComPullInfo:
    """Information about an xcom_pull call."""

    task_ids: str | list[str] | None  # Can be string, list, or variable name
    key: str | None  # The key parameter if specified
    is_constant: bool  # Whether task_ids is a constant value
    source_text: str  # Original source text of the call
    line_number: int | None = None
    is_multi_task: bool = False  # Whether pulling from multiple tasks

    def __post_init__(self):
        """Set is_multi_task based on task_ids type."""
        if isinstance(self.task_ids, list) and len(self.task_ids) > 1:
            self.is_multi_task = True


@dataclass
class XComPushInfo:
    """Information about an xcom_push call."""

    key: str | None
    value_expr: str  # The expression being pushed
    source_text: str
    line_number: int | None = None


@dataclass
class XComUsage:
    """Comprehensive XCom usage information."""

    pulls: list[XComPullInfo] = field(default_factory=list)
    pushes: list[XComPushInfo] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_complex_patterns(self) -> bool:
        """Check if any patterns require manual review."""
        for pull in self.pulls:
            if not pull.is_constant:
                return True
            if pull.key is not None and pull.key != "return_value":
                return True
        return False

    @property
    def has_multi_task_pulls(self) -> bool:
        """Check if any pulls are from multiple tasks."""
        return any(pull.is_multi_task for pull in self.pulls)

    @property
    def simple_pull_task_ids(self) -> list[str]:
        """Get task_ids from simple constant pulls (single task only)."""
        result = []
        for pull in self.pulls:
            if pull.is_constant and isinstance(pull.task_ids, str):
                result.append(pull.task_ids)
        return result

    @property
    def multi_task_pull_ids(self) -> list[list[str]]:
        """Get task_ids from multi-task pulls."""
        result = []
        for pull in self.pulls:
            if pull.is_multi_task and isinstance(pull.task_ids, list):
                result.append(pull.task_ids)
        return result

    @property
    def all_pull_task_ids(self) -> list[str]:
        """Get all task_ids from all pulls (flattened)."""
        result = []
        for pull in self.pulls:
            if pull.is_constant:
                if isinstance(pull.task_ids, str):
                    result.append(pull.task_ids)
                elif isinstance(pull.task_ids, list):
                    result.extend(pull.task_ids)
        return result


@dataclass
class ExtractedFunction:
    """Extracted function information from PythonOperator."""

    name: str
    args: list[str]
    body: str
    docstring: str | None
    has_ti_param: bool  # Uses TaskInstance (ti) for XCom
    has_context: bool  # Uses **context or **kwargs
    xcom_pulls: list[str]  # task_ids that this function pulls from (legacy simple list)
    xcom_pushes: list[str]  # keys that this function pushes (legacy simple list)
    xcom_usage: XComUsage = field(default_factory=XComUsage)  # Detailed XCom info


class FunctionExtractor(ast.NodeVisitor):
    """Extract function definitions and their XCom usage."""

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.functions: dict[str, ExtractedFunction] = {}

    def _get_source_segment(self, node: ast.AST) -> str:
        """Get source code for an AST node."""
        try:
            return ast.get_source_segment(self.source_code, node) or ""
        except Exception:
            return ""

    def _extract_xcom_pull(self, call_node: ast.Call) -> XComPullInfo:
        """Extract detailed info from an xcom_pull call."""
        task_ids = None
        key = None
        is_constant = False
        source_text = self._get_source_segment(call_node)
        line_number = getattr(call_node, "lineno", None)

        # Check positional args first (ti.xcom_pull('task_id'))
        if call_node.args:
            first_arg = call_node.args[0]
            if isinstance(first_arg, ast.Constant):
                task_ids = first_arg.value
                is_constant = True
            elif isinstance(first_arg, ast.List):
                # List of task_ids
                task_ids = []
                is_constant = True
                for elt in first_arg.elts:
                    if isinstance(elt, ast.Constant):
                        task_ids.append(elt.value)
                    else:
                        is_constant = False
                        task_ids = self._get_source_segment(first_arg)
                        break
            else:
                # Variable or expression
                task_ids = self._get_source_segment(first_arg)
                is_constant = False

        # Check keyword args
        for keyword in call_node.keywords:
            if keyword.arg == "task_ids":
                if isinstance(keyword.value, ast.Constant):
                    task_ids = keyword.value.value
                    is_constant = True
                elif isinstance(keyword.value, ast.List):
                    task_ids = []
                    is_constant = True
                    for elt in keyword.value.elts:
                        if isinstance(elt, ast.Constant):
                            task_ids.append(elt.value)
                        else:
                            is_constant = False
                            task_ids = self._get_source_segment(keyword.value)
                            break
                else:
                    task_ids = self._get_source_segment(keyword.value)
                    is_constant = False
            elif keyword.arg == "key":
                if isinstance(keyword.value, ast.Constant):
                    key = keyword.value.value
                else:
                    key = self._get_source_segment(keyword.value)

        return XComPullInfo(
            task_ids=task_ids,
            key=key,
            is_constant=is_constant,
            source_text=source_text,
            line_number=line_number,
        )

    def _extract_xcom_push(self, call_node: ast.Call) -> XComPushInfo:
        """Extract detailed info from an xcom_push call."""
        key = None
        value_expr = ""
        source_text = self._get_source_segment(call_node)
        line_number = getattr(call_node, "lineno", None)

        for keyword in call_node.keywords:
            if keyword.arg == "key":
                if isinstance(keyword.value, ast.Constant):
                    key = keyword.value.value
                else:
                    key = self._get_source_segment(keyword.value)
            elif keyword.arg == "value":
                value_expr = self._get_source_segment(keyword.value)

        return XComPushInfo(
            key=key,
            value_expr=value_expr,
            source_text=source_text,
            line_number=line_number,
        )

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Extract function definition."""
        # Get arguments
        args = []
        has_ti_param = False
        has_context = False

        for arg in node.args.args:
            arg_name = arg.arg
            args.append(arg_name)
            if arg_name == "ti":
                has_ti_param = True

        # Check for **kwargs or **context
        if node.args.kwarg:
            has_context = True

        # Get docstring
        docstring = ast.get_docstring(node)

        # Get function body as source
        body_lines = []
        start_line = node.body[0].lineno - 1
        end_line = node.body[-1].end_lineno

        # Skip docstring if present
        if docstring and isinstance(node.body[0], ast.Expr):
            if len(node.body) > 1:
                start_line = node.body[1].lineno - 1
            else:
                body_lines = ["pass"]

        if not body_lines:
            body_lines = self.source_lines[start_line:end_line]

        # Dedent the body
        body = textwrap.dedent("\n".join(body_lines))

        # Find XCom usage with detailed extraction
        xcom_usage = XComUsage()
        xcom_pulls_simple = []  # Legacy simple list
        xcom_pushes_simple = []  # Legacy simple list

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if child.func.attr == "xcom_pull":
                        pull_info = self._extract_xcom_pull(child)
                        xcom_usage.pulls.append(pull_info)
                        # Also populate legacy simple list for backward compat
                        if pull_info.is_constant and isinstance(pull_info.task_ids, str):
                            xcom_pulls_simple.append(pull_info.task_ids)
                        elif pull_info.is_constant and isinstance(pull_info.task_ids, list):
                            xcom_pulls_simple.extend(pull_info.task_ids)
                    elif child.func.attr == "xcom_push":
                        push_info = self._extract_xcom_push(child)
                        xcom_usage.pushes.append(push_info)
                        if push_info.key:
                            xcom_pushes_simple.append(push_info.key)

        # Generate warnings for complex patterns
        for pull in xcom_usage.pulls:
            if not pull.is_constant:
                xcom_usage.warnings.append(
                    f"Dynamic task_ids in xcom_pull at line {pull.line_number}: {pull.source_text}. "
                    "This requires manual conversion - task_ids cannot be resolved statically."
                )
            if pull.is_multi_task:
                xcom_usage.warnings.append(
                    f"Multi-task xcom_pull at line {pull.line_number}: pulling from {pull.task_ids}. "
                    "Each task's result is now a separate function parameter."
                )
            if pull.key and pull.key != "return_value":
                xcom_usage.warnings.append(
                    f"Custom key '{pull.key}' in xcom_pull at line {pull.line_number}. "
                    "Prefect tasks return single values - consider restructuring data."
                )

        self.functions[node.name] = ExtractedFunction(
            name=node.name,
            args=args,
            body=body,
            docstring=docstring,
            has_ti_param=has_ti_param,
            has_context=has_context,
            xcom_pulls=xcom_pulls_simple,
            xcom_pushes=xcom_pushes_simple,
            xcom_usage=xcom_usage,
        )

        self.generic_visit(node)


def extract_functions(source_code: str) -> dict[str, ExtractedFunction]:
    """Extract all function definitions from source code."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return {}
    
    extractor = FunctionExtractor(source_code)
    extractor.visit(tree)
    return extractor.functions


@dataclass
class PythonOperatorConversionResult:
    """Result of PythonOperator conversion."""

    code: str
    warnings: list[str] = field(default_factory=list)
    xcom_usage: XComUsage | None = None


def convert_python_operator(
    task_id: str,
    python_callable: str,
    functions: dict[str, ExtractedFunction],
    op_kwargs: dict | None = None,
    include_comments: bool = True,
) -> PythonOperatorConversionResult:
    """Convert a PythonOperator to a Prefect @task.

    Args:
        task_id: Airflow task ID
        python_callable: Name of the callable function
        functions: Extracted function definitions
        op_kwargs: Operator keyword arguments
        include_comments: Include educational comments

    Returns:
        PythonOperatorConversionResult with code, warnings, and xcom info
    """
    lines = []
    warnings = []

    func = functions.get(python_callable)

    if func:
        xcom_usage = func.xcom_usage

        # Add warnings for complex XCom patterns
        if xcom_usage.has_complex_patterns:
            warnings.append(
                f"Function '{python_callable}' has complex XCom patterns that require manual review."
            )

        # We have the actual function - convert it
        if include_comments and (func.has_ti_param or func.xcom_pulls):
            lines.append("# ✨ Prefect Advantage: Direct Data Passing")
            lines.append(
                "# Original function used ti.xcom_pull() - now data flows directly as parameters."
            )
            lines.append("")

        # Add warning comments for complex patterns
        if include_comments and xcom_usage.has_complex_patterns:
            lines.append("# ⚠️ WARNING: Complex XCom patterns detected - manual review required:")
            for warning in xcom_usage.warnings:
                lines.append(f"#   - {warning}")
            lines.append("")

        # Build new function signature
        new_args = []
        for arg in func.args:
            if arg == "ti":
                # Replace ti with actual data parameters from all pulls
                # Handle simple single-task pulls
                for pull_task in xcom_usage.simple_pull_task_ids:
                    safe_name = pull_task.replace("-", "_").replace(" ", "_")
                    new_args.append(f"{safe_name}_data")
                # Handle multi-task pulls - add parameter for each task
                for pull in xcom_usage.pulls:
                    if pull.is_multi_task and isinstance(pull.task_ids, list):
                        for task_id in pull.task_ids:
                            safe_name = task_id.replace("-", "_").replace(" ", "_")
                            if f"{safe_name}_data" not in new_args:
                                new_args.append(f"{safe_name}_data")
            elif arg not in ("context", "kwargs", "ds", "execution_date"):
                new_args.append(arg)

        # Add parameters for XCom pulls if not already captured
        if xcom_usage.all_pull_task_ids and not func.has_ti_param:
            for pull_task in xcom_usage.all_pull_task_ids:
                safe_name = pull_task.replace("-", "_").replace(" ", "_")
                if f"{safe_name}_data" not in new_args:
                    new_args.append(f"{safe_name}_data")

        lines.append("@task")

        args_str = ", ".join(new_args) if new_args else ""
        lines.append(f"def {task_id}({args_str}):")

        # Add docstring
        if func.docstring:
            lines.append(f'    """{func.docstring}"""')
        else:
            lines.append(f'    """Converted from PythonOperator: {python_callable}."""')

        # Convert the body
        converted_body, body_warnings = _convert_function_body(
            func.body, func.xcom_pulls, xcom_usage
        )
        warnings.extend(body_warnings)

        # Indent the body
        for line in converted_body.splitlines():
            lines.append(f"    {line}" if line.strip() else "")

    else:
        # No function found - generate a stub
        xcom_usage = None
        lines.append("@task")
        lines.append(f"def {task_id}():")
        lines.append(f'    """Converted from PythonOperator: {python_callable}."""')
        lines.append(f"    # TODO: Implement - original callable '{python_callable}' not found")
        lines.append("    pass")
        warnings.append(f"Function '{python_callable}' not found - generated stub requires implementation")

    lines.append("")
    return PythonOperatorConversionResult(
        code="\n".join(lines),
        warnings=warnings,
        xcom_usage=xcom_usage if func else None,
    )


def _convert_function_body(
    body: str, xcom_pulls: list[str], xcom_usage: XComUsage | None = None
) -> tuple[str, list[str]]:
    """Convert function body, replacing XCom calls with direct references.

    Args:
        body: Original function body
        xcom_pulls: List of task_ids this function pulls from (simple list)
        xcom_usage: Detailed XCom usage info (optional, for better conversion)

    Returns:
        Tuple of (converted body, list of warnings)
    """
    converted = body
    warnings = []

    # Use detailed xcom_usage if available
    if xcom_usage:
        # Handle xcom_pull replacements
        for pull in xcom_usage.pulls:
            if pull.is_constant and isinstance(pull.task_ids, str):
                safe_name = pull.task_ids.replace("-", "_").replace(" ", "_")
                replacement = f"{safe_name}_data"

                # Replace the entire xcom_pull call
                if pull.source_text:
                    converted = converted.replace(pull.source_text, replacement)
            elif pull.is_constant and isinstance(pull.task_ids, list):
                # List of task_ids - generate dict comprehension or tuple
                if len(pull.task_ids) == 1:
                    # Single item in list - treat as simple case
                    safe_name = pull.task_ids[0].replace("-", "_").replace(" ", "_")
                    replacement = f"{safe_name}_data"
                else:
                    # Multiple task_ids - generate dict/tuple of results
                    safe_names = [
                        tid.replace("-", "_").replace(" ", "_") for tid in pull.task_ids
                    ]
                    # Generate a dict with task_id keys for easy access
                    dict_items = ", ".join(
                        f'"{tid}": {safe}_data'
                        for tid, safe in zip(pull.task_ids, safe_names, strict=False)
                    )
                    replacement = "{" + dict_items + "}"
                    warnings.append(
                        f"Multi-task xcom_pull converted to dict: {pull.source_text} -> {replacement}. "
                        "Access individual results via result['task_id']."
                    )

                if pull.source_text:
                    converted = converted.replace(pull.source_text, replacement)
            else:
                # Dynamic task_ids
                warnings.append(
                    f"Dynamic xcom_pull requires manual conversion: {pull.source_text}"
                )
                if pull.source_text:
                    converted = converted.replace(
                        pull.source_text,
                        f"# TODO: Dynamic xcom_pull - {pull.source_text}",
                    )

        # Handle xcom_push replacements
        for push in xcom_usage.pushes:
            if push.value_expr:
                # Replace with return statement
                if push.source_text:
                    converted = converted.replace(push.source_text, f"return {push.value_expr}")
            else:
                warnings.append(f"Could not extract value from xcom_push: {push.source_text}")
                if push.source_text:
                    converted = converted.replace(
                        push.source_text,
                        f"# TODO: Convert xcom_push to return - {push.source_text}",
                    )

        # Extend warnings with any detected by the extractor
        warnings.extend(xcom_usage.warnings)

    else:
        # Fallback to simple string replacement (legacy behavior)
        for pull_task in xcom_pulls:
            safe_name = pull_task.replace("-", "_").replace(" ", "_")
            # Handle various xcom_pull patterns with regex for flexibility
            patterns = [
                # ti.xcom_pull(task_ids='xxx') or ti.xcom_pull(task_ids="xxx")
                r"ti\.xcom_pull\s*\(\s*task_ids\s*=\s*['\"]" + re.escape(pull_task) + r"['\"]\s*\)",
                # ti.xcom_pull('xxx') or ti.xcom_pull("xxx")
                r"ti\.xcom_pull\s*\(\s*['\"]" + re.escape(pull_task) + r"['\"]\s*\)",
                # context['ti'].xcom_pull(...)
                r"context\s*\[\s*['\"]ti['\"]\s*\]\.xcom_pull\s*\(\s*task_ids\s*=\s*['\"]"
                + re.escape(pull_task)
                + r"['\"]\s*\)",
                # kwargs['ti'].xcom_pull(...)
                r"kwargs\s*\[\s*['\"]ti['\"]\s*\]\.xcom_pull\s*\(\s*task_ids\s*=\s*['\"]"
                + re.escape(pull_task)
                + r"['\"]\s*\)",
            ]
            for pattern in patterns:
                converted = re.sub(pattern, f"{safe_name}_data", converted, flags=re.MULTILINE)

        # Handle xcom_push with more flexible regex
        if "xcom_push" in converted:
            # Pattern to match xcom_push with value= parameter (handles multiline)
            push_pattern = r"(?:ti|context\s*\[\s*['\"]ti['\"]\s*\]|kwargs\s*\[\s*['\"]ti['\"]\s*\])\.xcom_push\s*\([^)]*value\s*=\s*([^,\)]+)[^)]*\)"
            matches = list(re.finditer(push_pattern, converted, re.MULTILINE | re.DOTALL))

            for match in reversed(matches):  # Reverse to preserve positions
                value = match.group(1).strip()
                converted = converted[: match.start()] + f"return {value}" + converted[match.end() :]

            # If there are still xcom_push calls, warn
            if "xcom_push" in converted:
                warnings.append(
                    "Some xcom_push calls could not be automatically converted. Manual review required."
                )
                # Add TODO comment for remaining
                converted = re.sub(
                    r"(.*\.xcom_push\s*\([^)]*\))",
                    r"# TODO: Convert to return statement\n    # \1",
                    converted,
                )

    return converted, warnings
