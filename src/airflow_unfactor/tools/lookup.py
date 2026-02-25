"""Lookup Airflow→Prefect translation knowledge.

Queries Colin-compiled JSON output for operators, concepts, patterns,
and connections. Falls back to built-in mappings if Colin output is unavailable.
"""

import json

from airflow_unfactor.knowledge import load_knowledge, lookup


async def lookup_concept(concept: str) -> str:
    """Look up translation knowledge for an Airflow concept.

    Searches Colin-compiled knowledge for operators, patterns,
    connections, and core concepts. Falls back to built-in mappings
    if Colin output is not available.

    Args:
        concept: The Airflow concept to look up (e.g. "PythonOperator",
                "XCom", "TaskGroup", "postgres_default").

    Returns:
        JSON with concept_type, airflow info, prefect_equivalent,
        translation_rules, and source ("colin" or "fallback").
        Returns status "not_found" with suggestions if not matched.
    """
    knowledge = load_knowledge()

    # If no Colin output, use fallback directly
    if not knowledge:
        result = lookup(concept, {})
    else:
        result = lookup(concept, knowledge)

    return json.dumps(result, indent=2)
