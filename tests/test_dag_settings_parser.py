"""Tests for DAG-level settings parsing and runbook generation."""

from __future__ import annotations

from airflow_unfactor.analysis.parser import parse_dag


class TestParseDAGSettings:
    """Test parsing of DAG-level configuration settings."""

    def test_parse_schedule_interval(self):
        """Extract schedule_interval from DAG definition."""
        code = """
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG("test_dag", schedule_interval="@daily") as dag:
    task = PythonOperator(task_id="task1", python_callable=lambda: None)
"""
        result = parse_dag(code)
        assert result["schedule"] == "@daily"

    def test_parse_schedule_cron(self):
        """Extract cron schedule from DAG definition."""
        code = """
from airflow.decorators import dag

@dag(schedule="0 * * * *")
def test_dag():
    pass
"""
        result = parse_dag(code)
        assert result["schedule"] == "0 * * * *"

    def test_parse_catchup(self):
        """Extract catchup setting from DAG definition."""
        code = """
from airflow.decorators import dag

@dag(catchup=False, schedule=None)
def test_dag():
    pass
"""
        result = parse_dag(code)
        assert result["catchup"] is False

    def test_parse_max_active_runs(self):
        """Extract max_active_runs from DAG definition."""
        code = """
from airflow import DAG

with DAG("test", max_active_runs=3, schedule=None) as dag:
    pass
"""
        result = parse_dag(code)
        assert result["max_active_runs"] == 3

    def test_parse_max_consecutive_failed_dag_runs(self):
        """Extract max_consecutive_failed_dag_runs from DAG definition."""
        code = """
from airflow.decorators import dag

@dag(max_consecutive_failed_dag_runs=5, schedule=None)
def test_dag():
    pass
"""
        result = parse_dag(code)
        assert result["max_consecutive_failed_dag_runs"] == 5

    def test_parse_default_args_retries(self):
        """Extract retries from default_args."""
        code = """
from airflow import DAG

with DAG("test", default_args={"retries": 3, "retry_delay": 5}, schedule=None) as dag:
    pass
"""
        result = parse_dag(code)
        assert result["default_args"]["retries"] == 3
        assert result["default_args"]["retry_delay"] == 5

    def test_parse_tags(self):
        """Extract tags from DAG definition."""
        code = """
from airflow.decorators import dag

@dag(tags=["production", "etl"], schedule=None)
def test_dag():
    pass
"""
        result = parse_dag(code)
        assert "production" in result["tags"]
        assert "etl" in result["tags"]

    def test_parse_on_failure_callback(self):
        """Extract on_failure_callback presence."""
        code = """
from airflow import DAG

def notify_failure(context):
    pass

with DAG("test", on_failure_callback=notify_failure, schedule=None) as dag:
    pass
"""
        result = parse_dag(code)
        assert result["has_failure_callback"] is True

    def test_parse_on_success_callback(self):
        """Extract on_success_callback presence."""
        code = """
from airflow.decorators import dag

def notify_success(context):
    pass

@dag(on_success_callback=notify_success, schedule=None)
def test_dag():
    pass
"""
        result = parse_dag(code)
        assert result["has_success_callback"] is True
