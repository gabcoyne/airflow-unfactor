"""Tests for search_prefect_docs tool."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

from airflow_unfactor.tools.search_docs import search_prefect_docs


class TestSearchPrefectDocs:
    """Tests for search_prefect_docs wrapper."""

    def test_returns_results(self):
        """Successful search returns JSON results."""
        with patch(
            "airflow_unfactor.tools.search_docs.search_prefect_mcp",
            new_callable=AsyncMock,
            return_value={"hits": [{"title": "Work Pools"}]},
        ):
            result = json.loads(asyncio.run(search_prefect_docs("work pools")))

        assert result == {"hits": [{"title": "Work Pools"}]}

    def test_returns_error_when_unavailable(self):
        """Error from MCP client is passed through."""
        with patch(
            "airflow_unfactor.tools.search_docs.search_prefect_mcp",
            new_callable=AsyncMock,
            return_value={"error": "Cannot connect to Prefect MCP at https://docs.prefect.io/mcp. Run 'colin run' for cached context."},
        ):
            result = json.loads(asyncio.run(search_prefect_docs("test")))

        assert "error" in result
        assert "colin run" in result["error"]

    def test_returns_disabled_error(self):
        """Disabled MCP returns disabled error."""
        with patch(
            "airflow_unfactor.tools.search_docs.search_prefect_mcp",
            new_callable=AsyncMock,
            return_value={"error": "Prefect MCP search is disabled (MCP_PREFECT_ENABLED=false)"},
        ):
            result = json.loads(asyncio.run(search_prefect_docs("test")))

        assert "disabled" in result["error"].lower()
