"""External MCP proxy tools.

See specs/external-mcp-integration.openspec.md
"""

from airflow_unfactor.external_mcp import ExternalMCPClient


async def prefect_search(query: str) -> str:
    client = ExternalMCPClient.from_env()
    result = await client.call_prefect_search(query)
    return str(result)


async def astronomer_migration(query: str) -> str:
    client = ExternalMCPClient.from_env()
    result = await client.call_astronomer_migration(query)
    return str(result)
