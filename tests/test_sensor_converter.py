"""Tests for Sensor to Trigger converter.

See specs/sensor-trigger-converter.openspec.md for specification.
"""

import pytest
from airflow_unfactor.converters.sensors import (
    detect_sensors,
    convert_sensor,
    convert_all_sensors,
    SensorInfo,
)


class TestDetectSensors:
    """Test sensor detection."""

    def test_detect_s3_sensor(self):
        code = '''
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor

wait_for_data = S3KeySensor(
    task_id="wait_for_data",
    bucket_name="my-bucket",
    bucket_key="data/input.csv",
    poke_interval=60,
    timeout=3600,
)
'''
        sensors = detect_sensors(code)
        
        assert len(sensors) == 1
        assert sensors[0].sensor_type == "S3KeySensor"
        assert sensors[0].task_id == "wait_for_data"
        assert sensors[0].poke_interval == 60

    def test_detect_http_sensor(self):
        code = '''
from airflow.providers.http.sensors.http import HttpSensor

check_api = HttpSensor(
    task_id="check_api",
    endpoint="/health",
    http_conn_id="api_conn",
)
'''
        sensors = detect_sensors(code)
        
        assert len(sensors) == 1
        assert sensors[0].sensor_type == "HttpSensor"
        assert sensors[0].parameters.get("endpoint") == "/health"

    def test_detect_external_task_sensor(self):
        code = '''
from airflow.sensors.external_task import ExternalTaskSensor

wait_for_upstream = ExternalTaskSensor(
    task_id="wait_for_upstream",
    external_dag_id="upstream_dag",
    external_task_id="final_task",
)
'''
        sensors = detect_sensors(code)
        
        assert len(sensors) == 1
        assert sensors[0].sensor_type == "ExternalTaskSensor"
        assert sensors[0].parameters.get("external_dag_id") == "upstream_dag"

    def test_detect_multiple_sensors(self):
        code = '''
from airflow.sensors.filesystem import FileSensor
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor

wait_file = FileSensor(task_id="wait_file", filepath="/data/input")
wait_s3 = S3KeySensor(task_id="wait_s3", bucket_key="s3://bucket/key")
'''
        sensors = detect_sensors(code)
        
        assert len(sensors) == 2
        types = {s.sensor_type for s in sensors}
        assert types == {"FileSensor", "S3KeySensor"}

    def test_detect_reschedule_mode(self):
        code = '''
from airflow.sensors.filesystem import FileSensor

wait = FileSensor(
    task_id="wait",
    filepath="/data",
    mode="reschedule",
    poke_interval=300,
)
'''
        sensors = detect_sensors(code)
        
        assert sensors[0].mode == "reschedule"
        assert sensors[0].poke_interval == 300


class TestConvertSensor:
    """Test sensor conversion."""

    def test_convert_s3_sensor(self):
        sensor = SensorInfo(
            sensor_type="S3KeySensor",
            task_id="wait_for_data",
            parameters={"bucket_name": "my-bucket", "bucket_key": "data/file.csv"},
            poke_interval=60,
            timeout=3600,
        )
        
        result = convert_sensor(sensor)
        
        assert "boto3" in result.polling_code
        assert "@task" in result.polling_code
        assert "retries=60" in result.polling_code  # 3600/60
        assert "head_object" in result.polling_code

    def test_convert_http_sensor(self):
        sensor = SensorInfo(
            sensor_type="HttpSensor",
            task_id="check_api",
            parameters={"endpoint": "/health"},
            poke_interval=30,
            timeout=600,
        )
        
        result = convert_sensor(sensor)
        
        assert "httpx" in result.polling_code
        assert "check_api" in result.polling_code
        assert "retries=20" in result.polling_code  # 600/30

    def test_convert_external_task_sensor_warns(self):
        sensor = SensorInfo(
            sensor_type="ExternalTaskSensor",
            task_id="wait_upstream",
            parameters={"external_dag_id": "other_dag"},
        )
        
        result = convert_sensor(sensor)
        
        assert any("event" in w.lower() for w in result.warnings)
        assert "other_dag" in result.polling_code

    def test_convert_reschedule_mode_warns(self):
        sensor = SensorInfo(
            sensor_type="FileSensor",
            task_id="wait",
            mode="reschedule",
        )
        
        result = convert_sensor(sensor)
        
        assert any("reschedule" in w.lower() for w in result.warnings)

    def test_event_suggestion_for_s3(self):
        sensor = SensorInfo(
            sensor_type="S3KeySensor",
            task_id="wait",
        )
        
        result = convert_sensor(sensor)
        
        assert "event-driven" in result.event_suggestion.lower()
        assert "s3.object.created" in result.event_suggestion


class TestConvertAllSensors:
    """Test batch sensor conversion."""

    def test_convert_dag_with_sensors(self):
        code = '''
from airflow import DAG
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.operators.python import PythonOperator

with DAG("my_dag") as dag:
    wait = S3KeySensor(
        task_id="wait_for_data",
        bucket_key="s3://bucket/data",
        poke_interval=120,
        timeout=7200,
    )
    
    process = PythonOperator(
        task_id="process",
        python_callable=lambda: None,
    )
    
    wait >> process
'''
        result = convert_all_sensors(code)
        
        assert len(result["conversions"]) == 1
        assert "S3KeySensor" in result["summary"]
        assert "@task" in result["polling_code"]

    def test_no_sensors_returns_empty(self):
        code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG("my_dag") as dag:
    task = PythonOperator(task_id="task", python_callable=lambda: None)
'''
        result = convert_all_sensors(code)
        
        assert result["conversions"] == []
        assert "No sensors" in result["summary"]

    def test_produces_valid_python(self):
        code = '''
from airflow.sensors.filesystem import FileSensor

wait = FileSensor(task_id="wait", filepath="/data/file.txt")
'''
        result = convert_all_sensors(code)
        
        # Should produce valid Python
        compile(result["polling_code"], "<sensor>", "exec")
