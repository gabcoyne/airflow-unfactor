"""Base converter for Airflow DAGs to Prefect flows."""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from airflow_unfactor.analysis.dependencies import extract_dependencies


@dataclass
class DependencyGraph:
    """Task dependency graph for execution ordering."""

    # Map task_id -> list of upstream task_ids (must complete before this task)
    upstream: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    # Map task_id -> list of downstream task_ids (wait for this task)
    downstream: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    # All task IDs in the graph
    all_tasks: set[str] = field(default_factory=set)

    def add_dependency(self, upstream_task: str, downstream_task: str):
        """Add a dependency: downstream_task depends on upstream_task."""
        self.upstream[downstream_task].append(upstream_task)
        self.downstream[upstream_task].append(downstream_task)
        self.all_tasks.add(upstream_task)
        self.all_tasks.add(downstream_task)

    def get_roots(self) -> list[str]:
        """Get tasks with no upstream dependencies (entry points)."""
        return [t for t in self.all_tasks if not self.upstream[t]]

    def topological_sort(self) -> list[str]:
        """Return tasks in topological order (respects dependencies)."""
        # Kahn's algorithm
        in_degree = {t: len(self.upstream[t]) for t in self.all_tasks}
        queue = [t for t in self.all_tasks if in_degree[t] == 0]
        result = []

        while queue:
            # Sort to ensure deterministic order
            queue.sort()
            task = queue.pop(0)
            result.append(task)

            for downstream in self.downstream[task]:
                in_degree[downstream] -= 1
                if in_degree[downstream] == 0:
                    queue.append(downstream)

        # Check for cycles
        if len(result) != len(self.all_tasks):
            # Cycle detected - return best effort
            remaining = self.all_tasks - set(result)
            result.extend(sorted(remaining))

        return result

    def get_execution_groups(self) -> list[list[str]]:
        """Group tasks by execution level (tasks in same group can run in parallel)."""
        if not self.all_tasks:
            return []

        levels: dict[str, int] = {}

        # Calculate level for each task (max distance from any root)
        def get_level(task: str, visited: set) -> int:
            if task in levels:
                return levels[task]
            if task in visited:
                return 0  # Cycle detected
            visited.add(task)

            if not self.upstream[task]:
                levels[task] = 0
            else:
                levels[task] = 1 + max(
                    get_level(up, visited) for up in self.upstream[task]
                )
            return levels[task]

        for task in self.all_tasks:
            get_level(task, set())

        # Group by level
        groups: dict[int, list[str]] = defaultdict(list)
        for task, level in levels.items():
            groups[level].append(task)

        # Return as ordered list of groups
        return [sorted(groups[i]) for i in sorted(groups.keys())]


def build_dependency_graph(dependencies: list[list[str]], task_ids: list[str]) -> DependencyGraph:
    """Build a dependency graph from extracted dependencies.

    Args:
        dependencies: List of [upstream, downstream] pairs
        task_ids: List of all task IDs (including those without dependencies)

    Returns:
        DependencyGraph with all tasks and their relationships
    """
    graph = DependencyGraph()

    # Add all tasks first
    for task_id in task_ids:
        graph.all_tasks.add(task_id)

    # Add dependencies
    for upstream, downstream in dependencies:
        if upstream in task_ids and downstream in task_ids:
            graph.add_dependency(upstream, downstream)

    return graph

# Educational comment templates
COMMENTS = {
    "header": '''"""Prefect flow converted from Airflow DAG: {dag_id}

✨ Converted by airflow-unfactor

Key differences from Airflow:
- Tasks are regular Python functions with @task decorator
- Data passes directly between tasks (no XCom database)
- Dependencies are implicit via function calls
- Retries and logging are built into decorators
"""
''',
    "xcom": '''# ✨ Prefect Advantage: Direct Data Passing
# In Airflow, you'd use ti.xcom_push() and ti.xcom_pull() to pass
# data between tasks, hitting the metadata database each time.
# In Prefect, just return values — data flows in-memory between tasks.
# Faster, simpler, and no arbitrary size limits.
''',
    "task": '''# ✨ Prefect Advantage: Simple Task Definition
# No need for PythonOperator wrapper — just decorate your function.
# The @task decorator handles retries, logging, and state management.
''',
    "flow": '''# ✨ Prefect Advantage: Flow as Function
# No DAG class, no context managers, no >> operators.
# Just call tasks in order — Prefect tracks dependencies automatically.
''',
    "branch": '''# ✨ Prefect Advantage: Native Python Branching
# No BranchPythonOperator needed — just use if/else.
# Prefect only runs the tasks you actually call.
''',
    "sensor": '''# ✨ Prefect Note: Sensor Conversion
# Airflow sensors block a worker slot while polling.
# Consider Prefect alternatives:
# - Event-driven triggers (no polling needed)
# - Lightweight scheduled flows that check conditions
# - Webhooks for push-based notifications
''',
}


def convert_dag_to_flow(
    dag_info: dict[str, Any],
    original_code: str,
    include_comments: bool = True,
) -> dict[str, Any]:
    """Convert parsed DAG info to a Prefect flow.
    
    Args:
        dag_info: Parsed DAG information
        original_code: Original DAG source code
        include_comments: Include educational comments
        
    Returns:
        Dictionary with flow_code, imports, warnings, mapping
    """
    dag_id = dag_info.get("dag_id", "converted_flow")
    operators = dag_info.get("operators", [])
    
    # Build imports
    imports = [
        "from prefect import flow, task",
    ]
    
    # Check if we need additional imports
    has_bash = any(op.get("type") == "BashOperator" for op in operators)
    if has_bash:
        imports.append("import subprocess")
    
    # Start building the flow code
    lines = []
    
    # Add header comment
    if include_comments:
        lines.append(COMMENTS["header"].format(dag_id=dag_id))
    
    # Add imports
    lines.extend(imports)
    lines.append("")
    
    # Convert operators to tasks
    task_mapping = {}
    warnings = []
    
    if include_comments and operators:
        lines.append(COMMENTS["task"])
    
    for op in operators:
        op_type = op.get("type", "")
        task_id = op.get("task_id", "unknown_task")
        
        # Generate Prefect task
        if op_type == "PythonOperator":
            lines.append("@task")
            lines.append(f"def {task_id}():")
            lines.append('    """Converted from PythonOperator."""')
            lines.append("    # TODO: Add original function logic")
            lines.append("    pass")
            lines.append("")
            task_mapping[task_id] = task_id
            
        elif op_type == "BashOperator":
            lines.append("@task")
            lines.append(f"def {task_id}():")
            lines.append('    """Converted from BashOperator."""')
            lines.append("    import subprocess")
            lines.append("    # TODO: Add original bash command")
            lines.append("    result = subprocess.run(['echo', 'hello'], capture_output=True, text=True)")
            lines.append("    return result.stdout")
            lines.append("")
            task_mapping[task_id] = task_id
            
        elif op_type == "BranchPythonOperator":
            if include_comments:
                lines.append(COMMENTS["branch"])
            lines.append(f"def {task_id}_decide():")
            lines.append('    """Branching logic from BranchPythonOperator."""')
            lines.append("    # TODO: Return which branch to take")
            lines.append("    return True  # or False")
            lines.append("")
            task_mapping[task_id] = f"{task_id}_decide"
            warnings.append(f"BranchPythonOperator '{task_id}' converted to function - review branching logic")
            
        elif op_type in ("DummyOperator", "EmptyOperator"):
            # Skip dummy operators
            warnings.append(f"Removed {op_type} '{task_id}' (not needed in Prefect)")
            
        elif "Sensor" in op_type:
            if include_comments:
                lines.append(COMMENTS["sensor"])
            lines.append("@task(retries=3, retry_delay_seconds=60)")
            lines.append(f"def {task_id}():")
            lines.append(f'    """Converted from {op_type} - consider event triggers."""')
            lines.append("    # TODO: Implement polling logic or use Prefect triggers")
            lines.append("    pass")
            lines.append("")
            task_mapping[task_id] = task_id
            warnings.append(f"Sensor '{task_id}' converted to polling task - consider Prefect triggers")
            
        else:
            # Generic conversion
            lines.append("@task")
            lines.append(f"def {task_id}():")
            lines.append(f'    """Converted from {op_type}."""')
            lines.append("    # TODO: Implement equivalent logic")
            lines.append("    pass")
            lines.append("")
            task_mapping[task_id] = task_id
            warnings.append(f"Operator '{op_type}' requires manual review")
    
    # Extract dependencies from original code
    dependencies = extract_dependencies(original_code)
    task_ids = list(task_mapping.keys())
    dep_graph = build_dependency_graph(dependencies, task_ids)

    # Add flow function
    if include_comments:
        lines.append(COMMENTS["flow"])

    flow_name = dag_id.replace("-", "_").replace(" ", "_")
    lines.append(f'@flow(name="{dag_id}")')
    lines.append(f"def {flow_name}():")
    lines.append('    """Main flow - converted from Airflow DAG."""')

    # Generate task calls respecting dependencies
    if task_mapping:
        execution_groups = dep_graph.get_execution_groups()

        if execution_groups:
            # We have dependency info - generate ordered execution
            if include_comments and len(execution_groups) > 1:
                lines.append("    # Tasks are organized by execution level (parallel groups)")
                lines.append("")

            # Track task results for passing to downstream tasks
            task_results: dict[str, str] = {}

            for level, group in enumerate(execution_groups):
                if include_comments and len(execution_groups) > 1:
                    if len(group) > 1:
                        lines.append(f"    # Level {level}: {', '.join(group)} (can run in parallel)")
                    else:
                        lines.append(f"    # Level {level}: {group[0]}")

                for task_id in group:
                    converted = task_mapping.get(task_id, task_id)
                    upstream_tasks = dep_graph.upstream.get(task_id, [])

                    # Check if we need to pass data or use wait_for
                    if upstream_tasks:
                        # Get the result variables of upstream tasks
                        upstream_vars = [
                            task_results.get(up, f"{up}_result") for up in upstream_tasks
                        ]

                        if len(upstream_tasks) == 1:
                            # Single upstream - pass result as argument if data flow makes sense
                            up_var = upstream_vars[0]
                            result_var = f"{task_id}_result"
                            lines.append(f"    {result_var} = {converted}({up_var})")
                        else:
                            # Multiple upstream - use wait_for pattern
                            wait_for_list = ", ".join(upstream_vars)
                            result_var = f"{task_id}_result"
                            lines.append(
                                f"    {result_var} = {converted}.submit(wait_for=[{wait_for_list}])"
                            )
                    else:
                        # No upstream - just call the task
                        result_var = f"{task_id}_result"
                        lines.append(f"    {result_var} = {converted}()")

                    task_results[task_id] = result_var

                if len(group) > 1 and level < len(execution_groups) - 1:
                    lines.append("")  # Blank line between groups
        else:
            # No dependency info - preserve original order with warning
            warnings.append(
                "No task dependencies detected. Tasks are called in declaration order. "
                "Review and add wait_for or data passing to enforce correct execution order."
            )
            for task_id, converted in task_mapping.items():
                lines.append(f"    {converted}()")
    else:
        lines.append("    pass")

    lines.append("")

    # Add main block
    lines.append("")
    lines.append('if __name__ == "__main__":')
    lines.append(f"    {flow_name}()")

    flow_code = "\n".join(lines)

    return {
        "flow_code": flow_code,
        "imports": imports,
        "warnings": warnings,
        "original_to_new_mapping": task_mapping,
        "dependencies": dependencies,
        "execution_groups": [list(g) for g in dep_graph.get_execution_groups()],
    }
