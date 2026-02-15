"""Tests for DAG-level settings parsing and runbook generation."""

from __future__ import annotations

import asyncio
import json

from airflow_unfactor.analysis.parser import parse_dag
from airflow_unfactor.tools.convert import convert_dag


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


class TestRunbookSpecificity:
    """Test that runbook generates specific guidance based on DAG settings."""

    def test_runbook_includes_schedule_guidance(self):
        """Runbook should include specific schedule mapping."""
        code = """
from airflow.decorators import dag, task

@dag(schedule="0 2 * * *", catchup=False)
def daily_etl():
    @task
    def extract():
        return "data"
    extract()
"""
        payload = asyncio.run(
            convert_dag(
                content=code,
                include_comments=False,
                generate_tests=False,
                include_external_context=False,
            )
        )
        result = json.loads(payload)
        runbook = result["conversion_runbook_md"]

        # Should mention the specific schedule
        assert "0 2 * * *" in runbook
        assert "schedule" in runbook.lower()
        # Should provide guidance on Prefect deployment
        assert "deployment" in runbook.lower()

    def test_runbook_includes_catchup_guidance(self):
        """Runbook should explain catchup=False mapping."""
        code = """
from airflow.decorators import dag, task

@dag(schedule="@daily", catchup=False)
def no_backfill():
    @task
    def work():
        pass
    work()
"""
        payload = asyncio.run(
            convert_dag(
                content=code,
                include_comments=False,
                generate_tests=False,
                include_external_context=False,
            )
        )
        result = json.loads(payload)
        runbook = result["conversion_runbook_md"]

        # Should mention catchup behavior
        assert "catchup" in runbook.lower() or "backfill" in runbook.lower()

    def test_runbook_includes_retry_guidance(self):
        """Runbook should map retry settings to Prefect."""
        code = """
from airflow import DAG

with DAG("test", default_args={"retries": 3, "retry_delay": 300}, schedule=None) as dag:
    pass
"""
        payload = asyncio.run(
            convert_dag(
                content=code,
                include_comments=False,
                generate_tests=False,
                include_external_context=False,
            )
        )
        result = json.loads(payload)
        runbook = result["conversion_runbook_md"]

        # Should mention retry configuration
        assert "3" in runbook  # the retry count
        assert "retries" in runbook.lower() or "retry" in runbook.lower()

    def test_runbook_includes_concurrency_guidance(self):
        """Runbook should map max_active_runs to Prefect concurrency."""
        code = """
from airflow import DAG

with DAG("test", max_active_runs=5, schedule=None) as dag:
    pass
"""
        payload = asyncio.run(
            convert_dag(
                content=code,
                include_comments=False,
                generate_tests=False,
                include_external_context=False,
            )
        )
        result = json.loads(payload)
        runbook = result["conversion_runbook_md"]

        # Should mention concurrency
        assert "5" in runbook
        assert "concurrency" in runbook.lower() or "max_active_runs" in runbook.lower()

    def test_runbook_includes_callback_guidance(self):
        """Runbook should guide on converting callbacks to Prefect."""
        code = """
from airflow import DAG

def notify(context):
    pass

with DAG("test", on_failure_callback=notify, schedule=None) as dag:
    pass
"""
        payload = asyncio.run(
            convert_dag(
                content=code,
                include_comments=False,
                generate_tests=False,
                include_external_context=False,
            )
        )
        result = json.loads(payload)
        runbook = result["conversion_runbook_md"]

        # Should mention callbacks/notifications
        assert (
            "callback" in runbook.lower()
            or "notification" in runbook.lower()
            or "alert" in runbook.lower()
        )

    def test_runbook_includes_tags_guidance(self):
        """Runbook should mention tag mapping."""
        code = """
from airflow.decorators import dag

@dag(tags=["production", "critical"], schedule=None)
def tagged_dag():
    pass
"""
        payload = asyncio.run(
            convert_dag(
                content=code,
                include_comments=False,
                generate_tests=False,
                include_external_context=False,
            )
        )
        result = json.loads(payload)
        runbook = result["conversion_runbook_md"]

        # Should mention tags
        assert "production" in runbook or "tags" in runbook.lower()

    def test_runbook_with_complex_dag_settings(self):
        """Test runbook generation for DAG with multiple settings."""
        code = """
from airflow.decorators import dag, task

@dag(
    schedule="0 2 * * *",
    catchup=False,
    max_active_runs=3,
    max_consecutive_failed_dag_runs=5,
    default_args={"retries": 3, "retry_delay": 300},
    tags=["production", "etl"]
)
def complex_dag():
    @task
    def work():
        pass
    work()
"""
        payload = asyncio.run(
            convert_dag(
                content=code,
                include_comments=False,
                generate_tests=False,
                include_external_context=False,
            )
        )
        result = json.loads(payload)
        runbook = result["conversion_runbook_md"]

        # Should have a dedicated section for DAG settings
        assert "schedule" in runbook.lower()
        assert "3" in runbook  # max_active_runs or retries
        assert "deployment" in runbook.lower() or "work pool" in runbook.lower()
