"""Tests for tool-level DAG conversion output."""

from __future__ import annotations

import asyncio
import json
import os

from airflow_unfactor.metrics import clear_metrics, get_all_metrics
from airflow_unfactor.tools.convert import convert_dag


def test_convert_includes_runbook_and_dataset_outputs() -> None:
    code = """
from airflow.assets import Asset
from airflow.decorators import dag, task

sales_asset = Asset("s3://sales/daily")

@task(outlets=[sales_asset])
def build_sales():
    return "ok"

@dag(schedule=[sales_asset])
def sales_flow():
    build_sales()
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

    assert "conversion_runbook_md" in result
    # New runbook format uses "Migration Checklist" instead of "Server/API Configuration Checklist"
    assert "Migration Checklist" in result["conversion_runbook_md"]
    assert "dataset_conversion" in result
    assert "materialization_code" in result["dataset_conversion"]
    assert (
        '@materialize("s3://sales/daily")' in result["dataset_conversion"]["materialization_code"]
    )


def test_convert_runbook_present_without_dataset_patterns(simple_etl_dag: str) -> None:
    payload = asyncio.run(
        convert_dag(
            content=simple_etl_dag,
            include_comments=False,
            generate_tests=False,
            include_external_context=False,
        )
    )
    result = json.loads(payload)

    assert "conversion_runbook_md" in result
    # New runbook format focuses on migration checklist, not dataset patterns
    assert "Migration Runbook" in result["conversion_runbook_md"]
    assert "Migration Checklist" in result["conversion_runbook_md"]
    assert "dataset_conversion" in result
    assert result["dataset_conversion"]["events"] == []


def test_convert_records_metrics_when_enabled(simple_etl_dag: str) -> None:
    """Test that metrics are recorded when AIRFLOW_UNFACTOR_METRICS=1."""
    # Clear any existing metrics
    clear_metrics()

    # Enable metrics via environment variable
    os.environ["AIRFLOW_UNFACTOR_METRICS"] = "1"
    try:
        payload = asyncio.run(
            convert_dag(
                content=simple_etl_dag,
                include_comments=False,
                generate_tests=False,
                include_external_context=False,
            )
        )
        result = json.loads(payload)

        # Check conversion succeeded
        assert "flow_code" in result

        # Check metrics were recorded
        metrics = get_all_metrics()
        assert len(metrics) == 1

        m = metrics[0]
        assert m.success is True
        assert m.dag_id == "simple_etl"
        assert m.operators_total > 0
        assert m.execution_time_ms is not None
        assert m.execution_time_ms > 0
    finally:
        # Clean up
        os.environ.pop("AIRFLOW_UNFACTOR_METRICS", None)
        clear_metrics()


def test_convert_no_metrics_when_disabled(simple_etl_dag: str) -> None:
    """Test that metrics are NOT recorded when AIRFLOW_UNFACTOR_METRICS is not set."""
    # Clear any existing metrics
    clear_metrics()

    # Ensure metrics are disabled
    os.environ.pop("AIRFLOW_UNFACTOR_METRICS", None)

    payload = asyncio.run(
        convert_dag(
            content=simple_etl_dag,
            include_comments=False,
            generate_tests=False,
            include_external_context=False,
        )
    )
    result = json.loads(payload)

    # Check conversion succeeded
    assert "flow_code" in result

    # Check no metrics were recorded
    metrics = get_all_metrics()
    assert len(metrics) == 0
