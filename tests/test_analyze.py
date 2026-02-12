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

    def test_parse_dag_settings(self):
        """Extract DAG-level settings."""
        dag_with_settings = """from airflow import DAG
from datetime import datetime, timedelta

default_args = {
    'owner': 'data_team',
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'email': ['team@example.com'],
}

with DAG(
    dag_id='test_settings',
    start_date=datetime(2024, 1, 1),
    schedule_interval='@daily',
    catchup=False,
    max_active_runs=2,
    tags=['production', 'etl'],
    default_args=default_args,
) as dag:
    pass
"""
        result = parse_dag(dag_with_settings)

        assert result['dag_id'] == 'test_settings'
        assert 'dag_settings' in result

        settings = result['dag_settings']
        assert settings.get('schedule_interval') == '@daily'
        assert settings.get('catchup') is False
        assert settings.get('max_active_runs') == 2
        assert settings.get('tags') == ['production', 'etl']
        assert 'default_args' in settings
        # default_args should be a variable reference since it's not inline
        assert settings['default_args'] is not None

    def test_parse_dag_settings_inline_default_args(self):
        """Extract inline default_args."""
        dag_with_inline_args = """from airflow import DAG
from datetime import datetime

with DAG(
    dag_id='test_inline',
    start_date=datetime(2024, 1, 1),
    default_args={'owner': 'john', 'retries': 2, 'retry_delay': 5},
) as dag:
    pass
"""
        result = parse_dag(dag_with_inline_args)

        settings = result['dag_settings']
        assert 'default_args' in settings
        default_args = settings['default_args']
        assert default_args.get('owner') == 'john'
        assert default_args.get('retries') == 2
        assert default_args.get('retry_delay') == 5

    def test_parse_dag_decorator(self):
        """Extract settings from @dag decorator."""
        dag_decorator = """from airflow.decorators import dag
from datetime import datetime

@dag(
    dag_id='decorator_dag',
    start_date=datetime(2024, 1, 1),
    schedule_interval='@hourly',
    catchup=True,
    tags=['test'],
)
def my_dag():
    pass

my_dag()
"""
        result = parse_dag(dag_decorator)

        assert result['dag_id'] == 'decorator_dag'
        settings = result['dag_settings']
        assert settings.get('schedule_interval') == '@hourly'
        assert settings.get('catchup') is True
        assert settings.get('tags') == ['test']

    def test_parse_dag_callbacks(self):
        """Detect DAG callbacks."""
        dag_with_callbacks = """from airflow import DAG
from datetime import datetime

def success_callback(context):
    print("Success!")

def failure_callback(context):
    print("Failed!")

with DAG(
    dag_id='callback_dag',
    start_date=datetime(2024, 1, 1),
    on_success_callback=success_callback,
    on_failure_callback=failure_callback,
) as dag:
    pass
"""
        result = parse_dag(dag_with_callbacks)

        settings = result['dag_settings']
        assert 'callbacks' in settings
        assert 'on_success_callback' in settings['callbacks']
        assert 'on_failure_callback' in settings['callbacks']