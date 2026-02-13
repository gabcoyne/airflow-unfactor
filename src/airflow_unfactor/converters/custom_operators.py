"""Handle custom/unknown Airflow operators during conversion.

Custom operators are those NOT in the provider_mappings registry:
- Inline class definitions extending BaseOperator
- Imported operators from custom packages

This module detects them, extracts execute() method bodies where possible,
and generates stub @task functions with TODO comments and original context.
"""

import ast
import textwrap
from dataclasses import dataclass, field
from typing import Any

from airflow_unfactor.converters.provider_mappings import OPERATOR_MAPPINGS


# Core Airflow operators that are handled elsewhere (not custom)
CORE_OPERATORS = {
    "BaseOperator",
    "PythonOperator",
    "BashOperator",
    "BranchPythonOperator",
    "EmptyOperator",
    "DummyOperator",
    "ShortCircuitOperator",
    "PythonVirtualenvOperator",
    "ExternalPythonOperator",
}


@dataclass
class CustomOperatorInfo:
    """Information about a detected custom operator."""

    class_name: str
    task_id: str
    parameters: dict[str, Any] = field(default_factory=dict)
    execute_body: str = ""  # Body of execute() method if inline class
    import_path: str = ""  # e.g. "myproject.operators.MyOperator"
    line_number: int = 0
    is_inline_class: bool = False  # True if class defined in same file
    base_classes: list[str] = field(default_factory=list)


class CustomOperatorVisitor(ast.NodeVisitor):
    """AST visitor to detect unknown operators and extract execute() methods.

    Detects:
    1. Operator instantiations NOT in OPERATOR_MAPPINGS or CORE_OPERATORS
    2. Inline class definitions that extend BaseOperator
    """

    def __init__(self, source_lines: list[str]):
        self.source_lines = source_lines
        self.source = "\n".join(source_lines)
        self.custom_operators: list[CustomOperatorInfo] = []
        self.inline_classes: dict[str, CustomOperatorInfo] = {}  # class_name -> info
        self.imports: dict[str, str] = {}  # class_name -> import_path

    def visit_Import(self, node: ast.Import):
        """Track regular imports."""
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[-1]
            self.imports[name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track from-imports to identify custom operator sources."""
        module = node.module or ""
        for alias in node.names:
            name = alias.asname or alias.name
            if module:
                self.imports[name] = f"{module}.{alias.name}"
            else:
                self.imports[name] = alias.name
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """Detect inline custom operator class definitions."""
        # Check if this class extends an Operator
        base_names = []
        is_operator = False

        for base in node.bases:
            base_name = ast.unparse(base)
            base_names.append(base_name)
            if "Operator" in base_name:
                is_operator = True

        if is_operator:
            # Extract execute() method body
            execute_body = self._extract_execute_method(node)

            info = CustomOperatorInfo(
                class_name=node.name,
                task_id="",  # Will be filled when instantiated
                execute_body=execute_body,
                line_number=node.lineno,
                is_inline_class=True,
                base_classes=base_names,
            )
            self.inline_classes[node.name] = info

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Detect operator instantiations."""
        func_name = self._get_func_name(node)

        if func_name and self._is_custom_operator(func_name):
            info = self._extract_operator_info(node, func_name)
            if info:
                self.custom_operators.append(info)

        self.generic_visit(node)

    def _get_func_name(self, node: ast.Call) -> str:
        """Get the function/class name from a Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    def _is_custom_operator(self, name: str) -> bool:
        """Check if this operator name is NOT known (custom)."""
        # Must end with Operator
        if not name.endswith("Operator"):
            return False

        # Skip if in known mappings
        if name in OPERATOR_MAPPINGS:
            return False

        # Skip core operators (handled elsewhere)
        if name in CORE_OPERATORS:
            return False

        return True

    def _extract_operator_info(
        self, node: ast.Call, class_name: str
    ) -> CustomOperatorInfo | None:
        """Extract information about an operator instantiation."""
        params = {}
        task_id = "unknown_task"

        for kw in node.keywords:
            if kw.arg == "task_id" and isinstance(kw.value, ast.Constant):
                task_id = kw.value.value
            elif kw.arg:
                try:
                    params[kw.arg] = ast.literal_eval(kw.value)
                except (ValueError, TypeError):
                    params[kw.arg] = ast.unparse(kw.value)

        # Check if this is an inline class we already parsed
        if class_name in self.inline_classes:
            inline = self.inline_classes[class_name]
            return CustomOperatorInfo(
                class_name=class_name,
                task_id=task_id,
                parameters=params,
                execute_body=inline.execute_body,
                line_number=node.lineno,
                is_inline_class=True,
                base_classes=inline.base_classes,
            )

        # It's an imported custom operator
        import_path = self.imports.get(class_name, "")

        return CustomOperatorInfo(
            class_name=class_name,
            task_id=task_id,
            parameters=params,
            import_path=import_path,
            line_number=node.lineno,
            is_inline_class=False,
        )

    def _extract_execute_method(self, class_node: ast.ClassDef) -> str:
        """Extract the body of the execute() method from an operator class."""
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "execute":
                return self._get_method_body(item)
        return ""

    def _get_method_body(self, func_node: ast.FunctionDef) -> str:
        """Extract method body source code."""
        if not func_node.body:
            return "pass"

        # Get line range
        start_line = func_node.body[0].lineno - 1
        end_line = func_node.body[-1].end_lineno

        # Extract lines
        body_lines = self.source_lines[start_line:end_line]

        if not body_lines:
            return "pass"

        # Find minimum indentation
        non_empty = [line for line in body_lines if line.strip()]
        if not non_empty:
            return "pass"

        min_indent = min(len(line) - len(line.lstrip()) for line in non_empty)

        # Dedent
        dedented = [
            line[min_indent:] if len(line) > min_indent else line.lstrip()
            for line in body_lines
        ]

        return "\n".join(dedented)


def extract_custom_operators(dag_code: str) -> list[CustomOperatorInfo]:
    """Extract custom operators from DAG source code.

    Args:
        dag_code: Source code of the DAG file

    Returns:
        List of detected custom operators
    """
    try:
        tree = ast.parse(dag_code)
    except SyntaxError:
        return []

    source_lines = dag_code.splitlines()
    visitor = CustomOperatorVisitor(source_lines)
    visitor.visit(tree)

    return visitor.custom_operators


def generate_custom_operator_stub(
    info: CustomOperatorInfo,
    include_comments: bool = True,
) -> str:
    """Generate a stub @task function for a custom operator.

    Args:
        info: Custom operator information
        include_comments: Include TODO comments and context

    Returns:
        Generated Prefect task code
    """
    lines = []

    if include_comments:
        lines.append(f"# TODO: Manual conversion required for {info.class_name}")
        if info.import_path:
            lines.append(f"# Original import: {info.import_path}")
        if info.base_classes:
            lines.append(f"# Base class(es): {', '.join(info.base_classes)}")
        lines.append("")

    # Build decorator
    lines.append("@task")

    # Build function signature
    # Extract parameter hints for the function signature
    param_names = [k for k in info.parameters.keys() if k != "task_id"]

    if param_names:
        # Include parameters as function arguments for context
        lines.append(f"def {info.task_id}():")
    else:
        lines.append(f"def {info.task_id}():")

    # Add docstring with context
    lines.append(f'    """Converted from custom operator: {info.class_name}')
    lines.append("")
    lines.append("    TODO: Review and implement the operator logic.")
    if info.parameters:
        lines.append("")
        lines.append("    Original parameters:")
        for key, value in info.parameters.items():
            if key != "task_id":
                lines.append(f"        {key}: {value!r}")
    lines.append('    """')

    # If we have execute() body, include it as commented code
    if info.execute_body and include_comments:
        lines.append("    # Original execute() method body:")
        for body_line in info.execute_body.splitlines():
            lines.append(f"    # {body_line}")
        lines.append("")
        lines.append("    # TODO: Adapt the above logic for Prefect task")

    # Add placeholder implementation
    lines.append(f'    raise NotImplementedError("Convert {info.class_name} logic")')

    return "\n".join(lines)


def convert_custom_operators(
    dag_code: str,
    include_comments: bool = True,
) -> dict[str, Any]:
    """Convert all custom operators in a DAG file to Prefect task stubs.

    Args:
        dag_code: Source code of the DAG file
        include_comments: Include educational comments

    Returns:
        Dictionary with:
            - operators: List of CustomOperatorInfo
            - stubs: Generated task stub code
            - warnings: Conversion warnings
            - imports: Required imports
    """
    operators = extract_custom_operators(dag_code)

    if not operators:
        return {
            "operators": [],
            "stubs": "",
            "warnings": [],
            "imports": ["from prefect import task"],
        }

    warnings = []
    stub_lines = []

    # Add imports
    stub_lines.append("from prefect import task")
    stub_lines.append("")

    for op in operators:
        stub = generate_custom_operator_stub(op, include_comments)
        stub_lines.append(stub)
        stub_lines.append("")

        # Generate warnings
        if op.is_inline_class:
            if op.execute_body:
                warnings.append(
                    f"Custom operator '{op.class_name}' (task_id='{op.task_id}'): "
                    f"execute() method body extracted. Review self.* references."
                )
            else:
                warnings.append(
                    f"Custom operator '{op.class_name}' (task_id='{op.task_id}'): "
                    f"No execute() method found. Check parent class implementation."
                )
        else:
            if op.import_path:
                warnings.append(
                    f"Custom operator '{op.class_name}' (task_id='{op.task_id}'): "
                    f"Imported from '{op.import_path}'. Locate source to extract logic."
                )
            else:
                warnings.append(
                    f"Custom operator '{op.class_name}' (task_id='{op.task_id}'): "
                    f"Import path unknown. Search codebase for class definition."
                )

    return {
        "operators": operators,
        "stubs": "\n".join(stub_lines).rstrip(),
        "warnings": warnings,
        "imports": ["from prefect import task"],
    }


def is_known_operator(operator_name: str) -> bool:
    """Check if an operator name is known (in mappings or core).

    Args:
        operator_name: Name of the operator class

    Returns:
        True if the operator is known, False if custom
    """
    return operator_name in OPERATOR_MAPPINGS or operator_name in CORE_OPERATORS
