"""Tests for the validate tool - behavioral equivalence checking."""

import json

import pytest

from airflow_unfactor.tools.validate import (
    GraphInfo,
    ValidationIssue,
    ValidationReport,
    calculate_confidence,
    compare_data_flow,
    compare_dependencies,
    compare_task_counts,
    extract_dag_graph,
    extract_flow_graph,
    validate_conversion_sync,
)


# =============================================================================
# Test Fixtures: DAG and Flow Code Samples
# =============================================================================

SIMPLE_DAG = """
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

with DAG('simple_dag', start_date=datetime(2024, 1, 1)) as dag:
    task_a = PythonOperator(task_id='task_a', python_callable=lambda: 1)
    task_b = PythonOperator(task_id='task_b', python_callable=lambda: 2)
    task_a >> task_b
"""

SIMPLE_FLOW = """
from prefect import flow, task

@task
def task_a():
    return 1

@task
def task_b(upstream):
    return 2

@flow
def simple_flow():
    a_result = task_a()
    b_result = task_b(a_result)
"""

COMPLEX_DAG = """
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime

with DAG('complex_dag', start_date=datetime(2024, 1, 1)) as dag:
    start = EmptyOperator(task_id='start')
    task_a = PythonOperator(task_id='task_a', python_callable=lambda: 1)
    task_b = PythonOperator(task_id='task_b', python_callable=lambda: 2)
    task_c = PythonOperator(task_id='task_c', python_callable=lambda: 3)
    end = EmptyOperator(task_id='end')

    start >> [task_a, task_b] >> task_c >> end
"""

COMPLEX_FLOW = """
from prefect import flow, task

@task
def task_a():
    return 1

@task
def task_b():
    return 2

@task
def task_c(a_result, b_result):
    return 3

@flow
def complex_flow():
    a = task_a()
    b = task_b()
    c = task_c(a, b)
"""

XCOM_DAG = """
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def push_data(**context):
    context['ti'].xcom_push(key='result', value=42)

def pull_data(**context):
    value = context['ti'].xcom_pull(task_ids='producer', key='result')
    return value * 2

with DAG('xcom_dag', start_date=datetime(2024, 1, 1)) as dag:
    producer = PythonOperator(task_id='producer', python_callable=push_data)
    consumer = PythonOperator(task_id='consumer', python_callable=pull_data)
    producer >> consumer
"""

XCOM_FLOW = """
from prefect import flow, task

@task
def producer():
    return 42

@task
def consumer(value):
    return value * 2

@flow
def xcom_flow():
    result = producer()
    final = consumer(result)
"""

MISMATCHED_FLOW = """
from prefect import flow, task

@task
def task_a():
    return 1

@flow
def mismatched_flow():
    task_a()
"""


# =============================================================================
# Test DAG Graph Extraction
# =============================================================================

class TestDAGGraphExtraction:
    """Tests for extracting task graphs from Airflow DAGs."""

    def test_extract_simple_dag(self):
        """Should extract tasks and dependencies from simple DAG."""
        graph = extract_dag_graph(SIMPLE_DAG)

        assert graph.task_count == 2
        assert "task_a" in graph.tasks
        assert "task_b" in graph.tasks
        assert ("task_a", "task_b") in graph.edges

    def test_extract_complex_dag_ignores_empty_operators(self):
        """Should ignore DummyOperator and EmptyOperator."""
        graph = extract_dag_graph(COMPLEX_DAG)

        # Only real tasks, not start/end EmptyOperators
        assert graph.task_count == 3
        assert "start" not in graph.tasks
        assert "end" not in graph.tasks
        assert "task_a" in graph.tasks
        assert "task_b" in graph.tasks
        assert "task_c" in graph.tasks

    def test_extract_xcom_patterns(self):
        """Should detect XCom push and pull patterns."""
        graph = extract_dag_graph(XCOM_DAG)

        assert len(graph.xcom_pushes) > 0
        assert len(graph.xcom_pulls) > 0

    def test_extract_list_dependencies(self):
        """Should handle list-style dependencies [a, b] >> c."""
        graph = extract_dag_graph(COMPLEX_DAG)

        # Both task_a and task_b should connect to task_c
        assert ("task_a", "task_c") in graph.edges
        assert ("task_b", "task_c") in graph.edges

    def test_empty_dag(self):
        """Should handle empty or minimal DAG."""
        graph = extract_dag_graph("# Empty file")
        assert graph.task_count == 0
        assert graph.edge_count == 0

    def test_syntax_error_dag(self):
        """Should handle DAG with syntax errors gracefully."""
        graph = extract_dag_graph("def broken(")
        assert graph.task_count == 0


class TestFlowGraphExtraction:
    """Tests for extracting task graphs from Prefect flows."""

    def test_extract_simple_flow(self):
        """Should extract tasks from simple flow."""
        graph = extract_flow_graph(SIMPLE_FLOW)

        assert graph.task_count == 2
        assert "task_a" in graph.tasks
        assert "task_b" in graph.tasks

    def test_extract_task_with_return(self):
        """Should detect tasks with return statements."""
        graph = extract_flow_graph(SIMPLE_FLOW)

        assert graph.tasks["task_a"].has_return is True
        assert graph.tasks["task_b"].has_return is True

    def test_extract_task_parameters(self):
        """Should detect task function parameters."""
        graph = extract_flow_graph(SIMPLE_FLOW)

        # task_b takes 'upstream' parameter
        assert "upstream" in graph.tasks["task_b"].parameters
        # task_a has no parameters
        assert graph.tasks["task_a"].parameters == []

    def test_extract_dependencies_from_calls(self):
        """Should infer dependencies from task call arguments."""
        graph = extract_flow_graph(SIMPLE_FLOW)

        # task_b is called with task_a result
        assert ("task_a", "task_b") in graph.edges

    def test_extract_complex_flow(self):
        """Should handle multiple parallel tasks."""
        graph = extract_flow_graph(COMPLEX_FLOW)

        assert graph.task_count == 3
        # task_c depends on both task_a and task_b
        assert ("task_a", "task_c") in graph.edges
        assert ("task_b", "task_c") in graph.edges


# =============================================================================
# Test Comparison Functions
# =============================================================================

class TestTaskCountComparison:
    """Tests for compare_task_counts function."""

    def test_matching_counts(self):
        """Should return True when counts match."""
        dag_graph = extract_dag_graph(SIMPLE_DAG)
        flow_graph = extract_flow_graph(SIMPLE_FLOW)

        match, issues = compare_task_counts(dag_graph, flow_graph)

        assert match is True
        assert len([i for i in issues if i.severity == "error"]) == 0

    def test_mismatched_counts(self):
        """Should return False and issues when counts differ."""
        dag_graph = extract_dag_graph(SIMPLE_DAG)
        flow_graph = extract_flow_graph(MISMATCHED_FLOW)

        match, issues = compare_task_counts(dag_graph, flow_graph)

        assert match is False
        assert any(i.category == "task_count" for i in issues)
        assert any("missing" in i.message.lower() for i in issues)

    def test_complex_dag_vs_flow(self):
        """Complex DAG (with EmptyOperators) should match flow without them."""
        dag_graph = extract_dag_graph(COMPLEX_DAG)
        flow_graph = extract_flow_graph(COMPLEX_FLOW)

        match, issues = compare_task_counts(dag_graph, flow_graph)

        assert match is True


class TestDependencyComparison:
    """Tests for compare_dependencies function."""

    def test_matching_dependencies(self):
        """Should return True when dependencies match."""
        dag_graph = extract_dag_graph(SIMPLE_DAG)
        flow_graph = extract_flow_graph(SIMPLE_FLOW)

        preserved, issues = compare_dependencies(dag_graph, flow_graph)

        assert preserved is True

    def test_missing_dependency(self):
        """Should detect missing dependency edges."""
        dag_graph = extract_dag_graph(SIMPLE_DAG)
        # Flow with no dependencies
        flow_graph = extract_flow_graph("""
from prefect import flow, task

@task
def task_a():
    return 1

@task
def task_b():
    return 2

@flow
def no_deps_flow():
    task_a()
    task_b()
""")

        preserved, issues = compare_dependencies(dag_graph, flow_graph)

        assert preserved is False
        assert any(i.severity == "error" for i in issues)

    def test_extra_dependencies_allowed(self):
        """Extra dependencies in flow should be info, not error."""
        dag_graph = GraphInfo()
        dag_graph.tasks["a"] = None
        dag_graph.tasks["b"] = None

        flow_graph = GraphInfo()
        flow_graph.tasks["a"] = None
        flow_graph.tasks["b"] = None
        flow_graph.edges.append(("a", "b"))

        preserved, issues = compare_dependencies(dag_graph, flow_graph)

        # Extra edge is fine, so still preserved
        assert preserved is True
        assert any(i.severity == "info" for i in issues)


class TestDataFlowComparison:
    """Tests for compare_data_flow function."""

    def test_xcom_to_return_conversion(self):
        """Should validate XCom patterns converted to return values."""
        dag_graph = extract_dag_graph(XCOM_DAG)
        flow_graph = extract_flow_graph(XCOM_FLOW)

        preserved, issues = compare_data_flow(dag_graph, flow_graph)

        # Should have info messages about XCom conversion
        assert any(i.category == "data_flow" for i in issues)

    def test_no_xcom_simple_case(self):
        """Should pass when neither has XCom patterns."""
        dag_graph = extract_dag_graph(SIMPLE_DAG)
        flow_graph = extract_flow_graph(SIMPLE_FLOW)

        preserved, issues = compare_data_flow(dag_graph, flow_graph)

        assert preserved is True


# =============================================================================
# Test Confidence Scoring
# =============================================================================

class TestConfidenceScore:
    """Tests for calculate_confidence function."""

    def test_perfect_match_high_confidence(self):
        """Perfect match should give 90+ confidence."""
        dag_graph = extract_dag_graph(SIMPLE_DAG)
        flow_graph = extract_flow_graph(SIMPLE_FLOW)

        score = calculate_confidence(dag_graph, flow_graph, [])

        assert score >= 90

    def test_mismatched_tasks_lower_confidence(self):
        """Task mismatch should reduce confidence."""
        dag_graph = extract_dag_graph(SIMPLE_DAG)
        flow_graph = extract_flow_graph(MISMATCHED_FLOW)

        issues = [ValidationIssue(
            severity="error",
            category="task_count",
            message="Missing tasks",
        )]

        score = calculate_confidence(dag_graph, flow_graph, issues)

        assert score < 90

    def test_xcom_complexity_reduces_confidence(self):
        """Complex XCom patterns should reduce confidence."""
        dag_graph = extract_dag_graph(XCOM_DAG)
        flow_graph = extract_flow_graph(XCOM_FLOW)

        score = calculate_confidence(dag_graph, flow_graph, [])

        # Should be lower than simple case due to XCom complexity
        assert 50 <= score <= 100

    def test_confidence_bounded(self):
        """Confidence should always be 0-100."""
        dag_graph = GraphInfo()
        flow_graph = GraphInfo()

        score = calculate_confidence(dag_graph, flow_graph, [])

        assert 0 <= score <= 100


# =============================================================================
# Test Full Validation
# =============================================================================

class TestValidateConversion:
    """Tests for the complete validate_conversion function."""

    def test_simple_valid_conversion(self):
        """Simple matching DAG and flow should pass validation."""
        report = validate_conversion_sync(SIMPLE_DAG, SIMPLE_FLOW)

        assert report.is_valid is True
        assert report.task_count_match is True
        assert report.dependency_preserved is True
        assert report.confidence_score >= 80

    def test_complex_valid_conversion(self):
        """Complex DAG with EmptyOperators should validate."""
        report = validate_conversion_sync(COMPLEX_DAG, COMPLEX_FLOW)

        assert report.is_valid is True
        assert report.task_count_match is True

    def test_invalid_conversion_detected(self):
        """Should detect when conversion is invalid."""
        report = validate_conversion_sync(SIMPLE_DAG, MISMATCHED_FLOW)

        assert report.is_valid is False
        assert report.task_count_match is False
        assert len(report.issues) > 0

    def test_xcom_conversion_validated(self):
        """Should validate XCom to return/parameter conversion."""
        report = validate_conversion_sync(XCOM_DAG, XCOM_FLOW)

        assert report.is_valid is True
        assert report.data_flow_preserved is True

    def test_sync_validation(self):
        """Synchronous validation should work correctly."""
        report = validate_conversion_sync(SIMPLE_DAG, SIMPLE_FLOW)

        assert isinstance(report, ValidationReport)
        assert report.is_valid is True
        assert report.task_count_match is True

    def test_report_includes_summaries(self):
        """Report should include DAG and flow summaries."""
        report = validate_conversion_sync(SIMPLE_DAG, SIMPLE_FLOW)

        assert "task_count" in report.dag_summary
        assert "task_count" in report.flow_summary
        assert report.dag_summary["task_count"] == 2
        assert report.flow_summary["task_count"] == 2

    def test_report_includes_task_lists(self):
        """Report should list actual task names."""
        report = validate_conversion_sync(SIMPLE_DAG, SIMPLE_FLOW)

        assert "task_a" in report.dag_summary["tasks"]
        assert "task_b" in report.dag_summary["tasks"]

    def test_to_dict_serialization(self):
        """Report should serialize to dict correctly."""
        report = validate_conversion_sync(SIMPLE_DAG, SIMPLE_FLOW)
        result = report.to_dict()

        assert result["is_valid"] is True
        assert "dag_summary" in result
        assert "flow_summary" in result
        assert isinstance(result["issues"], list)


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_dag_and_flow(self):
        """Should handle empty files gracefully."""
        report = validate_conversion_sync("# Empty DAG", "# Empty flow")

        assert report.is_valid is True
        assert report.task_count_match is True
        assert report.dag_summary["task_count"] == 0

    def test_syntax_error_in_dag(self):
        """Should handle syntax errors gracefully."""
        report = validate_conversion_sync("def broken(", "# Valid flow")

        # Should not crash, just report empty graph
        assert "task_count" in report.dag_summary

    def test_dag_with_set_upstream(self):
        """Should handle set_upstream/set_downstream syntax."""
        dag_code = """
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG('test') as dag:
    task_a = PythonOperator(task_id='task_a', python_callable=lambda: 1)
    task_b = PythonOperator(task_id='task_b', python_callable=lambda: 2)
    task_b.set_upstream(task_a)
"""
        graph = extract_dag_graph(dag_code)

        assert ("task_a", "task_b") in graph.edges

    def test_flow_with_submit_pattern(self):
        """Should handle task.submit() pattern."""
        flow_code = """
from prefect import flow, task

@task
def my_task():
    return 1

@flow
def my_flow():
    result = my_task.submit()
"""
        graph = extract_flow_graph(flow_code)

        assert "my_task" in graph.tasks

    def test_flow_with_wait_for(self):
        """Should detect wait_for dependencies."""
        flow_code = """
from prefect import flow, task

@task
def task_a():
    return 1

@task
def task_b():
    return 2

@flow
def my_flow():
    a = task_a()
    b = task_b.submit(wait_for=[a])
"""
        graph = extract_flow_graph(flow_code)

        assert ("task_a", "task_b") in graph.edges


class TestValidationIssueDetails:
    """Tests for validation issue detail reporting."""

    def test_missing_task_details(self):
        """Missing task issue should include task names."""
        dag_graph = extract_dag_graph(SIMPLE_DAG)
        flow_graph = extract_flow_graph(MISMATCHED_FLOW)

        _, issues = compare_task_counts(dag_graph, flow_graph)

        error_issues = [i for i in issues if i.severity == "error"]
        assert len(error_issues) > 0
        assert "missing_tasks" in error_issues[0].details
        assert "task_b" in error_issues[0].details["missing_tasks"]

    def test_missing_edge_details(self):
        """Missing dependency issue should include edge details."""
        dag_graph = GraphInfo()
        dag_graph.tasks["a"] = None
        dag_graph.tasks["b"] = None
        dag_graph.edges.append(("a", "b"))

        flow_graph = GraphInfo()
        flow_graph.tasks["a"] = None
        flow_graph.tasks["b"] = None
        # No edges

        _, issues = compare_dependencies(dag_graph, flow_graph)

        error_issues = [i for i in issues if i.severity == "error"]
        assert len(error_issues) > 0
        assert "missing_edges" in error_issues[0].details
