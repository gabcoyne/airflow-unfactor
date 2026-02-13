"""Tests for P3 Conversion Core Enhancements.

These tests cover:
- Multi-task XCom pull detection and conversion (5.1, 5.2)
- Dynamic XCom pattern warnings (5.3)
- Retry delay conversion to retry_delay_seconds (5.4)
- Exponential backoff warnings (5.5)
- Pool/pool_slots detection and warnings (5.6)
"""

import pytest
from airflow_unfactor.converters.operators.python import (
    extract_functions,
    convert_python_operator,
    XComPullInfo,
    XComUsage,
)
from airflow_unfactor.converters.base import (
    convert_dag_to_flow,
    _build_task_decorator,
)
from airflow_unfactor.analysis.parser import parse_dag


class TestMultiTaskXComPull:
    """Tests for multi-task XCom pull detection (5.1) and conversion (5.2)."""

    def test_detect_multi_task_xcom_pull(self):
        """Detect xcom_pull with list of task_ids."""
        code = '''
def aggregate(ti):
    results = ti.xcom_pull(task_ids=["task_a", "task_b"])
    return sum(results.values())
'''
        funcs = extract_functions(code)
        func = funcs["aggregate"]

        assert func.xcom_usage is not None
        assert len(func.xcom_usage.pulls) == 1
        pull = func.xcom_usage.pulls[0]
        assert pull.is_multi_task
        assert pull.task_ids == ["task_a", "task_b"]
        assert pull.is_constant

    def test_multi_task_pull_generates_multiple_params(self):
        """Multi-task pull should generate multiple function parameters."""
        code = '''
def aggregate(ti):
    results = ti.xcom_pull(task_ids=["extract_users", "extract_orders"])
    return {"users": results[0], "orders": results[1]}
'''
        funcs = extract_functions(code)
        result = convert_python_operator(
            task_id="aggregate",
            python_callable="aggregate",
            functions=funcs,
            include_comments=False,
        )

        # Should have parameters for both tasks
        assert "extract_users_data" in result.code
        assert "extract_orders_data" in result.code

    def test_multi_task_pull_with_key_generates_warning(self):
        """Multi-task pull with key parameter generates warning."""
        code = '''
def aggregate(ti):
    data = ti.xcom_pull(task_ids=["task_a", "task_b"], key="data")
    return sum(d for d in data if d)
'''
        funcs = extract_functions(code)
        result = convert_python_operator(
            task_id="aggregate",
            python_callable="aggregate",
            functions=funcs,
            include_comments=False,
        )

        # Should have warning about custom key
        assert result.xcom_usage is not None
        assert result.xcom_usage.has_complex_patterns

    def test_multi_task_pull_body_conversion(self):
        """Multi-task pull should convert to dict in body."""
        code = '''
def merge(ti):
    all_data = ti.xcom_pull(task_ids=["alpha", "beta"])
    return merge_data(all_data)
'''
        funcs = extract_functions(code)
        result = convert_python_operator(
            task_id="merge",
            python_callable="merge",
            functions=funcs,
            include_comments=False,
        )

        # The multi-task pull should be converted to a dict
        # Check warnings mention the conversion
        assert any("dict" in w.lower() or "multi" in w.lower() for w in result.warnings)

    def test_single_item_list_treated_as_simple(self):
        """A list with single task_id should be treated simply."""
        code = '''
def process(ti):
    data = ti.xcom_pull(task_ids=["only_task"])
    return transform(data)
'''
        funcs = extract_functions(code)
        func = funcs["process"]

        # Single-item list is still a list technically
        assert len(func.xcom_usage.pulls) == 1
        pull = func.xcom_usage.pulls[0]
        # Single item list is NOT multi-task
        assert not pull.is_multi_task

    def test_xcom_usage_all_pull_task_ids(self):
        """XComUsage.all_pull_task_ids returns flattened list."""
        code = '''
def combine(ti):
    a = ti.xcom_pull(task_ids="single")
    b = ti.xcom_pull(task_ids=["multi1", "multi2"])
    return a + b
'''
        funcs = extract_functions(code)
        func = funcs["combine"]

        all_ids = func.xcom_usage.all_pull_task_ids
        assert "single" in all_ids
        assert "multi1" in all_ids
        assert "multi2" in all_ids
        assert len(all_ids) == 3


class TestDynamicXComPatterns:
    """Tests for dynamic XCom pattern detection and warnings (5.3)."""

    def test_variable_task_id_warning(self):
        """Variable task_ids should generate warning."""
        code = '''
def dynamic_pull(ti, task_name):
    data = ti.xcom_pull(task_ids=task_name)
    return data
'''
        funcs = extract_functions(code)
        result = convert_python_operator(
            task_id="dynamic_pull",
            python_callable="dynamic_pull",
            functions=funcs,
            include_comments=True,
        )

        # Should have dynamic pattern warning
        assert result.xcom_usage is not None
        assert any("dynamic" in w.lower() for w in result.xcom_usage.warnings)
        # Should not be constant
        pull = result.xcom_usage.pulls[0]
        assert not pull.is_constant

    def test_fstring_task_id_warning(self):
        """F-string task_ids should generate warning."""
        code = '''
def loop_pull(ti):
    for i in range(3):
        data = ti.xcom_pull(task_ids=f"task_{i}")
        process(data)
'''
        funcs = extract_functions(code)
        func = funcs["loop_pull"]

        # Should detect the dynamic pattern
        assert len(func.xcom_usage.pulls) == 1
        pull = func.xcom_usage.pulls[0]
        assert not pull.is_constant  # F-string is not constant

    def test_computed_task_id_warning(self):
        """Computed task_ids should generate warning."""
        code = '''
def computed_pull(ti):
    task_id = "prefix_" + get_suffix()
    data = ti.xcom_pull(task_ids=task_id)
    return data
'''
        funcs = extract_functions(code)
        result = convert_python_operator(
            task_id="computed_pull",
            python_callable="computed_pull",
            functions=funcs,
            include_comments=True,
        )

        # Should have warning
        assert any("dynamic" in w.lower() or "manual" in w.lower() for w in result.warnings)


class TestRetryDelayConversion:
    """Tests for retry_delay to retry_delay_seconds conversion (5.4)."""

    def test_task_level_retries_parsed(self):
        """Task-level retries should be parsed."""
        code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG("test_dag") as dag:
    task = PythonOperator(
        task_id="retry_task",
        python_callable=my_func,
        retries=5,
    )
'''
        result = parse_dag(code)
        ops = result.get("operators", [])
        assert len(ops) == 1
        assert ops[0].get("retries") == 5

    def test_task_level_retry_delay_parsed(self):
        """Task-level retry_delay should be parsed."""
        code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import timedelta

with DAG("test_dag") as dag:
    task = PythonOperator(
        task_id="retry_task",
        python_callable=my_func,
        retry_delay=timedelta(minutes=5),
    )
'''
        result = parse_dag(code)
        ops = result.get("operators", [])
        assert len(ops) == 1
        # retry_delay is captured as a call string
        assert ops[0].get("retry_delay") is not None

    def test_build_decorator_with_retries(self):
        """_build_task_decorator includes retries."""
        op = {"task_id": "test", "retries": 3}
        decorator, warnings = _build_task_decorator(op, {})

        assert "retries=3" in decorator
        assert warnings == []

    def test_build_decorator_converts_retry_delay_integer(self):
        """Integer retry_delay converts directly to retry_delay_seconds."""
        op = {"task_id": "test", "retry_delay": 300}
        decorator, warnings = _build_task_decorator(op, {})

        assert "retry_delay_seconds=300" in decorator

    def test_build_decorator_converts_timedelta_string(self):
        """Timedelta string is parsed and converted."""
        op = {"task_id": "test", "retry_delay": "<call: timedelta(minutes=5)>"}
        decorator, warnings = _build_task_decorator(op, {})

        # Should convert minutes=5 to 300 seconds
        assert "retry_delay_seconds=300" in decorator

    def test_build_decorator_with_hours_timedelta(self):
        """Timedelta with hours is converted correctly."""
        op = {"task_id": "test", "retry_delay": "<call: timedelta(hours=1, minutes=30)>"}
        decorator, warnings = _build_task_decorator(op, {})

        # 1 hour + 30 minutes = 5400 seconds
        assert "retry_delay_seconds=5400" in decorator

    def test_task_overrides_default_args(self):
        """Task-level retry overrides default_args."""
        op = {"task_id": "test", "retries": 10}
        default_args = {"retries": 3}
        decorator, warnings = _build_task_decorator(op, default_args)

        assert "retries=10" in decorator
        assert "retries=3" not in decorator

    def test_default_args_used_when_task_unset(self):
        """default_args retries used when task doesn't specify."""
        op = {"task_id": "test"}
        default_args = {"retries": 5}
        decorator, warnings = _build_task_decorator(op, default_args)

        assert "retries=5" in decorator

    def test_task_disables_retries(self):
        """Task with retries=0 generates explicit @task(retries=0)."""
        op = {"task_id": "test", "retries": 0}
        decorator, warnings = _build_task_decorator(op, {})

        assert "retries=0" in decorator


class TestExponentialBackoffWarning:
    """Tests for exponential_backoff warning (5.5)."""

    def test_exponential_backoff_parsed(self):
        """retry_exponential_backoff is parsed from operators."""
        code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG("test_dag") as dag:
    task = PythonOperator(
        task_id="backoff_task",
        python_callable=my_func,
        retries=3,
        retry_exponential_backoff=True,
    )
'''
        result = parse_dag(code)
        ops = result.get("operators", [])
        assert len(ops) == 1
        assert ops[0].get("retry_exponential_backoff") is True

    def test_exponential_backoff_generates_warning(self):
        """Exponential backoff generates appropriate warning."""
        op = {"task_id": "backoff_task", "retry_exponential_backoff": True}
        decorator, warnings = _build_task_decorator(op, {})

        assert len(warnings) == 1
        assert "exponential" in warnings[0].lower()
        assert "backoff" in warnings[0].lower()

    def test_exponential_backoff_note_in_parser(self):
        """Parser adds note about exponential backoff."""
        code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG("test_dag") as dag:
    task = PythonOperator(
        task_id="backoff_task",
        python_callable=my_func,
        retry_exponential_backoff=True,
    )
'''
        result = parse_dag(code)
        notes = result.get("notes", [])
        assert any("exponential" in n.lower() for n in notes)

    def test_max_retry_delay_generates_warning(self):
        """max_retry_delay generates appropriate warning."""
        op = {"task_id": "test", "max_retry_delay": "<call: timedelta(hours=1)>"}
        decorator, warnings = _build_task_decorator(op, {})

        assert len(warnings) == 1
        assert "max_retry_delay" in warnings[0]


class TestPoolDetection:
    """Tests for pool/pool_slots detection and warnings (5.6)."""

    def test_pool_parsed(self):
        """Pool parameter is parsed from operators."""
        code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG("test_dag") as dag:
    task = PythonOperator(
        task_id="limited_task",
        python_callable=my_func,
        pool="limited_resources",
    )
'''
        result = parse_dag(code)
        ops = result.get("operators", [])
        assert len(ops) == 1
        assert ops[0].get("pool") == "limited_resources"

    def test_pool_slots_parsed(self):
        """pool_slots parameter is parsed from operators."""
        code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG("test_dag") as dag:
    task = PythonOperator(
        task_id="heavy_task",
        python_callable=my_func,
        pool="limited_resources",
        pool_slots=2,
    )
'''
        result = parse_dag(code)
        ops = result.get("operators", [])
        assert len(ops) == 1
        assert ops[0].get("pool_slots") == 2

    def test_pool_generates_warning(self):
        """Pool parameter generates work pool warning."""
        op = {"task_id": "test", "pool": "limited_resources"}
        decorator, warnings = _build_task_decorator(op, {})

        assert len(warnings) == 1
        assert "pool" in warnings[0].lower()
        assert "work pool" in warnings[0].lower() or "concurrency" in warnings[0].lower()

    def test_pool_slots_generates_warning(self):
        """pool_slots parameter generates concurrency warning."""
        op = {"task_id": "test", "pool_slots": 3}
        decorator, warnings = _build_task_decorator(op, {})

        assert len(warnings) == 1
        assert "pool_slots" in warnings[0]
        assert "concurrency" in warnings[0].lower()

    def test_pool_note_in_parser(self):
        """Parser adds note about pool usage."""
        code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG("test_dag") as dag:
    task = PythonOperator(
        task_id="pooled_task",
        python_callable=my_func,
        pool="my_pool",
    )
'''
        result = parse_dag(code)
        notes = result.get("notes", [])
        assert any("pool" in n.lower() for n in notes)


class TestFullConversion:
    """Integration tests for full DAG conversion with P3 features."""

    def test_conversion_preserves_task_retries(self):
        """Full conversion preserves task-level retry settings."""
        code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG("retry_dag") as dag:
    task = PythonOperator(
        task_id="my_task",
        python_callable=process,
        retries=5,
    )
'''
        dag_info = parse_dag(code)
        result = convert_dag_to_flow(dag_info, code, include_comments=False)

        # Decorator should include retries
        assert "retries=5" in result["flow_code"]

    def test_conversion_with_pool_warnings(self):
        """Full conversion generates pool warnings."""
        code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG("pool_dag") as dag:
    task = PythonOperator(
        task_id="pooled",
        python_callable=process,
        pool="limited",
    )
'''
        dag_info = parse_dag(code)
        result = convert_dag_to_flow(dag_info, code, include_comments=False)

        # Should have pool warning
        assert any("pool" in w.lower() for w in result["warnings"])

    def test_conversion_with_exponential_backoff_warning(self):
        """Full conversion generates exponential backoff warning."""
        code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG("backoff_dag") as dag:
    task = PythonOperator(
        task_id="retrying",
        python_callable=process,
        retry_exponential_backoff=True,
    )
'''
        dag_info = parse_dag(code)
        result = convert_dag_to_flow(dag_info, code, include_comments=False)

        # Should have backoff warning
        assert any("backoff" in w.lower() for w in result["warnings"])

    def test_conversion_uses_default_args_retry(self):
        """Conversion falls back to default_args for retry settings."""
        code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG(
    "defaults_dag",
    default_args={"retries": 3, "retry_delay": 60}
) as dag:
    task = PythonOperator(
        task_id="my_task",
        python_callable=process,
    )
'''
        dag_info = parse_dag(code)
        result = convert_dag_to_flow(dag_info, code, include_comments=False)

        # Should use default_args retries
        assert "retries=3" in result["flow_code"]
