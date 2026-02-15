"""Convert Airflow Trigger Rules to Prefect state-based patterns.

Airflow trigger_rule determines when a task runs based on upstream task states.
Prefect handles this with explicit state inspection using return_state=True.
"""

import ast
from dataclasses import dataclass, field
from typing import Any

# Mapping of Airflow trigger rules to Prefect code patterns
# Each pattern is a template that gets formatted with task details
TRIGGER_RULE_PATTERNS: dict[str, str] = {
    "all_success": """\
# Trigger rule: all_success (default)
# Task runs only if all upstream tasks succeed.
# In Prefect, this is the default behavior - just call the task normally.
{task_id}_result = {task_id}({upstream_args})""",
    "all_done": """\
# Trigger rule: all_done
# Task runs when all upstream tasks complete, regardless of success/failure.
# In Prefect, use return_state=True to get state without raising on failure.
{upstream_states_code}
{task_id}_result = {task_id}({upstream_args})""",
    "all_failed": """\
# Trigger rule: all_failed
# Task runs only if ALL upstream tasks failed.
# Check that every upstream state is failed before proceeding.
{upstream_states_code}
if all(state.is_failed() for state in [{upstream_state_vars}]):
    {task_id}_result = {task_id}({upstream_args})
else:
    {task_id}_result = None  # Skip: not all upstream tasks failed""",
    "one_failed": """\
# Trigger rule: one_failed
# Task runs if ANY upstream task failed.
# Check if at least one upstream state is failed.
{upstream_states_code}
if any(state.is_failed() for state in [{upstream_state_vars}]):
    {task_id}_result = {task_id}({upstream_args})
else:
    {task_id}_result = None  # Skip: no upstream task failed""",
    "one_success": """\
# Trigger rule: one_success
# Task runs if ANY upstream task succeeded.
# Check if at least one upstream state is completed (succeeded).
{upstream_states_code}
if any(state.is_completed() for state in [{upstream_state_vars}]):
    {task_id}_result = {task_id}({upstream_args})
else:
    {task_id}_result = None  # Skip: no upstream task succeeded""",
    "none_failed": """\
# Trigger rule: none_failed
# Task runs if NO upstream task failed (allows skipped/success).
# Check that no upstream state is failed.
{upstream_states_code}
if not any(state.is_failed() for state in [{upstream_state_vars}]):
    {task_id}_result = {task_id}({upstream_args})
else:
    {task_id}_result = None  # Skip: at least one upstream task failed""",
    "none_failed_min_one_success": """\
# Trigger rule: none_failed_min_one_success
# Task runs if no upstream failed AND at least one succeeded.
{upstream_states_code}
states = [{upstream_state_vars}]
if not any(s.is_failed() for s in states) and any(s.is_completed() for s in states):
    {task_id}_result = {task_id}({upstream_args})
else:
    {task_id}_result = None  # Skip: condition not met""",
    "none_skipped": """\
# Trigger rule: none_skipped
# Task runs if no upstream task was skipped.
# Note: Prefect doesn't have a native "skipped" state like Airflow.
# Treat None results as skipped.
{upstream_states_code}
if all(result is not None for result in [{upstream_result_vars}]):
    {task_id}_result = {task_id}({upstream_args})
else:
    {task_id}_result = None  # Skip: upstream task was skipped""",
    "always": """\
# Trigger rule: always
# Task ALWAYS runs, regardless of upstream state.
# Use return_state=True and ignore failures.
{upstream_states_code}
{task_id}_result = {task_id}({upstream_args})""",
    "dummy": """\
# Trigger rule: dummy (deprecated alias for always)
# Task ALWAYS runs, regardless of upstream state.
{upstream_states_code}
{task_id}_result = {task_id}({upstream_args})""",
}


@dataclass
class TriggerRuleInfo:
    """Information about a task's trigger rule."""

    task_id: str
    rule: str
    upstream_tasks: list[str] = field(default_factory=list)
    line_number: int = 0
    operator_type: str = ""


class TriggerRuleVisitor(ast.NodeVisitor):
    """AST visitor to extract trigger_rule from operators."""

    def __init__(self):
        self.trigger_rules: list[TriggerRuleInfo] = []

    def visit_Call(self, node: ast.Call):
        """Detect operator instantiation with trigger_rule parameter."""
        func_name = self._get_func_name(node)

        if func_name and ("Operator" in func_name or "Sensor" in func_name):
            info = self._extract_trigger_rule(node, func_name)
            if info:
                self.trigger_rules.append(info)

        self.generic_visit(node)

    def _get_func_name(self, node: ast.Call) -> str:
        """Extract function/class name from Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    def _extract_trigger_rule(self, node: ast.Call, operator_type: str) -> TriggerRuleInfo | None:
        """Extract trigger_rule info from an operator call."""
        task_id = "unknown_task"
        trigger_rule = "all_success"  # Airflow default

        for kw in node.keywords:
            if kw.arg == "task_id" and isinstance(kw.value, ast.Constant):
                task_id = str(kw.value.value)
            elif kw.arg == "trigger_rule":
                if isinstance(kw.value, ast.Constant):
                    trigger_rule = str(kw.value.value)
                elif isinstance(kw.value, ast.Attribute):
                    # Handle TriggerRule.ALL_DONE style
                    trigger_rule = kw.value.attr.lower()

        # Only record non-default trigger rules
        if trigger_rule != "all_success":
            return TriggerRuleInfo(
                task_id=task_id,
                rule=trigger_rule,
                line_number=node.lineno,
                operator_type=operator_type,
            )

        return None


def detect_trigger_rules(dag_code: str) -> list[TriggerRuleInfo]:
    """Detect trigger rules in DAG code.

    Args:
        dag_code: Source code of the DAG file

    Returns:
        List of tasks with non-default trigger rules
    """
    try:
        tree = ast.parse(dag_code)
    except SyntaxError:
        return []

    visitor = TriggerRuleVisitor()
    visitor.visit(tree)
    return visitor.trigger_rules


def generate_trigger_rule_code(info: TriggerRuleInfo) -> tuple[str, list[str]]:
    """Generate Prefect code for a trigger rule.

    Args:
        info: TriggerRuleInfo with task details

    Returns:
        Tuple of (generated_code, required_imports)
    """
    imports: list[str] = []

    # Get the pattern for this rule
    pattern = TRIGGER_RULE_PATTERNS.get(info.rule)
    if not pattern:
        # Unknown rule - generate warning comment
        code = f"""\
# WARNING: Unknown trigger rule '{info.rule}' on task '{info.task_id}'
# Please manually review and implement the appropriate state handling.
{info.task_id}_result = {info.task_id}()"""
        return (code, imports)

    # Build upstream state fetching code
    upstream_states_lines = []
    upstream_state_vars = []
    upstream_result_vars = []
    upstream_args = ""

    if info.upstream_tasks:
        for upstream in info.upstream_tasks:
            state_var = f"{upstream}_state"
            upstream_state_vars.append(state_var)
            upstream_result_vars.append(f"{upstream}_result")

            # For rules that need state inspection, call with return_state=True
            if info.rule in (
                "all_done",
                "all_failed",
                "one_failed",
                "one_success",
                "none_failed",
                "none_failed_min_one_success",
                "always",
                "dummy",
            ):
                upstream_states_lines.append(f"{state_var} = {upstream}.submit(return_state=True)")

        upstream_args = ", ".join(upstream_result_vars) if upstream_result_vars else ""

    upstream_states_code = (
        "\n".join(upstream_states_lines) if upstream_states_lines else "# No upstream tasks"
    )

    # Format the pattern
    code = pattern.format(
        task_id=info.task_id,
        upstream_states_code=upstream_states_code,
        upstream_state_vars=", ".join(upstream_state_vars),
        upstream_result_vars=", ".join(upstream_result_vars),
        upstream_args=upstream_args,
    )

    return (code, imports)


def convert_trigger_rules(
    dag_code: str,
    include_comments: bool = True,
) -> dict[str, Any]:
    """Convert all trigger rules in a DAG file to Prefect patterns.

    Args:
        dag_code: Source code of the DAG file
        include_comments: Include educational comments

    Returns:
        Dictionary with:
            - trigger_rules: List of TriggerRuleInfo detected
            - conversions: Dict mapping task_id to (code, imports)
            - summary: Human-readable summary
            - warnings: List of warnings
            - all_imports: Combined list of all required imports
    """
    trigger_rules = detect_trigger_rules(dag_code)

    if not trigger_rules:
        return {
            "trigger_rules": [],
            "conversions": {},
            "summary": "No non-default trigger rules detected",
            "warnings": [],
            "all_imports": [],
        }

    conversions: dict[str, tuple[str, list[str]]] = {}
    warnings: list[str] = []
    all_imports: set[str] = set()

    for info in trigger_rules:
        code, imports = generate_trigger_rule_code(info)
        conversions[info.task_id] = (code, imports)
        all_imports.update(imports)

        # Add warnings for complex rules
        if info.rule in ("all_failed", "one_failed"):
            warnings.append(
                f"Task '{info.task_id}' uses '{info.rule}' - ensure error handling "
                "is properly configured in the Prefect flow."
            )
        elif info.rule == "always":
            warnings.append(
                f"Task '{info.task_id}' uses 'always' - this task runs even when "
                "upstream tasks fail. Ensure this is the desired behavior."
            )
        elif info.rule not in TRIGGER_RULE_PATTERNS:
            warnings.append(
                f"Task '{info.task_id}' uses unknown trigger rule '{info.rule}' - "
                "requires manual conversion."
            )

    # Build summary
    rule_counts: dict[str, int] = {}
    for info in trigger_rules:
        rule_counts[info.rule] = rule_counts.get(info.rule, 0) + 1

    summary_parts = [f"{count} {rule}" for rule, count in sorted(rule_counts.items())]
    summary = f"Detected {len(trigger_rules)} trigger rule(s): {', '.join(summary_parts)}"

    return {
        "trigger_rules": trigger_rules,
        "conversions": conversions,
        "summary": summary,
        "warnings": warnings,
        "all_imports": sorted(all_imports),
    }


def get_trigger_rule_documentation() -> str:
    """Get educational documentation about trigger rules conversion.

    Returns:
        Markdown documentation explaining the conversion patterns.
    """
    return """\
# Airflow Trigger Rules to Prefect Conversion

## Overview

Airflow's `trigger_rule` parameter controls when a task executes based on
upstream task states. Prefect handles this differently - you explicitly
inspect task states using `return_state=True`.

## Conversion Patterns

### all_success (default)
- **Airflow**: Task runs only if all upstream tasks succeeded
- **Prefect**: Default behavior - just call the task normally

### all_done
- **Airflow**: Task runs when all upstreams complete (success or failure)
- **Prefect**: Use `return_state=True` to get state without raising on failure

### all_failed
- **Airflow**: Task runs only if ALL upstream tasks failed
- **Prefect**: Check `all(s.is_failed() for s in states)`

### one_failed
- **Airflow**: Task runs if ANY upstream task failed
- **Prefect**: Check `any(s.is_failed() for s in states)`

### one_success
- **Airflow**: Task runs if ANY upstream task succeeded
- **Prefect**: Check `any(s.is_completed() for s in states)`

### none_failed
- **Airflow**: Task runs if NO upstream task failed
- **Prefect**: Check `not any(s.is_failed() for s in states)`

### always
- **Airflow**: Task ALWAYS runs regardless of upstream state
- **Prefect**: Call with `return_state=True`, ignore failures

## Key Prefect State Methods

- `state.is_completed()` - Task finished successfully
- `state.is_failed()` - Task failed with an exception
- `state.is_cancelled()` - Task was cancelled
- `state.is_pending()` - Task hasn't started yet

## Example

```python
from prefect import flow, task

@task
def upstream_task():
    # May fail
    pass

@task
def downstream_task(data):
    # Process data
    pass

@flow
def my_flow():
    # Get state without raising on failure
    state = upstream_task.submit(return_state=True)

    # Run downstream only if upstream didn't fail
    if not state.is_failed():
        downstream_task(state.result())
```
"""
