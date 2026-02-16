"""Tests for Astronomer example DAG fixtures.

These tests verify that the analyzer handles real-world DAGs
from the Astronomer 2.9 example repository.
"""

from pathlib import Path

import pytest

from airflow_unfactor.analysis.parser import parse_dag

FIXTURES_DIR = Path(__file__).parent / "fixtures"
ASTRONOMER_TOYS = FIXTURES_DIR / "astronomer-2-9" / "dags" / "toys"


# Toy DAGs without external dependencies (safe for parsing tests)
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

# DAGs with dataset scheduling (test detection)
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
