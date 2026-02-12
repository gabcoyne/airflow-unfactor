"""Base converter for Airflow DAGs to Prefect flows."""

from typing import Any

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
    
    # Add flow function
    if include_comments:
        lines.append(COMMENTS["flow"])
    
    flow_name = dag_id.replace("-", "_").replace(" ", "_")
    lines.append(f'@flow(name="{dag_id}")')
    lines.append(f"def {flow_name}():")
    lines.append('    """Main flow - converted from Airflow DAG."""')
    
    # Add task calls based on mapping
    if task_mapping:
        for original, converted in task_mapping.items():
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
    }
