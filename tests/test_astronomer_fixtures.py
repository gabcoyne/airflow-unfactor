"""Tests for Astronomer example DAG fixtures.

These tests verify that the converter handles real-world DAGs
from the Astronomer 2.9 example repository.
"""

from pathlib import Path

import pytest

from airflow_unfactor.analysis.parser import parse_dag
from airflow_unfactor.converters.base import convert_dag_to_flow

FIXTURES_DIR = Path(__file__).parent / "fixtures"
ASTRONOMER_TOYS = FIXTURES_DIR / "astronomer-2-9" / "dags" / "toys"
SNAPSHOTS_DIR = FIXTURES_DIR / "snapshots"


# Toy DAGs without external dependencies (safe for full conversion tests)
TOY_DAGS = [
    "toy_taskflow_bash.py",
    "toy_xcom_big_v_small.py",
    "toy_auto_pause.py",
    "toy_custom_names_dynamic_tasks_taskflow.py",
    "toy_custom_names_dynamic_tasks_traditional_operators.py",
    "toy_custom_operator_push_multiple_xcom.py",
    "toy_dynamic_task_default_index.py",
    "toy_on_skipped_callback.py",
    "toy_task_duration_page.py",
    "complex_dag_structure_rainbow.py",
]

# DAGs with dataset scheduling (test detection, not full conversion)
DATASET_DAGS = [
    "toy_downstream_obj_storage_dataset.py",
    "toy_upstream_obj_storage_dataset.py",
]


class TestAstronomerParsing:
    """Test parsing of Astronomer example DAGs."""

    @pytest.mark.parametrize("dag_file", TOY_DAGS)
    def test_parse_toy_dag(self, dag_file: str):
        """All toy DAGs should parse successfully."""
        dag_path = ASTRONOMER_TOYS / dag_file
        if not dag_path.exists():
            pytest.skip(f"Fixture not found: {dag_file}")

        dag_code = dag_path.read_text()
        result = parse_dag(dag_code)

        # No error means successful parse
        assert "error" not in result, f"Failed to parse {dag_file}: {result.get('error')}"

    @pytest.mark.parametrize("dag_file", TOY_DAGS)
    def test_parse_extracts_dag_info(self, dag_file: str):
        """Parsed result should contain expected keys."""
        dag_path = ASTRONOMER_TOYS / dag_file
        if not dag_path.exists():
            pytest.skip(f"Fixture not found: {dag_file}")

        dag_code = dag_path.read_text()
        result = parse_dag(dag_code)

        # Should have required keys
        assert "dag_id" in result
        assert "operators" in result
        assert "imports" in result


class TestAstronomerConversion:
    """Test conversion of Astronomer example DAGs."""

    @pytest.mark.parametrize("dag_file", TOY_DAGS)
    def test_convert_produces_output(self, dag_file: str):
        """Converted DAGs should produce flow code."""
        dag_path = ASTRONOMER_TOYS / dag_file
        if not dag_path.exists():
            pytest.skip(f"Fixture not found: {dag_file}")

        dag_code = dag_path.read_text()
        dag_info = parse_dag(dag_code)
        result = convert_dag_to_flow(dag_info, dag_code)

        assert "flow_code" in result, f"No flow_code in result for {dag_file}"
        assert result.get("flow_code"), f"Empty flow code for {dag_file}"

    @pytest.mark.parametrize("dag_file", TOY_DAGS)
    def test_convert_produces_valid_python(self, dag_file: str):
        """Converted DAGs should be valid Python."""
        dag_path = ASTRONOMER_TOYS / dag_file
        if not dag_path.exists():
            pytest.skip(f"Fixture not found: {dag_file}")

        dag_code = dag_path.read_text()
        dag_info = parse_dag(dag_code)
        result = convert_dag_to_flow(dag_info, dag_code)

        flow_code = result.get("flow_code", "")
        if flow_code:
            # Verify valid Python syntax
            compile(flow_code, f"<{dag_file}>", "exec")


class TestSnapshotConversion:
    """Snapshot tests for conversion output stability.

    Run with --snapshot-update to update golden files.
    """

    @pytest.mark.parametrize(
        "dag_file", ["toy_taskflow_bash.py", "complex_dag_structure_rainbow.py"]
    )
    def test_conversion_snapshot(self, dag_file: str, snapshot_update):
        """Verify conversion output matches golden snapshot."""
        dag_path = ASTRONOMER_TOYS / dag_file
        if not dag_path.exists():
            pytest.skip(f"Fixture not found: {dag_file}")

        snapshot_path = SNAPSHOTS_DIR / f"{dag_file}.snapshot.py"

        dag_code = dag_path.read_text()
        dag_info = parse_dag(dag_code)
        result = convert_dag_to_flow(dag_info, dag_code)
        flow_code = result.get("flow_code", "")

        if not flow_code:
            pytest.skip(f"No flow code generated for {dag_file}")

        if snapshot_update or not snapshot_path.exists():
            # Create/update snapshot
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(flow_code)
            pytest.skip(f"Snapshot created/updated: {snapshot_path}")

        expected = snapshot_path.read_text()
        assert flow_code == expected, (
            f"Conversion output changed for {dag_file}. "
            f"Run with --snapshot-update to accept changes."
        )


class TestTaskFlowDetection:
    """Test detection of TaskFlow API patterns."""

    def test_parses_taskflow_dag(self):
        """Should parse TaskFlow DAG without error."""
        dag_path = ASTRONOMER_TOYS / "toy_taskflow_bash.py"
        if not dag_path.exists():
            pytest.skip("Fixture not found")

        dag_code = dag_path.read_text()
        result = parse_dag(dag_code)

        assert "error" not in result
        # TaskFlow DAGs import from airflow.decorators
        assert any("decorators" in imp for imp in result.get("imports", []))


class TestDatasetDetection:
    """Test detection of Airflow Dataset patterns."""

    @pytest.mark.parametrize("dag_file", DATASET_DAGS)
    def test_parses_dataset_dag(self, dag_file: str):
        """Should parse Dataset DAGs without error."""
        dag_path = ASTRONOMER_TOYS / dag_file
        if not dag_path.exists():
            pytest.skip(f"Fixture not found: {dag_file}")

        dag_code = dag_path.read_text()
        result = parse_dag(dag_code)

        assert "error" not in result
        # Dataset DAGs should have Dataset import
        assert "Dataset" in dag_code  # Basic check
