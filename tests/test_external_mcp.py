"""Tests for external MCP client with configurable contracts."""

from __future__ import annotations

import asyncio
import os
from typing import Any
from unittest.mock import patch

import pytest

from airflow_unfactor.external_mcp import (
    ExternalMCPClient,
    FallbackMode,
    ProviderContract,
    TransportType,
    MCPServerConfig,
    _contract_from_env,
    _load_headers,
    _normalize_error,
    _to_contract,
    DEFAULT_PREFECT_CONTRACT,
)


class _DummyResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.reason_phrase = "OK" if status_code == 200 else "Error"

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError(
                "Error",
                request=None,  # type: ignore
                response=self,  # type: ignore
            )

    def json(self) -> dict[str, Any]:
        return self._payload


class _DummyAsyncClient:
    def __init__(self, timeout: float, response: _DummyResponse):
        self.timeout = timeout
        self.response = response
        self.last_url: str | None = None
        self.last_json: dict | None = None
        self.last_headers: dict | None = None

    async def __aenter__(self) -> "_DummyAsyncClient":
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def post(
        self,
        url: str,
        json: dict[str, Any],
        headers: dict[str, str],
    ) -> _DummyResponse:
        self.last_url = url
        self.last_json = json
        self.last_headers = headers
        return self.response


class TestProviderContract:
    """Tests for ProviderContract dataclass."""

    def test_default_values(self):
        """Test default contract values."""
        contract = ProviderContract(name="test", url="http://test.com")
        assert contract.transport == TransportType.HTTP_POST
        assert contract.tool_path == "/tools/{tool}"
        assert contract.payload_wrapper == "input"
        assert contract.timeout == 8.0
        assert contract.fallback_mode == FallbackMode.ERROR
        assert contract.enabled is True

    def test_custom_values(self):
        """Test custom contract values."""
        contract = ProviderContract(
            name="custom",
            url="http://custom.com",
            transport=TransportType.HTTP_RPC,
            tool_name="CustomTool",
            timeout=15.0,
            fallback_mode=FallbackMode.SILENT,
            enabled=False,
        )
        assert contract.transport == TransportType.HTTP_RPC
        assert contract.tool_name == "CustomTool"
        assert contract.timeout == 15.0
        assert contract.fallback_mode == FallbackMode.SILENT
        assert contract.enabled is False


class TestExternalMCPClient:
    """Tests for ExternalMCPClient."""

    def test_from_env_default_values(self):
        """Test client creation with default env values."""
        client = ExternalMCPClient.from_env()
        assert client.prefect.name == "prefect"
        assert client.astronomer.name == "astronomer"
        assert client.prefect.enabled is True

    def test_from_env_custom_url(self, monkeypatch):
        """Test client with custom URL from environment."""
        monkeypatch.setenv("MCP_PREFECT_URL", "http://custom-prefect.com")
        client = ExternalMCPClient.from_env()
        assert client.prefect.url == "http://custom-prefect.com"

    def test_from_env_disabled(self, monkeypatch):
        """Test client with disabled provider."""
        monkeypatch.setenv("MCP_PREFECT_ENABLED", "false")
        client = ExternalMCPClient.from_env()
        assert client.prefect.enabled is False

    def test_from_env_custom_timeout(self, monkeypatch):
        """Test client with custom timeout."""
        monkeypatch.setenv("MCP_PREFECT_TIMEOUT", "15.0")
        client = ExternalMCPClient.from_env()
        assert client.prefect.timeout == 15.0

    def test_from_env_fallback_mode(self, monkeypatch):
        """Test client with custom fallback mode."""
        monkeypatch.setenv("MCP_PREFECT_FALLBACK", "silent")
        client = ExternalMCPClient.from_env()
        assert client.prefect.fallback_mode == FallbackMode.SILENT

    def test_disabled_client(self):
        """Test disabled client creation."""
        client = ExternalMCPClient.disabled()
        assert client.prefect.enabled is False
        assert client.astronomer.enabled is False

    def test_call_disabled_provider(self):
        """Test calling disabled provider returns error."""
        client = ExternalMCPClient.disabled()
        result = asyncio.run(client.call_prefect_search("test query"))
        assert result["ok"] is False
        assert result["disabled"] is True
        assert "disabled" in result["error"].lower()


class TestMCPCallSuccess:
    """Tests for successful MCP calls."""

    def test_http_post_transport(self, monkeypatch):
        """Test HTTP POST transport success."""
        import airflow_unfactor.external_mcp as external_mcp

        response = _DummyResponse({"hits": [{"title": "Result"}]})
        dummy_client = None

        def make_client(timeout):
            nonlocal dummy_client
            dummy_client = _DummyAsyncClient(timeout, response)
            return dummy_client

        monkeypatch.setattr(external_mcp.httpx, "AsyncClient", make_client)

        contract = ProviderContract(
            name="test",
            url="http://test.com/mcp",
            tool_name="TestTool",
            headers={"Authorization": "Bearer token"},
        )
        client = ExternalMCPClient(prefect=contract, astronomer=contract)

        result = asyncio.run(client.call_prefect_search("test query"))

        assert result["ok"] is True
        assert result["tool"] == "TestTool"
        assert result["query"] == "test query"
        assert "elapsed_ms" in result
        assert result["result"] == {"hits": [{"title": "Result"}]}
        assert dummy_client.last_url == "http://test.com/mcp/tools/TestTool"
        assert dummy_client.last_json == {"input": {"query": "test query"}}


class TestMCPCallErrors:
    """Tests for MCP call error handling."""

    def test_error_fallback_mode_error(self):
        """Test error fallback mode returns error in response."""
        contract = ProviderContract(
            name="test",
            url="http://127.0.0.1:1",  # Will fail to connect
            tool_name="TestTool",
            timeout=0.01,
            fallback_mode=FallbackMode.ERROR,
        )
        client = ExternalMCPClient(prefect=contract, astronomer=contract)

        result = asyncio.run(client.call_prefect_search("test query"))

        assert result["ok"] is False
        assert result["tool"] == "TestTool"
        assert result["query"] == "test query"
        assert "error" in result
        assert "silenced" not in result

    def test_error_fallback_mode_silent(self):
        """Test silent fallback mode includes silenced flag."""
        contract = ProviderContract(
            name="test",
            url="http://127.0.0.1:1",
            tool_name="TestTool",
            timeout=0.01,
            fallback_mode=FallbackMode.SILENT,
        )
        client = ExternalMCPClient(prefect=contract, astronomer=contract)

        result = asyncio.run(client.call_prefect_search("test query"))

        assert result["ok"] is False
        assert result["silenced"] is True

    def test_error_fallback_mode_raise(self):
        """Test raise fallback mode raises exception."""
        contract = ProviderContract(
            name="test",
            url="http://127.0.0.1:1",
            tool_name="TestTool",
            timeout=0.01,
            fallback_mode=FallbackMode.RAISE,
        )
        client = ExternalMCPClient(prefect=contract, astronomer=contract)

        with pytest.raises(Exception):
            asyncio.run(client.call_prefect_search("test query"))


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_load_headers_valid_json(self):
        """Test loading headers from valid JSON."""
        headers = _load_headers('{"Authorization": "Bearer token"}')
        assert headers == {"Authorization": "Bearer token"}

    def test_load_headers_invalid_json(self):
        """Test loading headers from invalid JSON."""
        headers = _load_headers("not json")
        assert headers is None

    def test_load_headers_none(self):
        """Test loading headers from None."""
        headers = _load_headers(None)
        assert headers is None

    def test_load_headers_empty(self):
        """Test loading headers from empty string."""
        headers = _load_headers("")
        assert headers is None

    def test_normalize_error_timeout(self):
        """Test normalizing timeout error."""
        import httpx
        error = httpx.TimeoutException("timed out")
        assert _normalize_error(error) == "Request timed out"

    def test_normalize_error_connection(self):
        """Test normalizing connection error."""
        import httpx
        error = httpx.ConnectError("connection refused")
        assert "Connection failed" in _normalize_error(error)

    def test_normalize_error_generic(self):
        """Test normalizing generic error."""
        error = ValueError("something went wrong")
        assert _normalize_error(error) == "something went wrong"


class TestToContract:
    """Tests for _to_contract conversion."""

    def test_none_returns_default(self):
        """Test None input returns default contract."""
        result = _to_contract(None, DEFAULT_PREFECT_CONTRACT)
        assert result == DEFAULT_PREFECT_CONTRACT

    def test_contract_passthrough(self):
        """Test ProviderContract passes through unchanged."""
        contract = ProviderContract(name="custom", url="http://custom.com")
        result = _to_contract(contract, DEFAULT_PREFECT_CONTRACT)
        assert result == contract

    def test_legacy_config_conversion(self):
        """Test MCPServerConfig converts to ProviderContract."""
        legacy = MCPServerConfig(
            name="legacy",
            url="http://legacy.com",
            headers={"X-Custom": "value"},
        )
        result = _to_contract(legacy, DEFAULT_PREFECT_CONTRACT)

        assert result.name == "legacy"
        assert result.url == "http://legacy.com"
        assert result.headers == {"X-Custom": "value"}
        # Should inherit defaults from default contract
        assert result.tool_name == DEFAULT_PREFECT_CONTRACT.tool_name


class TestContractFromEnv:
    """Tests for _contract_from_env."""

    def test_default_values_when_no_env(self):
        """Test default values when no env vars set."""
        result = _contract_from_env("TEST", DEFAULT_PREFECT_CONTRACT)
        assert result.url == DEFAULT_PREFECT_CONTRACT.url
        assert result.enabled is True
        assert result.timeout == DEFAULT_PREFECT_CONTRACT.timeout

    def test_custom_url(self, monkeypatch):
        """Test custom URL from env."""
        monkeypatch.setenv("MCP_TEST_URL", "http://custom.com")
        result = _contract_from_env("TEST", DEFAULT_PREFECT_CONTRACT)
        assert result.url == "http://custom.com"

    def test_disabled(self, monkeypatch):
        """Test disabled from env."""
        monkeypatch.setenv("MCP_TEST_ENABLED", "false")
        result = _contract_from_env("TEST", DEFAULT_PREFECT_CONTRACT)
        assert result.enabled is False

    def test_invalid_fallback_uses_default(self, monkeypatch):
        """Test invalid fallback mode uses default."""
        monkeypatch.setenv("MCP_TEST_FALLBACK", "invalid")
        result = _contract_from_env("TEST", DEFAULT_PREFECT_CONTRACT)
        assert result.fallback_mode == DEFAULT_PREFECT_CONTRACT.fallback_mode
