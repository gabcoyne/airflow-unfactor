"""Tests for runbook generation from DAG settings extraction."""

import pytest

from airflow_unfactor.converters.runbook import (
    DAGSettings,
    CallbackInfo,
    DAGSettingsVisitor,
    extract_dag_settings,
    generate_runbook,
    _convert_schedule_to_cron,
    SCHEDULE_PRESETS,
)


class TestDAGSettingsDataclass:
    """Test DAGSettings dataclass behavior."""

    def test_default_values(self):
        settings = DAGSettings()
        assert settings.dag_id == ""
        assert settings.schedule is None
        assert settings.catchup is None
        assert settings.default_args == {}
        assert settings.max_active_runs is None
        assert settings.tags == []
        assert settings.callbacks == []
        assert settings.source_type == "unknown"

    def test_with_values(self):
        settings = DAGSettings(
            dag_id="my_dag",
            schedule="@daily",
            catchup=False,
            default_args={"retries": 3},
            max_active_runs=5,
            tags=["production", "etl"],
        )
        assert settings.dag_id == "my_dag"
        assert settings.schedule == "@daily"
        assert settings.catchup is False
        assert settings.default_args == {"retries": 3}
        assert settings.max_active_runs == 5
        assert settings.tags == ["production", "etl"]


class TestCallbackInfoDataclass:
    """Test CallbackInfo dataclass behavior."""

    def test_default_values(self):
        callback = CallbackInfo(
            callback_type="on_failure_callback",
            function_name="notify_failure",
        )
        assert callback.callback_type == "on_failure_callback"
        assert callback.function_name == "notify_failure"
        assert callback.line_number == 0

    def test_with_line_number(self):
        callback = CallbackInfo(
            callback_type="on_success_callback",
            function_name="notify_success",
            line_number=42,
        )
        assert callback.line_number == 42


class TestExtractDAGSettingsFromDAGConstructor:
    """Test extraction from DAG() constructor."""

    def test_extract_dag_id_from_first_arg(self):
        code = '''
from airflow import DAG

with DAG("my_etl_dag", schedule=None) as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert settings.dag_id == "my_etl_dag"
        assert settings.source_type == "DAG()"

    def test_extract_dag_id_from_keyword(self):
        code = '''
from airflow import DAG

with DAG(dag_id="keyword_dag", schedule=None) as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert settings.dag_id == "keyword_dag"

    def test_extract_schedule_interval(self):
        code = '''
from airflow import DAG

with DAG("test", schedule_interval="@daily") as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert settings.schedule == "@daily"

    def test_extract_schedule(self):
        code = '''
from airflow import DAG

with DAG("test", schedule="0 2 * * *") as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert settings.schedule == "0 2 * * *"

    def test_extract_catchup_false(self):
        code = '''
from airflow import DAG

with DAG("test", catchup=False, schedule=None) as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert settings.catchup is False

    def test_extract_catchup_true(self):
        code = '''
from airflow import DAG

with DAG("test", catchup=True, schedule=None) as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert settings.catchup is True

    def test_extract_max_active_runs(self):
        code = '''
from airflow import DAG

with DAG("test", max_active_runs=3, schedule=None) as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert settings.max_active_runs == 3

    def test_extract_max_consecutive_failed_dag_runs(self):
        code = '''
from airflow import DAG

with DAG("test", max_consecutive_failed_dag_runs=5, schedule=None) as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert settings.max_consecutive_failed_dag_runs == 5

    def test_extract_tags(self):
        code = '''
from airflow import DAG

with DAG("test", tags=["production", "etl", "critical"], schedule=None) as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert settings.tags == ["production", "etl", "critical"]

    def test_extract_default_args_inline(self):
        code = '''
from airflow import DAG

with DAG("test", default_args={"retries": 3, "retry_delay": 300}, schedule=None) as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert settings.default_args["retries"] == 3
        assert settings.default_args["retry_delay"] == 300

    def test_extract_on_failure_callback(self):
        code = '''
from airflow import DAG

def notify_failure(context):
    pass

with DAG("test", on_failure_callback=notify_failure, schedule=None) as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert len(settings.callbacks) == 1
        assert settings.callbacks[0].callback_type == "on_failure_callback"
        assert settings.callbacks[0].function_name == "notify_failure"

    def test_extract_on_success_callback(self):
        code = '''
from airflow import DAG

def notify_success(context):
    pass

with DAG("test", on_success_callback=notify_success, schedule=None) as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert len(settings.callbacks) == 1
        assert settings.callbacks[0].callback_type == "on_success_callback"
        assert settings.callbacks[0].function_name == "notify_success"

    def test_extract_sla_miss_callback(self):
        code = '''
from airflow import DAG

def sla_alert(dag, task_list, blocking_task_list, slas, blocking_tis):
    pass

with DAG("test", sla_miss_callback=sla_alert, schedule=None) as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert len(settings.callbacks) == 1
        assert settings.callbacks[0].callback_type == "sla_miss_callback"
        assert settings.callbacks[0].function_name == "sla_alert"

    def test_extract_multiple_callbacks(self):
        code = '''
from airflow import DAG

def on_fail(context): pass
def on_success(context): pass

with DAG(
    "test",
    on_failure_callback=on_fail,
    on_success_callback=on_success,
    schedule=None
) as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert len(settings.callbacks) == 2
        callback_types = {c.callback_type for c in settings.callbacks}
        assert "on_failure_callback" in callback_types
        assert "on_success_callback" in callback_types

    def test_extract_concurrency(self):
        code = '''
from airflow import DAG

with DAG("test", concurrency=10, schedule=None) as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert settings.concurrency == 10

    def test_extract_dagrun_timeout(self):
        code = '''
from airflow import DAG
from datetime import timedelta

with DAG("test", dagrun_timeout=timedelta(hours=2), schedule=None) as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert "timedelta" in str(settings.dagrun_timeout)

    def test_extract_description(self):
        code = '''
from airflow import DAG

with DAG("test", description="This is my ETL pipeline", schedule=None) as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert settings.description == "This is my ETL pipeline"


class TestExtractDAGSettingsFromDecorator:
    """Test extraction from @dag decorator."""

    def test_extract_bare_dag_decorator(self):
        code = '''
from airflow.decorators import dag

@dag
def my_taskflow_dag():
    pass
'''
        settings = extract_dag_settings(code)
        assert settings.dag_id == "my_taskflow_dag"
        assert settings.source_type == "@dag"

    def test_extract_dag_decorator_with_args(self):
        code = '''
from airflow.decorators import dag

@dag(schedule="@daily", catchup=False)
def daily_etl():
    pass
'''
        settings = extract_dag_settings(code)
        assert settings.dag_id == "daily_etl"
        assert settings.schedule == "@daily"
        assert settings.catchup is False
        assert settings.source_type == "@dag"

    def test_extract_dag_decorator_with_dag_id(self):
        code = '''
from airflow.decorators import dag

@dag(dag_id="custom_dag_id", schedule=None)
def my_function():
    pass
'''
        settings = extract_dag_settings(code)
        assert settings.dag_id == "custom_dag_id"

    def test_extract_dag_decorator_all_settings(self):
        code = '''
from airflow.decorators import dag

@dag(
    schedule="0 2 * * *",
    catchup=False,
    max_active_runs=3,
    max_consecutive_failed_dag_runs=5,
    default_args={"retries": 2, "retry_delay": 60},
    tags=["production", "ml"]
)
def complex_dag():
    pass
'''
        settings = extract_dag_settings(code)
        assert settings.schedule == "0 2 * * *"
        assert settings.catchup is False
        assert settings.max_active_runs == 3
        assert settings.max_consecutive_failed_dag_runs == 5
        assert settings.default_args["retries"] == 2
        assert settings.tags == ["production", "ml"]

    def test_extract_dag_decorator_with_callbacks(self):
        code = '''
from airflow.decorators import dag

def notify(context):
    pass

@dag(on_failure_callback=notify, schedule=None)
def my_dag():
    pass
'''
        settings = extract_dag_settings(code)
        assert len(settings.callbacks) == 1
        assert settings.callbacks[0].callback_type == "on_failure_callback"
        assert settings.callbacks[0].function_name == "notify"


class TestExtractDAGSettingsEdgeCases:
    """Test edge cases in extraction."""

    def test_invalid_syntax_returns_empty(self):
        code = "def invalid( syntax error"
        settings = extract_dag_settings(code)
        assert settings.dag_id == ""
        assert settings.schedule is None

    def test_no_dag_returns_empty(self):
        code = '''
from airflow.operators.python import PythonOperator

def my_func():
    pass
'''
        settings = extract_dag_settings(code)
        assert settings.dag_id == ""

    def test_dag_assignment_not_context_manager(self):
        code = '''
from airflow import DAG

dag = DAG("assigned_dag", schedule="@hourly")
'''
        settings = extract_dag_settings(code)
        assert settings.dag_id == "assigned_dag"
        assert settings.schedule == "@hourly"

    def test_lambda_callback(self):
        code = '''
from airflow import DAG

with DAG("test", on_failure_callback=lambda ctx: print(ctx), schedule=None) as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert len(settings.callbacks) == 1
        assert settings.callbacks[0].function_name == "<lambda>"

    def test_variable_reference_default_args(self):
        code = '''
from airflow import DAG

default_args = {"retries": 3}

with DAG("test", default_args=default_args, schedule=None) as dag:
    pass
'''
        settings = extract_dag_settings(code)
        assert "_variable_ref" in settings.default_args or isinstance(
            settings.default_args.get("_variable_ref", ""), str
        )


class TestConvertScheduleToCron:
    """Test schedule preset to cron conversion."""

    def test_hourly_preset(self):
        assert _convert_schedule_to_cron("@hourly") == "0 * * * *"

    def test_daily_preset(self):
        assert _convert_schedule_to_cron("@daily") == "0 0 * * *"

    def test_weekly_preset(self):
        assert _convert_schedule_to_cron("@weekly") == "0 0 * * 0"

    def test_monthly_preset(self):
        assert _convert_schedule_to_cron("@monthly") == "0 0 1 * *"

    def test_yearly_preset(self):
        assert _convert_schedule_to_cron("@yearly") == "0 0 1 1 *"

    def test_annually_preset(self):
        assert _convert_schedule_to_cron("@annually") == "0 0 1 1 *"

    def test_once_preset_returns_none(self):
        assert _convert_schedule_to_cron("@once") is None

    def test_cron_expression_passthrough(self):
        assert _convert_schedule_to_cron("0 2 * * *") == "0 2 * * *"
        assert _convert_schedule_to_cron("30 14 * * 1-5") == "30 14 * * 1-5"

    def test_none_returns_none(self):
        assert _convert_schedule_to_cron(None) is None


class TestGenerateRunbookBasic:
    """Test basic runbook generation."""

    def test_minimal_runbook(self):
        settings = DAGSettings(dag_id="test_dag")
        runbook = generate_runbook(settings)

        assert "# Migration Runbook: `test_dag`" in runbook
        assert "## Summary" in runbook
        assert "## Migration Checklist" in runbook

    def test_runbook_includes_dag_id(self):
        settings = DAGSettings(dag_id="my_special_dag")
        runbook = generate_runbook(settings)

        assert "my_special_dag" in runbook


class TestGenerateRunbookSchedule:
    """Test schedule section in runbook."""

    def test_runbook_with_schedule(self):
        settings = DAGSettings(dag_id="test", schedule="@daily")
        runbook = generate_runbook(settings)

        assert "## Schedule Configuration" in runbook
        assert "@daily" in runbook
        assert "cron" in runbook.lower()
        assert "prefect.yaml" in runbook

    def test_runbook_with_cron_schedule(self):
        settings = DAGSettings(dag_id="test", schedule="0 2 * * *")
        runbook = generate_runbook(settings)

        assert "0 2 * * *" in runbook
        assert "flow.serve" in runbook

    def test_runbook_schedule_preset_description(self):
        settings = DAGSettings(dag_id="test", schedule="@hourly")
        runbook = generate_runbook(settings)

        assert "@hourly" in runbook
        assert "Every hour" in runbook


class TestGenerateRunbookCatchup:
    """Test catchup section in runbook."""

    def test_runbook_catchup_false(self):
        settings = DAGSettings(dag_id="test", catchup=False)
        runbook = generate_runbook(settings)

        assert "## Catchup" in runbook
        assert "catchup" in runbook.lower()
        assert "default behavior" in runbook.lower()

    def test_runbook_catchup_true(self):
        settings = DAGSettings(dag_id="test", catchup=True)
        runbook = generate_runbook(settings)

        assert "## Catchup" in runbook
        assert "backfill" in runbook.lower()


class TestGenerateRunbookRetries:
    """Test retry section in runbook."""

    def test_runbook_with_retries(self):
        settings = DAGSettings(
            dag_id="test",
            default_args={"retries": 3, "retry_delay": 300},
        )
        runbook = generate_runbook(settings)

        assert "## Retry Configuration" in runbook
        assert "retries" in runbook.lower()
        assert "3" in runbook
        assert "@task" in runbook

    def test_runbook_with_email_settings(self):
        settings = DAGSettings(
            dag_id="test",
            default_args={
                "email": "alerts@example.com",
                "email_on_failure": True,
            },
        )
        runbook = generate_runbook(settings)

        assert "email" in runbook.lower()
        assert "notification" in runbook.lower() or "Automation" in runbook


class TestGenerateRunbookConcurrency:
    """Test concurrency section in runbook."""

    def test_runbook_max_active_runs(self):
        settings = DAGSettings(dag_id="test", max_active_runs=5)
        runbook = generate_runbook(settings)

        assert "## Concurrency" in runbook
        assert "max_active_runs" in runbook.lower() or "5" in runbook
        assert "concurrency" in runbook.lower()

    def test_runbook_concurrency_setting(self):
        settings = DAGSettings(dag_id="test", concurrency=10)
        runbook = generate_runbook(settings)

        assert "## Concurrency" in runbook
        assert "10" in runbook


class TestGenerateRunbookAutoPause:
    """Test auto-pause section in runbook."""

    def test_runbook_max_consecutive_failed(self):
        settings = DAGSettings(dag_id="test", max_consecutive_failed_dag_runs=5)
        runbook = generate_runbook(settings)

        assert "## Auto-Pause" in runbook
        assert "5" in runbook
        assert "automation" in runbook.lower()


class TestGenerateRunbookTags:
    """Test tags section in runbook."""

    def test_runbook_with_tags(self):
        settings = DAGSettings(dag_id="test", tags=["production", "etl"])
        runbook = generate_runbook(settings)

        assert "## Tags" in runbook
        assert "production" in runbook
        assert "etl" in runbook
        assert "@flow(tags=" in runbook


class TestGenerateRunbookCallbacks:
    """Test callbacks section in runbook."""

    def test_runbook_on_failure_callback(self):
        settings = DAGSettings(
            dag_id="test",
            callbacks=[
                CallbackInfo(
                    callback_type="on_failure_callback",
                    function_name="notify_failure",
                )
            ],
        )
        runbook = generate_runbook(settings)

        assert "## Callbacks" in runbook
        assert "on_failure_callback" in runbook
        assert "notify_failure" in runbook
        assert "on_failure" in runbook  # Prefect hook

    def test_runbook_on_success_callback(self):
        settings = DAGSettings(
            dag_id="test",
            callbacks=[
                CallbackInfo(
                    callback_type="on_success_callback",
                    function_name="notify_success",
                )
            ],
        )
        runbook = generate_runbook(settings)

        assert "## Callbacks" in runbook
        assert "on_success_callback" in runbook
        assert "on_completion" in runbook  # Prefect uses on_completion

    def test_runbook_sla_miss_callback(self):
        settings = DAGSettings(
            dag_id="test",
            callbacks=[
                CallbackInfo(
                    callback_type="sla_miss_callback",
                    function_name="sla_alert",
                )
            ],
        )
        runbook = generate_runbook(settings)

        assert "sla_miss_callback" in runbook
        assert "SLA" in runbook


class TestGenerateRunbookTimeout:
    """Test timeout section in runbook."""

    def test_runbook_dagrun_timeout(self):
        settings = DAGSettings(
            dag_id="test",
            dagrun_timeout="<call: timedelta(...)>",
        )
        runbook = generate_runbook(settings)

        assert "## Timeout" in runbook
        assert "timeout_seconds" in runbook


class TestGenerateRunbookConnections:
    """Test connections section in runbook."""

    def test_runbook_with_connections(self):
        class MockConnection:
            def __init__(self, name, conn_type):
                self.name = name
                self.conn_type = conn_type

        connections = [
            MockConnection("postgres_db", "postgres"),
            MockConnection("s3_bucket", "s3"),
        ]

        settings = DAGSettings(dag_id="test")
        runbook = generate_runbook(settings, connections=connections)

        assert "## Connection Migration" in runbook
        assert "postgres_db" in runbook
        assert "s3_bucket" in runbook
        assert "SqlAlchemyConnector" in runbook
        assert "S3Bucket" in runbook


class TestGenerateRunbookVariables:
    """Test variables section in runbook."""

    def test_runbook_with_variables(self):
        class MockVariable:
            def __init__(self, name, is_set=False, is_sensitive=False):
                self.name = name
                self.is_set = is_set
                self.is_sensitive = is_sensitive

        variables = [
            MockVariable("api_key", is_sensitive=True),
            MockVariable("batch_size"),
        ]

        settings = DAGSettings(dag_id="test")
        runbook = generate_runbook(settings, variables=variables)

        assert "## Variable Migration" in runbook
        assert "api_key" in runbook
        assert "batch_size" in runbook
        assert "Secret" in runbook  # For sensitive variable


class TestGenerateRunbookChecklist:
    """Test migration checklist in runbook."""

    def test_checklist_basic(self):
        settings = DAGSettings(dag_id="test")
        runbook = generate_runbook(settings)

        assert "## Migration Checklist" in runbook
        assert "Pre-Migration" in runbook
        assert "Deployment" in runbook
        assert "Validation" in runbook
        assert "Cutover" in runbook

    def test_checklist_includes_connection_tasks(self):
        class MockConnection:
            def __init__(self, name, conn_type):
                self.name = name
                self.conn_type = conn_type

        connections = [MockConnection("my_db", "postgres")]
        settings = DAGSettings(dag_id="test")
        runbook = generate_runbook(settings, connections=connections)

        assert "my_db" in runbook
        assert "Block" in runbook

    def test_checklist_includes_schedule_verification(self):
        settings = DAGSettings(dag_id="test", schedule="0 2 * * *")
        runbook = generate_runbook(settings)

        assert "schedule" in runbook.lower()
        assert "cron" in runbook.lower()

    def test_checklist_includes_callback_tasks(self):
        settings = DAGSettings(
            dag_id="test",
            callbacks=[
                CallbackInfo(
                    callback_type="on_failure_callback",
                    function_name="notify",
                )
            ],
        )
        runbook = generate_runbook(settings)

        assert "hook" in runbook.lower() or "automation" in runbook.lower()


class TestGenerateRunbookIntegration:
    """Integration tests for full runbook generation."""

    def test_complex_dag_runbook(self):
        settings = DAGSettings(
            dag_id="complex_etl",
            schedule="0 2 * * *",
            catchup=False,
            max_active_runs=3,
            max_consecutive_failed_dag_runs=5,
            default_args={"retries": 3, "retry_delay": 300},
            tags=["production", "etl"],
            callbacks=[
                CallbackInfo(
                    callback_type="on_failure_callback",
                    function_name="alert_team",
                ),
                CallbackInfo(
                    callback_type="on_success_callback",
                    function_name="log_success",
                ),
            ],
        )

        class MockConnection:
            def __init__(self, name, conn_type):
                self.name = name
                self.conn_type = conn_type

        class MockVariable:
            def __init__(self, name, is_sensitive=False):
                self.name = name
                self.is_set = False
                self.is_sensitive = is_sensitive

        connections = [
            MockConnection("prod_postgres", "postgres"),
            MockConnection("data_lake_s3", "s3"),
        ]
        variables = [
            MockVariable("api_key", is_sensitive=True),
            MockVariable("batch_size"),
        ]

        runbook = generate_runbook(settings, connections=connections, variables=variables)

        # Verify all major sections are present
        assert "# Migration Runbook: `complex_etl`" in runbook
        assert "## Summary" in runbook
        assert "## Schedule Configuration" in runbook
        assert "## Catchup" in runbook
        assert "## Retry Configuration" in runbook
        assert "## Concurrency" in runbook
        assert "## Auto-Pause" in runbook
        assert "## Tags" in runbook
        assert "## Callbacks" in runbook
        assert "## Connection Migration" in runbook
        assert "## Variable Migration" in runbook
        assert "## Migration Checklist" in runbook

        # Verify specific values appear
        assert "complex_etl" in runbook
        assert "0 2 * * *" in runbook
        assert "production" in runbook
        assert "prod_postgres" in runbook
        assert "api_key" in runbook

    def test_extract_and_generate_integration(self):
        """Test full pipeline: extract settings then generate runbook."""
        code = '''
from airflow.decorators import dag, task

def notify(context):
    pass

@dag(
    schedule="@daily",
    catchup=False,
    max_active_runs=5,
    default_args={"retries": 2},
    tags=["analytics"],
    on_failure_callback=notify,
)
def analytics_pipeline():
    @task
    def extract():
        return "data"

    extract()
'''
        settings = extract_dag_settings(code)
        runbook = generate_runbook(settings)

        assert "analytics_pipeline" in runbook
        assert "@daily" in runbook
        assert "catchup" in runbook.lower()
        assert "retries" in runbook.lower()
        assert "analytics" in runbook
        assert "on_failure_callback" in runbook


class TestSchedulePresets:
    """Test SCHEDULE_PRESETS constant."""

    def test_all_presets_have_descriptions(self):
        expected_presets = [
            "@once",
            "@hourly",
            "@daily",
            "@weekly",
            "@monthly",
            "@yearly",
            "@annually",
        ]
        for preset in expected_presets:
            assert preset in SCHEDULE_PRESETS
            assert SCHEDULE_PRESETS[preset]  # Non-empty description
