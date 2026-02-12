"""Tests for Airflow version detection.

See specs/airflow-version-detection.openspec.md for specification.
"""

import pytest
from airflow_unfactor.analysis.version import detect_airflow_version, AirflowVersion


class TestVersionDetection:
    """Test version detection from imports and patterns."""

    def test_detect_airflow_1x_from_imports(self):
        """TC1: Detect Airflow 1.x from legacy imports."""
        code = '''
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.dummy_operator import DummyOperator
'''
        result = detect_airflow_version(code)
        
        assert result.major == 1
        assert not result.has_taskflow
        assert not result.has_datasets
        assert result.confidence >= 0.6

    def test_detect_airflow_2x_taskflow(self):
        """TC2: Detect Airflow 2.x from TaskFlow API."""
        code = '''
from airflow.decorators import dag, task

@dag(schedule=None)
def my_dag():
    @task
    def hello():
        return "world"
    hello()

my_dag()
'''
        result = detect_airflow_version(code)
        
        assert result.major == 2
        assert result.has_taskflow
        assert not result.has_datasets
        assert result.confidence >= 0.6

    def test_detect_airflow_29_task_bash(self):
        """TC3: Detect Airflow 2.9+ from @task.bash."""
        code = '''
from airflow.decorators import dag, task

@dag()
def my_dag():
    @task.bash
    def run_script():
        return "echo hello"
    run_script()

my_dag()
'''
        result = detect_airflow_version(code)
        
        assert result.major == 2
        assert result.minor == 9
        assert result.has_taskflow
        assert result.has_task_bash

    def test_detect_airflow_24_datasets(self):
        """Detect Airflow 2.4+ from Datasets API."""
        code = '''
from airflow.decorators import dag, task
from airflow.datasets import Dataset

my_dataset = Dataset("s3://bucket/data")

@dag(schedule=[my_dataset])
def dataset_dag():
    pass

dataset_dag()
'''
        result = detect_airflow_version(code)
        
        assert result.major == 2
        assert result.minor is not None and result.minor >= 4
        assert result.has_datasets
        assert result.has_taskflow

    def test_detect_airflow_3x_assets(self):
        """TC4: Detect Airflow 3.x from Assets API."""
        code = '''
from airflow.assets import Asset
from airflow.decorators import dag, task

my_asset = Asset("s3://bucket/data")

@dag(schedule=[my_asset])
def asset_dag():
    pass

asset_dag()
'''
        result = detect_airflow_version(code)
        
        assert result.major == 3
        assert result.has_assets
        assert result.has_taskflow

    def test_detect_dynamic_task_mapping(self):
        """Detect Airflow 2.3+ from dynamic task mapping."""
        code = '''
from airflow.decorators import dag, task

@dag()
def mapped_dag():
    @task
    def process(item):
        return item * 2
    
    items = [1, 2, 3]
    process.expand(item=items)

mapped_dag()
'''
        result = detect_airflow_version(code)
        
        assert result.major == 2
        assert result.has_dynamic_task_mapping
        assert result.has_taskflow

    def test_confidence_increases_with_evidence(self):
        """More evidence should increase confidence."""
        # Single signal
        code1 = "from airflow.decorators import dag"
        result1 = detect_airflow_version(code1)
        
        # Multiple signals
        code2 = '''
from airflow.decorators import dag, task
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
'''
        result2 = detect_airflow_version(code2)
        
        assert result2.confidence >= result1.confidence

    def test_version_string_format(self):
        """Version string should be human-readable."""
        v = AirflowVersion(major=2, minor=9)
        assert v.version_string == "2.9+"
        
        v2 = AirflowVersion(major=2, minor=None)
        assert v2.version_string == "2.x"

    def test_str_representation(self):
        """String representation should include features."""
        v = AirflowVersion(
            major=2, 
            minor=9,
            has_taskflow=True,
            has_task_bash=True,
            confidence=0.9
        )
        s = str(v)
        assert "2.9+" in s
        assert "TaskFlow" in s
        assert "@task.bash" in s
        assert "90%" in s

    def test_handles_syntax_error(self):
        """Should handle invalid Python gracefully."""
        code = "this is not valid python {{{"
        result = detect_airflow_version(code)
        
        assert result.confidence == 0.0
        assert "Failed to parse" in result.evidence[0]


class TestRealWorldDags:
    """Test version detection on real Astronomer DAGs."""
    
    @pytest.fixture
    def astronomer_toys_dir(self):
        from pathlib import Path
        return Path(__file__).parent / "fixtures" / "astronomer-2-9" / "dags" / "toys"
    
    def test_toy_taskflow_bash_is_29(self, astronomer_toys_dir):
        """toy_taskflow_bash.py should be detected as 2.9+."""
        dag_path = astronomer_toys_dir / "toy_taskflow_bash.py"
        if not dag_path.exists():
            pytest.skip("Fixture not found")
        
        code = dag_path.read_text()
        result = detect_airflow_version(code)
        
        assert result.major == 2
        assert result.minor == 9
        assert result.has_task_bash
        assert result.has_taskflow
    
    def test_dataset_dags_are_24_plus(self, astronomer_toys_dir):
        """Dataset DAGs should be detected as 2.4+."""
        for dag_name in ["toy_downstream_obj_storage_dataset.py", "toy_upstream_obj_storage_dataset.py"]:
            dag_path = astronomer_toys_dir / dag_name
            if not dag_path.exists():
                continue
            
            code = dag_path.read_text()
            result = detect_airflow_version(code)
            
            assert result.major == 2
            assert result.minor is not None and result.minor >= 4, f"{dag_name} should be 2.4+"
            assert result.has_datasets, f"{dag_name} should have datasets"
