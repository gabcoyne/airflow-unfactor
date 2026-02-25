"""Validate DAG to flow conversions.

Returns both source files for LLM comparison plus syntax validation.
Structural comparison is done by the LLM, not AST.
"""

import json
from pathlib import Path

from airflow_unfactor.validation import validate_python_syntax


async def validate_conversion(
    original_dag: str,
    converted_flow: str,
) -> str:
    """Validate a converted flow against the original DAG.

    Returns both source files for the LLM to compare, plus a syntax
    check on the generated code.

    Args:
        original_dag: Path or content of original DAG
        converted_flow: Path or content of converted flow

    Returns:
        JSON with original_source, converted_source, syntax_valid,
        syntax_errors, and comparison_guidance.
    """
    # Load content if paths provided
    original_source = original_dag
    if Path(original_dag).exists():
        original_source = Path(original_dag).read_text()

    converted_source = converted_flow
    if Path(converted_flow).exists():
        converted_source = Path(converted_flow).read_text()

    # Syntax check the generated code
    syntax_result = validate_python_syntax(converted_source)

    syntax_errors = None
    if not syntax_result.valid:
        syntax_errors = [
            {
                "line": syntax_result.line,
                "column": syntax_result.column,
                "message": syntax_result.error,
            }
        ]

    return json.dumps(
        {
            "original_source": original_source,
            "converted_source": converted_source,
            "syntax_valid": syntax_result.valid,
            "syntax_errors": syntax_errors,
            "comparison_guidance": (
                "Compare the original Airflow DAG with the generated Prefect flow. Verify:\n"
                "1. All tasks from the DAG are represented in the flow\n"
                "2. Task dependencies are preserved (>> chains become function call order)\n"
                "3. XCom push/pull is replaced with task return values and parameters\n"
                "4. Connections are mapped to Prefect blocks\n"
                "5. Variables are mapped to Prefect variables or environment config\n"
                "6. Schedule, retries, and other DAG config is carried over\n"
                "7. Sensors are converted to polling tasks with retries or event triggers\n"
                "8. TaskGroups are converted to subflows\n"
                "9. Trigger rules are handled with state inspection"
            ),
        },
        indent=2,
    )
