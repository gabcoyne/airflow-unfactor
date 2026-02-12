"""Tests for Provider Operator mappings.

See specs/provider-operators.openspec.md for specification.
"""

import pytest
from airflow_unfactor.converters.provider_mappings import (
    get_operator_mapping,
    get_all_mappings,
    generate_conversion_code,
    summarize_operator_support,
    OperatorMapping,
)


class TestOperatorMappings:
    """Test operator mapping registry."""

    def test_s3_operator_mapping(self):
        mapping = get_operator_mapping("S3CreateObjectOperator")
        
        assert mapping is not None
        assert mapping.prefect_integration == "prefect-aws"
        assert "prefect-aws" in mapping.pip_packages

    def test_bigquery_operator_mapping(self):
        mapping = get_operator_mapping("BigQueryInsertJobOperator")
        
        assert mapping is not None
        assert mapping.prefect_integration == "prefect-gcp"
        assert "bigquery" in mapping.prefect_function

    def test_postgres_operator_mapping(self):
        mapping = get_operator_mapping("PostgresOperator")
        
        assert mapping is not None
        assert "sqlalchemy" in mapping.prefect_integration.lower()
        assert "psycopg" in mapping.pip_packages[1]

    def test_snowflake_operator_mapping(self):
        mapping = get_operator_mapping("SnowflakeOperator")
        
        assert mapping is not None
        assert "snowflake" in mapping.prefect_integration.lower()

    def test_slack_operator_mapping(self):
        mapping = get_operator_mapping("SlackWebhookOperator")
        
        assert mapping is not None
        assert "slack" in mapping.prefect_integration.lower()
        assert "send_message" in mapping.prefect_function

    def test_unknown_operator_returns_none(self):
        mapping = get_operator_mapping("FakeOperator")
        assert mapping is None

    def test_all_mappings_returns_dict(self):
        mappings = get_all_mappings()
        
        assert isinstance(mappings, dict)
        assert len(mappings) > 5  # We have several mappings
        assert all(isinstance(v, OperatorMapping) for v in mappings.values())


class TestGenerateConversionCode:
    """Test code generation for operators."""

    def test_generate_s3_code(self):
        result = generate_conversion_code(
            "S3CreateObjectOperator",
            task_id="upload_data",
            parameters={"bucket_name": "my-bucket", "key": "data.csv"},
        )
        
        assert "@task" in result["code"]
        assert "S3Bucket" in result["code"]
        assert "prefect-aws" in result["packages"]

    def test_generate_bigquery_code(self):
        result = generate_conversion_code(
            "BigQueryInsertJobOperator",
            task_id="run_query",
            parameters={"sql": "SELECT * FROM table"},
        )
        
        assert "bigquery" in result["code"].lower()
        assert "prefect-gcp" in result["packages"]

    def test_generate_unknown_operator_code(self):
        result = generate_conversion_code(
            "CustomOperator",
            task_id="custom_task",
            parameters={"param": "value"},
        )
        
        assert "NotImplementedError" in result["code"]
        assert "Manual conversion" in result["notes"][0]

    def test_generated_code_is_valid_python(self):
        """All generated code should be valid Python."""
        for op_name in ["S3CreateObjectOperator", "PostgresOperator", "SlackWebhookOperator"]:
            result = generate_conversion_code(
                op_name,
                task_id=f"test_{op_name.lower()}",
                parameters={},
            )
            # Should compile without errors
            compile(result["code"], f"<{op_name}>", "exec")

    def test_includes_comments_when_requested(self):
        result = generate_conversion_code(
            "PostgresOperator",
            task_id="pg_task",
            parameters={},
            include_comments=True,
        )
        
        assert "Converted from Airflow" in result["code"]

    def test_excludes_comments_when_not_requested(self):
        result = generate_conversion_code(
            "PostgresOperator",
            task_id="pg_task",
            parameters={},
            include_comments=False,
        )
        
        assert "Converted from Airflow" not in result["code"]


class TestSupportSummary:
    """Test support summary generation."""

    def test_summary_includes_categories(self):
        summary = summarize_operator_support()
        
        assert "AWS" in summary
        assert "GCP" in summary
        assert "Database" in summary
        assert "Notifications" in summary

    def test_summary_includes_operators(self):
        summary = summarize_operator_support()
        
        assert "S3CreateObjectOperator" in summary
        assert "BigQueryInsertJobOperator" in summary
        assert "PostgresOperator" in summary
