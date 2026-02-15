"""Tests for Airflow Connection to Prefect Block converter."""

from airflow_unfactor.converters.connections import (
    CONNECTION_TO_BLOCK,
    ConnectionInfo,
    _sanitize_block_name,
    convert_all_connections,
    extract_connections,
    generate_block_scaffold,
    infer_conn_type_from_id,
)


class TestExtractConnections:
    """Test connection detection."""

    def test_detect_postgres_hook(self):
        code = """
from airflow.providers.postgres.hooks.postgres import PostgresHook

def extract_data():
    hook = PostgresHook(postgres_conn_id="my_postgres_conn")
    return hook.get_records("SELECT * FROM users")
"""
        connections = extract_connections(code)

        assert len(connections) == 1
        assert connections[0].name == "my_postgres_conn"
        assert connections[0].conn_type == "postgres"
        assert connections[0].hook_class == "PostgresHook"

    def test_detect_base_hook_get_connection(self):
        code = """
from airflow.hooks.base import BaseHook

def get_creds():
    conn = BaseHook.get_connection("my_aws_conn")
    return conn.extra_dejson
"""
        connections = extract_connections(code)

        assert len(connections) == 1
        assert connections[0].name == "my_aws_conn"
        assert connections[0].conn_type == "aws"
        assert connections[0].hook_class is None

    def test_detect_operator_conn_id(self):
        code = """
from airflow.providers.postgres.operators.postgres import PostgresOperator

task = PostgresOperator(
    task_id="run_query",
    postgres_conn_id="warehouse_db",
    sql="SELECT 1",
)
"""
        connections = extract_connections(code)

        assert len(connections) == 1
        assert connections[0].name == "warehouse_db"
        assert connections[0].conn_type == "postgres"

    def test_detect_multiple_connections(self):
        code = """
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook

def etl():
    pg_hook = PostgresHook(postgres_conn_id="pg_conn")
    s3_hook = S3Hook(aws_conn_id="aws_conn")
    return pg_hook, s3_hook
"""
        connections = extract_connections(code)

        assert len(connections) == 2
        conn_names = {c.name for c in connections}
        assert conn_names == {"pg_conn", "aws_conn"}

    def test_detect_snowflake_hook(self):
        code = """
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

hook = SnowflakeHook(snowflake_conn_id="sf_warehouse")
"""
        connections = extract_connections(code)

        assert len(connections) == 1
        assert connections[0].name == "sf_warehouse"
        assert connections[0].conn_type == "snowflake"
        assert connections[0].hook_class == "SnowflakeHook"

    def test_detect_bigquery_hook(self):
        code = """
from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook

hook = BigQueryHook(gcp_conn_id="gcp_default")
"""
        connections = extract_connections(code)

        assert len(connections) == 1
        assert connections[0].name == "gcp_default"
        assert connections[0].conn_type == "bigquery"

    def test_detect_slack_hook(self):
        code = """
from airflow.providers.slack.hooks.slack_webhook import SlackWebhookHook

hook = SlackWebhookHook(slack_webhook_conn_id="slack_alerts")
"""
        connections = extract_connections(code)

        assert len(connections) == 1
        assert connections[0].name == "slack_alerts"
        assert connections[0].conn_type == "slack_webhook"

    def test_deduplicate_connections(self):
        code = """
from airflow.providers.postgres.hooks.postgres import PostgresHook

def task1():
    hook = PostgresHook(postgres_conn_id="shared_db")
    return hook.get_records("SELECT 1")

def task2():
    hook = PostgresHook(postgres_conn_id="shared_db")
    return hook.get_records("SELECT 2")
"""
        connections = extract_connections(code)

        # Should only detect once
        assert len(connections) == 1
        assert connections[0].name == "shared_db"

    def test_infer_type_from_conn_id_pattern(self):
        code = """
from airflow.hooks.base import BaseHook

conn1 = BaseHook.get_connection("postgres_warehouse")
conn2 = BaseHook.get_connection("my_snowflake_db")
conn3 = BaseHook.get_connection("bigquery_analytics")
"""
        connections = extract_connections(code)

        conn_map = {c.name: c.conn_type for c in connections}
        assert conn_map["postgres_warehouse"] == "postgres"
        assert conn_map["my_snowflake_db"] == "snowflake"
        assert conn_map["bigquery_analytics"] == "bigquery"

    def test_no_connections(self):
        code = """
from airflow.operators.python import PythonOperator

def my_func():
    print("Hello")

task = PythonOperator(task_id="hello", python_callable=my_func)
"""
        connections = extract_connections(code)
        assert connections == []

    def test_invalid_syntax_returns_empty(self):
        code = "def invalid( syntax error"
        connections = extract_connections(code)
        assert connections == []


class TestInferConnType:
    """Test connection type inference from ID patterns."""

    def test_postgres_patterns(self):
        assert infer_conn_type_from_id("postgres_default") == "postgres"
        assert infer_conn_type_from_id("my_postgresql_conn") == "postgres"
        assert infer_conn_type_from_id("pg_warehouse") == "postgres"

    def test_snowflake_patterns(self):
        assert infer_conn_type_from_id("snowflake_prod") == "snowflake"
        assert infer_conn_type_from_id("sf_analytics") == "snowflake"

    def test_bigquery_patterns(self):
        assert infer_conn_type_from_id("bigquery_default") == "bigquery"
        assert infer_conn_type_from_id("bq_project") == "bigquery"

    def test_aws_patterns(self):
        assert infer_conn_type_from_id("aws_default") == "aws"
        assert infer_conn_type_from_id("s3_bucket_conn") == "s3"

    def test_gcp_patterns(self):
        assert infer_conn_type_from_id("gcp_default") == "google_cloud"
        assert infer_conn_type_from_id("google_analytics_conn") == "google_cloud"

    def test_unknown_pattern(self):
        assert infer_conn_type_from_id("my_custom_conn") is None
        assert infer_conn_type_from_id("xyz123") is None


class TestSanitizeBlockName:
    """Test block name sanitization."""

    def test_underscore_to_hyphen(self):
        assert _sanitize_block_name("my_postgres_conn") == "my-postgres-conn"

    def test_lowercase(self):
        assert _sanitize_block_name("MY_CONN") == "my-conn"

    def test_remove_invalid_chars(self):
        assert _sanitize_block_name("conn@123!") == "conn123"

    def test_strip_hyphens(self):
        assert _sanitize_block_name("-conn-") == "conn"

    def test_empty_returns_default(self):
        assert _sanitize_block_name("@@@") == "default-connection"


class TestGenerateBlockScaffold:
    """Test Block scaffold code generation."""

    def test_postgres_scaffold(self):
        info = ConnectionInfo(
            name="my_postgres_conn",
            conn_type="postgres",
            hook_class="PostgresHook",
            line_number=10,
        )

        code, setup, warnings = generate_block_scaffold(info)

        assert "SqlAlchemyConnector" in code
        assert "prefect_sqlalchemy" in code
        assert 'SqlAlchemyConnector.load("my-postgres-conn")' in code
        assert "postgresql+psycopg2" in setup
        assert len(warnings) == 0

    def test_s3_scaffold(self):
        info = ConnectionInfo(
            name="s3_data_bucket",
            conn_type="s3",
            hook_class="S3Hook",
            line_number=5,
        )

        code, setup, warnings = generate_block_scaffold(info)

        assert "S3Bucket" in code
        assert "prefect_aws" in code
        assert 'S3Bucket.load("s3-data-bucket")' in code
        assert len(warnings) == 0

    def test_snowflake_scaffold(self):
        info = ConnectionInfo(
            name="sf_warehouse",
            conn_type="snowflake",
            hook_class="SnowflakeHook",
        )

        code, setup, warnings = generate_block_scaffold(info)

        assert "SnowflakeConnector" in code
        assert "prefect_snowflake" in code
        assert "SnowflakeCredentials" in setup
        assert len(warnings) == 0

    def test_bigquery_scaffold(self):
        info = ConnectionInfo(
            name="bq_default",
            conn_type="bigquery",
            hook_class="BigQueryHook",
        )

        code, setup, warnings = generate_block_scaffold(info)

        assert "BigQueryWarehouse" in code
        assert "prefect_gcp" in code
        assert len(warnings) == 0

    def test_slack_scaffold(self):
        info = ConnectionInfo(
            name="slack_webhook",
            conn_type="slack",
            hook_class="SlackHook",
        )

        code, setup, warnings = generate_block_scaffold(info)

        assert "SlackWebhook" in code
        assert "prefect_slack" in code
        assert "webhook" in setup.lower()
        assert len(warnings) == 0

    def test_unknown_type_warns(self):
        info = ConnectionInfo(
            name="my_custom_conn",
            conn_type="custom_type",
            hook_class="CustomHook",
        )

        code, setup, warnings = generate_block_scaffold(info)

        assert len(warnings) == 1
        assert "Unknown connection type" in warnings[0]
        assert "Manual configuration required" in code or "TODO" in code

    def test_unknown_type_no_conn_type(self):
        info = ConnectionInfo(
            name="mystery_conn",
            conn_type=None,
            hook_class=None,
        )

        code, setup, warnings = generate_block_scaffold(info)

        assert len(warnings) == 1
        assert "unknown" in warnings[0].lower()

    def test_without_comments(self):
        info = ConnectionInfo(
            name="pg_conn",
            conn_type="postgres",
            hook_class=None,
        )

        code, _, _ = generate_block_scaffold(info, include_comments=False)

        # Should not have comment lines
        assert not any(line.strip().startswith("#") for line in code.split("\n") if line.strip())


class TestConvertAllConnections:
    """Test batch connection conversion."""

    def test_convert_dag_with_multiple_connections(self):
        code = """
from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

with DAG("etl_dag") as dag:
    def extract():
        pg = PostgresHook(postgres_conn_id="source_db")
        return pg.get_records("SELECT * FROM data")

    def load():
        s3 = S3Hook(aws_conn_id="data_lake")
        sf = SnowflakeHook(snowflake_conn_id="warehouse")
"""
        result = convert_all_connections(code)

        assert len(result["connections"]) == 3
        assert len(result["scaffolds"]) == 3
        assert "prefect-sqlalchemy" in result["pip_packages"]
        assert "prefect-aws" in result["pip_packages"]
        assert "prefect-snowflake" in result["pip_packages"]

    def test_no_connections_returns_empty(self):
        code = """
from airflow import DAG
from airflow.operators.python import PythonOperator

task = PythonOperator(task_id="hello", python_callable=lambda: None)
"""
        result = convert_all_connections(code)

        assert result["connections"] == []
        assert result["scaffolds"] == []
        assert result["pip_packages"] == []
        assert "No Airflow connections" in result["combined_setup"]

    def test_combined_code_valid_python(self):
        code = """
from airflow.providers.postgres.hooks.postgres import PostgresHook

hook = PostgresHook(postgres_conn_id="db")
"""
        result = convert_all_connections(code)

        # Combined code should be valid Python
        compile(result["combined_code"], "<test>", "exec")

    def test_warnings_collected(self):
        code = """
from airflow.hooks.base import BaseHook

conn = BaseHook.get_connection("unknown_system_xyz")
"""
        result = convert_all_connections(code)

        # Should have a warning for unknown connection type
        assert len(result["all_warnings"]) >= 1


class TestConnectionToBlockMapping:
    """Test the CONNECTION_TO_BLOCK mapping completeness."""

    def test_postgres_mapping_exists(self):
        assert "postgres" in CONNECTION_TO_BLOCK
        assert "postgresql" in CONNECTION_TO_BLOCK

    def test_aws_mappings_exist(self):
        assert "aws" in CONNECTION_TO_BLOCK
        assert "s3" in CONNECTION_TO_BLOCK

    def test_gcp_mappings_exist(self):
        assert "google_cloud" in CONNECTION_TO_BLOCK
        assert "google_cloud_platform" in CONNECTION_TO_BLOCK
        assert "bigquery" in CONNECTION_TO_BLOCK

    def test_snowflake_mapping_exists(self):
        assert "snowflake" in CONNECTION_TO_BLOCK

    def test_slack_mapping_exists(self):
        assert "slack" in CONNECTION_TO_BLOCK
        assert "slack_webhook" in CONNECTION_TO_BLOCK

    def test_all_mappings_have_required_fields(self):
        for conn_type, block_info in CONNECTION_TO_BLOCK.items():
            assert block_info.block_class, f"{conn_type} missing block_class"
            assert block_info.import_statement, f"{conn_type} missing import_statement"
            assert block_info.pip_package, f"{conn_type} missing pip_package"
            assert block_info.load_pattern, f"{conn_type} missing load_pattern"
            assert block_info.setup_instructions, f"{conn_type} missing setup_instructions"


class TestRealWorldDAGPatterns:
    """Test with realistic DAG patterns."""

    def test_typical_etl_dag(self):
        code = '''
from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.operators.python import PythonOperator
from datetime import datetime

with DAG(
    "customer_data_etl",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
) as dag:

    def extract_customers():
        hook = PostgresHook(postgres_conn_id="prod_db")
        records = hook.get_records("""
            SELECT id, name, email, created_at
            FROM customers
            WHERE created_at >= '{{ ds }}'
        """)
        return records

    def upload_to_s3(**context):
        s3 = S3Hook(aws_conn_id="data_lake_s3")
        records = context["ti"].xcom_pull(task_ids="extract")
        s3.load_string(
            string_data=str(records),
            bucket_name="customer-data",
            key="daily/{{ ds }}/customers.json",
        )

    extract = PythonOperator(
        task_id="extract",
        python_callable=extract_customers,
    )

    upload = PythonOperator(
        task_id="upload",
        python_callable=upload_to_s3,
    )

    extract >> upload
'''
        result = convert_all_connections(code)

        assert len(result["connections"]) == 2

        conn_map = {c.name: c for c in result["connections"]}
        assert "prod_db" in conn_map
        assert "data_lake_s3" in conn_map
        assert conn_map["prod_db"].conn_type == "postgres"
        assert conn_map["data_lake_s3"].conn_type == "s3"

        assert "SqlAlchemyConnector" in result["combined_code"]
        assert "S3Bucket" in result["combined_code"]

    def test_notification_dag(self):
        code = """
from airflow.providers.slack.hooks.slack_webhook import SlackWebhookHook

def send_alert():
    hook = SlackWebhookHook(slack_webhook_conn_id="team_alerts")
    hook.send_text("Pipeline completed!")
"""
        result = convert_all_connections(code)

        assert len(result["connections"]) == 1
        assert result["connections"][0].conn_type == "slack_webhook"
        assert "SlackWebhook" in result["combined_code"]
        assert "prefect-slack" in result["pip_packages"]

    def test_multi_database_dag(self):
        code = """
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

def sync_data():
    # Extract from MySQL
    mysql = MySqlHook(mysql_conn_id="source_mysql")
    data = mysql.get_records("SELECT * FROM orders")

    # Load to Postgres staging
    pg = PostgresHook(postgres_conn_id="staging_pg")
    pg.insert_rows("staging.orders", data)

    # Load to Snowflake warehouse
    sf = SnowflakeHook(snowflake_conn_id="analytics_sf")
    sf.run("INSERT INTO orders SELECT * FROM staging.orders")
"""
        result = convert_all_connections(code)

        assert len(result["connections"]) == 3

        # All should map to appropriate blocks
        conn_types = {c.conn_type for c in result["connections"]}
        assert "mysql" in conn_types
        assert "postgres" in conn_types
        assert "snowflake" in conn_types

        # Should need multiple packages
        assert "prefect-sqlalchemy" in result["pip_packages"]
        assert "prefect-snowflake" in result["pip_packages"]
