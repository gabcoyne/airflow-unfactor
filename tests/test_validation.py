"""Tests for code validation utilities."""

from airflow_unfactor.validation import (
    ValidationResult,
    validate_generated_code,
    validate_python_syntax,
)


class TestValidatePythonSyntax:
    """Tests for validate_python_syntax function."""

    def test_valid_code(self):
        """Valid Python code should pass validation."""
        code = """
from prefect import flow, task

@task
def my_task():
    return 42

@flow
def my_flow():
    my_task()
"""
        result = validate_python_syntax(code)
        assert result.valid is True
        assert result.error is None

    def test_syntax_error(self):
        """Code with syntax error should fail validation."""
        code = """
def broken_function(
    # Missing closing paren
    return 42
"""
        result = validate_python_syntax(code)
        assert result.valid is False
        assert result.error is not None
        assert result.line is not None

    def test_indentation_error(self):
        """Code with indentation error should fail validation."""
        code = """
def my_func():
return 42
"""
        result = validate_python_syntax(code)
        assert result.valid is False

    def test_empty_code(self):
        """Empty code should be valid."""
        result = validate_python_syntax("")
        assert result.valid is True


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_to_warning_valid(self):
        """Valid result should return None warning."""
        result = ValidationResult(valid=True)
        assert result.to_warning() is None

    def test_to_warning_invalid(self):
        """Invalid result should return warning string."""
        result = ValidationResult(
            valid=False,
            error="unexpected EOF",
            line=5,
            column=10,
        )
        warning = result.to_warning()
        assert warning is not None
        assert "line 5" in warning
        assert "column 10" in warning
        assert "unexpected EOF" in warning


class TestValidateGeneratedCode:
    """Tests for validate_generated_code function."""

    def test_valid_flow_and_test_code(self):
        """Valid flow and test code should return no warnings."""
        flow_code = "@flow\ndef my_flow(): pass"
        test_code = "def test_something(): assert True"
        warnings = validate_generated_code(flow_code=flow_code, test_code=test_code)
        assert warnings == []

    def test_invalid_flow_code(self):
        """Invalid flow code should return warning."""
        flow_code = "def broken("  # Missing closing paren
        warnings = validate_generated_code(flow_code=flow_code)
        assert len(warnings) == 1
        assert "Flow code" in warnings[0]

    def test_invalid_test_code(self):
        """Invalid test code should return warning."""
        test_code = "def broken("  # Missing closing paren
        warnings = validate_generated_code(test_code=test_code)
        assert len(warnings) == 1
        assert "Test code" in warnings[0]

    def test_both_invalid(self):
        """Both invalid should return two warnings."""
        warnings = validate_generated_code(
            flow_code="def broken(",
            test_code="def also_broken(",
        )
        assert len(warnings) == 2

    def test_none_inputs(self):
        """None inputs should return no warnings."""
        warnings = validate_generated_code(flow_code=None, test_code=None)
        assert warnings == []
