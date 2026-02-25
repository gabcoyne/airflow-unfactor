"""Tests for simplified external MCP client."""

import asyncio
from unittest.mock import AsyncMock, patch

import httpx

from airflow_unfactor.external_mcp import search_prefect_mcp


class TestSearchPrefectMCP:
    """Tests for search_prefect_mcp function."""

    def test_disabled_returns_error(self, monkeypatch):
        """Disabled via env var returns explicit error."""
        monkeypatch.setenv("MCP_PREFECT_ENABLED", "false")
        result = asyncio.run(search_prefect_mcp("test query"))
        assert "error" in result
        assert "disabled" in result["error"].lower()

    def test_success_returns_results(self, monkeypatch):
        """Successful call returns JSON response."""
        from unittest.mock import MagicMock

        monkeypatch.setenv("MCP_PREFECT_ENABLED", "true")

        # Use MagicMock for response since httpx Response.json() is sync
        mock_response = MagicMock()
        mock_response.json.return_value = {"hits": [{"title": "Prefect Flows"}]}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("airflow_unfactor.external_mcp.httpx.AsyncClient", return_value=mock_client):
            result = asyncio.run(search_prefect_mcp("Prefect flows"))

        assert result == {"hits": [{"title": "Prefect Flows"}]}
        mock_client.post.assert_called_once()

    def test_connection_error_returns_error(self, monkeypatch):
        """Connection failure returns descriptive error, not silent empty result."""
        monkeypatch.setenv("MCP_PREFECT_ENABLED", "true")

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        with patch("airflow_unfactor.external_mcp.httpx.AsyncClient", return_value=mock_client):
            result = asyncio.run(search_prefect_mcp("test"))

        assert "error" in result
        assert "Cannot connect" in result["error"]
        assert "colin run" in result["error"]

    def test_timeout_returns_error(self, monkeypatch):
        """Timeout returns descriptive error."""
        monkeypatch.setenv("MCP_PREFECT_ENABLED", "true")

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        with patch("airflow_unfactor.external_mcp.httpx.AsyncClient", return_value=mock_client):
            result = asyncio.run(search_prefect_mcp("test"))

        assert "error" in result
        assert "timed out" in result["error"].lower()

    def test_custom_url(self, monkeypatch):
        """Custom URL from environment is used."""
        from unittest.mock import MagicMock

        monkeypatch.setenv("MCP_PREFECT_ENABLED", "true")
        monkeypatch.setenv("MCP_PREFECT_URL", "http://custom.example.com/mcp")

        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("airflow_unfactor.external_mcp.httpx.AsyncClient", return_value=mock_client):
            asyncio.run(search_prefect_mcp("test"))

        call_args = mock_client.post.call_args
        assert "custom.example.com" in call_args[0][0]

    def test_default_enabled(self, monkeypatch):
        """Enabled by default when env var not set."""
        monkeypatch.delenv("MCP_PREFECT_ENABLED", raising=False)

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("no server"))

        with patch("airflow_unfactor.external_mcp.httpx.AsyncClient", return_value=mock_client):
            result = asyncio.run(search_prefect_mcp("test"))

        # Should attempt the call (not return "disabled")
        assert "disabled" not in result.get("error", "")
