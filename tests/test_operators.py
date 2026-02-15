"""Tests for operator-specific converters."""

from airflow_unfactor.converters.operators import (
    convert_bash_operator,
    convert_branch_operator,
    convert_python_operator,
    extract_functions,
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
        code = """
def transform(ti):
    data = ti.xcom_pull(task_ids="extract")
    return data * 2
"""
        funcs = extract_functions(code)
        assert "transform" in funcs
        func = funcs["transform"]
        assert func.has_ti_param
        assert func.xcom_pulls == ["extract"]

    def test_extract_function_with_kwargs(self):
        """Extract a function with **kwargs."""
        code = """
def task_with_context(**kwargs):
    ds = kwargs.get("ds")
    return ds
"""
        funcs = extract_functions(code)
        func = funcs["task_with_context"]
        assert func.has_context


class TestConvertPythonOperator:
    """Tests for PythonOperator conversion."""

    def test_convert_simple_function(self):
        """Convert a simple function."""
        code = """
def extract():
    return {"users": [1, 2, 3]}
"""
        funcs = extract_functions(code)
        result = convert_python_operator(
            task_id="extract",
            python_callable="extract",
            functions=funcs,
            include_comments=False,
        )
        assert "@task" in result.code
        assert "def extract():" in result.code
        assert result.warnings == []

    def test_convert_xcom_function(self):
        """Convert a function that uses XCom."""
        code = """
def transform(ti):
    data = ti.xcom_pull(task_ids="extract")
    return {"result": data}
"""
        funcs = extract_functions(code)
        result = convert_python_operator(
            task_id="transform",
            python_callable="transform",
            functions=funcs,
        )
        assert "@task" in result.code
        # Should have educational comment about data passing
        assert "Prefect Advantage" in result.code
        # Parameter should be renamed from ti to extracted data
        assert "extract_data" in result.code

    def test_convert_xcom_with_dynamic_task_ids(self):
        """Convert function with dynamic task_ids warns about manual conversion."""
        code = """
def process(ti, task_list):
    results = ti.xcom_pull(task_ids=task_list)
    return results
"""
        funcs = extract_functions(code)
        result = convert_python_operator(
            task_id="process",
            python_callable="process",
            functions=funcs,
            include_comments=True,
        )
        # Should have warnings about dynamic task_ids
        assert len(result.warnings) > 0
        assert any("dynamic" in w.lower() or "manual" in w.lower() for w in result.warnings)
        # Should have xcom_usage info
        assert result.xcom_usage is not None
        assert result.xcom_usage.has_complex_patterns

    def test_convert_xcom_with_custom_key(self):
        """Convert function with custom XCom key warns about manual conversion."""
        code = """
def load(ti):
    schema = ti.xcom_pull(task_ids="extract", key="schema")
    data = ti.xcom_pull(task_ids="extract", key="data")
    return {"schema": schema, "data": data}
"""
        funcs = extract_functions(code)
        result = convert_python_operator(
            task_id="load",
            python_callable="load",
            functions=funcs,
            include_comments=True,
        )
        # Should warn about custom keys
        assert result.xcom_usage is not None
        assert result.xcom_usage.has_complex_patterns

    def test_convert_xcom_push_to_return(self):
        """Convert xcom_push to return statement."""
        code = """
def produce(ti):
    result = {"processed": True}
    ti.xcom_push(key="result", value=result)
"""
        funcs = extract_functions(code)
        result = convert_python_operator(
            task_id="produce",
            python_callable="produce",
            functions=funcs,
            include_comments=False,
        )
        # xcom_push should be converted to return
        assert "return result" in result.code or "return {" in result.code


class TestConvertBashOperator:
    """Tests for BashOperator conversion."""

    def test_convert_simple_bash(self):
        """Convert a simple bash command."""
        result = convert_bash_operator(
            task_id="run_script",
            bash_command="echo hello",
            include_comments=False,
        )
        assert "@task" in result.code
        assert "def run_script():" in result.code
        assert "subprocess.run" in result.code
        assert "echo hello" in result.code
        assert result.warnings == []

    def test_convert_bash_with_comments(self):
        """Conversion includes educational comments."""
        result = convert_bash_operator(
            task_id="run_script",
            bash_command="echo hello",
            include_comments=True,
        )
        assert "Prefect Advantage" in result.code
        assert "subprocess" in result.code

    def test_convert_bash_detects_jinja2(self):
        """Conversion detects and warns about Jinja2 templates."""
        result = convert_bash_operator(
            task_id="run_dated_script",
            bash_command="gsutil cp gs://bucket/{{ ds }}/data.csv .",
            include_comments=True,
        )
        # Should have warnings
        assert len(result.warnings) > 0
        assert "Jinja2" in result.warnings[0]
        # Code should have warning comments
        assert "WARNING" in result.code
        assert "{{ ds }}" in result.code
        # Detection info should be present
        assert result.jinja2_detection is not None
        assert result.jinja2_detection.has_templates
        assert "{{ ds }}" in result.jinja2_detection.templates_found

    def test_convert_bash_no_jinja2(self):
        """No warnings for commands without Jinja2."""
        result = convert_bash_operator(
            task_id="simple_echo",
            bash_command="echo 'no templates here'",
            include_comments=False,
        )
        assert result.warnings == []
        assert result.jinja2_detection is None or not result.jinja2_detection.has_templates


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
