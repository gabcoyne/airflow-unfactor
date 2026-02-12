"""Converters for Airflow DAGs to Prefect flows."""

from airflow_unfactor.converters.base import convert_dag_to_flow
from airflow_unfactor.converters.taskflow import (
    convert_taskflow_to_prefect,
    extract_taskflow_info,
    TaskInfo,
    DagInfo,
)
from airflow_unfactor.converters.datasets import (
    analyze_datasets,
    generate_event_code,
    uri_to_event_name,
    DatasetInfo,
    DatasetAnalysis,
)
from airflow_unfactor.converters.sensors import (
    detect_sensors,
    convert_sensor,
    convert_all_sensors,
    SensorInfo,
    SensorConversion,
)
from airflow_unfactor.converters.provider_mappings import (
    get_operator_mapping,
    get_all_mappings,
    generate_conversion_code,
    summarize_operator_support,
    OperatorMapping,
)

__all__ = [
    # Base converter
    "convert_dag_to_flow",
    # TaskFlow converter
    "convert_taskflow_to_prefect",
    "extract_taskflow_info",
    "TaskInfo",
    "DagInfo",
    # Dataset converter
    "analyze_datasets",
    "generate_event_code",
    "uri_to_event_name",
    "DatasetInfo",
    "DatasetAnalysis",
    # Sensor converter
    "detect_sensors",
    "convert_sensor",
    "convert_all_sensors",
    "SensorInfo",
    "SensorConversion",
    # Provider operators
    "get_operator_mapping",
    "get_all_mappings",
    "generate_conversion_code",
    "summarize_operator_support",
    "OperatorMapping",
]
