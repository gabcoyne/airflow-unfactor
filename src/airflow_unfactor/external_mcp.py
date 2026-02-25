"""External MCP client for Prefect documentation search.

Uses FastMCP Client to communicate with the Prefect MCP server
via the Streamable HTTP transport. Errors are returned explicitly.
"""

import os
from typing import Any

from fastmcp import Client

# Defaults
DEFAULT_PREFECT_URL = "https://docs.prefect.io/mcp"
DEFAULT_TIMEOUT = 15.0


async def search_prefect_mcp(query: str) -> dict[str, Any]:
    """Search Prefect documentation via the Prefect MCP server.

    Configuration via environment variables:
        MCP_PREFECT_ENABLED: "true" (default) or "false"
        MCP_PREFECT_URL: MCP server URL (default: https://docs.prefect.io/mcp)

    Args:
        query: Search query for Prefect docs.

    Returns:
        Dict with search results, or {"error": "..."} on failure.
    """
    enabled = os.getenv("MCP_PREFECT_ENABLED", "true").lower() != "false"
    if not enabled:
        return {"error": "Prefect MCP search is disabled (MCP_PREFECT_ENABLED=false)"}

    url = os.getenv("MCP_PREFECT_URL", DEFAULT_PREFECT_URL).rstrip("/")

    try:
        async with Client(url) as client:
            result = await client.call_tool("SearchPrefect", {"query": query})
            # Extract text content from CallToolResult
            results = []
            for item in result.content:
                if hasattr(item, "text"):
                    results.append(item.text)  # type: ignore[union-attr]
            return {"results": results, "query": query, "source": url}
    except Exception as e:
        error_msg = str(e)
        if "connect" in error_msg.lower() or "refused" in error_msg.lower():
            return {
                "error": f"Cannot connect to Prefect MCP at {url}. Run 'colin run' for cached context."
            }
        if "timeout" in error_msg.lower():
            return {"error": f"Prefect MCP request timed out after {DEFAULT_TIMEOUT}s"}
        return {"error": f"Prefect MCP error: {error_msg}"}
