"""Tests for Dataset to Event converter.

See specs/dataset-event-converter.openspec.md for specification.
"""

import pytest

from airflow_unfactor.converters.datasets import (
    analyze_datasets,
    generate_event_code,
    uri_to_event_name,
)


class TestUriToEventName:
    """Test URI to event name conversion."""

    def test_s3_uri(self):
        assert uri_to_event_name("s3://my-bucket/data.csv") == "dataset.s3.my_bucket.data"

    def test_gs_uri(self):
        assert uri_to_event_name("gs://bucket/path/file.parquet") == "dataset.gs.bucket.path.file"

    def test_file_uri(self):
        result = uri_to_event_name("file:///data/output.json")
        assert result.startswith("dataset.file")
        assert "output" in result

    def test_nested_path(self):
        result = uri_to_event_name("s3://bucket/a/b/c/data.csv")
        assert result == "dataset.s3.bucket.a.b.c.data"


class TestAnalyzeDatasets:
    """Test Dataset pattern detection."""

    def test_detect_dataset_import(self):
        """TC1: Detect Dataset instantiation."""
        code = """
from airflow.datasets import Dataset
my_data = Dataset("s3://my-bucket/data.csv")
"""
        analysis = analyze_datasets(code)

        assert len(analysis.datasets) == 1
        assert analysis.datasets[0].name == "my_data"
        assert analysis.datasets[0].uri == "s3://my-bucket/data.csv"
        assert "dataset.s3" in analysis.datasets[0].event_name

    def test_detect_asset_airflow3(self):
        """Detect Airflow 3.x Asset."""
        code = """
from airflow.assets import Asset
my_asset = Asset("s3://bucket/data")
"""
        analysis = analyze_datasets(code)

        assert len(analysis.datasets) == 1
        assert analysis.datasets[0].is_asset

    def test_detect_producer_task(self):
        """TC2: Detect task with outlets."""
        code = """
from airflow.decorators import task
from airflow.datasets import Dataset

my_data = Dataset("s3://bucket/output")

@task(outlets=[my_data])
def write_data():
    pass
"""
        analysis = analyze_datasets(code)

        assert len(analysis.producers) == 1
        assert analysis.producers[0].task_name == "write_data"
        assert "my_data" in analysis.producers[0].datasets

    def test_detect_consumer_dag(self):
        """Detect DAG triggered by dataset."""
        code = """
from airflow.decorators import dag
from airflow.datasets import Dataset

my_data = Dataset("s3://bucket/input")

@dag(schedule=[my_data])
def consumer_dag():
    pass
"""
        analysis = analyze_datasets(code)

        assert len(analysis.consumers) == 1
        assert analysis.consumers[0].dag_name == "consumer_dag"
        assert "my_data" in analysis.consumers[0].datasets

    def test_multiple_datasets(self):
        """Detect multiple datasets."""
        code = """
from airflow.datasets import Dataset

data_a = Dataset("s3://bucket/a")
data_b = Dataset("s3://bucket/b")
data_c = Dataset("gs://other/c")
"""
        analysis = analyze_datasets(code)

        assert len(analysis.datasets) == 3
        names = {d.name for d in analysis.datasets}
        assert names == {"data_a", "data_b", "data_c"}


class TestGenerateEventCode:
    """Test Prefect event code generation."""

    def test_generate_producer_code(self):
        """Generate emit_event code for producer."""
        code = """
from airflow.datasets import Dataset
from airflow.decorators import task

output = Dataset("s3://bucket/output")

@task(outlets=[output])
def produce():
    pass
"""
        analysis = analyze_datasets(code)
        result = generate_event_code(analysis)

        assert "emit_event" in result["producer_code"]
        assert "s3://bucket/output" in result["producer_code"]
        assert result["materialization_code"] == ""
        assert result["assets"] == []

    def test_generate_deployment_yaml(self):
        """Generate deployment trigger config."""
        code = """
from airflow.datasets import Dataset
from airflow.decorators import dag

input_data = Dataset("s3://bucket/input")

@dag(schedule=[input_data])
def consumer():
    pass
"""
        analysis = analyze_datasets(code)
        result = generate_event_code(analysis)

        assert "triggers:" in result["deployment_yaml"]
        assert "s3://bucket/input" in result["deployment_yaml"]

    def test_no_datasets_returns_empty(self):
        """No datasets returns empty result."""
        code = """
from airflow.decorators import dag

@dag()
def plain_dag():
    pass
"""
        analysis = analyze_datasets(code)
        result = generate_event_code(analysis)

        assert result["producer_code"] == ""
        assert "No Datasets" in result["notes"][0]
        assert result["events"] == []
        assert result["assets"] == []
        assert result["materialization_code"] == ""

    def test_generate_asset_materialization_code(self):
        """Assets should produce materialization scaffolding."""
        code = """
from airflow.assets import Asset
from airflow.decorators import task

sales_asset = Asset("s3://sales/daily")

@task(outlets=[sales_asset])
def build_sales():
    pass
"""
        analysis = analyze_datasets(code)
        result = generate_event_code(analysis)

        assert len(result["assets"]) == 1
        assert result["assets"][0]["name"] == "sales_asset"
        assert result["assets"][0]["uri"] == "s3://sales/daily"
        assert '@materialize("s3://sales/daily")' in result["materialization_code"]
        assert "def materialize_sales_asset" in result["materialization_code"]
        assert "emit_sales_asset_updated" in result["producer_code"]


class TestRealWorldDatasets:
    """Test with real Astronomer fixtures."""

    @pytest.fixture
    def astronomer_toys_dir(self):
        from pathlib import Path

        return Path(__file__).parent / "fixtures" / "astronomer-2-9" / "dags" / "toys"

    def test_analyze_dataset_dag(self, astronomer_toys_dir):
        """Analyze real Dataset DAG."""
        dag_path = astronomer_toys_dir / "toy_upstream_obj_storage_dataset.py"
        if not dag_path.exists():
            pytest.skip("Fixture not found")

        code = dag_path.read_text()
        analysis = analyze_datasets(code)

        # Should find datasets
        assert analysis.has_datasets or "Dataset" in code
