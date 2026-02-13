"""Convert Airflow BashOperator to Prefect @task."""

import ast
import re
from dataclasses import dataclass, field
from typing import Optional


# Common Airflow Jinja2 template variables and their Prefect equivalents (where applicable)
JINJA2_TEMPLATE_MAPPINGS = {
    # Execution context
    "{{ ds }}": "# Prefect: Use flow_run.scheduled_start_time.strftime('%Y-%m-%d')",
    "{{ ds_nodash }}": "# Prefect: Use flow_run.scheduled_start_time.strftime('%Y%m%d')",
    "{{ execution_date }}": "# Prefect: Use flow_run.scheduled_start_time (datetime object)",
    "{{ data_interval_start }}": "# Prefect: Use flow_run.scheduled_start_time",
    "{{ data_interval_end }}": "# Prefect: No direct equivalent - calculate from schedule",
    "{{ logical_date }}": "# Prefect: Use flow_run.scheduled_start_time",
    "{{ ts }}": "# Prefect: Use flow_run.scheduled_start_time.isoformat()",
    "{{ ts_nodash }}": "# Prefect: Use flow_run.scheduled_start_time.strftime('%Y%m%dT%H%M%S')",
    "{{ ts_nodash_with_tz }}": "# Prefect: Format scheduled_start_time with timezone",
    # Task/DAG context
    "{{ task.task_id }}": "# Prefect: Use task_run.task.task_key or function name",
    "{{ task_instance.task_id }}": "# Prefect: Use task_run.task.task_key",
    "{{ ti.task_id }}": "# Prefect: Use task_run.task.task_key",
    "{{ dag.dag_id }}": "# Prefect: Use flow_run.flow.name",
    "{{ dag_run.dag_id }}": "# Prefect: Use flow_run.flow.name",
    "{{ run_id }}": "# Prefect: Use str(flow_run.id)",
    # Parameters
    "{{ params.": "# Prefect: Use flow parameters directly",
    "{{ var.value.": "# Prefect: Use Prefect Variables or Blocks",
    "{{ var.json.": "# Prefect: Use Prefect JSON Blocks",
    "{{ conn.": "# Prefect: Use Prefect Blocks for connections",
    # Macros
    "{{ macros.": "# Prefect: Use standard Python libraries",
}

# Regex pattern to detect any Jinja2-style template
JINJA2_PATTERN = re.compile(r"\{\{.*?\}\}|\{%.*?%\}")


@dataclass
class Jinja2Detection:
    """Result of Jinja2 template detection in a command."""

    has_templates: bool
    templates_found: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggested_replacements: dict[str, str] = field(default_factory=dict)


def detect_jinja2_templates(command: str) -> Jinja2Detection:
    """Detect Jinja2 templates in a bash command.

    Args:
        command: The bash command to analyze

    Returns:
        Jinja2Detection with findings
    """
    if not command:
        return Jinja2Detection(has_templates=False)

    templates_found = JINJA2_PATTERN.findall(command)
    if not templates_found:
        return Jinja2Detection(has_templates=False)

    warnings = []
    suggested_replacements = {}

    for template in templates_found:
        # Check for known mappings
        matched = False
        for airflow_template, prefect_hint in JINJA2_TEMPLATE_MAPPINGS.items():
            if airflow_template in template or template.startswith(airflow_template.rstrip("}")):
                suggested_replacements[template] = prefect_hint
                matched = True
                break

        if not matched:
            suggested_replacements[template] = "# Prefect: Requires manual conversion"

    # Build warning message
    if templates_found:
        warnings.append(
            f"Jinja2 templates detected in bash command: {templates_found}. "
            "These will NOT render in Prefect and will cause runtime failures. "
            "Convert to Python string formatting or Prefect runtime context."
        )

    return Jinja2Detection(
        has_templates=True,
        templates_found=templates_found,
        warnings=warnings,
        suggested_replacements=suggested_replacements,
    )


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


@dataclass
class BashConversionResult:
    """Result of BashOperator conversion."""

    code: str
    warnings: list[str] = field(default_factory=list)
    jinja2_detection: Optional[Jinja2Detection] = None


def convert_bash_operator(
    task_id: str,
    bash_command: Optional[str] = None,
    env: Optional[dict] = None,
    include_comments: bool = True,
) -> BashConversionResult:
    """Convert a BashOperator to a Prefect @task.

    Args:
        task_id: Airflow task ID
        bash_command: The bash command to execute
        env: Environment variables
        include_comments: Include educational comments

    Returns:
        BashConversionResult with code, warnings, and jinja2 detection
    """
    lines = []
    warnings = []
    jinja2_detection = None

    # Detect Jinja2 templates if command is provided
    if bash_command:
        jinja2_detection = detect_jinja2_templates(bash_command)
        if jinja2_detection.has_templates:
            warnings.extend(jinja2_detection.warnings)

    if include_comments:
        lines.append("# ✨ Prefect Advantage: Native Python Subprocess")
        lines.append("# No special BashOperator needed - just use subprocess.")
        lines.append("# Better error handling and output capture built-in.")
        lines.append("")

    # Add Jinja2 warning comments if detected
    if jinja2_detection and jinja2_detection.has_templates:
        lines.append("# ⚠️ WARNING: Jinja2 templates detected in original command!")
        lines.append("# The following templates will NOT work and need manual conversion:")
        for template, hint in jinja2_detection.suggested_replacements.items():
            lines.append(f"#   {template} -> {hint}")
        lines.append("# See: https://docs.prefect.io/concepts/runtime-context/")
        lines.append("")

    lines.append("@task")
    lines.append(f"def {task_id}():")

    if bash_command:
        # Escape the command for use in Python string
        escaped_cmd = bash_command.replace("\\", "\\\\").replace('"', '\\"')

        # Check if it's a simple or complex command
        if "\n" in bash_command or len(bash_command) > 80:
            # Multi-line or long command - use triple quotes
            lines.append('    """Execute bash command."""')
            lines.append("    import subprocess")
            lines.append('    cmd = """\\')
            for cmd_line in bash_command.splitlines():
                lines.append(f"{cmd_line}")
            lines.append('"""')
        else:
            lines.append(
                f'    """Execute: {escaped_cmd[:50]}{"..." if len(escaped_cmd) > 50 else ""}"""'
            )
            lines.append("    import subprocess")
            lines.append(f'    cmd = "{escaped_cmd}"')

        # Add TODO comment for Jinja2 templates
        if jinja2_detection and jinja2_detection.has_templates:
            lines.append("")
            lines.append("    # TODO: Replace Jinja2 templates with Python equivalents")
            lines.append("    # Example: Use Prefect runtime context for execution metadata")
            lines.append("    # from prefect import runtime")
            lines.append("    # flow_run_id = runtime.flow_run.id")
            lines.append("    # scheduled_time = runtime.flow_run.scheduled_start_time")
            lines.append("")

        # Add environment if specified
        if env:
            lines.append("    import os")
            lines.append("    env = os.environ.copy()")
            for key, value in env.items():
                lines.append(f'    env["{key}"] = "{value}"')
            lines.append(
                "    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)"
            )
        else:
            lines.append("    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)")

        lines.append("    if result.returncode != 0:")
        lines.append('        raise RuntimeError(f"Bash command failed: {result.stderr}")')
        lines.append("    return result.stdout")
    else:
        lines.append('    """Converted from BashOperator."""')
        lines.append("    import subprocess")
        lines.append("    # TODO: Add the original bash command")
        lines.append('    cmd = "echo TODO"')
        lines.append("    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)")
        lines.append("    return result.stdout")

    lines.append("")
    return BashConversionResult(
        code="\n".join(lines),
        warnings=warnings,
        jinja2_detection=jinja2_detection,
    )


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
