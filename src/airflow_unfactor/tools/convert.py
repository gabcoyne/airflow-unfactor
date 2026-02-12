"""Convert Airflow DAGs to Prefect flows."""

import json
from pathlib import Path
from typing import Optional

from airflow_unfactor.analysis.parser import parse_dag
from airflow_unfactor.converters.base import convert_dag_to_flow


async def convert_dag(
    path: Optional[str] = None,
    content: Optional[str] = None,
    include_comments: bool = True,
) -> str:
    """Convert an Airflow DAG to a Prefect flow.

    Args:
        path: Path to DAG file
        content: DAG code content
        include_comments: Include educational comments

    Returns:
        JSON with converted code and metadata
    """
    if content is None and path:
        content = Path(path).read_text()

    if content is None:
        return json.dumps({"error": "No DAG content provided"})

    try:
        dag_info = parse_dag(content)
        result = convert_dag_to_flow(
            dag_info,
            original_code=content,
            include_comments=include_comments,
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})