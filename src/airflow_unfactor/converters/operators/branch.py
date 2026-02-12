"""Convert Airflow BranchPythonOperator to native Python branching."""

from typing import Optional
from dataclasses import dataclass


@dataclass
class BranchInfo:
    """Information about a branching task."""
    task_id: str
    python_callable: str
    branches: list[str]  # Possible downstream task IDs


def convert_branch_operator(
    task_id: str,
    python_callable: str,
    downstream_tasks: list[str],
    function_body: Optional[str] = None,
    include_comments: bool = True,
) -> tuple[str, str]:
    """Convert a BranchPythonOperator to native Python branching.
    
    This generates TWO things:
    1. A decision function that returns which branch to take
    2. Guidance on how to use if/else in the flow
    
    Args:
        task_id: Airflow task ID
        python_callable: Name of the branching function
        downstream_tasks: List of possible downstream task IDs
        function_body: Original function body if available
        include_comments: Include educational comments
        
    Returns:
        Tuple of (decision_function_code, flow_usage_guidance)
    """
    decision_lines = []
    guidance_lines = []
    
    # Generate the decision function
    if include_comments:
        decision_lines.append("# ✨ Prefect Advantage: Native Python Branching")
        decision_lines.append("# No BranchPythonOperator needed - just use if/else!")
        decision_lines.append("# Prefect only runs the tasks you actually call.")
        decision_lines.append("")
    
    # The decision function
    decision_lines.append("@task")
    decision_lines.append(f"def {task_id}_decide(**kwargs) -> str:")
    decision_lines.append(f'    """Decide which branch to execute."""')
    
    if function_body:
        # Include the original logic
        decision_lines.append("    # Original branching logic:")
        for line in function_body.splitlines():
            decision_lines.append(f"    {line}" if line.strip() else "")
    else:
        decision_lines.append("    # TODO: Implement branching logic")
        decision_lines.append(f"    # Should return one of: {downstream_tasks}")
        decision_lines.append(f'    return "{downstream_tasks[0] if downstream_tasks else "default"}"')
    
    decision_lines.append("")
    
    # Generate flow usage guidance
    guidance_lines.append("# In your @flow function, use native Python branching:")
    guidance_lines.append("#")
    guidance_lines.append(f"#     branch = {task_id}_decide()")
    guidance_lines.append("#")
    
    if downstream_tasks:
        for i, task in enumerate(downstream_tasks):
            safe_task = task.replace('-', '_').replace(' ', '_')
            if i == 0:
                guidance_lines.append(f'#     if branch == "{task}":')
            else:
                guidance_lines.append(f'#     elif branch == "{task}":')
            guidance_lines.append(f"#         {safe_task}()")
    else:
        guidance_lines.append('#     if branch == "option_a":')
        guidance_lines.append("#         task_a()")
        guidance_lines.append('#     else:')
        guidance_lines.append("#         task_b()")
    
    guidance_lines.append("#")
    guidance_lines.append("# Prefect only executes the branch that's actually called!")
    guidance_lines.append("")
    
    return "\n".join(decision_lines), "\n".join(guidance_lines)


def convert_short_circuit_operator(
    task_id: str,
    python_callable: str,
    function_body: Optional[str] = None,
    include_comments: bool = True,
) -> str:
    """Convert a ShortCircuitOperator to early return pattern.
    
    Args:
        task_id: Airflow task ID
        python_callable: Name of the condition function
        function_body: Original function body if available
        include_comments: Include educational comments
        
    Returns:
        Prefect code showing the early return pattern
    """
    lines = []
    
    if include_comments:
        lines.append("# ✨ Prefect Advantage: Native Python Control Flow")
        lines.append("# No ShortCircuitOperator needed - just return early from your flow!")
        lines.append("")
    
    lines.append("@task")
    lines.append(f"def {task_id}_should_continue(**kwargs) -> bool:")
    lines.append('    """Check if flow should continue."""')
    
    if function_body:
        for line in function_body.splitlines():
            lines.append(f"    {line}" if line.strip() else "")
    else:
        lines.append("    # TODO: Implement condition logic")
        lines.append("    return True")
    
    lines.append("")
    lines.append("# In your @flow function:")
    lines.append("#")
    lines.append(f"#     if not {task_id}_should_continue():")
    lines.append("#         return  # Short-circuit - skip remaining tasks")
    lines.append("#")
    lines.append("#     # Continue with remaining tasks...")
    lines.append("")
    
    return "\n".join(lines)


def analyze_branching_structure(
    dag_code: str,
    branch_task_id: str,
) -> list[str]:
    """Analyze DAG code to find downstream tasks of a branch.
    
    Args:
        dag_code: Full DAG source code
        branch_task_id: Task ID of the branching operator
        
    Returns:
        List of downstream task IDs
    """
    import ast
    
    downstream = []
    
    try:
        tree = ast.parse(dag_code)
    except SyntaxError:
        return downstream
    
    # Look for dependency patterns like:
    # branch_task >> [task_a, task_b]
    # branch_task >> task_a
    # task_a.set_upstream(branch_task)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.RShift):
            # Check if left side is our branch task
            if isinstance(node.left, ast.Name) and node.left.id == branch_task_id:
                # Get the right side (downstream tasks)
                if isinstance(node.right, ast.List):
                    for elt in node.right.elts:
                        if isinstance(elt, ast.Name):
                            downstream.append(elt.id)
                elif isinstance(node.right, ast.Name):
                    downstream.append(node.right.id)
    
    return downstream
