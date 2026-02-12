"""External MCP client integration.

See specs/external-mcp-integration.openspec.md
"""

import json
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class MCPServerConfig:
    name: str
    url: str
    transport: str = "http"
    headers: dict[str, str] | None = None


class ExternalMCPClient:
    """Client to call external MCP servers."""

    def __init__(self, prefect: MCPServerConfig, astronomer: MCPServerConfig):
        self.prefect = prefect
        self.astronomer = astronomer

    @staticmethod
    def from_env() -> "ExternalMCPClient":
        prefect_url = os.getenv("MCP_PREFECT_URL", "https://docs.prefect.io/mcp")
        astronomer_url = os.getenv("MCP_ASTRONOMER_URL", "https://mcpmarket.com/ja/tools/skills/airflow-2-to-3-migration")
        prefect_headers = _load_headers(os.getenv("MCP_PREFECT_HEADERS"))
        astronomer_headers = _load_headers(os.getenv("MCP_ASTRONOMER_HEADERS"))

        return ExternalMCPClient(
            prefect=MCPServerConfig("prefect", prefect_url, headers=prefect_headers),
            astronomer=MCPServerConfig("astronomer", astronomer_url, headers=astronomer_headers),
        )

    async def call_prefect_search(self, query: str, timeout: float = 8.0) -> dict[str, Any]:
        """Call Prefect MCP Search tool."""
        return await _mcp_call(self.prefect, "SearchPrefect", {"query": query}, timeout)

    async def call_astronomer_migration(self, query: str, timeout: float = 8.0) -> dict[str, Any]:
        """Call Astronomer MCP migration tool."""
        # Using generic tool name; may vary by server implementation
        return await _mcp_call(self.astronomer, "Airflow2to3Migration", {"query": query}, timeout)


def _load_headers(value: str | None) -> dict[str, str] | None:
    if not value:
        return None
    try:
        data = json.loads(value)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except json.JSONDecodeError:
        return None
    return None


async def _mcp_call(
    server: MCPServerConfig,
    tool_name: str,
    payload: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    """Call MCP tool over HTTP transport.

    Follows JSON schema:
    POST {server.url}/tools/{tool_name}
    {"input": payload}
    """
    url = server.url.rstrip("/")

    # Common MCP HTTP tool invocation path
    tool_url = f"{url}/tools/{tool_name}"

    headers = server.headers or {}

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(tool_url, json={"input": payload}, headers=headers)
            resp.raise_for_status()
            return {
                "ok": True,
                "tool": tool_name,
                "elapsed_ms": int((time.time() - start) * 1000),
                "result": resp.json(),
            }
    except Exception as e:
        return {
            "ok": False,
            "tool": tool_name,
            "elapsed_ms": int((time.time() - start) * 1000),
            "error": str(e),
        }
