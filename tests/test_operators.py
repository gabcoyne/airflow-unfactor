"""Tests for operator-specific converters."""

import pytest
from airflow_unfactor.converters.operators import (
    extract_functions,
    convert_python_operator,
    convert_bash_operator,
    convert_branch_operator,
)


class TestExtractFunctions:
    """Tests for function extraction."""

    def test_extract_simple_function(self):
        """Extract a simple function."""
        code = '''
def my_task():
    """Do something."""
    return 42
'''
        funcs = extract_functions(code)
        assert "my_task" in funcs
        func = funcs["my_task"]
        assert func.name == "my_task"
        assert func.args == []
        assert func.docstring == "Do something."
        assert not func.has_ti_param

    def test_extract_function_with_ti_param(self):
        """Extract a function that uses TaskInstance."""
        code = '''
def transform(ti):
    data = ti.xcom_pull(task_ids="extract")
    return data * 2
'''
        funcs = extract_functions(code)
        assert "transform" in funcs
        func = funcs["transform"]
        assert func.has_ti_param
        assert func.xcom_pulls == ["extract"]

    def test_extract_function_with_kwargs(self):
        """Extract a function with **kwargs."""
        code = '''
def task_with_context(**kwargs):
    ds = kwargs.get("ds")
    return ds
'''
        funcs = extract_functions(code)
        func = funcs["task_with_context"]
        assert func.has_context


class TestConvertPythonOperator:
    """Tests for PythonOperator conversion."""

    def test_convert_simple_function(self):
        """Convert a simple function."""
        code = '''
def extract():
    return {"users": [1, 2, 3]}
'''
        funcs = extract_functions(code)
        result = convert_python_operator(
            task_id="extract",
            python_callable="extract",
            functions=funcs,
            include_comments=False,
        )
        assert "@task" in result
        assert "def extract():" in result

    def test_convert_xcom_function(self):
        """Convert a function that uses XCom."""
        code = '''
def transform(ti):
    data = ti.xcom_pull(task_ids="extract")
    return {"result": data}
'''
        funcs = extract_functions(code)
        result = convert_python_operator(
            task_id="transform",
            python_callable="transform",
            functions=funcs,
        )
        assert "@task" in result
        # Should have educational comment about data passing
        assert "Prefect Advantage" in result
        # Parameter should be renamed from ti to extracted data
        assert "extract_data" in result


class TestConvertBashOperator:
    """Tests for BashOperator conversion."""

    def test_convert_simple_bash(self):
        """Convert a simple bash command."""
        result = convert_bash_operator(
            task_id="run_script",
            bash_command="echo hello",
            include_comments=False,
        )
        assert "@task" in result
        assert "def run_script():" in result
        assert "subprocess.run" in result
        assert "echo hello" in result

    def test_convert_bash_with_comments(self):
        """Conversion includes educational comments."""
        result = convert_bash_operator(
            task_id="run_script",
            bash_command="echo hello",
            include_comments=True,
        )
        assert "Prefect Advantage" in result
        assert "subprocess" in result


class TestConvertBranchOperator:
    """Tests for BranchPythonOperator conversion."""

    def test_convert_branch(self):
        """Convert a branch operator."""
        decision_code, guidance = convert_branch_operator(
            task_id="choose_branch",
            python_callable="decide",
            downstream_tasks=["task_a", "task_b"],
            include_comments=False,
        )
        assert "@task" in decision_code
        assert "choose_branch_decide" in decision_code
        assert "task_a" in guidance
        assert "task_b" in guidance
        assert "if/else" in guidance or "if branch" in guidance

    def test_branch_with_comments(self):
        """Branch conversion includes educational comments."""
        decision_code, guidance = convert_branch_operator(
            task_id="choose_branch",
            python_callable="decide",
            downstream_tasks=["task_a", "task_b"],
            include_comments=True,
        )
        assert "Prefect Advantage" in decision_code
        assert "BranchPythonOperator" in decision_code