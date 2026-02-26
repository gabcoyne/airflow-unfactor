"""Tests for server startup behavior."""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from airflow_unfactor.server import main


class TestStartupWarning:
    """Tests for SRVR-01: startup warning when Colin output missing/empty."""

    def test_warns_when_colin_dir_missing(self, caplog):
        """Warning emitted when colin/output directory does not exist."""
        with caplog.at_level(logging.WARNING, logger="airflow_unfactor"):
            with patch("sys.argv", ["airflow-unfactor"]):
                with patch("airflow_unfactor.server.mcp") as mock_mcp:
                    with patch("pathlib.Path") as mock_path_cls:
                        mock_path_instance = MagicMock()
                        mock_path_instance.exists.return_value = False
                        mock_path_instance.glob.return_value = iter([])
                        mock_path_instance.__str__ = lambda s: "colin/output"
                        mock_path_cls.return_value = mock_path_instance
                        mock_mcp.run.return_value = None
                        main()
        assert "colin run" in caplog.text

    def test_warns_when_colin_dir_empty(self, tmp_path, caplog):
        """Warning emitted when colin/output exists but has no JSON files."""
        colin_dir = tmp_path / "colin" / "output"
        colin_dir.mkdir(parents=True)
        with caplog.at_level(logging.WARNING, logger="airflow_unfactor"):
            with patch("sys.argv", ["airflow-unfactor"]):
                with patch("airflow_unfactor.server.mcp") as mock_mcp:
                    with patch("pathlib.Path") as mock_path_cls:
                        mock_path_instance = MagicMock()
                        mock_path_instance.exists.return_value = True
                        mock_path_instance.glob.return_value = iter([])
                        mock_path_instance.__str__ = lambda s: "colin/output"
                        mock_path_cls.return_value = mock_path_instance
                        mock_mcp.run.return_value = None
                        main()
        assert "colin run" in caplog.text

    def test_no_warning_when_colin_dir_has_json(self, tmp_path, caplog):
        """No warning when colin/output has JSON files."""
        colin_dir = tmp_path / "colin" / "output"
        colin_dir.mkdir(parents=True)
        json_file = colin_dir / "test.json"
        json_file.write_text("{}")
        with caplog.at_level(logging.WARNING, logger="airflow_unfactor"):
            with patch("sys.argv", ["airflow-unfactor"]):
                with patch("airflow_unfactor.server.mcp") as mock_mcp:
                    with patch("pathlib.Path") as mock_path_cls:
                        mock_path_instance = MagicMock()
                        mock_path_instance.exists.return_value = True
                        mock_path_instance.glob.return_value = iter([json_file])
                        mock_path_instance.__str__ = lambda s: "colin/output"
                        mock_path_cls.return_value = mock_path_instance
                        mock_mcp.run.return_value = None
                        main()
        assert "colin run" not in caplog.text
