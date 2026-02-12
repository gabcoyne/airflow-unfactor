"""Analyze Airflow DAGs."""

import ast
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

from airflow_unfactor.analysis.parser import parse_dag
from airflow_unfactor.analysis.complexity import calculate_complexity
from airflow_unfactor.analysis.dependencies import extract_dependencies


@dataclass
class AnalysisResult:
    """Result of DAG analysis."""
    dag_id: str
    operators: list[dict]
    dependencies: list[list[str]]
    xcom_usage: list[str]
    complexity_score: int
    conversion_notes: list[str]


async def analyze_dag(
    path: Optional[str] = None,
    content: Optional[str] = None,
) -> str:
    """Analyze an Airflow DAG file.

    Args:
        path: Path to DAG file
        content: DAG code content (alternative to path)

    Returns:
        JSON string with analysis results
    """
    if content is None and path:
        content = Path(path).read_text()

    if content is None:
        return json.dumps({"error": "No DAG content provided"})

    try:
        dag_info = parse_dag(content)
        deps = extract_dependencies(content)
        complexity = calculate_complexity(dag_info)

        result = AnalysisResult(
            dag_id=dag_info.get("dag_id", "unknown"),
            operators=dag_info.get("operators", []),
            dependencies=deps,
            xcom_usage=dag_info.get("xcom_usage", []),
            complexity_score=complexity,
            conversion_notes=dag_info.get("notes", []),
        )

        return json.dumps(asdict(result), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})