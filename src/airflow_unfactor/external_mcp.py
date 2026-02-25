"""External MCP client for Prefect documentation search.

Simple httpx-based client. Errors are returned explicitly, never swallowed.
"""

import os
from typing import Any

import httpx

# Defaults
DEFAULT_PREFECT_URL = "https://docs.prefect.io/mcp"
DEFAULT_TIMEOUT = 10.0


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
    tool_url = f"{url}/tools/SearchPrefect"

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(tool_url, json={"input": {"query": query}})
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        return {"error": f"Cannot connect to Prefect MCP at {url}. Run 'colin run' for cached context."}
    except httpx.TimeoutException:
        return {"error": f"Prefect MCP request timed out after {DEFAULT_TIMEOUT}s"}
    except httpx.HTTPStatusError as e:
        return {"error": f"Prefect MCP returned HTTP {e.response.status_code}"}
    except Exception as e:
        return {"error": f"Prefect MCP error: {e}"}
