"""External MCP client integration.

Supports configurable MCP invocation contracts per provider with fallback modes.
"""

import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx


class TransportType(str, Enum):
    """Supported MCP transport types."""

    HTTP_POST = "http_post"  # POST /tools/{tool}
    HTTP_RPC = "http_rpc"  # POST / with {"method": "tools/call", ...}
    STDIO = "stdio"  # Not implemented - placeholder for future


class FallbackMode(str, Enum):
    """How to handle MCP call failures."""

    SILENT = "silent"  # Return empty result, no error
    ERROR = "error"  # Return error in response
    RAISE = "raise"  # Raise exception


@dataclass
class ProviderContract:
    """Contract defining how to invoke a specific MCP provider."""

    name: str
    url: str
    transport: TransportType = TransportType.HTTP_POST
    tool_name: str = ""  # Actual tool name to call
    tool_path: str = "/tools/{tool}"  # URL path template
    payload_wrapper: str = "input"  # Key to wrap payload in
    headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 8.0
    fallback_mode: FallbackMode = FallbackMode.ERROR
    enabled: bool = True


# Default provider contracts
DEFAULT_PREFECT_CONTRACT = ProviderContract(
    name="prefect",
    url="https://docs.prefect.io/mcp",
    transport=TransportType.HTTP_POST,
    tool_name="SearchPrefect",
    tool_path="/tools/{tool}",
    payload_wrapper="input",
    timeout=8.0,
    fallback_mode=FallbackMode.SILENT,
)

DEFAULT_ASTRONOMER_CONTRACT = ProviderContract(
    name="astronomer",
    url="https://mcpmarket.com/ja/tools/skills/airflow-2-to-3-migration",
    transport=TransportType.HTTP_POST,
    tool_name="Airflow2to3Migration",
    tool_path="/tools/{tool}",
    payload_wrapper="input",
    timeout=8.0,
    fallback_mode=FallbackMode.SILENT,
)


@dataclass
class MCPServerConfig:
    """Legacy config - kept for backward compatibility."""

    name: str
    url: str
    transport: str = "http"
    headers: dict[str, str] | None = None


class ExternalMCPClient:
    """Client to call external MCP servers with configurable contracts."""

    def __init__(
        self,
        prefect: ProviderContract | MCPServerConfig | None = None,
        astronomer: ProviderContract | MCPServerConfig | None = None,
    ):
        # Convert legacy configs to contracts
        self.prefect = _to_contract(prefect, DEFAULT_PREFECT_CONTRACT)
        self.astronomer = _to_contract(astronomer, DEFAULT_ASTRONOMER_CONTRACT)

    @staticmethod
    def from_env() -> "ExternalMCPClient":
        """Create client from environment variables.

        Environment variables:
          MCP_PREFECT_URL: Prefect MCP server URL
          MCP_PREFECT_ENABLED: Set to "false" to disable
          MCP_PREFECT_TIMEOUT: Timeout in seconds
          MCP_PREFECT_HEADERS: JSON headers dict
          MCP_PREFECT_TOOL: Tool name override
          MCP_PREFECT_FALLBACK: silent|error|raise

          MCP_ASTRONOMER_URL: Astronomer MCP server URL
          MCP_ASTRONOMER_ENABLED: Set to "false" to disable
          MCP_ASTRONOMER_TIMEOUT: Timeout in seconds
          MCP_ASTRONOMER_HEADERS: JSON headers dict
          MCP_ASTRONOMER_TOOL: Tool name override
          MCP_ASTRONOMER_FALLBACK: silent|error|raise
        """
        prefect = _contract_from_env("PREFECT", DEFAULT_PREFECT_CONTRACT)
        astronomer = _contract_from_env("ASTRONOMER", DEFAULT_ASTRONOMER_CONTRACT)

        return ExternalMCPClient(prefect=prefect, astronomer=astronomer)

    @staticmethod
    def disabled() -> "ExternalMCPClient":
        """Create client with all providers disabled."""
        prefect = ProviderContract(**{**DEFAULT_PREFECT_CONTRACT.__dict__, "enabled": False})
        astronomer = ProviderContract(**{**DEFAULT_ASTRONOMER_CONTRACT.__dict__, "enabled": False})
        return ExternalMCPClient(prefect=prefect, astronomer=astronomer)

    async def call_prefect_search(self, query: str, timeout: float | None = None) -> dict[str, Any]:
        """Call Prefect MCP Search tool."""
        return await self._call_provider(self.prefect, {"query": query}, timeout)

    async def call_astronomer_migration(
        self, query: str, timeout: float | None = None
    ) -> dict[str, Any]:
        """Call Astronomer MCP migration tool."""
        return await self._call_provider(self.astronomer, {"query": query}, timeout)

    async def _call_provider(
        self,
        contract: ProviderContract,
        payload: dict[str, Any],
        timeout_override: float | None = None,
    ) -> dict[str, Any]:
        """Execute MCP call according to provider contract."""
        if not contract.enabled:
            return _disabled_response(contract)

        timeout = timeout_override or contract.timeout
        start = time.time()
        query = str(payload.get("query", ""))

        try:
            result = await _execute_transport(contract, payload, timeout)
            return {
                "ok": True,
                "tool": contract.tool_name,
                "query": query,
                "elapsed_ms": int((time.time() - start) * 1000),
                "result": result,
            }
        except Exception as e:
            return _handle_error(contract, query, start, e)


def _to_contract(
    config: ProviderContract | MCPServerConfig | None,
    default: ProviderContract,
) -> ProviderContract:
    """Convert config to ProviderContract."""
    if config is None:
        return default
    if isinstance(config, ProviderContract):
        return config
    # Legacy MCPServerConfig
    return ProviderContract(
        name=config.name,
        url=config.url,
        headers=config.headers or {},
        tool_name=default.tool_name,
        tool_path=default.tool_path,
        payload_wrapper=default.payload_wrapper,
        timeout=default.timeout,
        fallback_mode=default.fallback_mode,
    )


def _contract_from_env(prefix: str, default: ProviderContract) -> ProviderContract:
    """Load contract configuration from environment variables."""
    env_prefix = f"MCP_{prefix}_"

    url = os.getenv(f"{env_prefix}URL", default.url)
    enabled = os.getenv(f"{env_prefix}ENABLED", "true").lower() != "false"
    timeout_str = os.getenv(f"{env_prefix}TIMEOUT")
    timeout = float(timeout_str) if timeout_str else default.timeout
    headers = _load_headers(os.getenv(f"{env_prefix}HEADERS")) or default.headers
    tool_name = os.getenv(f"{env_prefix}TOOL", default.tool_name)
    fallback_str = os.getenv(f"{env_prefix}FALLBACK", default.fallback_mode.value)

    try:
        fallback_mode = FallbackMode(fallback_str.lower())
    except ValueError:
        fallback_mode = default.fallback_mode

    return ProviderContract(
        name=default.name,
        url=url,
        transport=default.transport,
        tool_name=tool_name,
        tool_path=default.tool_path,
        payload_wrapper=default.payload_wrapper,
        headers=headers,
        timeout=timeout,
        fallback_mode=fallback_mode,
        enabled=enabled,
    )


def _load_headers(value: str | None) -> dict[str, str] | None:
    """Parse JSON headers from environment variable."""
    if not value:
        return None
    try:
        data = json.loads(value)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except json.JSONDecodeError:
        return None
    return None


async def _execute_transport(
    contract: ProviderContract,
    payload: dict[str, Any],
    timeout: float,
) -> Any:
    """Execute MCP call over configured transport."""
    if contract.transport == TransportType.HTTP_POST:
        return await _http_post_transport(contract, payload, timeout)
    elif contract.transport == TransportType.HTTP_RPC:
        return await _http_rpc_transport(contract, payload, timeout)
    else:
        raise ValueError(f"Unsupported transport: {contract.transport}")


async def _http_post_transport(
    contract: ProviderContract,
    payload: dict[str, Any],
    timeout: float,
) -> Any:
    """HTTP POST transport: POST /tools/{tool}"""
    url = contract.url.rstrip("/")
    tool_path = contract.tool_path.format(tool=contract.tool_name)
    tool_url = f"{url}{tool_path}"

    # Wrap payload according to contract
    body = {contract.payload_wrapper: payload} if contract.payload_wrapper else payload

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(tool_url, json=body, headers=contract.headers)
        resp.raise_for_status()
        return resp.json()


async def _http_rpc_transport(
    contract: ProviderContract,
    payload: dict[str, Any],
    timeout: float,
) -> Any:
    """HTTP RPC transport: POST / with JSON-RPC style body"""
    url = contract.url.rstrip("/")

    body = {
        "method": f"tools/{contract.tool_name}",
        "params": payload,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=body, headers=contract.headers)
        resp.raise_for_status()
        result = resp.json()
        # Extract result from RPC response
        if isinstance(result, dict) and "result" in result:
            return result["result"]
        return result


def _disabled_response(contract: ProviderContract) -> dict[str, Any]:
    """Return response for disabled provider."""
    return {
        "ok": False,
        "tool": contract.tool_name,
        "query": "",
        "elapsed_ms": 0,
        "error": f"Provider '{contract.name}' is disabled",
        "disabled": True,
    }


def _handle_error(
    contract: ProviderContract,
    query: str,
    start: float,
    error: Exception,
) -> dict[str, Any]:
    """Handle error according to fallback mode."""
    elapsed_ms = int((time.time() - start) * 1000)
    error_msg = _normalize_error(error)

    if contract.fallback_mode == FallbackMode.RAISE:
        raise error

    if contract.fallback_mode == FallbackMode.SILENT:
        return {
            "ok": False,
            "tool": contract.tool_name,
            "query": query,
            "elapsed_ms": elapsed_ms,
            "error": error_msg,
            "silenced": True,
        }

    # FallbackMode.ERROR (default)
    return {
        "ok": False,
        "tool": contract.tool_name,
        "query": query,
        "elapsed_ms": elapsed_ms,
        "error": error_msg,
    }


def _normalize_error(error: Exception) -> str:
    """Normalize error message for consistent output."""
    if isinstance(error, httpx.HTTPStatusError):
        return f"HTTP {error.response.status_code}: {error.response.reason_phrase}"
    if isinstance(error, httpx.ConnectError):
        return f"Connection failed: {error}"
    if isinstance(error, httpx.TimeoutException):
        return "Request timed out"
    return str(error)
