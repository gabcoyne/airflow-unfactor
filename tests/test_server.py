"""Tests for server startup behavior."""

import logging
from unittest.mock import patch

from airflow_unfactor.server import main


class TestStartupWarning:
    """Tests for startup warning when Colin knowledge is unavailable."""

    def test_warns_when_no_knowledge_found(self, caplog):
        """Warning emitted when no bundled data or colin dir found."""
        with (
            caplog.at_level(logging.WARNING, logger="airflow_unfactor"),
            patch("sys.argv", ["airflow-unfactor"]),
            patch("airflow_unfactor.server.mcp") as mock_mcp,
            patch("airflow_unfactor.knowledge._find_knowledge_dir", return_value=None),
        ):
            mock_mcp.run.return_value = None
            main()
        assert "colin run" in caplog.text

    def test_no_warning_when_knowledge_found(self, tmp_path, caplog):
        """No warning when knowledge directory is found."""
        (tmp_path / "test.json").write_text("{}")
        with (
            caplog.at_level(logging.WARNING, logger="airflow_unfactor"),
            patch("sys.argv", ["airflow-unfactor"]),
            patch("airflow_unfactor.server.mcp") as mock_mcp,
            patch("airflow_unfactor.knowledge._find_knowledge_dir", return_value=tmp_path),
        ):
            mock_mcp.run.return_value = None
            main()
        assert "colin run" not in caplog.text
