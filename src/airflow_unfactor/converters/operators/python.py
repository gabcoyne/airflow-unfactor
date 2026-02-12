"""Convert Airflow PythonOperator to Prefect @task."""

import ast
import textwrap
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class ExtractedFunction:
    """Extracted function information from PythonOperator."""
    name: str
    args: list[str]
    body: str
    docstring: Optional[str]
    has_ti_param: bool  # Uses TaskInstance (ti) for XCom
    has_context: bool   # Uses **context or **kwargs
    xcom_pulls: list[str]  # task_ids that this function pulls from
    xcom_pushes: list[str]  # keys that this function pushes


class FunctionExtractor(ast.NodeVisitor):
    """Extract function definitions and their XCom usage."""
    
    def __init__(self, source_code: str):
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.functions: dict[str, ExtractedFunction] = {}
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Extract function definition."""
        # Get arguments
        args = []
        has_ti_param = False
        has_context = False
        
        for arg in node.args.args:
            arg_name = arg.arg
            args.append(arg_name)
            if arg_name == 'ti':
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
        body = textwrap.dedent('\n'.join(body_lines))
        
        # Find XCom usage
        xcom_pulls = []
        xcom_pushes = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if child.func.attr == 'xcom_pull':
                        # Try to extract task_ids
                        for keyword in child.keywords:
                            if keyword.arg == 'task_ids' and isinstance(keyword.value, ast.Constant):
                                xcom_pulls.append(keyword.value.value)
                    elif child.func.attr == 'xcom_push':
                        for keyword in child.keywords:
                            if keyword.arg == 'key' and isinstance(keyword.value, ast.Constant):
                                xcom_pushes.append(keyword.value.value)
        
        self.functions[node.name] = ExtractedFunction(
            name=node.name,
            args=args,
            body=body,
            docstring=docstring,
            has_ti_param=has_ti_param,
            has_context=has_context,
            xcom_pulls=xcom_pulls,
            xcom_pushes=xcom_pushes,
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


def convert_python_operator(
    task_id: str,
    python_callable: str,
    functions: dict[str, ExtractedFunction],
    op_kwargs: Optional[dict] = None,
    include_comments: bool = True,
) -> str:
    """Convert a PythonOperator to a Prefect @task.
    
    Args:
        task_id: Airflow task ID
        python_callable: Name of the callable function
        functions: Extracted function definitions
        op_kwargs: Operator keyword arguments
        include_comments: Include educational comments
        
    Returns:
        Prefect task code as string
    """
    lines = []
    
    func = functions.get(python_callable)
    
    if func:
        # We have the actual function - convert it
        if include_comments and (func.has_ti_param or func.xcom_pulls):
            lines.append("# ✨ Prefect Advantage: Direct Data Passing")
            lines.append("# Original function used ti.xcom_pull() - now data flows directly as parameters.")
            lines.append("")
        
        # Build new function signature
        new_args = []
        for arg in func.args:
            if arg == 'ti':
                # Replace ti with actual data parameters
                for pull_task in func.xcom_pulls:
                    safe_name = pull_task.replace('-', '_').replace(' ', '_')
                    new_args.append(f"{safe_name}_data")
            elif arg not in ('context', 'kwargs', 'ds', 'execution_date'):
                new_args.append(arg)
        
        # Add parameters for XCom pulls if not already captured
        if func.xcom_pulls and not func.has_ti_param:
            for pull_task in func.xcom_pulls:
                safe_name = pull_task.replace('-', '_').replace(' ', '_')
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
        converted_body = _convert_function_body(func.body, func.xcom_pulls)
        
        # Indent the body
        for line in converted_body.splitlines():
            lines.append(f"    {line}" if line.strip() else "")
            
    else:
        # No function found - generate a stub
        lines.append("@task")
        lines.append(f"def {task_id}():")
        lines.append(f'    """Converted from PythonOperator: {python_callable}."""')
        lines.append(f"    # TODO: Implement - original callable '{python_callable}' not found")
        lines.append("    pass")
    
    lines.append("")
    return "\n".join(lines)


def _convert_function_body(body: str, xcom_pulls: list[str]) -> str:
    """Convert function body, replacing XCom calls with direct references.
    
    Args:
        body: Original function body
        xcom_pulls: List of task_ids this function pulls from
        
    Returns:
        Converted function body
    """
    converted = body
    
    # Replace ti.xcom_pull(task_ids='xxx') with xxx_data
    for pull_task in xcom_pulls:
        safe_name = pull_task.replace('-', '_').replace(' ', '_')
        # Handle various xcom_pull patterns
        patterns = [
            f"ti.xcom_pull(task_ids='{pull_task}')",
            f"ti.xcom_pull(task_ids=\"{pull_task}\")",
            f"ti.xcom_pull('{pull_task}')",
            f"ti.xcom_pull(\"{pull_task}\")",
        ]
        for pattern in patterns:
            converted = converted.replace(pattern, f"{safe_name}_data")
    
    # Remove ti.xcom_push calls - replace with return
    # This is a simplification; complex cases may need manual review
    if "ti.xcom_push" in converted:
        # Try to extract the value being pushed
        import re
        push_pattern = r"ti\.xcom_push\([^)]*value=([^,\)]+)[^)]*\)"
        match = re.search(push_pattern, converted)
        if match:
            value = match.group(1).strip()
            converted = re.sub(push_pattern, f"return {value}", converted)
        else:
            # Can't extract cleanly, add a comment
            converted = converted.replace(
                "ti.xcom_push",
                "# TODO: Convert xcom_push to return\n    # ti.xcom_push"
            )
    
    return converted
