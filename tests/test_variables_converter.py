"""Tests for Variable to config converter.

Tests the conversion of Airflow Variable.get() and Variable.set() patterns
to Prefect Secrets, Variables, and flow parameters.
"""

import pytest

from airflow_unfactor.converters.variables import (
    SENSITIVE_PATTERNS,
    VariableInfo,
    _is_sensitive_name,
    _to_python_identifier,
    convert_all_variables,
    extract_variables,
    generate_variable_scaffold,
)


class TestSensitivePatterns:
    """Test sensitive name pattern matching."""

    def test_sensitive_patterns_exist(self):
        """Ensure sensitive patterns are defined."""
        assert len(SENSITIVE_PATTERNS) > 0
        assert "password" in SENSITIVE_PATTERNS
        assert "secret" in SENSITIVE_PATTERNS
        assert "token" in SENSITIVE_PATTERNS

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("api_key", True),
            ("API_KEY", True),
            ("my_api_key_value", True),
            ("password", True),
            ("db_password", True),
            ("PASSWORD_123", True),
            ("secret", True),
            ("aws_secret_access_key", True),
            ("token", True),
            ("auth_token", True),
            ("credential", True),
            ("auth", True),
            ("oauth_config", True),
            ("private_key", True),
            ("passphrase", True),
            # Non-sensitive
            ("bucket_name", False),
            ("environment", False),
            ("retry_count", False),
            ("data_path", False),
            ("config_value", False),
        ],
    )
    def test_is_sensitive_name(self, name, expected):
        """Test sensitivity classification by name."""
        assert _is_sensitive_name(name) == expected


class TestPythonIdentifier:
    """Test Python identifier conversion."""

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("simple", "simple"),
            ("with_underscore", "with_underscore"),
            ("with-dash", "with_dash"),
            ("with.dot", "with_dot"),
            ("with spaces", "with_spaces"),
            ("123start", "_123start"),
            ("", "variable"),
            ("UPPER", "UPPER"),
        ],
    )
    def test_to_python_identifier(self, name, expected):
        """Test conversion to valid Python identifiers."""
        assert _to_python_identifier(name) == expected


class TestExtractVariables:
    """Test Variable extraction from DAG code."""

    def test_simple_variable_get(self):
        """Detect Variable.get with string literal."""
        code = '''
from airflow.models import Variable

value = Variable.get("my_config")
'''
        variables = extract_variables(code)

        assert len(variables) == 1
        assert variables[0].name == "my_config"
        assert variables[0].is_set is False
        assert variables[0].default_value is None

    def test_variable_get_with_default_var_keyword(self):
        """Detect Variable.get with default_var keyword argument."""
        code = '''
from airflow.models import Variable

value = Variable.get("my_config", default_var="fallback")
'''
        variables = extract_variables(code)

        assert len(variables) == 1
        assert variables[0].name == "my_config"
        assert variables[0].default_value == "'fallback'"

    def test_variable_get_with_positional_default(self):
        """Detect Variable.get with positional default argument."""
        code = '''
from airflow.models import Variable

value = Variable.get("my_config", "default_value")
'''
        variables = extract_variables(code)

        assert len(variables) == 1
        assert variables[0].default_value == "'default_value'"

    def test_variable_set(self):
        """Detect Variable.set calls."""
        code = '''
from airflow.models import Variable

Variable.set("last_run", "2024-01-01")
'''
        variables = extract_variables(code)

        assert len(variables) == 1
        assert variables[0].name == "last_run"
        assert variables[0].is_set is True

    def test_sensitive_variable_detected(self):
        """Sensitive variable names are classified correctly."""
        code = '''
from airflow.models import Variable

api_key = Variable.get("api_key")
password = Variable.get("db_password")
bucket = Variable.get("bucket_name")
'''
        variables = extract_variables(code)

        assert len(variables) == 3

        api_key_var = next(v for v in variables if v.name == "api_key")
        password_var = next(v for v in variables if v.name == "db_password")
        bucket_var = next(v for v in variables if v.name == "bucket_name")

        assert api_key_var.is_sensitive is True
        assert password_var.is_sensitive is True
        assert bucket_var.is_sensitive is False

    def test_multiple_variables(self):
        """Detect multiple Variable usages."""
        code = '''
from airflow.models import Variable

env = Variable.get("environment")
bucket = Variable.get("s3_bucket", default_var="default-bucket")
Variable.set("processed_date", "2024-01-01")
'''
        variables = extract_variables(code)

        assert len(variables) == 3

        names = [v.name for v in variables]
        assert "environment" in names
        assert "s3_bucket" in names
        assert "processed_date" in names

    def test_variable_with_models_prefix(self):
        """Detect Variable.get with models.Variable pattern."""
        code = '''
from airflow import models

value = models.Variable.get("config")
'''
        variables = extract_variables(code)

        assert len(variables) == 1
        assert variables[0].name == "config"

    def test_line_number_captured(self):
        """Line numbers are captured correctly."""
        code = '''
from airflow.models import Variable

# Line 4
value1 = Variable.get("var1")
# Line 6
value2 = Variable.get("var2")
'''
        variables = extract_variables(code)

        assert len(variables) == 2
        # Line numbers should be captured (exact values depend on parsing)
        assert all(v.line_number > 0 for v in variables)

    def test_invalid_syntax_returns_empty(self):
        """Invalid Python syntax returns empty list."""
        code = "this is not valid python {"
        variables = extract_variables(code)

        assert variables == []

    def test_no_variables_returns_empty(self):
        """Code without Variables returns empty list."""
        code = '''
from airflow.operators.python import PythonOperator

task = PythonOperator(task_id="task", python_callable=lambda: None)
'''
        variables = extract_variables(code)

        assert variables == []


class TestGenerateVariableScaffold:
    """Test scaffold generation for variables."""

    def test_sensitive_variable_recommends_secret(self):
        """Sensitive variables recommend Secret block."""
        info = VariableInfo(
            name="api_key",
            is_sensitive=True,
            line_number=10,
        )

        code, setup, warnings = generate_variable_scaffold(info)

        assert "Secret" in code
        assert "RECOMMENDED" in code or "Secret" in code
        assert "api_key" in code
        assert "Secret" in setup
        assert len(warnings) == 0  # No warnings for normal sensitive get

    def test_sensitive_variable_with_default(self):
        """Sensitive variables with defaults show the default in comments."""
        info = VariableInfo(
            name="db_password",
            default_value="'changeme'",
            is_sensitive=True,
            line_number=10,
        )

        code, setup, warnings = generate_variable_scaffold(info)

        assert "changeme" in code  # Default mentioned in comment

    def test_nonsensitive_variable_shows_options(self):
        """Non-sensitive variables show multiple options."""
        info = VariableInfo(
            name="bucket_name",
            is_sensitive=False,
            line_number=10,
        )

        code, setup, warnings = generate_variable_scaffold(info)

        # Should show all three options
        assert "OPTION 1" in code  # Flow parameter
        assert "OPTION 2" in code  # Prefect Variable
        assert "OPTION 3" in code  # Environment variable
        assert "flow" in code.lower()
        assert "Variable" in code
        assert "os.environ" in code

    def test_nonsensitive_with_default_includes_default(self):
        """Non-sensitive variables with defaults include them in generated code."""
        info = VariableInfo(
            name="retry_count",
            default_value="'3'",
            is_sensitive=False,
            line_number=10,
        )

        code, setup, warnings = generate_variable_scaffold(info)

        # Default should appear in parameter and Variable.get
        assert "'3'" in code

    def test_variable_set_warns_and_uses_api(self):
        """Variable.set() generates warning and uses Variables API."""
        info = VariableInfo(
            name="last_processed",
            is_set=True,
            is_sensitive=False,
            line_number=10,
        )

        code, setup, warnings = generate_variable_scaffold(info)

        assert len(warnings) == 1
        assert "Variable.set" in warnings[0]
        assert "await Variable.set" in code or "Variable.set" in code
        assert "overwrite=True" in code

    def test_generated_code_is_valid_python(self):
        """Generated code options are valid Python syntax."""
        info = VariableInfo(
            name="config_value",
            default_value="'default'",
            is_sensitive=False,
            line_number=10,
        )

        code, setup, warnings = generate_variable_scaffold(info)

        # Should compile without syntax errors
        # Note: May have undefined names but syntax should be valid
        compile(code, "<test>", "exec")


class TestConvertAllVariables:
    """Test batch variable conversion."""

    def test_full_dag_with_variables(self):
        """Convert a DAG with multiple variable patterns."""
        code = '''
from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator

with DAG("my_dag") as dag:
    env = Variable.get("environment", default_var="dev")
    api_key = Variable.get("api_key")
    bucket = Variable.get("s3_bucket")

    def process():
        Variable.set("last_run", "2024-01-01")

    task = PythonOperator(task_id="process", python_callable=process)
'''
        result = convert_all_variables(code)

        assert len(result["variables"]) == 4
        assert len(result["scaffolds"]) == 4  # Unique names
        assert result["has_sensitive"] is True  # api_key
        assert result["has_writes"] is True  # Variable.set

        # Check summary
        assert "4 unique" in result["summary"] or "4" in result["summary"]

    def test_no_variables_returns_empty_result(self):
        """DAG without variables returns appropriate empty result."""
        code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG("my_dag") as dag:
    task = PythonOperator(task_id="task", python_callable=lambda: None)
'''
        result = convert_all_variables(code)

        assert result["variables"] == []
        assert result["scaffolds"] == {}
        assert "No Airflow Variables" in result["summary"]
        assert result["has_sensitive"] is False
        assert result["has_writes"] is False

    def test_duplicate_variable_names_handled(self):
        """Same variable name used multiple times generates one scaffold."""
        code = '''
from airflow.models import Variable

# Used in multiple places
value1 = Variable.get("config")
value2 = Variable.get("config")
value3 = Variable.get("config", default_var="fallback")
'''
        result = convert_all_variables(code)

        # Three usages detected
        assert len(result["variables"]) == 3
        # But only one scaffold (unique name)
        assert len(result["scaffolds"]) == 1
        assert "config" in result["scaffolds"]

    def test_sensitive_detection_in_batch(self):
        """Batch conversion correctly identifies sensitive variables."""
        code = '''
from airflow.models import Variable

password = Variable.get("db_password")
host = Variable.get("db_host")
secret = Variable.get("aws_secret_key")
'''
        result = convert_all_variables(code)

        assert result["has_sensitive"] is True

        # Check individual scaffolds
        pw_code, _, _ = result["scaffolds"]["db_password"]
        host_code, _, _ = result["scaffolds"]["db_host"]

        assert "Secret" in pw_code
        assert "OPTION 1" in host_code  # Non-sensitive shows options

    def test_write_detection_in_batch(self):
        """Batch conversion correctly identifies write operations."""
        code = '''
from airflow.models import Variable

value = Variable.get("config")
Variable.set("last_run", "2024-01-01")
'''
        result = convert_all_variables(code)

        assert result["has_writes"] is True
        assert len(result["all_warnings"]) > 0  # Should warn about Variable.set

    def test_warnings_aggregated(self):
        """All warnings are collected in all_warnings."""
        code = '''
from airflow.models import Variable

Variable.set("state1", "value1")
Variable.set("state2", "value2")
'''
        result = convert_all_variables(code)

        # Should have warnings for both Variable.set calls
        assert len(result["all_warnings"]) == 2


class TestEdgeCases:
    """Test edge cases and unusual patterns."""

    def test_variable_in_function(self):
        """Detect Variable usage inside functions."""
        code = '''
from airflow.models import Variable

def get_config():
    return Variable.get("config")
'''
        variables = extract_variables(code)

        assert len(variables) == 1

    def test_variable_in_lambda(self):
        """Detect Variable usage in lambda expressions."""
        code = '''
from airflow.models import Variable

get_val = lambda: Variable.get("value")
'''
        variables = extract_variables(code)

        assert len(variables) == 1

    def test_variable_with_f_string_name(self):
        """Handle dynamic variable names (f-strings)."""
        code = '''
from airflow.models import Variable

env = "prod"
value = Variable.get(f"config_{env}")
'''
        variables = extract_variables(code)

        assert len(variables) == 1
        # Dynamic name should be captured as expression
        assert "config_" in variables[0].name or "f'" in variables[0].name

    def test_variable_get_deserialize(self):
        """Handle Variable.get with deserialize_json parameter."""
        code = '''
from airflow.models import Variable

config = Variable.get("json_config", deserialize_json=True)
'''
        variables = extract_variables(code)

        assert len(variables) == 1
        assert variables[0].name == "json_config"

    def test_non_variable_get_ignored(self):
        """Other .get() calls are ignored."""
        code = '''
my_dict = {"key": "value"}
value = my_dict.get("key")
'''
        variables = extract_variables(code)

        assert len(variables) == 0

    def test_non_variable_set_ignored(self):
        """Other .set() calls are ignored."""
        code = '''
my_set = set()
my_set.add("value")

class Config:
    @classmethod
    def set(cls, key, value):
        pass

Config.set("key", "value")
'''
        variables = extract_variables(code)

        assert len(variables) == 0
