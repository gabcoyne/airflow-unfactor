"""Tests for DAG conversion including test generation."""

import json
import pytest
from airflow_unfactor.analysis.parser import parse_dag
from airflow_unfactor.converters.base import convert_dag_to_flow
from airflow_unfactor.converters.test_generator import generate_flow_tests


class TestConvertDag:
    """Test DAG to flow conversion."""

    def test_convert_simple_etl(self, simple_etl_dag):
        """Convert a simple ETL DAG to a Prefect flow."""
        dag_info = parse_dag(simple_etl_dag)
        result = convert_dag_to_flow(dag_info, simple_etl_dag)

        assert "flow_code" in result
        assert "from prefect import flow, task" in result["flow_code"]
        assert "@task" in result["flow_code"]
        assert "@flow" in result["flow_code"]

    def test_convert_includes_educational_comments(self, simple_etl_dag):
        """Verify educational comments are included."""
        dag_info = parse_dag(simple_etl_dag)
        result = convert_dag_to_flow(dag_info, simple_etl_dag, include_comments=True)

        # Should have Prefect Advantage comments
        assert "Prefect" in result["flow_code"]

    def test_convert_tracks_task_mapping(self, simple_etl_dag):
        """Verify task mapping is tracked."""
        dag_info = parse_dag(simple_etl_dag)
        result = convert_dag_to_flow(dag_info, simple_etl_dag)

        mapping = result["original_to_new_mapping"]
        assert "extract_data" in mapping
        assert "transform_data" in mapping
        assert "load_data" in mapping


class TestGenerateTests:
    """Test generation of pytest tests for converted flows."""

    def test_generate_tests_for_simple_etl(self, simple_etl_dag):
        """Generate tests for a simple ETL flow."""
        dag_info = parse_dag(simple_etl_dag)
        result = convert_dag_to_flow(dag_info, simple_etl_dag)

        test_code = generate_flow_tests(
            dag_info=dag_info,
            flow_name="simple_etl",
            task_mapping=result["original_to_new_mapping"],
        )

        # Should have proper imports
        assert "import pytest" in test_code
        assert "prefect_test_harness" in test_code

        # Should have tests for each task
        assert "TestExtractData" in test_code or "test_extract_data" in test_code

        # Should have flow tests
        assert "test_flow_executes" in test_code

        # Should have migration verification
        assert "TestMigrationVerification" in test_code
        assert "test_no_xcom_references" in test_code

    def test_generated_tests_are_valid_python(self, simple_etl_dag):
        """Verify generated test code is valid Python."""
        dag_info = parse_dag(simple_etl_dag)
        result = convert_dag_to_flow(dag_info, simple_etl_dag)

        test_code = generate_flow_tests(
            dag_info=dag_info,
            flow_name="simple_etl",
            task_mapping=result["original_to_new_mapping"],
        )

        # Should compile without syntax errors
        compile(test_code, "<test>", "exec")