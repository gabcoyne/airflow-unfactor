"""Tests for external MCP client."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from airflow_unfactor.external_mcp import search_prefect_mcp


def _mock_call_tool_result(texts: list[str]):
    """Create a mock CallToolResult with text content items."""
    result = MagicMock()
    items = []
    for text in texts:
        item = MagicMock()
        item.text = text
        items.append(item)
    result.content = items
    return result


class TestSearchPrefectMCP:
    """Tests for search_prefect_mcp function."""

    def test_disabled_returns_error(self, monkeypatch):
        """Disabled via env var returns explicit error."""
        monkeypatch.setenv("MCP_PREFECT_ENABLED", "false")
        result = asyncio.run(search_prefect_mcp("test query"))
        assert "error" in result
        assert "disabled" in result["error"].lower()

    def test_success_returns_results(self, monkeypatch):
        """Successful call returns search results."""
        monkeypatch.setenv("MCP_PREFECT_ENABLED", "true")

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.call_tool = AsyncMock(
            return_value=_mock_call_tool_result(["Title: Prefect Flows\nContent: ..."])
        )

        with patch("airflow_unfactor.external_mcp.Client", return_value=mock_client):
            result = asyncio.run(search_prefect_mcp("Prefect flows"))

        assert "results" in result
        assert len(result["results"]) == 1
        assert "Prefect Flows" in result["results"][0]
        assert result["query"] == "Prefect flows"
        mock_client.call_tool.assert_called_once_with("SearchPrefect", {"query": "Prefect flows"})

    def test_connection_error_returns_error(self, monkeypatch):
        """Connection failure returns descriptive error."""
        monkeypatch.setenv("MCP_PREFECT_ENABLED", "true")

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(side_effect=ConnectionRefusedError("Connection refused"))

        with patch("airflow_unfactor.external_mcp.Client", return_value=mock_client):
            result = asyncio.run(search_prefect_mcp("test"))

        assert "error" in result
        assert "connect" in result["error"].lower() or "refused" in result["error"].lower()

    def test_timeout_returns_error(self, monkeypatch):
        """Timeout returns descriptive error."""
        monkeypatch.setenv("MCP_PREFECT_ENABLED", "true")

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(side_effect=TimeoutError("Request timeout"))

        with patch("airflow_unfactor.external_mcp.Client", return_value=mock_client):
            result = asyncio.run(search_prefect_mcp("test"))

        assert "error" in result
        assert "timed out" in result["error"].lower()

    def test_custom_url(self, monkeypatch):
        """Custom URL from environment is used."""
        monkeypatch.setenv("MCP_PREFECT_ENABLED", "true")
        monkeypatch.setenv("MCP_PREFECT_URL", "http://custom.example.com/mcp")

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.call_tool = AsyncMock(return_value=_mock_call_tool_result(["result"]))

        with patch("airflow_unfactor.external_mcp.Client", return_value=mock_client) as mock_cls:
            asyncio.run(search_prefect_mcp("test"))

        # Verify the Client was constructed with the custom URL
        mock_cls.assert_called_once_with("http://custom.example.com/mcp")

    def test_default_enabled(self, monkeypatch):
        """Enabled by default when env var not set."""
        monkeypatch.delenv("MCP_PREFECT_ENABLED", raising=False)

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(side_effect=ConnectionRefusedError("no server"))

        with patch("airflow_unfactor.external_mcp.Client", return_value=mock_client):
            result = asyncio.run(search_prefect_mcp("test"))

        # Should attempt the call (not return "disabled")
        assert "disabled" not in result.get("error", "")
