"""Validation utilities for generated code."""

import ast
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of code validation."""

    valid: bool
    error: str | None = None
    line: int | None = None
    column: int | None = None

    def to_warning(self) -> str | None:
        """Convert to warning message if invalid."""
        if self.valid:
            return None
        location = ""
        if self.line is not None:
            location = f" at line {self.line}"
            if self.column is not None:
                location += f", column {self.column}"
        return f"Generated code has syntax error{location}: {self.error}"


def validate_python_syntax(code: str) -> ValidationResult:
    """Validate that code is syntactically valid Python.

    Args:
        code: Python source code to validate

    Returns:
        ValidationResult with valid=True if code parses,
        or valid=False with error details
    """
    try:
        ast.parse(code)
        return ValidationResult(valid=True)
    except SyntaxError as e:
        return ValidationResult(
            valid=False,
            error=e.msg,
            line=e.lineno,
            column=e.offset,
        )


def validate_generated_code(
    flow_code: str | None = None,
    test_code: str | None = None,
) -> list[str]:
    """Validate all generated code and return warnings.

    Args:
        flow_code: Generated flow code
        test_code: Generated test code

    Returns:
        List of warning messages for any validation failures
    """
    warnings = []

    if flow_code:
        result = validate_python_syntax(flow_code)
        if not result.valid:
            warnings.append(f"Flow code syntax error: {result.to_warning()}")

    if test_code:
        result = validate_python_syntax(test_code)
        if not result.valid:
            warnings.append(f"Test code syntax error: {result.to_warning()}")

    return warnings
