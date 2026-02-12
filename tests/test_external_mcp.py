"""Tests for external MCP client payload shape."""

from __future__ import annotations

import asyncio
from typing import Any

from airflow_unfactor.external_mcp import MCPServerConfig, _mcp_call


class _DummyResponse:
    def __init__(self, payload: dict[str, Any]):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _DummyAsyncClient:
    def __init__(self, timeout: float):
        self.timeout = timeout

    async def __aenter__(self) -> "_DummyAsyncClient":
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def post(
        self,
        tool_url: str,
        json: dict[str, Any],
        headers: dict[str, str],
    ) -> _DummyResponse:
        assert tool_url.endswith("/tools/SearchPrefect")
        assert json == {"input": {"query": "taskflow conversion"}}
        assert headers == {"x-test": "1"}
        return _DummyResponse({"hits": [{"title": "Taskflow"}]})


def test_mcp_call_success_includes_query(monkeypatch) -> None:
    import airflow_unfactor.external_mcp as external_mcp

    monkeypatch.setattr(external_mcp.httpx, "AsyncClient", _DummyAsyncClient)
    server = MCPServerConfig(
        name="prefect",
        url="https://docs.prefect.io/mcp",
        headers={"x-test": "1"},
    )

    result = asyncio.run(
        _mcp_call(
            server=server,
            tool_name="SearchPrefect",
            payload={"query": "taskflow conversion"},
            timeout=8.0,
        )
    )

    assert result["ok"] is True
    assert result["tool"] == "SearchPrefect"
    assert result["query"] == "taskflow conversion"
    assert "result" in result
    assert "error" not in result


def test_mcp_call_error_includes_query() -> None:
    server = MCPServerConfig(name="prefect", url="http://127.0.0.1:1")

    result = asyncio.run(
        _mcp_call(
            server=server,
            tool_name="SearchPrefect",
            payload={"query": "taskflow conversion"},
            timeout=0.01,
        )
    )

    assert result["ok"] is False
    assert result["tool"] == "SearchPrefect"
    assert result["query"] == "taskflow conversion"
    assert "error" in result
    assert "result" not in result
