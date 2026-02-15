"""Tests for Provider Operator mappings.

See specs/provider-operators.openspec.md for specification.
"""

import pytest

from airflow_unfactor.converters.provider_mappings import (
    OPERATOR_MAPPINGS,
    OperatorMapping,
    generate_conversion_code,
    get_all_mappings,
    get_operator_mapping,
    get_operators_by_category,
    summarize_operator_support,
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


class TestNewAWSOperators:
    """Tests for expanded AWS operator coverage."""

    def test_s3_copy_operator(self):
        mapping = get_operator_mapping("S3CopyObjectOperator")

        assert mapping is not None
        assert mapping.prefect_integration == "prefect-aws"
        assert "copy" in mapping.prefect_function

    def test_s3_list_operator(self):
        mapping = get_operator_mapping("S3ListOperator")

        assert mapping is not None
        assert "list" in mapping.prefect_function

    def test_s3_file_transform_operator(self):
        mapping = get_operator_mapping("S3FileTransformOperator")

        assert mapping is not None
        assert "transform" in mapping.prefect_function

    def test_ecs_run_task_operator(self):
        mapping = get_operator_mapping("EcsRunTaskOperator")

        assert mapping is not None
        assert mapping.prefect_integration == "prefect-aws"
        assert "ecs" in mapping.prefect_function

    def test_eks_create_cluster_operator(self):
        mapping = get_operator_mapping("EksCreateClusterOperator")

        assert mapping is not None
        assert "eks" in mapping.prefect_function

    def test_eks_pod_operator(self):
        mapping = get_operator_mapping("EksPodOperator")

        assert mapping is not None
        assert mapping.prefect_integration == "prefect-kubernetes"

    def test_glue_job_operator(self):
        mapping = get_operator_mapping("GlueJobOperator")

        assert mapping is not None
        assert "glue" in mapping.prefect_function

    def test_glue_crawler_operator(self):
        mapping = get_operator_mapping("GlueCrawlerOperator")

        assert mapping is not None
        assert "glue" in mapping.prefect_function

    def test_redshift_sql_operator(self):
        mapping = get_operator_mapping("RedshiftSQLOperator")

        assert mapping is not None
        assert "redshift" in mapping.prefect_function


class TestNewGCPOperators:
    """Tests for expanded GCP operator coverage."""

    def test_gcs_to_gcs_operator(self):
        mapping = get_operator_mapping("GCSToGCSOperator")

        assert mapping is not None
        assert mapping.prefect_integration == "prefect-gcp"
        assert "copy" in mapping.prefect_function

    def test_gcs_delete_objects_operator(self):
        mapping = get_operator_mapping("GCSDeleteObjectsOperator")

        assert mapping is not None
        assert "delete" in mapping.prefect_function

    def test_gcs_file_transform_operator(self):
        mapping = get_operator_mapping("GCSFileTransformOperator")

        assert mapping is not None
        assert "transform" in mapping.prefect_function

    def test_dataproc_submit_job_operator(self):
        mapping = get_operator_mapping("DataprocSubmitJobOperator")

        assert mapping is not None
        assert "dataproc" in mapping.prefect_function

    def test_dataproc_create_cluster_operator(self):
        mapping = get_operator_mapping("DataprocCreateClusterOperator")

        assert mapping is not None
        assert "dataproc" in mapping.prefect_function

    def test_pubsub_publish_message_operator(self):
        mapping = get_operator_mapping("PubSubPublishMessageOperator")

        assert mapping is not None
        assert "pubsub" in mapping.prefect_function

    def test_pubsub_create_subscription_operator(self):
        mapping = get_operator_mapping("PubSubCreateSubscriptionOperator")

        assert mapping is not None
        assert "pubsub" in mapping.prefect_function


class TestAzureOperators:
    """Tests for Azure operator coverage."""

    def test_wasb_blob_operator(self):
        mapping = get_operator_mapping("WasbBlobOperator")

        assert mapping is not None
        assert mapping.prefect_integration == "prefect-azure"
        assert "blob" in mapping.prefect_function

    def test_azure_data_factory_operator(self):
        mapping = get_operator_mapping("AzureDataFactoryRunPipelineOperator")

        assert mapping is not None
        assert "adf" in mapping.prefect_function


class TestDatabricksOperators:
    """Tests for Databricks operator coverage."""

    def test_databricks_run_now_operator(self):
        mapping = get_operator_mapping("DatabricksRunNowOperator")

        assert mapping is not None
        assert mapping.prefect_integration == "prefect-databricks"
        assert "run_now" in mapping.prefect_function

    def test_databricks_submit_run_operator(self):
        mapping = get_operator_mapping("DatabricksSubmitRunOperator")

        assert mapping is not None
        assert "submit" in mapping.prefect_function

    def test_databricks_sql_operator(self):
        mapping = get_operator_mapping("DatabricksSqlOperator")

        assert mapping is not None
        assert "sql" in mapping.prefect_function


class TestDbtOperators:
    """Tests for dbt operator coverage."""

    def test_dbt_cloud_run_job_operator(self):
        mapping = get_operator_mapping("DbtCloudRunJobOperator")

        assert mapping is not None
        assert mapping.prefect_integration == "prefect-dbt"
        assert "dbt_cloud" in mapping.prefect_function

    def test_dbt_run_operator(self):
        mapping = get_operator_mapping("DbtRunOperator")

        assert mapping is not None
        assert "dbt" in mapping.prefect_function


class TestCategoryOrganization:
    """Tests for operator category organization."""

    def test_get_operators_by_category_returns_all_categories(self):
        categories = get_operators_by_category()

        assert "aws_s3" in categories
        assert "aws_compute" in categories
        assert "aws_data" in categories
        assert "gcp_storage" in categories
        assert "gcp_compute" in categories
        assert "gcp_messaging" in categories
        assert "azure" in categories
        assert "databricks" in categories
        assert "dbt" in categories
        assert "database" in categories

    def test_all_categorized_operators_exist_in_registry(self):
        """All operators in categories should exist in OPERATOR_MAPPINGS."""
        categories = get_operators_by_category()

        for category, operators in categories.items():
            for op in operators:
                assert op in OPERATOR_MAPPINGS, f"{op} in {category} not in registry"

    def test_operator_count_meets_minimum(self):
        """Should have at least 30 operator mappings."""
        assert len(OPERATOR_MAPPINGS) >= 30


class TestCodeValidation:
    """Tests that all generated code is valid Python."""

    def test_all_operator_code_compiles(self):
        """All operator code templates should be valid Python."""
        for op_name in OPERATOR_MAPPINGS:
            try:
                # The code_template alone may not compile (needs decorator context)
                # So we wrap it in the full generated code
                result = generate_conversion_code(
                    op_name,
                    task_id=f"test_{op_name.lower().replace('operator', '')}",
                    parameters={},
                    include_comments=False,
                )
                compile(result["code"], f"<{op_name}>", "exec")
            except SyntaxError as e:
                pytest.fail(f"Invalid Python in {op_name}: {e}")
