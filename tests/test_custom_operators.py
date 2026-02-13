"""Tests for custom operator detection and conversion.

Custom operators are those NOT in provider_mappings.OPERATOR_MAPPINGS.
"""

import pytest
from airflow_unfactor.converters.custom_operators import (
    extract_custom_operators,
    generate_custom_operator_stub,
    convert_custom_operators,
    is_known_operator,
    CustomOperatorInfo,
    CORE_OPERATORS,
)


class TestExtractCustomOperators:
    """Test detection of custom operators."""

    def test_detect_imported_custom_operator(self):
        """Detect custom operator from import."""
        code = '''
from myproject.operators import MyCustomOperator

with DAG("test") as dag:
    task1 = MyCustomOperator(
        task_id="custom_task",
        param1="value1",
        param2=42,
    )
'''
        operators = extract_custom_operators(code)

        assert len(operators) == 1
        assert operators[0].class_name == "MyCustomOperator"
        assert operators[0].task_id == "custom_task"
        assert operators[0].parameters["param1"] == "value1"
        assert operators[0].parameters["param2"] == 42
        assert operators[0].import_path == "myproject.operators.MyCustomOperator"
        assert not operators[0].is_inline_class

    def test_detect_inline_custom_operator(self):
        """Detect inline custom operator class definition."""
        code = '''
from airflow.models import BaseOperator

class MyInlineOperator(BaseOperator):
    def __init__(self, my_param, **kwargs):
        super().__init__(**kwargs)
        self.my_param = my_param

    def execute(self, context):
        print(f"Running with {self.my_param}")
        return self.my_param * 2

with DAG("test") as dag:
    task1 = MyInlineOperator(
        task_id="inline_task",
        my_param=10,
    )
'''
        operators = extract_custom_operators(code)

        assert len(operators) == 1
        assert operators[0].class_name == "MyInlineOperator"
        assert operators[0].task_id == "inline_task"
        assert operators[0].is_inline_class
        assert "print(f\"Running with {self.my_param}\")" in operators[0].execute_body
        assert "return self.my_param * 2" in operators[0].execute_body

    def test_skip_known_provider_operators(self):
        """Known provider operators should not be detected as custom."""
        code = '''
from airflow.providers.amazon.aws.operators.s3 import S3CreateObjectOperator

with DAG("test") as dag:
    task1 = S3CreateObjectOperator(
        task_id="s3_task",
        bucket_name="my-bucket",
    )
'''
        operators = extract_custom_operators(code)
        assert len(operators) == 0

    def test_skip_core_operators(self):
        """Core Airflow operators should not be detected as custom."""
        code = '''
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

with DAG("test") as dag:
    t1 = PythonOperator(task_id="python_task", python_callable=my_func)
    t2 = BashOperator(task_id="bash_task", bash_command="echo hello")
    t3 = EmptyOperator(task_id="empty_task")
'''
        operators = extract_custom_operators(code)
        assert len(operators) == 0

    def test_detect_multiple_custom_operators(self):
        """Detect multiple different custom operators."""
        code = '''
from team.operators import TeamOperator
from partner.operators import PartnerOperator

with DAG("test") as dag:
    t1 = TeamOperator(task_id="team_task", team_id=123)
    t2 = PartnerOperator(task_id="partner_task", partner_name="acme")
'''
        operators = extract_custom_operators(code)

        assert len(operators) == 2
        class_names = {op.class_name for op in operators}
        assert class_names == {"TeamOperator", "PartnerOperator"}

    def test_extract_execute_with_complex_body(self):
        """Extract execute() method with complex logic."""
        code = '''
from airflow.models import BaseOperator
import requests

class APICallOperator(BaseOperator):
    template_fields = ["endpoint"]

    def __init__(self, endpoint, method="GET", **kwargs):
        super().__init__(**kwargs)
        self.endpoint = endpoint
        self.method = method

    def execute(self, context):
        response = requests.request(
            self.method,
            self.endpoint,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        self.log.info(f"Got {len(data)} items")
        return data

with DAG("test") as dag:
    api_task = APICallOperator(
        task_id="call_api",
        endpoint="https://api.example.com/data",
        method="POST",
    )
'''
        operators = extract_custom_operators(code)

        assert len(operators) == 1
        assert operators[0].class_name == "APICallOperator"
        assert "requests.request(" in operators[0].execute_body
        assert "response.raise_for_status()" in operators[0].execute_body
        assert "return data" in operators[0].execute_body

    def test_handle_syntax_error(self):
        """Gracefully handle syntax errors."""
        code = "this is not valid python {{{{"
        operators = extract_custom_operators(code)
        assert operators == []

    def test_detect_operator_without_import_path(self):
        """Detect operator when import is complex/not traceable."""
        code = '''
# Operator imported dynamically or through __init__
CustomOperator = get_operator_class()

with DAG("test") as dag:
    task = CustomOperator(task_id="dynamic_task", value=1)
'''
        operators = extract_custom_operators(code)

        assert len(operators) == 1
        assert operators[0].class_name == "CustomOperator"
        assert operators[0].import_path == ""  # Unknown import


class TestGenerateCustomOperatorStub:
    """Test stub generation for custom operators."""

    def test_generate_stub_for_imported_operator(self):
        """Generate stub with import path context."""
        info = CustomOperatorInfo(
            class_name="MyCustomOperator",
            task_id="my_task",
            parameters={"param1": "value1", "param2": 42},
            import_path="myproject.operators.MyCustomOperator",
            line_number=10,
        )

        stub = generate_custom_operator_stub(info)

        assert "# TODO: Manual conversion required for MyCustomOperator" in stub
        assert "# Original import: myproject.operators.MyCustomOperator" in stub
        assert "@task" in stub
        assert "def my_task():" in stub
        assert "param1: 'value1'" in stub
        assert "param2: 42" in stub
        assert 'raise NotImplementedError("Convert MyCustomOperator logic")' in stub

    def test_generate_stub_with_execute_body(self):
        """Generate stub including original execute() body."""
        info = CustomOperatorInfo(
            class_name="InlineOperator",
            task_id="inline_task",
            parameters={"x": 10},
            execute_body="result = self.x * 2\nreturn result",
            is_inline_class=True,
            base_classes=["BaseOperator"],
        )

        stub = generate_custom_operator_stub(info)

        assert "# Base class(es): BaseOperator" in stub
        assert "# Original execute() method body:" in stub
        assert "# result = self.x * 2" in stub
        assert "# return result" in stub
        assert "# TODO: Adapt the above logic" in stub

    def test_generate_stub_without_comments(self):
        """Generate minimal stub without comments."""
        info = CustomOperatorInfo(
            class_name="SimpleOperator",
            task_id="simple_task",
            parameters={},
        )

        stub = generate_custom_operator_stub(info, include_comments=False)

        assert "# TODO:" not in stub
        assert "@task" in stub
        assert "def simple_task():" in stub
        # Docstring should still exist
        assert '"""Converted from custom operator: SimpleOperator' in stub


class TestConvertCustomOperators:
    """Test full conversion of custom operators."""

    def test_convert_returns_empty_for_no_custom_ops(self):
        """Return empty result when no custom operators found."""
        code = '''
from airflow.operators.python import PythonOperator

with DAG("test") as dag:
    task = PythonOperator(task_id="task", python_callable=fn)
'''
        result = convert_custom_operators(code)

        assert result["operators"] == []
        assert result["stubs"] == ""
        assert result["warnings"] == []

    def test_convert_generates_stubs_and_warnings(self):
        """Convert generates stubs and appropriate warnings."""
        code = '''
from team.operators import TeamOperator

with DAG("test") as dag:
    task = TeamOperator(task_id="team_task", team_id=123)
'''
        result = convert_custom_operators(code)

        assert len(result["operators"]) == 1
        assert "from prefect import task" in result["stubs"]
        assert "@task" in result["stubs"]
        assert "def team_task():" in result["stubs"]
        assert len(result["warnings"]) == 1
        assert "TeamOperator" in result["warnings"][0]
        assert "team.operators.TeamOperator" in result["warnings"][0]

    def test_convert_warns_about_inline_without_execute(self):
        """Warn when inline operator has no execute() method."""
        code = '''
from airflow.models import BaseOperator

class CustomEmptyOperator(BaseOperator):
    pass  # No execute method

with DAG("test") as dag:
    task = CustomEmptyOperator(task_id="empty_custom")
'''
        result = convert_custom_operators(code)

        assert len(result["warnings"]) == 1
        assert "No execute() method found" in result["warnings"][0]

    def test_convert_warns_about_self_references(self):
        """Warn about self.* references in execute() body."""
        code = '''
from airflow.models import BaseOperator

class SelfRefOperator(BaseOperator):
    def execute(self, context):
        return self.some_value

with DAG("test") as dag:
    task = SelfRefOperator(task_id="self_ref_task")
'''
        result = convert_custom_operators(code)

        assert len(result["warnings"]) == 1
        assert "Review self.* references" in result["warnings"][0]


class TestIsKnownOperator:
    """Test operator classification."""

    def test_known_provider_operators(self):
        """Provider operators are known."""
        assert is_known_operator("S3CreateObjectOperator")
        assert is_known_operator("BigQueryInsertJobOperator")
        assert is_known_operator("SlackWebhookOperator")

    def test_core_operators_are_known(self):
        """Core Airflow operators are known."""
        assert is_known_operator("PythonOperator")
        assert is_known_operator("BashOperator")
        assert is_known_operator("EmptyOperator")
        assert is_known_operator("BaseOperator")

    def test_custom_operators_not_known(self):
        """Custom operators are not known."""
        assert not is_known_operator("MyCustomOperator")
        assert not is_known_operator("TeamSpecificOperator")
        assert not is_known_operator("LegacyETLOperator")


class TestCoreOperatorsList:
    """Test the CORE_OPERATORS constant."""

    def test_core_operators_contains_base(self):
        """BaseOperator should be in core list."""
        assert "BaseOperator" in CORE_OPERATORS

    def test_core_operators_contains_python(self):
        """PythonOperator variants should be in core list."""
        assert "PythonOperator" in CORE_OPERATORS
        assert "BranchPythonOperator" in CORE_OPERATORS

    def test_core_operators_contains_bash(self):
        """BashOperator should be in core list."""
        assert "BashOperator" in CORE_OPERATORS

    def test_core_operators_contains_empty(self):
        """Empty/Dummy operators should be in core list."""
        assert "EmptyOperator" in CORE_OPERATORS
        assert "DummyOperator" in CORE_OPERATORS
