"""Tests for DAG analysis."""

import json
import pytest
from airflow_unfactor.analysis.parser import parse_dag


class TestParseDag:
    """Test DAG parsing."""

    def test_parse_simple_etl(self, simple_etl_dag):
        """Parse a simple ETL DAG and extract operators."""
        result = parse_dag(simple_etl_dag)

        assert result['dag_id'] == 'simple_etl'
        assert len(result['operators']) == 3

        op_types = [op['type'] for op in result['operators']]
        assert 'PythonOperator' in op_types

        task_ids = [op['task_id'] for op in result['operators']]
        assert 'extract_data' in task_ids
        assert 'transform_data' in task_ids
        assert 'load_data' in task_ids

    def test_parse_detects_xcom(self, simple_etl_dag):
        """Detect XCom usage in DAG."""
        result = parse_dag(simple_etl_dag)

        # Should detect xcom_pull usage
        assert len(result['xcom_usage']) > 0 or 'xcom' in str(result['notes']).lower()

    def test_parse_invalid_syntax(self):
        """Handle invalid Python syntax gracefully."""
        result = parse_dag('def broken(')

        assert 'error' in result

    def test_parse_empty_dag(self):
        """Handle DAG with no operators."""
        empty_dag = """from airflow import DAG
from datetime import datetime

with DAG(dag_id='empty_dag', start_date=datetime(2024, 1, 1)) as dag:
    pass
"""
        result = parse_dag(empty_dag)

        assert result['dag_id'] == 'empty_dag'
        assert len(result['operators']) == 0