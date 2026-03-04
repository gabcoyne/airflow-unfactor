# tests/test_generate_migration_report.py
"""Tests for generate_migration_report tool."""

import asyncio
import json

from airflow_unfactor.tools.generate_migration_report import (
    PREFECT_DOC_LINKS,
    _render_checklist,
    _render_decisions_table,
    generate_migration_report,
)


class TestDocLinks:
    """The doc links map must cover core action types."""

    def test_core_action_types_have_links(self):
        for key in ["setup_work_pool", "configure_block", "migrate_connections", "create_automation"]:
            assert key in PREFECT_DOC_LINKS, f"Missing doc link for {key}"
            assert PREFECT_DOC_LINKS[key].startswith("http"), f"Bad URL for {key}"


class TestDecisionsTable:
    """Markdown table rendering for conversion decisions."""

    def test_table_has_headers(self):
        table = _render_decisions_table([
            {"component": "S3KeySensor", "outcome": "polling @task", "rationale": "short wait"},
        ])
        assert "Component" in table
        assert "Outcome" in table
        assert "Rationale" in table

    def test_decision_appears_in_table(self):
        table = _render_decisions_table([
            {"component": "S3KeySensor", "outcome": "polling @task", "rationale": "short wait"},
        ])
        assert "S3KeySensor" in table
        assert "polling @task" in table

    def test_manual_action_flagged(self):
        table = _render_decisions_table([
            {
                "component": "S3KeySensor",
                "outcome": "polling @task",
                "manual_action": "configure_s3_block",
            }
        ])
        assert "⚠" in table or "manual" in table.lower() or "action" in table.lower()

    def test_empty_decisions(self):
        table = _render_decisions_table([])
        assert isinstance(table, str)


class TestChecklist:
    """Markdown checklist rendering."""

    def test_checklist_items_are_checkboxes(self):
        checklist = _render_checklist(
            decisions=[{"component": "X", "outcome": "Y", "manual_action": "setup_work_pool"}],
            manual_actions=["migrate_connections"],
        )
        assert "- [ ]" in checklist

    def test_checklist_deduplicated(self):
        checklist = _render_checklist(
            decisions=[
                {"component": "A", "outcome": "x", "manual_action": "setup_work_pool"},
                {"component": "B", "outcome": "y", "manual_action": "setup_work_pool"},
            ],
            manual_actions=["setup_work_pool"],
        )
        assert checklist.count("work pool") == 1 or checklist.count("work_pool") == 1

    def test_known_action_has_link(self):
        checklist = _render_checklist(
            decisions=[],
            manual_actions=["setup_work_pool"],
        )
        assert "https://docs.prefect.io" in checklist

    def test_unknown_action_still_appears(self):
        checklist = _render_checklist(
            decisions=[],
            manual_actions=["some_custom_action"],
        )
        assert "some_custom_action" in checklist


class TestGenerateMigrationReport:
    """Integration tests for the full tool."""

    def test_writes_migration_md(self, tmp_path):
        result_json = asyncio.run(
            generate_migration_report(
                output_directory=str(tmp_path),
                dag_path="dags/etl_dag.py",
                flow_path="deployments/default/etl/flow.py",
                decisions=[
                    {"component": "S3KeySensor", "outcome": "polling @task",
                     "manual_action": "configure_s3_block"},
                ],
                manual_actions=["setup_work_pool"],
            )
        )
        result = json.loads(result_json)
        assert (tmp_path / "MIGRATION.md").exists()
        assert result["created_file"].endswith("MIGRATION.md")
        assert result["checklist_items_count"] >= 1

    def test_report_has_all_sections(self, tmp_path):
        asyncio.run(
            generate_migration_report(
                output_directory=str(tmp_path),
                dag_path="dags/etl_dag.py",
                flow_path="deployments/default/etl/flow.py",
                decisions=[],
                manual_actions=["setup_work_pool"],
            )
        )
        content = (tmp_path / "MIGRATION.md").read_text()
        assert "## Summary" in content
        assert "## Conversion Decisions" in content
        assert "## Before Production" in content
        assert "Prefect MCP" in content

    def test_mcp_suggestion_in_report(self, tmp_path):
        asyncio.run(
            generate_migration_report(
                output_directory=str(tmp_path),
                dag_path="dags/etl_dag.py",
                flow_path="deployments/default/etl/flow.py",
                decisions=[],
                manual_actions=[],
            )
        )
        content = (tmp_path / "MIGRATION.md").read_text()
        assert "https://docs.prefect.io/mcp" in content

    def test_mcp_prominent_when_claude_mcp_json_exists(self, tmp_path):
        """When .claude/mcp.json exists without Prefect, MCP note is prominent."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "mcp.json").write_text('{"mcpServers": {}}')

        asyncio.run(
            generate_migration_report(
                output_directory=str(tmp_path),
                dag_path="dags/etl_dag.py",
                flow_path="deployments/default/etl/flow.py",
                decisions=[],
                manual_actions=[],
            )
        )
        content = (tmp_path / "MIGRATION.md").read_text()
        # Prominent = appears before the checklist section or has a callout marker
        mcp_pos = content.find("https://docs.prefect.io/mcp")
        before_prod_pos = content.find("## Before Production")
        assert mcp_pos < before_prod_pos or "> " in content  # callout or early

    def test_dag_path_in_summary(self, tmp_path):
        asyncio.run(
            generate_migration_report(
                output_directory=str(tmp_path),
                dag_path="dags/my_dag.py",
                flow_path="deployments/default/my-flow/flow.py",
                decisions=[],
                manual_actions=[],
            )
        )
        content = (tmp_path / "MIGRATION.md").read_text()
        assert "my_dag.py" in content
        assert "my-flow/flow.py" in content
