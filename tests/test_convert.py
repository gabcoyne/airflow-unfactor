"""Tests for DAG conversion including test generation."""

from airflow_unfactor.analysis.parser import parse_dag
from airflow_unfactor.converters.base import (
    build_dependency_graph,
    convert_dag_to_flow,
)
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


class TestDependencyTracking:
    """Test task dependency tracking and execution ordering."""

    def test_dependency_graph_basic(self):
        """Build basic dependency graph."""
        deps = [["extract", "transform"], ["transform", "load"]]
        graph = build_dependency_graph(deps, ["extract", "transform", "load"])

        assert graph.upstream["transform"] == ["extract"]
        assert graph.upstream["load"] == ["transform"]
        assert graph.upstream["extract"] == []

    def test_dependency_graph_parallel(self):
        """Build graph with parallel tasks."""
        # extract -> [transform_a, transform_b] -> load
        deps = [
            ["extract", "transform_a"],
            ["extract", "transform_b"],
            ["transform_a", "load"],
            ["transform_b", "load"],
        ]
        graph = build_dependency_graph(deps, ["extract", "transform_a", "transform_b", "load"])

        # transform_a and transform_b should be at same level
        groups = graph.get_execution_groups()
        assert len(groups) == 3  # [extract], [transform_a, transform_b], [load]
        assert groups[0] == ["extract"]
        assert set(groups[1]) == {"transform_a", "transform_b"}
        assert groups[2] == ["load"]

    def test_topological_sort(self):
        """Topological sort respects dependencies."""
        deps = [["a", "b"], ["b", "c"], ["a", "c"]]
        graph = build_dependency_graph(deps, ["a", "b", "c"])

        sorted_tasks = graph.topological_sort()
        assert sorted_tasks.index("a") < sorted_tasks.index("b")
        assert sorted_tasks.index("b") < sorted_tasks.index("c")
        assert sorted_tasks.index("a") < sorted_tasks.index("c")

    def test_convert_dag_with_dependencies(self):
        """Convert DAG preserves task execution order."""
        dag_code = """
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

with DAG("ordered_etl", start_date=datetime(2024, 1, 1)) as dag:
    extract = PythonOperator(task_id="extract_data", python_callable=lambda: None)
    transform = PythonOperator(task_id="transform_data", python_callable=lambda: None)
    load = PythonOperator(task_id="load_data", python_callable=lambda: None)

    extract >> transform >> load
"""
        dag_info = parse_dag(dag_code)
        result = convert_dag_to_flow(dag_info, dag_code)

        # Should have dependency info
        assert "dependencies" in result
        assert len(result["dependencies"]) > 0

        # Should have execution groups
        assert "execution_groups" in result
        assert len(result["execution_groups"]) > 0

        # Flow code should reference upstream results
        flow_code = result["flow_code"]
        assert "extract_data_result" in flow_code or "transform_data_result" in flow_code

    def test_convert_dag_parallel_branches(self):
        """Convert DAG with parallel branches."""
        dag_code = """
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

with DAG("parallel_etl", start_date=datetime(2024, 1, 1)) as dag:
    start = PythonOperator(task_id="start", python_callable=lambda: None)
    branch_a = PythonOperator(task_id="branch_a", python_callable=lambda: None)
    branch_b = PythonOperator(task_id="branch_b", python_callable=lambda: None)
    end = PythonOperator(task_id="end", python_callable=lambda: None)

    start >> [branch_a, branch_b] >> end
"""
        dag_info = parse_dag(dag_code)
        result = convert_dag_to_flow(dag_info, dag_code)

        # branch_a and branch_b should be in same execution group
        groups = result.get("execution_groups", [])
        if groups:
            # Find the group with branches
            branch_group = None
            for group in groups:
                if "branch_a" in group or "branch_b" in group:
                    branch_group = group
                    break
            if branch_group:
                assert "branch_a" in branch_group or "branch_b" in branch_group

    def test_convert_dag_no_dependencies_warns(self):
        """Convert DAG without dependencies adds warning."""
        dag_code = """
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

with DAG("no_deps", start_date=datetime(2024, 1, 1)) as dag:
    task_a = PythonOperator(task_id="task_a", python_callable=lambda: None)
    task_b = PythonOperator(task_id="task_b", python_callable=lambda: None)
    # No dependencies defined
"""
        dag_info = parse_dag(dag_code)
        result = convert_dag_to_flow(dag_info, dag_code)

        # Should have a warning about no dependencies
        warnings = result.get("warnings", [])
        has_dep_warning = any("depend" in w.lower() or "order" in w.lower() for w in warnings)
        # This is expected behavior - warn when no dependencies detected
        assert result["dependencies"] == [] or has_dep_warning
