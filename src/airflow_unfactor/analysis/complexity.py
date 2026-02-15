"""Calculate DAG complexity scores."""

from typing import Any

# Complexity weights
WEIGHTS = {
    "PythonOperator": 1,
    "BashOperator": 1,
    "DummyOperator": 0,
    "EmptyOperator": 0,
    "BranchPythonOperator": 3,
    "ShortCircuitOperator": 2,
    "TriggerDagRunOperator": 2,
    "TaskGroup": 2,
    # Sensors are more complex
    "PythonSensor": 3,
    "ExternalTaskSensor": 4,
    "FileSensor": 3,
    "S3KeySensor": 4,
    "HttpSensor": 3,
    "SqlSensor": 4,
    # Providers
    "S3CreateObjectOperator": 2,
    "BigQueryInsertJobOperator": 3,
    "PostgresOperator": 2,
    "SlackWebhookOperator": 1,
    "EmailOperator": 1,
    "SimpleHttpOperator": 2,
}

DEFAULT_WEIGHT = 2


def calculate_complexity(dag_info: dict[str, Any]) -> int:
    """Calculate a complexity score for a DAG.

    Factors:
    - Number and types of operators
    - XCom usage
    - Branching/control flow
    - External dependencies (sensors)

    Args:
        dag_info: Parsed DAG information

    Returns:
        Complexity score (higher = more complex)
    """
    score = 0

    # Operator complexity
    for op in dag_info.get("operators", []):
        op_type = op.get("type", "")
        score += WEIGHTS.get(op_type, DEFAULT_WEIGHT)

    # XCom usage adds complexity
    xcom_count = len(dag_info.get("xcom_usage", []))
    score += xcom_count * 2

    # Notes indicate complexity factors
    notes = dag_info.get("notes", [])
    for note in notes:
        if "sensor" in note.lower():
            score += 2
        if "branch" in note.lower():
            score += 2
        if "taskgroup" in note.lower():
            score += 1

    return score


def complexity_level(score: int) -> str:
    """Convert score to human-readable level."""
    if score <= 5:
        return "simple"
    elif score <= 15:
        return "moderate"
    elif score <= 30:
        return "complex"
    else:
        return "very_complex"
