"""Converters for Airflow DAGs to Prefect flows."""

from airflow_unfactor.converters.base import convert_dag_to_flow
from airflow_unfactor.converters.custom_operators import (
    CORE_OPERATORS,
    CustomOperatorInfo,
    convert_custom_operators,
    extract_custom_operators,
    generate_custom_operator_stub,
    is_known_operator,
)
from airflow_unfactor.converters.datasets import (
    DatasetAnalysis,
    DatasetInfo,
    analyze_datasets,
    generate_event_code,
    uri_to_event_name,
)
from airflow_unfactor.converters.dynamic_mapping import (
    ConversionResult,
    DynamicMappingInfo,
    MappingType,
    convert_all_dynamic_mappings,
    convert_dynamic_mapping,
    extract_dynamic_mapping,
)
from airflow_unfactor.converters.jinja import (
    JinjaPattern,
    JinjaPatternType,
    analyze_jinja_in_code,
    convert_jinja_to_fstring,
    detect_jinja_patterns,
    has_jinja_patterns,
)
from airflow_unfactor.converters.provider_mappings import (
    OperatorMapping,
    generate_conversion_code,
    get_all_mappings,
    get_operator_mapping,
    summarize_operator_support,
)
from airflow_unfactor.converters.runbook import (
    SCHEDULE_PRESETS,
    CallbackInfo,
    DAGSettings,
    DAGSettingsVisitor,
    extract_dag_settings,
    generate_runbook,
)
from airflow_unfactor.converters.sensors import (
    SensorConversion,
    SensorInfo,
    convert_all_sensors,
    convert_sensor,
    detect_sensors,
)
from airflow_unfactor.converters.taskflow import (
    DagInfo,
    TaskInfo,
    convert_taskflow_to_prefect,
    extract_taskflow_info,
)
from airflow_unfactor.converters.taskgroup import (
    TaskGroupInfo,
    convert_all_task_groups,
    convert_task_group,
    extract_task_groups,
)
from airflow_unfactor.converters.trigger_rules import (
    TRIGGER_RULE_PATTERNS,
    TriggerRuleInfo,
    convert_trigger_rules,
    detect_trigger_rules,
    generate_trigger_rule_code,
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
    # Jinja2 converter
    "detect_jinja_patterns",
    "convert_jinja_to_fstring",
    "has_jinja_patterns",
    "analyze_jinja_in_code",
    "JinjaPattern",
    "JinjaPatternType",
    # Dynamic mapping converter
    "extract_dynamic_mapping",
    "convert_dynamic_mapping",
    "convert_all_dynamic_mappings",
    "DynamicMappingInfo",
    "MappingType",
    "ConversionResult",
    # Trigger rules converter
    "detect_trigger_rules",
    "generate_trigger_rule_code",
    "convert_trigger_rules",
    "TriggerRuleInfo",
    "TRIGGER_RULE_PATTERNS",
    # TaskGroup converter
    "extract_task_groups",
    "convert_task_group",
    "convert_all_task_groups",
    "TaskGroupInfo",
    # Custom operator handler
    "extract_custom_operators",
    "generate_custom_operator_stub",
    "convert_custom_operators",
    "is_known_operator",
    "CustomOperatorInfo",
    "CORE_OPERATORS",
    # Runbook generator
    "extract_dag_settings",
    "generate_runbook",
    "DAGSettings",
    "CallbackInfo",
    "DAGSettingsVisitor",
    "SCHEDULE_PRESETS",
]
