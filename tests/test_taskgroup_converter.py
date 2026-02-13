"""Tests for TaskGroup to Prefect subflow converter."""

import pytest
from airflow_unfactor.converters.taskgroup import (
    extract_task_groups,
    convert_task_group,
    convert_all_task_groups,
    TaskGroupInfo,
)


class TestExtractTaskGroups:
    """Test extraction of TaskGroup patterns."""

    def test_extract_task_group_decorator(self):
        """Extract @task_group decorated function."""
        code = '''
from airflow.decorators import dag, task, task_group

@dag()
def my_dag():
    @task_group
    def process_data():
        @task
        def extract():
            return [1, 2, 3]

        @task
        def transform(data):
            return [x * 2 for x in data]

        transform(extract())

    process_data()
'''
        groups = extract_task_groups(code)

        assert len(groups) == 1
        assert groups[0].name == "process_data"
        assert groups[0].function_name == "process_data"
        assert groups[0].is_decorator is True

    def test_extract_task_group_with_group_id(self):
        """Extract @task_group with explicit group_id."""
        code = '''
from airflow.decorators import task_group

@task_group(group_id="custom_group_name")
def my_group():
    pass
'''
        groups = extract_task_groups(code)

        assert len(groups) == 1
        assert groups[0].name == "custom_group_name"
        assert groups[0].function_name == "my_group"

    def test_extract_task_group_context_manager(self):
        """Extract TaskGroup context manager pattern."""
        code = '''
from airflow import DAG
from airflow.utils.task_group import TaskGroup
from airflow.operators.python import PythonOperator

with DAG("my_dag") as dag:
    with TaskGroup("extraction_group") as extract:
        task1 = PythonOperator(task_id="task1", python_callable=lambda: 1)
        task2 = PythonOperator(task_id="task2", python_callable=lambda: 2)
'''
        groups = extract_task_groups(code)

        assert len(groups) == 1
        assert groups[0].name == "extraction_group"
        assert groups[0].function_name == "extract"
        assert groups[0].is_decorator is False

    def test_extract_task_group_context_manager_without_as(self):
        """Extract TaskGroup context manager without 'as' clause."""
        code = '''
from airflow.utils.task_group import TaskGroup
from airflow.operators.empty import EmptyOperator

with TaskGroup("my_group"):
    t1 = EmptyOperator(task_id="t1")
'''
        groups = extract_task_groups(code)

        assert len(groups) == 1
        assert groups[0].name == "my_group"

    def test_extract_task_group_with_expand(self):
        """Detect .expand() on TaskGroup function."""
        code = '''
from airflow.decorators import dag, task, task_group

@dag()
def my_dag():
    @task_group
    def process_file(filename):
        @task
        def process(f):
            return f.upper()
        return process(filename)

    # Dynamic mapping
    process_file.expand(filename=["a.txt", "b.txt", "c.txt"])
'''
        groups = extract_task_groups(code)

        assert len(groups) == 1
        assert groups[0].has_expand is True
        assert "filename" in groups[0].expand_params
        assert groups[0].expand_params["filename"] == "['a.txt', 'b.txt', 'c.txt']"

    def test_extract_multiple_task_groups(self):
        """Extract multiple TaskGroups from same DAG."""
        code = '''
from airflow.decorators import dag, task_group

@dag()
def pipeline():
    @task_group
    def extract_group():
        pass

    @task_group
    def transform_group():
        pass

    @task_group
    def load_group():
        pass

    extract_group() >> transform_group() >> load_group()
'''
        groups = extract_task_groups(code)

        assert len(groups) == 3
        names = {g.name for g in groups}
        assert names == {"extract_group", "transform_group", "load_group"}

    def test_extract_task_group_with_args(self):
        """Extract TaskGroup with function arguments."""
        code = '''
from airflow.decorators import task_group

@task_group
def process_item(item_id, config=None):
    pass
'''
        groups = extract_task_groups(code)

        assert len(groups) == 1
        assert groups[0].args == ["item_id", "config"]

    def test_extract_nested_tasks(self):
        """Extract tasks defined within @task_group."""
        code = '''
from airflow.decorators import dag, task, task_group

@task_group
def etl_group():
    @task
    def extract():
        return "data"

    @task
    def transform(data):
        return data.upper()

    @task
    def load(data):
        print(data)
'''
        groups = extract_task_groups(code)

        assert len(groups) == 1
        assert "extract" in groups[0].tasks
        assert "transform" in groups[0].tasks
        assert "load" in groups[0].tasks


class TestConvertTaskGroup:
    """Test conversion of TaskGroups to Prefect subflows."""

    def test_convert_simple_task_group(self):
        """Convert simple @task_group to @flow."""
        info = TaskGroupInfo(
            name="process_data",
            function_name="process_data",
            tasks=["extract", "transform"],
            is_decorator=True,
        )

        code, warnings = convert_task_group(info)

        assert "@flow" in code
        assert 'name="process_data"' in code
        assert "def process_data" in code
        assert "subflow" in code.lower()  # Educational comment

    def test_convert_task_group_with_args(self):
        """Convert TaskGroup with arguments."""
        info = TaskGroupInfo(
            name="process_item",
            function_name="process_item",
            args=["item_id", "config"],
            is_decorator=True,
        )

        code, warnings = convert_task_group(info)

        assert "def process_item(item_id, config):" in code
        assert "@flow" in code

    def test_convert_task_group_context_manager_warns(self):
        """Warn about context manager pattern conversion."""
        info = TaskGroupInfo(
            name="my_group",
            function_name="my_group",
            is_decorator=False,
        )

        code, warnings = convert_task_group(info)

        assert any("context manager" in w.lower() for w in warnings)
        assert "@flow" in code

    def test_convert_task_group_with_expand(self):
        """Convert TaskGroup.expand() to wrapper task pattern."""
        info = TaskGroupInfo(
            name="process_file",
            function_name="process_file",
            args=["filename"],
            has_expand=True,
            expand_params={"filename": "files"},
            is_decorator=True,
        )

        code, warnings = convert_task_group(info)

        # Should have both subflow and wrapper task
        assert "@flow" in code
        assert "@task" in code
        assert "process_file_expanded" in code
        assert ".map(" in code
        assert any("expand" in w.lower() for w in warnings)

    def test_convert_includes_educational_comments(self):
        """Include educational comments by default."""
        info = TaskGroupInfo(
            name="my_group",
            function_name="my_group",
            is_decorator=True,
        )

        code, _ = convert_task_group(info, include_comments=True)

        assert "subflow" in code.lower()
        assert "observability" in code.lower() or "organizational" in code.lower()

    def test_convert_without_comments(self):
        """Skip educational comments when disabled."""
        info = TaskGroupInfo(
            name="my_group",
            function_name="my_group",
            is_decorator=True,
        )

        code, _ = convert_task_group(info, include_comments=False)

        # Should still have decorator and function
        assert "@flow" in code
        assert "def my_group" in code
        # But minimal comments
        assert code.count("#") < 5

    def test_convert_with_custom_group_id(self):
        """Preserve custom group_id as flow name."""
        info = TaskGroupInfo(
            name="custom_pipeline_name",
            function_name="my_function",
            is_decorator=True,
        )

        code, _ = convert_task_group(info)

        assert 'name="custom_pipeline_name"' in code
        assert "def my_function" in code

    def test_convert_preserves_body(self):
        """Preserve function body in conversion."""
        info = TaskGroupInfo(
            name="process",
            function_name="process",
            is_decorator=True,
            body_source="result = extract()\ntransformed = transform(result)\nreturn transformed",
        )

        code, _ = convert_task_group(info)

        assert "extract()" in code
        assert "transform(result)" in code


class TestConvertAllTaskGroups:
    """Test batch TaskGroup conversion."""

    def test_convert_dag_with_task_groups(self):
        """Convert DAG with multiple TaskGroups."""
        code = '''
from airflow.decorators import dag, task, task_group

@dag()
def my_pipeline():
    @task_group
    def extract():
        @task
        def get_data():
            return [1, 2, 3]
        return get_data()

    @task_group
    def transform(data):
        @task
        def process(d):
            return d * 2
        return process(data)

    data = extract()
    transform(data)
'''
        result = convert_all_task_groups(code)

        assert len(result["conversions"]) == 2
        assert "2 TaskGroup" in result["summary"]
        assert "@flow" in result["prefect_code"]

    def test_no_task_groups_returns_empty(self):
        """Non-TaskGroup code returns empty result."""
        code = '''
from airflow.decorators import dag, task

@dag()
def simple_dag():
    @task
    def my_task():
        return 1
    my_task()
'''
        result = convert_all_task_groups(code)

        assert result["conversions"] == []
        assert "No TaskGroup" in result["summary"]
        assert result["prefect_code"] == ""

    def test_mixed_decorator_and_context_manager(self):
        """Handle mix of decorator and context manager patterns."""
        code = '''
from airflow.decorators import dag, task, task_group
from airflow.utils.task_group import TaskGroup
from airflow.operators.python import PythonOperator

@dag()
def mixed_dag():
    @task_group
    def decorator_group():
        pass

    with TaskGroup("context_group") as cg:
        t = PythonOperator(task_id="t", python_callable=lambda: 1)
'''
        result = convert_all_task_groups(code)

        assert len(result["conversions"]) == 2
        assert "1 @task_group" in result["summary"]
        assert "1 context manager" in result["summary"]

    def test_produces_valid_python(self):
        """Output should be valid Python."""
        code = '''
from airflow.decorators import dag, task, task_group

@dag()
def my_dag():
    @task_group(group_id="processor")
    def process():
        @task
        def step():
            return 42
        step()

    process()
'''
        result = convert_all_task_groups(code)

        # Should compile without errors
        compile(result["prefect_code"], "<converted>", "exec")


class TestTaskGroupWithExpand:
    """Test TaskGroup.expand() pattern conversion."""

    def test_expand_detection(self):
        """Detect .expand() call on TaskGroup."""
        code = '''
from airflow.decorators import dag, task, task_group

@dag()
def batch_processing():
    @task_group
    def process_batch(batch_id):
        @task
        def process(id):
            return f"processed_{id}"
        return process(batch_id)

    process_batch.expand(batch_id=[1, 2, 3, 4, 5])
'''
        groups = extract_task_groups(code)

        assert len(groups) == 1
        assert groups[0].has_expand is True
        assert groups[0].expand_params == {"batch_id": "[1, 2, 3, 4, 5]"}

    def test_expand_conversion_generates_wrapper(self):
        """Generate wrapper task for .expand() pattern."""
        code = '''
from airflow.decorators import dag, task, task_group

@dag()
def my_dag():
    @task_group
    def process_file(filepath):
        pass

    process_file.expand(filepath=files_list)
'''
        result = convert_all_task_groups(code)

        # Should have both the subflow and wrapper
        assert "@flow" in result["prefect_code"]
        assert "@task" in result["prefect_code"]
        assert "process_file_expanded" in result["prefect_code"]
        assert ".map(" in result["prefect_code"]

    def test_expand_with_multiple_params(self):
        """Handle .expand() with multiple parameters."""
        code = '''
from airflow.decorators import task_group

@task_group
def process(file, config):
    pass

process.expand(file=files, config=configs)
'''
        groups = extract_task_groups(code)

        assert len(groups) == 1
        assert groups[0].has_expand is True
        assert "file" in groups[0].expand_params
        assert "config" in groups[0].expand_params


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_syntax_error_returns_empty(self):
        """Handle syntax errors gracefully."""
        code = '''
def broken(
    @task_group
    def missing_parens:
'''
        groups = extract_task_groups(code)

        assert groups == []

    def test_empty_task_group(self):
        """Handle TaskGroup with only pass."""
        code = '''
from airflow.decorators import task_group

@task_group
def empty_group():
    pass
'''
        groups = extract_task_groups(code)
        code_out, _ = convert_task_group(groups[0])

        assert len(groups) == 1
        assert "pass" in code_out

    def test_task_group_with_tooltip(self):
        """Handle TaskGroup tooltip parameter."""
        code = '''
from airflow.decorators import task_group

@task_group(group_id="etl", tooltip="Extract-Transform-Load pipeline")
def etl_pipeline():
    pass
'''
        groups = extract_task_groups(code)

        assert len(groups) == 1
        assert groups[0].name == "etl"
        # tooltip is stored in decorator_params
        assert groups[0].decorator_params.get("tooltip") == "Extract-Transform-Load pipeline"
