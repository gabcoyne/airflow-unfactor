"""Drift detection tests — verify docs and code agree.

These tests import the live MCP server, introspect registered tools,
and assert they match what README.md and the docs-site claim. If someone
adds a tool but forgets the README (or vice-versa), these fail.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

from airflow_unfactor.server import mcp

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
DOCS_MCP = ROOT / "docs-site" / "src" / "app" / "docs" / "mcp" / "page.mdx"
DOCS_SCHEMAS = ROOT / "docs-site" / "src" / "app" / "docs" / "mcp" / "schemas" / "page.mdx"
DOCS_INSTALL = (
    ROOT / "docs-site" / "src" / "app" / "docs" / "getting-started" / "installation" / "page.mdx"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def live_tools():
    """Return the list of tools registered on the live MCP server."""
    return asyncio.run(mcp.list_tools())


@pytest.fixture(scope="module")
def live_tool_names(live_tools):
    return {t.name for t in live_tools}


@pytest.fixture(scope="module")
def live_tool_map(live_tools):
    """Map tool name → tool object for parameter inspection."""
    return {t.name: t for t in live_tools}


# ---------------------------------------------------------------------------
# 1. Tool names match across code and docs
# ---------------------------------------------------------------------------


class TestToolNamesMatch:
    """README and docs-site must list exactly the tools the server registers."""

    def _extract_backtick_tool_names(self, text: str) -> set[str]:
        """Pull tool names from markdown backtick-code in table rows."""
        # Matches `tool_name` in table rows like | `read_dag` | ...
        return set(re.findall(r"\|\s*`(\w+)`\s*\|", text))

    def test_readme_tool_table_matches_server(self, live_tool_names):
        readme_text = README.read_text()
        readme_tools = self._extract_backtick_tool_names(readme_text)
        assert readme_tools == live_tool_names, (
            f"README tools {readme_tools} != server tools {live_tool_names}"
        )

    def test_docs_mcp_page_lists_all_tools(self, live_tool_names):
        docs_text = DOCS_MCP.read_text()
        # Tool names appear as ### `tool_name` headings
        heading_tools = set(re.findall(r"###\s*`(\w+)`", docs_text))
        assert heading_tools == live_tool_names, (
            f"docs/mcp tools {heading_tools} != server tools {live_tool_names}"
        )

    def test_docs_schemas_page_lists_all_tools(self, live_tool_names):
        schema_text = DOCS_SCHEMAS.read_text()
        heading_tools = set(re.findall(r"###\s*(\w+)", schema_text))
        assert heading_tools == live_tool_names, (
            f"docs/schemas tools {heading_tools} != server tools {live_tool_names}"
        )


# ---------------------------------------------------------------------------
# 2. Tool count claims are accurate
# ---------------------------------------------------------------------------


class TestToolCount:
    """Install docs say 'N tools listed' — the server must have exactly N."""

    def test_install_docs_tool_count(self, live_tools):
        install_text = DOCS_INSTALL.read_text()
        match = re.search(r"(\d+)\s+tools?\s+listed", install_text)
        assert match, "Install docs should mention how many tools are listed"
        claimed = int(match.group(1))
        assert len(live_tools) == claimed, (
            f"Install docs claim {claimed} tools, server has {len(live_tools)}"
        )

    def test_readme_says_seven_tools(self, live_tools):
        readme_text = README.read_text()
        assert "seven tools" in readme_text.lower(), (
            "README should mention 'seven tools'"
        )
        assert len(live_tools) == 7, (
            f"README says seven tools, server has {len(live_tools)}"
        )


# ---------------------------------------------------------------------------
# 3. Tool parameters match the live schema
# ---------------------------------------------------------------------------


class TestToolParameters:
    """Every tool's documented params must match the live server schema."""

    def test_scaffold_params_match_server(self, live_tool_map):
        scaffold = live_tool_map["scaffold"]
        schema = scaffold.parameters
        live_params = set(schema.get("properties", {}).keys())
        live_required = set(schema.get("required", []))

        expected_params = {
            "output_directory",
            "project_name",
            "workspace",
            "flow_names",
            "include_docker",
            "include_github_actions",
            "schedule_interval",
        }
        assert live_params == expected_params, (
            f"scaffold params {live_params} != expected {expected_params}"
        )
        assert live_required == {"output_directory"}

    def test_validate_params_match_server(self, live_tool_map):
        validate = live_tool_map["validate"]
        schema = validate.parameters
        live_params = set(schema.get("properties", {}).keys())
        live_required = set(schema.get("required", []))

        assert live_params == {"original_dag", "converted_flow"}
        assert live_required == {"original_dag", "converted_flow"}

    def test_read_dag_params_match_server(self, live_tool_map):
        read_dag = live_tool_map["read_dag"]
        schema = read_dag.parameters
        live_params = set(schema.get("properties", {}).keys())
        assert live_params == {"path", "content"}

    def test_lookup_concept_params_match_server(self, live_tool_map):
        lookup = live_tool_map["lookup_concept"]
        schema = lookup.parameters
        live_params = set(schema.get("properties", {}).keys())
        live_required = set(schema.get("required", []))
        assert live_params == {"concept"}
        assert live_required == {"concept"}

    def test_search_prefect_docs_params_match_server(self, live_tool_map):
        search = live_tool_map["search_prefect_docs"]
        schema = search.parameters
        live_params = set(schema.get("properties", {}).keys())
        live_required = set(schema.get("required", []))
        assert live_params == {"query"}
        assert live_required == {"query"}

    def test_schemas_doc_scaffold_has_all_params(self, live_tool_map):
        """The schemas page must document every scaffold parameter."""
        import json

        scaffold = live_tool_map["scaffold"]
        live_params = set(scaffold.parameters.get("properties", {}).keys())

        schema_text = DOCS_SCHEMAS.read_text()
        # Extract the scaffold section, then isolate the Input JSON block
        scaffold_section = schema_text.split("### scaffold")[1].split("### ")[0]
        input_block = scaffold_section.split("**Input:**")[1].split("**Output:**")[0]
        json_match = re.search(r"```json\n(.*?)```", input_block, re.DOTALL)
        assert json_match, "Scaffold input schema JSON block not found"
        schema = json.loads(json_match.group(1))
        doc_params = set(schema.get("properties", {}).keys())

        assert doc_params == live_params, (
            f"Schemas doc scaffold params {doc_params} != server params {live_params}"
        )


# ---------------------------------------------------------------------------
# 4. README doesn't claim features that don't exist
# ---------------------------------------------------------------------------


class TestNoFictionalFeatures:
    """The README must not reference features we removed or never built."""

    FICTIONAL_PATTERNS = [
        r"--ui\b",
        r"\[ui\]",
        r"`analyze`",
        r"`convert`",
        r"`explain`",
        r"`batch`",
    ]

    def test_no_fictional_features_in_readme(self):
        readme_text = README.read_text()
        for pattern in self.FICTIONAL_PATTERNS:
            assert not re.search(pattern, readme_text, re.IGNORECASE), (
                f"README contains fictional feature pattern: {pattern}"
            )

    def test_no_fictional_features_in_docs_mcp(self):
        docs_text = DOCS_MCP.read_text()
        for pattern in self.FICTIONAL_PATTERNS:
            assert not re.search(pattern, docs_text, re.IGNORECASE), (
                f"docs/mcp contains fictional feature pattern: {pattern}"
            )


# ---------------------------------------------------------------------------
# 5. Config snippets use consistent commands
# ---------------------------------------------------------------------------


class TestConfigSnippets:
    """All client config JSON blocks should use `uvx`, not `uv --directory`."""

    def _extract_json_blocks(self, text: str) -> list[str]:
        return re.findall(r"```json\n(.*?)```", text, re.DOTALL)

    def test_readme_config_uses_uvx(self):
        readme_text = README.read_text()
        for block in self._extract_json_blocks(readme_text):
            if "mcpServers" in block:
                assert "uvx" in block, "README config should use uvx"
                assert "uv --directory" not in block, (
                    "README config should not use 'uv --directory'"
                )

    def test_install_docs_config_uses_uvx(self):
        install_text = DOCS_INSTALL.read_text()
        for block in self._extract_json_blocks(install_text):
            if "mcpServers" in block:
                assert "uvx" in block, "Install docs config should use uvx"
                assert "uv --directory" not in block, (
                    "Install docs config should not use 'uv --directory'"
                )
