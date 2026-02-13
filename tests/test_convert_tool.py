"""Tests for tool-level DAG conversion output."""

from __future__ import annotations

import asyncio
import json

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
    assert '@materialize("s3://sales/daily")' in result["dataset_conversion"]["materialization_code"]


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
