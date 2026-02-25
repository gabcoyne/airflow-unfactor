"""Search Prefect documentation via the Prefect MCP server.

Wraps external_mcp.search_prefect_mcp as an MCP tool.
"""

import json

from airflow_unfactor.external_mcp import search_prefect_mcp


async def search_prefect_docs(query: str) -> str:
    """Search current Prefect documentation.

    Queries the Prefect MCP server for real-time documentation beyond
    what Colin pre-compiled. Returns search results or an error with
    suggestions.

    Args:
        query: Search query for Prefect docs.

    Returns:
        JSON with search results, or error with suggestion to run 'colin run'.
    """
    result = await search_prefect_mcp(query)
    return json.dumps(result, indent=2)
