"""Validate DAG to flow conversions.

This module provides behavioral equivalence checking between an original
Airflow DAG and a converted Prefect flow. It compares:
- Task counts (excluding DummyOperator/EmptyOperator)
- Dependency graph structure (isomorphism)
- Data flow patterns (XCom to return/parameter mapping)
"""

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TaskInfo:
    """Information about a task in a DAG or flow."""

    name: str
    task_type: str  # "operator", "task", "sensor", etc.
    line: int
    has_return: bool = False
    parameters: list[str] = field(default_factory=list)
    upstream: list[str] = field(default_factory=list)
    downstream: list[str] = field(default_factory=list)


@dataclass
class GraphInfo:
    """Graph structure extracted from code."""

    tasks: dict[str, TaskInfo] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)  # (upstream, downstream)
    xcom_pushes: list[dict[str, str]] = field(default_factory=list)
    xcom_pulls: list[dict[str, str]] = field(default_factory=list)

    @property
    def task_count(self) -> int:
        return len(self.tasks)

    @property
    def edge_count(self) -> int:
        return len(self.edges)


@dataclass
class ValidationIssue:
    """A specific validation issue found."""

    severity: str  # "error", "warning", "info"
    category: str  # "task_count", "dependency", "data_flow"
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    """Complete validation report."""

    is_valid: bool
    task_count_match: bool
    dependency_preserved: bool
    data_flow_preserved: bool
    confidence_score: int  # 0-100
    issues: list[ValidationIssue] = field(default_factory=list)
    dag_summary: dict[str, Any] = field(default_factory=dict)
    flow_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "task_count_match": self.task_count_match,
            "dependency_preserved": self.dependency_preserved,
            "data_flow_preserved": self.data_flow_preserved,
            "confidence_score": self.confidence_score,
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "message": i.message,
                    "details": i.details,
                }
                for i in self.issues
            ],
            "dag_summary": self.dag_summary,
            "flow_summary": self.flow_summary,
        }


# Operators that don't need Prefect equivalents
IGNORABLE_OPERATORS = {"DummyOperator", "EmptyOperator"}


class DAGGraphExtractor(ast.NodeVisitor):
    """Extract task graph from Airflow DAG code."""

    def __init__(self):
        self.graph = GraphInfo()
        self.task_vars: dict[str, str] = {}  # variable name -> task_id
        self.current_function: str | None = None

    def visit_Assign(self, node: ast.Assign):
        """Track operator assignments: task = SomeOperator(task_id='x')."""
        if isinstance(node.value, ast.Call):
            func_name = self._get_func_name(node.value)
            task_id = self._extract_task_id(node.value)

            if task_id and self._is_operator(func_name):
                # Map variable to task_id
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.task_vars[target.id] = task_id

                # Skip ignorable operators
                if func_name not in IGNORABLE_OPERATORS:
                    self.graph.tasks[task_id] = TaskInfo(
                        name=task_id,
                        task_type=func_name,
                        line=node.lineno,
                    )
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        """Handle >> and << dependency operators."""
        if isinstance(node.op, ast.RShift):
            self._add_dependencies(node.left, node.right)
        elif isinstance(node.op, ast.LShift):
            self._add_dependencies(node.right, node.left)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Detect XCom push/pull and set_upstream/set_downstream."""
        func_name = self._get_func_name(node)

        if func_name == "xcom_push":
            key = self._extract_kwarg(node, "key") or "return_value"
            self.graph.xcom_pushes.append({
                "key": key,
                "line": node.lineno,
            })
        elif func_name == "xcom_pull":
            task_ids = self._extract_kwarg(node, "task_ids")
            key = self._extract_kwarg(node, "key") or "return_value"
            self.graph.xcom_pulls.append({
                "task_ids": task_ids,
                "key": key,
                "line": node.lineno,
            })
        elif func_name in ("set_upstream", "set_downstream"):
            # Handle task.set_upstream(other) style
            if isinstance(node.func, ast.Attribute):
                caller = self._resolve_task_name(node.func.value)
                if node.args:
                    target = self._resolve_task_name(node.args[0])
                    if caller and target:
                        if func_name == "set_upstream":
                            self.graph.edges.append((target, caller))
                        else:
                            self.graph.edges.append((caller, target))

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        """Detect ti.xcom_push/xcom_pull method access."""
        if node.attr in ("xcom_push", "xcom_pull"):
            # Already handled in visit_Call when the method is called
            pass
        self.generic_visit(node)

    def _get_func_name(self, node: ast.Call) -> str:
        """Get the name of a function call."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    def _extract_task_id(self, node: ast.Call) -> str | None:
        """Extract task_id from operator call."""
        for kw in node.keywords:
            if kw.arg == "task_id" and isinstance(kw.value, ast.Constant):
                return kw.value.value
        return None

    def _extract_kwarg(self, node: ast.Call, key: str) -> str | None:
        """Extract keyword argument value."""
        for kw in node.keywords:
            if kw.arg == key and isinstance(kw.value, ast.Constant):
                return kw.value.value
        return None

    def _is_operator(self, name: str) -> bool:
        """Check if name looks like an Airflow operator."""
        return name.endswith("Operator") or name.endswith("Sensor") or name == "TaskGroup"

    def _add_dependencies(self, upstream: ast.expr, downstream: ast.expr):
        """Add dependency edges from upstream to downstream."""
        up_tasks = self._resolve_task_list(upstream)
        down_tasks = self._resolve_task_list(downstream)

        for up in up_tasks:
            for down in down_tasks:
                if up and down:
                    # Map variable names to task_ids
                    up_id = self.task_vars.get(up, up)
                    down_id = self.task_vars.get(down, down)
                    self.graph.edges.append((up_id, down_id))

    def _resolve_task_list(self, node: ast.expr) -> list[str]:
        """Resolve an expression to a list of task names."""
        if isinstance(node, ast.Name):
            return [node.id]
        elif isinstance(node, ast.List):
            result = []
            for elt in node.elts:
                result.extend(self._resolve_task_list(elt))
            return result
        elif isinstance(node, ast.BinOp):
            # For chained deps a >> b >> c, get rightmost for downstream
            if isinstance(node.op, (ast.RShift, ast.LShift)):
                return self._resolve_task_list(node.right)
        return []

    def _resolve_task_name(self, node: ast.expr) -> str | None:
        """Resolve a single expression to a task name."""
        if isinstance(node, ast.Name):
            return self.task_vars.get(node.id, node.id)
        return None


class FlowGraphExtractor(ast.NodeVisitor):
    """Extract task graph from Prefect flow code."""

    def __init__(self):
        self.graph = GraphInfo()
        self.task_functions: set[str] = set()
        self.current_flow: str | None = None
        self.task_vars: dict[str, str] = {}  # result_var -> task_name
        self.current_function: str | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Extract @task and @flow decorated functions."""
        for decorator in node.decorator_list:
            dec_name = self._get_decorator_name(decorator)
            if dec_name == "task":
                has_return = self._has_return_statement(node)
                params = [arg.arg for arg in node.args.args if arg.arg != "self"]
                self.graph.tasks[node.name] = TaskInfo(
                    name=node.name,
                    task_type="task",
                    line=node.lineno,
                    has_return=has_return,
                    parameters=params,
                )
                self.task_functions.add(node.name)
            elif dec_name == "flow":
                self.current_flow = node.name
                # Visit flow body to extract call dependencies
                old_function = self.current_function
                self.current_function = node.name
                self.generic_visit(node)
                self.current_function = old_function
                return

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        """Track task result assignments: result = task_func(...)."""
        if isinstance(node.value, ast.Call):
            func_name = self._get_call_name(node.value)
            if func_name in self.task_functions:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.task_vars[target.id] = func_name

                # Extract dependencies from call arguments
                self._extract_call_dependencies(func_name, node.value)
        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr):
        """Handle standalone task calls: task_func()."""
        if isinstance(node.value, ast.Call):
            func_name = self._get_call_name(node.value)
            if func_name in self.task_functions:
                self._extract_call_dependencies(func_name, node.value)
        self.generic_visit(node)

    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Get decorator name handling both @task and @task(...)."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id
        return ""

    def _get_call_name(self, node: ast.Call) -> str:
        """Get function name from a call."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            # Handle task.submit() pattern
            if isinstance(node.func.value, ast.Name):
                return node.func.value.id
        return ""

    def _has_return_statement(self, node: ast.FunctionDef) -> bool:
        """Check if function has a return statement with a value."""
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value is not None:
                return True
        return False

    def _extract_call_dependencies(self, task_name: str, call: ast.Call):
        """Extract dependencies from task call arguments."""
        # Check positional args for upstream task results
        for arg in call.args:
            upstream = self._resolve_upstream(arg)
            if upstream:
                self.graph.edges.append((upstream, task_name))

        # Check keyword args
        for kw in call.keywords:
            # Handle wait_for=[...]
            if kw.arg == "wait_for" and isinstance(kw.value, ast.List):
                for elt in kw.value.elts:
                    upstream = self._resolve_upstream(elt)
                    if upstream:
                        self.graph.edges.append((upstream, task_name))
            else:
                upstream = self._resolve_upstream(kw.value)
                if upstream:
                    self.graph.edges.append((upstream, task_name))

    def _resolve_upstream(self, node: ast.expr) -> str | None:
        """Resolve an expression to an upstream task name."""
        if isinstance(node, ast.Name):
            # Could be a result variable from a task
            return self.task_vars.get(node.id)
        elif isinstance(node, ast.Call):
            # Direct task call as argument
            func_name = self._get_call_name(node)
            if func_name in self.task_functions:
                return func_name
        return None


def extract_dag_graph(content: str) -> GraphInfo:
    """Extract task graph from Airflow DAG code.

    Args:
        content: Airflow DAG source code

    Returns:
        GraphInfo with tasks, edges, and XCom patterns
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return GraphInfo()

    extractor = DAGGraphExtractor()
    extractor.visit(tree)
    return extractor.graph


def extract_flow_graph(content: str) -> GraphInfo:
    """Extract task graph from Prefect flow code.

    Args:
        content: Prefect flow source code

    Returns:
        GraphInfo with tasks, edges, and data flow patterns
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return GraphInfo()

    extractor = FlowGraphExtractor()

    # First pass: identify all @task decorated functions
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                dec_name = extractor._get_decorator_name(decorator)
                if dec_name == "task":
                    extractor.task_functions.add(node.name)

    # Second pass: extract full graph
    extractor.visit(tree)
    return extractor.graph


def compare_task_counts(
    dag_graph: GraphInfo,
    flow_graph: GraphInfo,
) -> tuple[bool, list[ValidationIssue]]:
    """Compare task counts between DAG and flow.

    Ignores DummyOperator/EmptyOperator as Prefect doesn't need them.

    Returns:
        Tuple of (match: bool, issues: list)
    """
    issues = []

    dag_count = dag_graph.task_count
    flow_count = flow_graph.task_count

    if dag_count == flow_count:
        return True, issues

    # Find missing and extra tasks
    dag_tasks = set(dag_graph.tasks.keys())
    flow_tasks = set(flow_graph.tasks.keys())

    missing = dag_tasks - flow_tasks
    extra = flow_tasks - dag_tasks

    if missing:
        issues.append(ValidationIssue(
            severity="error",
            category="task_count",
            message=f"Missing {len(missing)} task(s) in converted flow",
            details={"missing_tasks": list(missing)},
        ))

    if extra:
        issues.append(ValidationIssue(
            severity="warning",
            category="task_count",
            message=f"Flow has {len(extra)} additional task(s) not in original DAG",
            details={"extra_tasks": list(extra)},
        ))

    return len(issues) == 0 or all(i.severity != "error" for i in issues), issues


def compare_dependencies(
    dag_graph: GraphInfo,
    flow_graph: GraphInfo,
) -> tuple[bool, list[ValidationIssue]]:
    """Compare dependency edges between DAG and flow.

    Checks for graph isomorphism considering task name mappings.
    Filters out edges involving ignored operators (DummyOperator/EmptyOperator).

    Returns:
        Tuple of (preserved: bool, issues: list)
    """
    issues = []

    # Get the set of actual tasks in each graph
    dag_tasks = set(dag_graph.tasks.keys())
    flow_tasks = set(flow_graph.tasks.keys())

    # Filter edges to only include those between actual tasks
    # This automatically excludes edges involving DummyOperator/EmptyOperator
    dag_edges = {
        (up, down) for up, down in dag_graph.edges
        if up in dag_tasks and down in dag_tasks
    }
    flow_edges = {
        (up, down) for up, down in flow_graph.edges
        if up in flow_tasks and down in flow_tasks
    }

    # Find missing and extra edges
    missing = dag_edges - flow_edges
    extra = flow_edges - dag_edges

    if missing:
        issues.append(ValidationIssue(
            severity="error",
            category="dependency",
            message=f"Missing {len(missing)} dependency edge(s) in flow",
            details={
                "missing_edges": [
                    {"upstream": up, "downstream": down}
                    for up, down in missing
                ]
            },
        ))

    if extra:
        # Extra edges are usually fine (more explicit dependencies)
        issues.append(ValidationIssue(
            severity="info",
            category="dependency",
            message=f"Flow has {len(extra)} additional dependency edge(s)",
            details={
                "extra_edges": [
                    {"upstream": up, "downstream": down}
                    for up, down in extra
                ]
            },
        ))

    return len(missing) == 0, issues


def compare_data_flow(
    dag_graph: GraphInfo,
    flow_graph: GraphInfo,
) -> tuple[bool, list[ValidationIssue]]:
    """Compare data flow patterns between DAG and flow.

    Verifies XCom push/pull patterns are converted to return/parameters.

    Returns:
        Tuple of (preserved: bool, issues: list)
    """
    issues = []

    # Check if XCom pushes have corresponding task returns
    xcom_push_tasks = {p.get("task_ids") for p in dag_graph.xcom_pushes if p.get("task_ids")}
    returning_tasks = {
        name for name, info in flow_graph.tasks.items()
        if info.has_return
    }

    # Check if XCom pulls have corresponding task parameters
    xcom_pull_count = len(dag_graph.xcom_pulls)
    tasks_with_params = {
        name for name, info in flow_graph.tasks.items()
        if info.parameters
    }

    # If DAG has XCom usage, flow should have data passing
    if xcom_pull_count > 0 and not tasks_with_params:
        issues.append(ValidationIssue(
            severity="warning",
            category="data_flow",
            message="DAG uses XCom pulls but flow tasks have no parameters",
            details={
                "xcom_pull_count": xcom_pull_count,
                "tasks_with_params": list(tasks_with_params),
            },
        ))

    # Check for any explicit XCom usage patterns that weren't converted
    if dag_graph.xcom_pushes:
        issues.append(ValidationIssue(
            severity="info",
            category="data_flow",
            message=f"DAG has {len(dag_graph.xcom_pushes)} XCom push(es) - verify return values in flow",
            details={"xcom_pushes": dag_graph.xcom_pushes},
        ))

    if dag_graph.xcom_pulls:
        issues.append(ValidationIssue(
            severity="info",
            category="data_flow",
            message=f"DAG has {len(dag_graph.xcom_pulls)} XCom pull(s) - verify parameters in flow",
            details={"xcom_pulls": dag_graph.xcom_pulls},
        ))

    # Data flow is preserved if no errors
    return all(i.severity != "error" for i in issues), issues


def calculate_confidence(
    dag_graph: GraphInfo,
    flow_graph: GraphInfo,
    issues: list[ValidationIssue],
) -> int:
    """Calculate confidence score for the validation.

    Returns:
        Score from 0-100 based on:
        - Task count match: +40 points
        - Dependency match: +30 points
        - No XCom complexity: +20 points
        - No trigger rules/dynamic mapping: +10 points
    """
    score = 0

    # Task count contribution
    if dag_graph.task_count == flow_graph.task_count:
        score += 40
    elif abs(dag_graph.task_count - flow_graph.task_count) <= 1:
        score += 30
    elif dag_graph.task_count > 0:
        ratio = min(dag_graph.task_count, flow_graph.task_count) / max(dag_graph.task_count, flow_graph.task_count)
        score += int(40 * ratio)

    # Dependency contribution
    dag_edges = set(dag_graph.edges)
    flow_edges = set(flow_graph.edges)
    if dag_edges == flow_edges:
        score += 30
    elif dag_edges and dag_edges.issubset(flow_edges):
        score += 25  # Flow has all DAG edges plus more
    elif dag_edges:
        missing = len(dag_edges - flow_edges)
        total = len(dag_edges)
        score += int(30 * (1 - missing / total))
    else:
        score += 30  # No dependencies to check

    # XCom complexity contribution
    xcom_count = len(dag_graph.xcom_pushes) + len(dag_graph.xcom_pulls)
    if xcom_count == 0:
        score += 20
    elif xcom_count <= 2:
        score += 15
    elif xcom_count <= 5:
        score += 10
    else:
        score += 5

    # Simple DAG bonus
    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")

    if error_count == 0 and warning_count == 0:
        score += 10
    elif error_count == 0:
        score += 5

    return min(100, max(0, score))


def validate_conversion_sync(
    original_dag: str,
    converted_flow: str,
) -> ValidationReport:
    """Validate a converted flow against the original DAG.

    This is the synchronous implementation of the validation logic.

    Args:
        original_dag: Airflow DAG source code
        converted_flow: Prefect flow source code

    Returns:
        ValidationReport with detailed comparison results
    """
    # Extract graphs
    dag_graph = extract_dag_graph(original_dag)
    flow_graph = extract_flow_graph(converted_flow)

    all_issues: list[ValidationIssue] = []

    # Compare task counts
    task_match, task_issues = compare_task_counts(dag_graph, flow_graph)
    all_issues.extend(task_issues)

    # Compare dependencies
    dep_match, dep_issues = compare_dependencies(dag_graph, flow_graph)
    all_issues.extend(dep_issues)

    # Compare data flow
    data_match, data_issues = compare_data_flow(dag_graph, flow_graph)
    all_issues.extend(data_issues)

    # Calculate confidence
    confidence = calculate_confidence(dag_graph, flow_graph, all_issues)

    # Overall validity
    is_valid = task_match and dep_match

    return ValidationReport(
        is_valid=is_valid,
        task_count_match=task_match,
        dependency_preserved=dep_match,
        data_flow_preserved=data_match,
        confidence_score=confidence,
        issues=all_issues,
        dag_summary={
            "task_count": dag_graph.task_count,
            "edge_count": dag_graph.edge_count,
            "tasks": list(dag_graph.tasks.keys()),
            "xcom_pushes": len(dag_graph.xcom_pushes),
            "xcom_pulls": len(dag_graph.xcom_pulls),
        },
        flow_summary={
            "task_count": flow_graph.task_count,
            "edge_count": flow_graph.edge_count,
            "tasks": list(flow_graph.tasks.keys()),
            "returning_tasks": [
                name for name, info in flow_graph.tasks.items()
                if info.has_return
            ],
            "tasks_with_params": [
                name for name, info in flow_graph.tasks.items()
                if info.parameters
            ],
        },
    )


async def validate_conversion(
    original_dag: str,
    converted_flow: str,
) -> str:
    """Validate a converted flow against the original DAG.

    Args:
        original_dag: Path or content of original DAG
        converted_flow: Path or content of converted flow

    Returns:
        JSON with validation results including:
        - is_valid: Overall pass/fail
        - task_count_match: Whether task counts match
        - dependency_preserved: Whether dependencies are preserved
        - data_flow_preserved: Whether XCom patterns are converted
        - confidence_score: 0-100 confidence in the validation
        - issues: List of specific issues found
    """
    # Load content if paths provided
    if Path(original_dag).exists():
        original_dag = Path(original_dag).read_text()
    if Path(converted_flow).exists():
        converted_flow = Path(converted_flow).read_text()

    report = validate_conversion_sync(original_dag, converted_flow)
    return json.dumps(report.to_dict(), indent=2)
