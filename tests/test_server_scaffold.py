"""MCP-level tests for the scaffold wrapper in server.py.

These tests import the MCP-decorated scaffold() function directly and call it
via asyncio.run(), proving that schedule_interval flows from the MCP wrapper
through to scaffold_project() and into the generated prefect.yaml.
"""

import asyncio
import json

from airflow_unfactor.server import scaffold


class TestMCPScaffoldScheduleForwarding:
    """Tests that schedule_interval flows through the MCP scaffold wrapper."""

    def test_mcp_scaffold_forwards_schedule_interval(self, tmp_path):
        """schedule_interval is forwarded to scaffold_project and appears in prefect.yaml."""
        output_dir = tmp_path / "output"

        result_json = asyncio.run(
            scaffold(output_directory=str(output_dir), schedule_interval="0 6 * * *")
        )
        result = json.loads(result_json)

        assert result_json  # non-empty response
        prefect_yaml = (output_dir / "prefect.yaml").read_text()
        assert 'cron: "0 6 * * *"' in prefect_yaml

    def test_mcp_scaffold_without_schedule_no_regression(self, tmp_path):
        """Calling scaffold without schedule_interval produces the same output as before."""
        output_dir = tmp_path / "output"

        result_json = asyncio.run(scaffold(output_directory=str(output_dir)))
        result = json.loads(result_json)

        assert result_json  # non-empty response
        prefect_yaml = (output_dir / "prefect.yaml").read_text()
        # Without a schedule, the deployments section uses the commented-out example with []
        assert "[]" in prefect_yaml

    def test_mcp_scaffold_schedule_in_report(self, tmp_path):
        """schedule field in the JSON report reflects the provided schedule_interval."""
        output_dir = tmp_path / "output"

        result_json = asyncio.run(
            scaffold(output_directory=str(output_dir), schedule_interval="@daily")
        )
        result = json.loads(result_json)

        assert result["schedule"] == "@daily"
