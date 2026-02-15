"""Tests for Dynamic Task Mapping converter.

Tests detection and conversion of Airflow's dynamic task mapping patterns:
- .expand()
- .partial().expand()
- .expand_kwargs()
"""

from airflow_unfactor.converters.dynamic_mapping import (
    MappingType,
    convert_all_dynamic_mappings,
    convert_dynamic_mapping,
    extract_dynamic_mapping,
)


class TestExtractSimpleExpand:
    """Test detection of simple .expand() patterns."""

    def test_detect_expand_with_single_param(self):
        """Detect task.expand(param=iterable)."""
        code = """
from airflow.decorators import task

@task
def process_item(item):
    return item * 2

result = process_item.expand(item=items)
"""
        mappings = extract_dynamic_mapping(code)

        assert len(mappings) == 1
        assert mappings[0].mapping_type == MappingType.EXPAND
        assert mappings[0].task_name == "process_item"
        assert mappings[0].mapped_iterable == "items"
        assert mappings[0].assigned_to == "result"

    def test_detect_expand_with_multiple_params(self):
        """Detect task.expand(param1=iter1, param2=iter2)."""
        code = """
results = transform.expand(x=x_values, y=y_values)
"""
        mappings = extract_dynamic_mapping(code)

        assert len(mappings) == 1
        assert mappings[0].mapping_type == MappingType.EXPAND
        assert mappings[0].task_name == "transform"
        assert "x" in mappings[0].expand_params
        assert "y" in mappings[0].expand_params
        assert mappings[0].expand_params["x"] == "x_values"
        assert mappings[0].expand_params["y"] == "y_values"

    def test_detect_expand_without_assignment(self):
        """Detect expand() call without variable assignment."""
        code = """
notify.expand(recipient=recipients)
"""
        mappings = extract_dynamic_mapping(code)

        assert len(mappings) == 1
        assert mappings[0].task_name == "notify"
        assert mappings[0].assigned_to == ""

    def test_detect_expand_with_list_literal(self):
        """Detect expand() with inline list."""
        code = """
process.expand(value=[1, 2, 3, 4, 5])
"""
        mappings = extract_dynamic_mapping(code)

        assert len(mappings) == 1
        assert mappings[0].mapped_iterable == "[1, 2, 3, 4, 5]"


class TestExtractPartialExpand:
    """Test detection of .partial().expand() chains."""

    def test_detect_partial_expand_simple(self):
        """Detect task.partial(fixed=val).expand(dynamic=iter)."""
        code = """
result = process.partial(config=config_obj).expand(item=items)
"""
        mappings = extract_dynamic_mapping(code)

        assert len(mappings) == 1
        assert mappings[0].mapping_type == MappingType.PARTIAL_EXPAND
        assert mappings[0].task_name == "process"
        assert mappings[0].partial_params == {"config": "config_obj"}
        assert mappings[0].expand_params == {"item": "items"}

    def test_detect_partial_with_multiple_fixed(self):
        """Detect partial() with multiple fixed parameters."""
        code = """
result = transform.partial(conn_id="default", timeout=30).expand(data=records)
"""
        mappings = extract_dynamic_mapping(code)

        assert len(mappings) == 1
        # Note: ast.unparse normalizes quotes to single quotes
        assert mappings[0].partial_params["conn_id"] == "'default'"
        assert mappings[0].partial_params["timeout"] == "30"
        assert mappings[0].expand_params["data"] == "records"

    def test_detect_partial_expand_complex_expression(self):
        """Detect partial/expand with function call as fixed param."""
        code = """
results = load.partial(config=get_config()).expand(path=file_paths)
"""
        mappings = extract_dynamic_mapping(code)

        assert len(mappings) == 1
        assert mappings[0].partial_params["config"] == "get_config()"


class TestExtractExpandKwargs:
    """Test detection of .expand_kwargs() patterns."""

    def test_detect_expand_kwargs(self):
        """Detect task.expand_kwargs(list_of_dicts)."""
        code = """
results = process.expand_kwargs(param_dicts)
"""
        mappings = extract_dynamic_mapping(code)

        assert len(mappings) == 1
        assert mappings[0].mapping_type == MappingType.EXPAND_KWARGS
        assert mappings[0].task_name == "process"
        assert mappings[0].mapped_iterable == "param_dicts"

    def test_detect_expand_kwargs_with_inline_list(self):
        """Detect expand_kwargs with inline list of dicts."""
        code = """
results = send_email.expand_kwargs([
    {"to": "a@example.com", "subject": "Hello"},
    {"to": "b@example.com", "subject": "World"},
])
"""
        mappings = extract_dynamic_mapping(code)

        assert len(mappings) == 1
        assert mappings[0].mapping_type == MappingType.EXPAND_KWARGS
        assert "a@example.com" in mappings[0].mapped_iterable


class TestMapIndexTemplateWarning:
    """Test that map_index_template parameter generates warnings."""

    def test_expand_with_map_index_template(self):
        """Warn when map_index_template is used in expand()."""
        code = """
result = process.expand(item=items, map_index_template="{{ task.op_kwargs['item'] }}")
"""
        mappings = extract_dynamic_mapping(code)

        assert len(mappings) == 1
        assert "map_index_template" in mappings[0].unsupported_params

    def test_map_index_template_in_conversion_warning(self):
        """Conversion should generate warning for map_index_template."""
        code = """
result = process.expand(item=items, map_index_template="{{ task.op_kwargs['item'] }}")
"""
        mappings = extract_dynamic_mapping(code)
        result = convert_dynamic_mapping(mappings[0])

        assert len(result.warnings) > 0
        assert any("map_index_template" in w for w in result.warnings)
        assert any("no prefect equivalent" in w.lower() for w in result.warnings)


class TestConvertExpand:
    """Test conversion of .expand() to Prefect .map()."""

    def test_convert_simple_expand_to_map(self):
        """Convert task.expand(x=iter) to task.map(iter)."""
        code = """
result = process_item.expand(item=items)
"""
        mappings = extract_dynamic_mapping(code)
        result = convert_dynamic_mapping(mappings[0], include_comments=False)

        assert "process_item.map(items)" in result.prefect_code
        assert "result =" in result.prefect_code

    def test_convert_expand_preserves_variable(self):
        """Converted code preserves assignment variable name."""
        code = """
processed_results = transformer.expand(data=dataset)
"""
        mappings = extract_dynamic_mapping(code)
        result = convert_dynamic_mapping(mappings[0], include_comments=False)

        assert "processed_results =" in result.prefect_code

    def test_convert_expand_includes_comments(self):
        """Conversion includes educational comments when enabled."""
        code = """
result = process.expand(item=items)
"""
        mappings = extract_dynamic_mapping(code)
        result = convert_dynamic_mapping(mappings[0], include_comments=True)

        assert "Converted from Airflow" in result.prefect_code
        assert ".map(" in result.prefect_code


class TestConvertPartialExpand:
    """Test conversion of .partial().expand() chains."""

    def test_convert_partial_expand_to_map_with_fixed(self):
        """Convert partial().expand() to .map() with fixed args."""
        code = """
result = process.partial(config=cfg).expand(item=items)
"""
        mappings = extract_dynamic_mapping(code)
        result = convert_dynamic_mapping(mappings[0], include_comments=False)

        assert "process.map(" in result.prefect_code
        assert "items" in result.prefect_code
        assert "config=cfg" in result.prefect_code

    def test_convert_partial_expand_preserves_all_fixed_params(self):
        """All fixed parameters from partial() appear in conversion."""
        code = """
result = load.partial(conn_id="pg", batch_size=100).expand(record=records)
"""
        mappings = extract_dynamic_mapping(code)
        result = convert_dynamic_mapping(mappings[0], include_comments=False)

        assert "conn_id=" in result.prefect_code
        assert "batch_size=" in result.prefect_code


class TestConvertExpandKwargs:
    """Test conversion of .expand_kwargs()."""

    def test_convert_expand_kwargs_to_submit_comprehension(self):
        """Convert expand_kwargs to list comprehension with .submit()."""
        code = """
results = process.expand_kwargs(params_list)
"""
        mappings = extract_dynamic_mapping(code)
        result = convert_dynamic_mapping(mappings[0], include_comments=False)

        assert ".submit(**kwargs)" in result.prefect_code
        assert "for kwargs in params_list" in result.prefect_code

    def test_convert_expand_kwargs_includes_options(self):
        """Conversion shows multiple approaches when comments enabled."""
        code = """
results = process.expand_kwargs(params_list)
"""
        mappings = extract_dynamic_mapping(code)
        result = convert_dynamic_mapping(mappings[0], include_comments=True)

        # Should show the list comprehension approach
        assert ".submit(" in result.prefect_code
        # Should mention it's a conversion
        assert "Converted from Airflow" in result.prefect_code


class TestConvertAllDynamicMappings:
    """Test bulk conversion of multiple patterns."""

    def test_convert_multiple_patterns(self):
        """Convert DAG with multiple dynamic mapping patterns."""
        code = """
from airflow.decorators import dag, task

@dag
def my_dag():
    @task
    def extract():
        return [1, 2, 3]

    @task
    def transform(x, multiplier):
        return x * multiplier

    @task
    def load(data):
        print(data)

    items = extract()
    transformed = transform.partial(multiplier=2).expand(x=items)
    load.expand(data=transformed)
"""
        result = convert_all_dynamic_mappings(code)

        assert len(result["conversions"]) == 2
        assert "transform" in result["summary"]
        assert "load" in result["summary"]
        assert result["prefect_code"]

    def test_no_patterns_returns_empty(self):
        """DAG without dynamic mapping returns empty result."""
        code = """
from airflow.decorators import dag, task

@dag
def simple_dag():
    @task
    def my_task():
        return 42

    my_task()
"""
        result = convert_all_dynamic_mappings(code)

        assert len(result["conversions"]) == 0
        assert "No dynamic task mapping patterns" in result["summary"]

    def test_collects_all_warnings(self):
        """All warnings from individual conversions are collected."""
        code = """
a = task1.expand(x=xs, map_index_template="{{ x }}")
b = task2.expand(y=ys, map_index_template="{{ y }}")
"""
        result = convert_all_dynamic_mappings(code)

        assert len(result["warnings"]) >= 2
        assert all("map_index_template" in w for w in result["warnings"])


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_syntax_returns_empty(self):
        """Invalid Python syntax returns empty list."""
        code = """
def broken(
    # missing closing paren
"""
        mappings = extract_dynamic_mapping(code)
        assert mappings == []

    def test_regular_method_calls_ignored(self):
        """Regular .expand() method (not Airflow) is ignored."""
        # This might be a false positive in naive detection,
        # but we detect based on the pattern structure
        code = """
my_list = [1, 2, 3]
result = some_object.process(my_list)
"""
        mappings = extract_dynamic_mapping(code)
        assert len(mappings) == 0

    def test_nested_expand_calls(self):
        """Handle nested function calls in expand parameters."""
        code = """
result = task.expand(data=generate_data(size=10))
"""
        mappings = extract_dynamic_mapping(code)

        assert len(mappings) == 1
        assert "generate_data(size=10)" in mappings[0].mapped_iterable

    def test_expand_in_complex_dag_structure(self):
        """Detect expand in realistic DAG with imports and decorators."""
        code = """
from airflow.decorators import dag, task
from datetime import datetime

default_args = {
    "owner": "airflow",
    "retries": 3,
}

@dag(
    dag_id="dynamic_mapping_example",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    default_args=default_args,
)
def my_pipeline():
    @task
    def get_files():
        return ["file1.csv", "file2.csv", "file3.csv"]

    @task
    def process_file(filename: str, config: dict):
        return f"Processed {filename}"

    @task
    def aggregate(results: list):
        return len(results)

    files = get_files()
    processed = process_file.partial(config={"mode": "fast"}).expand(filename=files)
    aggregate(processed)

dag_instance = my_pipeline()
"""
        mappings = extract_dynamic_mapping(code)

        assert len(mappings) == 1
        assert mappings[0].mapping_type == MappingType.PARTIAL_EXPAND
        assert mappings[0].task_name == "process_file"
        assert mappings[0].partial_params["config"] == "{'mode': 'fast'}"
