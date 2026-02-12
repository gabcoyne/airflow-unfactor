"""Convert Airflow BashOperator to Prefect @task."""

import ast
import re
from typing import Optional


def extract_bash_command(operator_node: ast.Call) -> Optional[str]:
    """Extract the bash_command from a BashOperator AST node.
    
    Args:
        operator_node: AST Call node for BashOperator
        
    Returns:
        The bash command string, or None if not found
    """
    for keyword in operator_node.keywords:
        if keyword.arg == 'bash_command':
            if isinstance(keyword.value, ast.Constant):
                return keyword.value.value
            elif isinstance(keyword.value, ast.JoinedStr):
                # f-string - return a representation
                return _reconstruct_fstring(keyword.value)
    return None


def _reconstruct_fstring(node: ast.JoinedStr) -> str:
    """Reconstruct an f-string from AST."""
    parts = []
    for value in node.values:
        if isinstance(value, ast.Constant):
            parts.append(value.value)
        elif isinstance(value, ast.FormattedValue):
            # This is a {variable} part
            if isinstance(value.value, ast.Name):
                parts.append(f"{{{value.value.id}}}")
            else:
                parts.append("{...}")  # Complex expression
    return ''.join(parts)


def convert_bash_operator(
    task_id: str,
    bash_command: Optional[str] = None,
    env: Optional[dict] = None,
    include_comments: bool = True,
) -> str:
    """Convert a BashOperator to a Prefect @task.
    
    Args:
        task_id: Airflow task ID
        bash_command: The bash command to execute
        env: Environment variables
        include_comments: Include educational comments
        
    Returns:
        Prefect task code as string
    """
    lines = []
    
    if include_comments:
        lines.append("# ✨ Prefect Advantage: Native Python Subprocess")
        lines.append("# No special BashOperator needed - just use subprocess.")
        lines.append("# Better error handling and output capture built-in.")
        lines.append("")
    
    lines.append("@task")
    lines.append(f"def {task_id}():")
    
    if bash_command:
        # Escape the command for use in Python string
        escaped_cmd = bash_command.replace('\\', '\\\\').replace('"', '\\"')
        
        # Check if it's a simple or complex command
        if '\n' in bash_command or len(bash_command) > 80:
            # Multi-line or long command - use triple quotes
            lines.append(f'    """Execute bash command."""')
            lines.append("    import subprocess")
            lines.append(f'    cmd = """\\')
            for cmd_line in bash_command.splitlines():
                lines.append(f'{cmd_line}')
            lines.append('"""')
        else:
            lines.append(f'    """Execute: {escaped_cmd[:50]}{"..." if len(escaped_cmd) > 50 else ""}"""')
            lines.append("    import subprocess")
            lines.append(f'    cmd = "{escaped_cmd}"')
        
        # Add environment if specified
        if env:
            lines.append("    import os")
            lines.append("    env = os.environ.copy()")
            for key, value in env.items():
                lines.append(f'    env["{key}"] = "{value}"')
            lines.append("    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)")
        else:
            lines.append("    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)")
        
        lines.append("    if result.returncode != 0:")
        lines.append("        raise RuntimeError(f\"Bash command failed: {result.stderr}\")")
        lines.append("    return result.stdout")
    else:
        lines.append('    """Converted from BashOperator."""')
        lines.append("    import subprocess")
        lines.append("    # TODO: Add the original bash command")
        lines.append('    cmd = "echo TODO"')
        lines.append("    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)")
        lines.append("    return result.stdout")
    
    lines.append("")
    return "\n".join(lines)


def convert_task_bash_decorator(
    task_id: str,
    function_body: str,
    include_comments: bool = True,
) -> str:
    """Convert Airflow @task.bash to a Prefect @task.
    
    In Airflow 2.9+, @task.bash returns a string that gets executed as bash.
    In Prefect, we execute it with subprocess.
    
    Args:
        task_id: Task ID
        function_body: The function body that returns a bash command
        include_comments: Include educational comments
        
    Returns:
        Prefect task code as string
    """
    lines = []
    
    if include_comments:
        lines.append("# ✨ Prefect Note: @task.bash Conversion")
        lines.append("# Airflow's @task.bash executes the returned string as bash.")
        lines.append("# In Prefect, we compute the command then execute it explicitly.")
        lines.append("")
    
    lines.append("@task")
    lines.append(f"def {task_id}(*args, **kwargs):")
    lines.append('    """Converted from @task.bash - computes and executes bash command."""')
    lines.append("    import subprocess")
    lines.append("")
    lines.append("    # Compute the bash command (original @task.bash logic)")
    
    # Indent the original function body
    for line in function_body.splitlines():
        if line.strip().startswith("return "):
            # Change return to assignment
            cmd_part = line.strip()[7:]  # Remove "return "
            lines.append(f"    cmd = {cmd_part}")
        else:
            lines.append(f"    {line}" if line.strip() else "")
    
    lines.append("")
    lines.append("    # Execute the computed command")
    lines.append("    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)")
    lines.append("    if result.returncode != 0:")
    lines.append("        raise RuntimeError(f\"Bash command failed: {result.stderr}\")")
    lines.append("    return result.stdout")
    lines.append("")
    
    return "\n".join(lines)
