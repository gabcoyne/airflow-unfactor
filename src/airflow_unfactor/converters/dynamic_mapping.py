"""Convert Airflow Dynamic Task Mapping to Prefect .map().

Airflow 2.3+ introduced dynamic task mapping with .expand(), .partial(), and
.expand_kwargs(). This converter detects these patterns and generates equivalent
Prefect code using the .map() method.

Key conversions:
- task.expand(iterable) -> task.map(iterable)
- task.partial(fixed=val).expand(iterable) -> Prefect functools.partial + .map()
- task.expand_kwargs(list_of_dicts) -> task.map(**dict unpacking)
"""

import ast
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MappingType(Enum):
    """Type of dynamic mapping pattern."""
    EXPAND = "expand"
    PARTIAL_EXPAND = "partial_expand"
    EXPAND_KWARGS = "expand_kwargs"


@dataclass
class DynamicMappingInfo:
    """Information about a detected dynamic mapping pattern."""

    # The type of mapping detected
    mapping_type: MappingType

    # The task or function being mapped
    task_name: str

    # The variable or expression being mapped over
    mapped_iterable: str

    # For .partial().expand(), the fixed parameters
    partial_params: dict[str, str] = field(default_factory=dict)

    # For .expand(), the keyword argument mappings
    expand_params: dict[str, str] = field(default_factory=dict)

    # Source line number for debugging/warnings
    line_number: int = 0

    # The variable this mapping is assigned to (if any)
    assigned_to: str = ""

    # Original source code for the expression
    original_source: str = ""

    # Any unsupported parameters that need warning
    unsupported_params: dict[str, str] = field(default_factory=dict)


@dataclass
class ConversionResult:
    """Result of converting dynamic mapping to Prefect code."""

    prefect_code: str
    warnings: list[str] = field(default_factory=list)


class DynamicMappingVisitor(ast.NodeVisitor):
    """AST visitor to detect dynamic task mapping patterns.

    Detects:
    - task.expand(arg=iterable)
    - task.partial(fixed=val).expand(arg=iterable)
    - task.expand_kwargs(list_of_dicts)
    """

    def __init__(self, source_lines: list[str]):
        self.source_lines = source_lines
        self.source = "\n".join(source_lines)
        self.mappings: list[DynamicMappingInfo] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        """Check assignments for dynamic mapping patterns."""
        if isinstance(node.value, ast.Call):
            mapping = self._check_for_mapping(node.value)
            if mapping:
                # Record what variable the mapping is assigned to
                if node.targets and isinstance(node.targets[0], ast.Name):
                    mapping.assigned_to = node.targets[0].id
                self.mappings.append(mapping)
        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> None:
        """Check standalone expressions for dynamic mapping patterns."""
        if isinstance(node.value, ast.Call):
            mapping = self._check_for_mapping(node.value)
            if mapping:
                self.mappings.append(mapping)
        self.generic_visit(node)

    def _check_for_mapping(self, call: ast.Call) -> DynamicMappingInfo | None:
        """Check if a call is a dynamic mapping pattern."""
        # Check for .expand() call
        if isinstance(call.func, ast.Attribute) and call.func.attr == "expand":
            return self._parse_expand(call)

        # Check for .expand_kwargs() call
        if isinstance(call.func, ast.Attribute) and call.func.attr == "expand_kwargs":
            return self._parse_expand_kwargs(call)

        return None

    def _parse_expand(self, call: ast.Call) -> DynamicMappingInfo | None:
        """Parse a .expand() call, checking for .partial() chain."""
        func = call.func
        if not isinstance(func, ast.Attribute):
            return None

        # Get expand parameters
        expand_params = {}
        unsupported_params = {}

        for kw in call.keywords:
            if kw.arg:
                value_str = ast.unparse(kw.value)
                # Check for map_index_template parameter
                if kw.arg == "map_index_template":
                    unsupported_params[kw.arg] = value_str
                else:
                    expand_params[kw.arg] = value_str

        # Check if this is task.partial().expand()
        if isinstance(func.value, ast.Call):
            inner_call = func.value
            if isinstance(inner_call.func, ast.Attribute) and inner_call.func.attr == "partial":
                return self._parse_partial_expand(inner_call, expand_params, unsupported_params, call.lineno)

        # Simple .expand() - get task name
        task_name = self._get_task_name(func.value)
        if not task_name:
            return None

        # Get the first (or primary) mapped iterable
        mapped_iterable = next(iter(expand_params.values()), "")

        return DynamicMappingInfo(
            mapping_type=MappingType.EXPAND,
            task_name=task_name,
            mapped_iterable=mapped_iterable,
            expand_params=expand_params,
            line_number=call.lineno,
            original_source=ast.unparse(call),
            unsupported_params=unsupported_params,
        )

    def _parse_partial_expand(
        self,
        partial_call: ast.Call,
        expand_params: dict[str, str],
        unsupported_params: dict[str, str],
        line_number: int,
    ) -> DynamicMappingInfo | None:
        """Parse a .partial().expand() chain."""
        # Get partial parameters
        partial_params = {}
        for kw in partial_call.keywords:
            if kw.arg:
                partial_params[kw.arg] = ast.unparse(kw.value)

        # Get task name from the partial call
        if not isinstance(partial_call.func, ast.Attribute):
            return None
        task_name = self._get_task_name(partial_call.func.value)
        if not task_name:
            return None

        # Get the mapped iterable
        mapped_iterable = next(iter(expand_params.values()), "")

        return DynamicMappingInfo(
            mapping_type=MappingType.PARTIAL_EXPAND,
            task_name=task_name,
            mapped_iterable=mapped_iterable,
            partial_params=partial_params,
            expand_params=expand_params,
            line_number=line_number,
            original_source=f"{task_name}.partial(...).expand(...)",
            unsupported_params=unsupported_params,
        )

    def _parse_expand_kwargs(self, call: ast.Call) -> DynamicMappingInfo | None:
        """Parse a .expand_kwargs() call."""
        func = call.func
        if not isinstance(func, ast.Attribute):
            return None

        task_name = self._get_task_name(func.value)
        if not task_name:
            return None

        # Get the argument (list of dicts)
        mapped_iterable = ""
        if call.args:
            mapped_iterable = ast.unparse(call.args[0])

        # Check for unsupported params
        unsupported_params = {}
        for kw in call.keywords:
            if kw.arg == "map_index_template":
                unsupported_params[kw.arg] = ast.unparse(kw.value)

        return DynamicMappingInfo(
            mapping_type=MappingType.EXPAND_KWARGS,
            task_name=task_name,
            mapped_iterable=mapped_iterable,
            line_number=call.lineno,
            original_source=ast.unparse(call),
            unsupported_params=unsupported_params,
        )

    def _get_task_name(self, node: ast.expr) -> str:
        """Extract task/function name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        elif isinstance(node, ast.Call):
            # Handle nested calls like task()(...)
            return self._get_task_name(node.func)
        return ""


def extract_dynamic_mapping(dag_code: str) -> list[DynamicMappingInfo]:
    """Extract dynamic mapping patterns from DAG source code.

    Args:
        dag_code: Source code of the DAG file

    Returns:
        List of detected dynamic mapping patterns
    """
    try:
        tree = ast.parse(dag_code)
    except SyntaxError:
        return []

    source_lines = dag_code.splitlines()
    visitor = DynamicMappingVisitor(source_lines)
    visitor.visit(tree)

    return visitor.mappings


def convert_dynamic_mapping(info: DynamicMappingInfo, include_comments: bool = True) -> ConversionResult:
    """Convert a dynamic mapping pattern to Prefect code.

    Args:
        info: Dynamic mapping information
        include_comments: Include educational comments

    Returns:
        ConversionResult with Prefect code and warnings
    """
    warnings = []
    lines = []

    # Check for unsupported parameters
    if "map_index_template" in info.unsupported_params:
        warnings.append(
            f"Line {info.line_number}: 'map_index_template' parameter has no Prefect equivalent. "
            "Prefect uses 0-based indices for mapped task naming automatically."
        )

    if info.mapping_type == MappingType.EXPAND:
        lines.extend(_convert_expand(info, include_comments))
    elif info.mapping_type == MappingType.PARTIAL_EXPAND:
        lines.extend(_convert_partial_expand(info, include_comments, warnings))
    elif info.mapping_type == MappingType.EXPAND_KWARGS:
        lines.extend(_convert_expand_kwargs(info, include_comments))

    return ConversionResult(
        prefect_code="\n".join(lines),
        warnings=warnings,
    )


def _convert_expand(info: DynamicMappingInfo, include_comments: bool) -> list[str]:
    """Convert simple .expand() to Prefect .map()."""
    lines = []

    if include_comments:
        lines.append(f"# Converted from Airflow dynamic task mapping: {info.task_name}.expand()")
        lines.append("# Prefect's .map() works similarly - iterates over the input")

    # Build the .map() call
    if len(info.expand_params) == 1:
        # Simple case: single parameter being mapped
        param_name, iterable = next(iter(info.expand_params.items()))
        assignment = f"{info.assigned_to} = " if info.assigned_to else ""
        lines.append(f"{assignment}{info.task_name}.map({iterable})")
    else:
        # Multiple parameters - need to handle differently
        # In Prefect, .map() maps over positional args
        # For keyword mapping, we'd need a different approach
        if include_comments:
            lines.append("# Note: Multiple expand params require unpacking")

        assignment = f"{info.assigned_to} = " if info.assigned_to else ""
        # Use the first iterable as the main mapping, others as keyword
        params = list(info.expand_params.items())
        first_param, first_iter = params[0]
        other_params = ", ".join(f"{k}={v}" for k, v in params[1:])

        if other_params:
            lines.append(f"{assignment}{info.task_name}.map({first_iter}, {other_params})")
        else:
            lines.append(f"{assignment}{info.task_name}.map({first_iter})")

    return lines


def _convert_partial_expand(
    info: DynamicMappingInfo,
    include_comments: bool,
    warnings: list[str],
) -> list[str]:
    """Convert .partial().expand() to Prefect pattern."""
    lines = []

    if include_comments:
        lines.append(f"# Converted from Airflow: {info.task_name}.partial(...).expand(...)")
        lines.append("# Prefect approach: Use functools.partial or pass fixed args to .map()")

    # Build the map call with fixed args
    fixed_args = ", ".join(f"{k}={v}" for k, v in info.partial_params.items())

    if info.expand_params:
        mapped_arg = next(iter(info.expand_params.values()), "items")
        assignment = f"{info.assigned_to} = " if info.assigned_to else ""

        if fixed_args:
            lines.append(f"{assignment}{info.task_name}.map({mapped_arg}, {fixed_args})")
        else:
            lines.append(f"{assignment}{info.task_name}.map({mapped_arg})")
    else:
        lines.append("# TODO: Review - no expand parameters found")
        lines.append(f"# {info.task_name}.map(...)")

    return lines


def _convert_expand_kwargs(info: DynamicMappingInfo, include_comments: bool) -> list[str]:
    """Convert .expand_kwargs() to Prefect pattern."""
    lines = []

    if include_comments:
        lines.append(f"# Converted from Airflow: {info.task_name}.expand_kwargs({info.mapped_iterable})")
        lines.append("# Prefect approach: Use a wrapper task or starmap pattern")

    # Generate helper function pattern
    lines.append("")
    lines.append("# Option 1: Use list comprehension with .submit()")
    assignment = f"{info.assigned_to} = " if info.assigned_to else "results = "
    lines.append(f"{assignment}[{info.task_name}.submit(**kwargs) for kwargs in {info.mapped_iterable}]")

    if include_comments:
        lines.append("")
        lines.append("# Option 2: Extract specific keys if structure is known")
        lines.append(f"# {info.task_name}.map(**{{k: [d[k] for d in {info.mapped_iterable}] for k in {info.mapped_iterable}[0]}})")

    return lines


def convert_all_dynamic_mappings(
    dag_code: str,
    include_comments: bool = True,
) -> dict[str, Any]:
    """Convert all dynamic mapping patterns in a DAG file.

    Args:
        dag_code: Source code of the DAG file
        include_comments: Include educational comments

    Returns:
        Dictionary with conversions, summary, and warnings
    """
    mappings = extract_dynamic_mapping(dag_code)

    if not mappings:
        return {
            "conversions": [],
            "summary": "No dynamic task mapping patterns detected",
            "warnings": [],
            "prefect_code": "",
        }

    conversions = []
    all_warnings = []
    all_code = []

    for mapping in mappings:
        result = convert_dynamic_mapping(mapping, include_comments)
        conversions.append({
            "mapping": mapping,
            "result": result,
        })
        all_warnings.extend(result.warnings)
        all_code.append(result.prefect_code)

    type_summary = ", ".join(
        f"{m.task_name} ({m.mapping_type.value})" for m in mappings
    )

    return {
        "conversions": conversions,
        "summary": f"Converted {len(mappings)} dynamic mapping(s): {type_summary}",
        "warnings": all_warnings,
        "prefect_code": "\n\n".join(all_code),
    }
