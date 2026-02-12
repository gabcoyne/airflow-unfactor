"""Extract task dependencies from DAG code."""

import ast
import re
from typing import Any


class DependencyVisitor(ast.NodeVisitor):
    """Extract task dependencies from DAG."""

    def __init__(self):
        self.dependencies = []  # List of [upstream, downstream] pairs
        self.task_vars = {}  # Map variable names to task_ids

    def visit_Assign(self, node: ast.Assign):
        """Track task variable assignments."""
        # Look for task = SomeOperator(task_id='...') patterns
        if isinstance(node.value, ast.Call):
            for keyword in node.value.keywords:
                if keyword.arg == "task_id" and isinstance(keyword.value, ast.Constant):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.task_vars[target.id] = keyword.value.value
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        """Handle >> and << operators for dependencies."""
        if isinstance(node.op, ast.RShift):  # >>
            self._extract_dependency(node.left, node.right)
        elif isinstance(node.op, ast.LShift):  # <<
            self._extract_dependency(node.right, node.left)
        self.generic_visit(node)

    def _extract_dependency(self, upstream: ast.expr, downstream: ast.expr):
        """Extract a dependency from upstream >> downstream."""
        up_tasks = self._resolve_tasks(upstream)
        down_tasks = self._resolve_tasks(downstream)

        for up in up_tasks:
            for down in down_tasks:
                if up and down:
                    self.dependencies.append([up, down])

    def _resolve_tasks(self, node: ast.expr) -> list[str]:
        """Resolve a node to task IDs."""
        if isinstance(node, ast.Name):
            task_id = self.task_vars.get(node.id)
            return [task_id] if task_id else [node.id]
        elif isinstance(node, ast.List):
            tasks = []
            for elt in node.elts:
                tasks.extend(self._resolve_tasks(elt))
            return tasks
        elif isinstance(node, ast.BinOp):
            # Nested dependencies: a >> b >> c
            if isinstance(node.op, ast.RShift):
                # For nested, just get the rightmost
                return self._resolve_tasks(node.right)
        return []


def extract_dependencies(content: str) -> list[list[str]]:
    """Extract task dependencies from DAG code.

    Args:
        content: DAG file content

    Returns:
        List of [upstream_task, downstream_task] pairs
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    visitor = DependencyVisitor()
    visitor.visit(tree)

    # Also check for set_upstream/set_downstream calls
    # This is a simpler regex-based approach
    set_upstream_pattern = r"\.set_upstream\([\"\']?(\w+)[\"\']?\)"
    set_downstream_pattern = r"\.set_downstream\([\"\']?(\w+)[\"\']?\)"
    
    set_upstream = re.findall(set_upstream_pattern, content)
    set_downstream = re.findall(set_downstream_pattern, content)

    return visitor.dependencies
