"""Tests for read_dag tool."""

import asyncio
import json

from airflow_unfactor.tools.read_dag import read_dag


class TestReadDag:
    """Tests for read_dag function."""

    def test_read_by_path(self, tmp_path):
        """Read a DAG file by path returns source and metadata."""
        dag_file = tmp_path / "my_dag.py"
        dag_file.write_text("from airflow import DAG\ndag = DAG('test')\n")

        result = json.loads(asyncio.run(read_dag(path=str(dag_file))))

        assert result["source"] == "from airflow import DAG\ndag = DAG('test')\n"
        assert result["file_path"] == str(dag_file.resolve())
        assert result["file_size_bytes"] == dag_file.stat().st_size
        assert result["line_count"] == 3  # two lines + trailing newline

    def test_read_by_content(self):
        """Read inline content returns source with null file_path."""
        content = "from airflow import DAG\ndag = DAG('test')"
        result = json.loads(asyncio.run(read_dag(content=content)))

        assert result["source"] == content
        assert result["file_path"] is None
        assert result["file_size_bytes"] == len(content.encode("utf-8"))
        assert result["line_count"] == 2

    def test_file_not_found(self):
        """Missing file returns error with null source."""
        result = json.loads(asyncio.run(read_dag(path="/nonexistent.py")))

        assert result["error"] == "File not found: /nonexistent.py"
        assert result["source"] is None

    def test_missing_args(self):
        """Neither path nor content returns error."""
        result = json.loads(asyncio.run(read_dag()))

        assert result["error"] == "Either path or content must be provided"

    def test_content_takes_precedence(self, tmp_path):
        """When both path and content are given, content is used."""
        dag_file = tmp_path / "dag.py"
        dag_file.write_text("file content")

        result = json.loads(asyncio.run(read_dag(path=str(dag_file), content="inline content")))

        assert result["source"] == "inline content"
        assert result["file_path"] is None
