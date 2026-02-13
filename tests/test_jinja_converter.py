"""Tests for Jinja2 template converter.

Tests the detection and conversion of Airflow Jinja2 template patterns
to Prefect runtime context expressions.
"""

import pytest
from airflow_unfactor.converters.jinja import (
    JinjaPattern,
    JinjaPatternType,
    detect_jinja_patterns,
    convert_jinja_to_fstring,
    has_jinja_patterns,
    analyze_jinja_in_code,
)


class TestDetectJinjaPatterns:
    """Test detection of Jinja2 patterns."""

    def test_detect_ds(self):
        """Detect {{ ds }} pattern."""
        patterns = detect_jinja_patterns("echo {{ ds }}")

        assert len(patterns) == 1
        assert patterns[0].pattern_type == JinjaPatternType.DS
        assert patterns[0].original == "{{ ds }}"

    def test_detect_ds_nodash(self):
        """Detect {{ ds_nodash }} pattern."""
        patterns = detect_jinja_patterns("file_{{ ds_nodash }}.csv")

        assert len(patterns) == 1
        assert patterns[0].pattern_type == JinjaPatternType.DS_NODASH

    def test_detect_ts(self):
        """Detect {{ ts }} pattern."""
        patterns = detect_jinja_patterns("timestamp: {{ ts }}")

        assert len(patterns) == 1
        assert patterns[0].pattern_type == JinjaPatternType.TS

    def test_detect_execution_date(self):
        """Detect {{ execution_date }} pattern."""
        patterns = detect_jinja_patterns("date: {{ execution_date }}")

        assert len(patterns) == 1
        assert patterns[0].pattern_type == JinjaPatternType.EXECUTION_DATE

    def test_detect_params(self):
        """Detect {{ params.x }} pattern."""
        patterns = detect_jinja_patterns("input: {{ params.input_path }}")

        assert len(patterns) == 1
        assert patterns[0].pattern_type == JinjaPatternType.PARAMS
        assert patterns[0].params["param_name"] == "input_path"

    def test_detect_macros_ds_add_positive(self):
        """Detect {{ macros.ds_add(ds, N) }} with positive days."""
        patterns = detect_jinja_patterns("tomorrow: {{ macros.ds_add(ds, 1) }}")

        assert len(patterns) == 1
        assert patterns[0].pattern_type == JinjaPatternType.MACROS_DS_ADD
        assert patterns[0].params["days"] == 1

    def test_detect_macros_ds_add_negative(self):
        """Detect {{ macros.ds_add(ds, -N) }} with negative days."""
        patterns = detect_jinja_patterns("yesterday: {{ macros.ds_add(ds, -1) }}")

        assert len(patterns) == 1
        assert patterns[0].pattern_type == JinjaPatternType.MACROS_DS_ADD
        assert patterns[0].params["days"] == -1

    def test_detect_macros_ds_format(self):
        """Detect {{ macros.ds_format(ds, 'format') }} pattern."""
        patterns = detect_jinja_patterns(
            "formatted: {{ macros.ds_format(ds, '%Y/%m/%d') }}"
        )

        assert len(patterns) == 1
        assert patterns[0].pattern_type == JinjaPatternType.MACROS_DS_FORMAT
        assert patterns[0].params["format"] == "%Y/%m/%d"

    def test_detect_prev_ds(self):
        """Detect {{ prev_ds }} pattern."""
        patterns = detect_jinja_patterns("previous: {{ prev_ds }}")

        assert len(patterns) == 1
        assert patterns[0].pattern_type == JinjaPatternType.PREV_DS

    def test_detect_next_ds(self):
        """Detect {{ next_ds }} pattern."""
        patterns = detect_jinja_patterns("next: {{ next_ds }}")

        assert len(patterns) == 1
        assert patterns[0].pattern_type == JinjaPatternType.NEXT_DS

    def test_detect_unknown_pattern(self):
        """Detect unrecognized Jinja2 patterns."""
        patterns = detect_jinja_patterns("custom: {{ dag_run.conf.key }}")

        assert len(patterns) == 1
        assert patterns[0].pattern_type == JinjaPatternType.UNKNOWN
        assert not patterns[0].is_supported

    def test_detect_multiple_patterns(self):
        """Detect multiple patterns in one string."""
        patterns = detect_jinja_patterns(
            "from {{ ds }} to {{ macros.ds_add(ds, 7) }}"
        )

        assert len(patterns) == 2
        assert patterns[0].pattern_type == JinjaPatternType.DS
        assert patterns[1].pattern_type == JinjaPatternType.MACROS_DS_ADD

    def test_detect_no_patterns(self):
        """Return empty list when no patterns found."""
        patterns = detect_jinja_patterns("regular string without templates")

        assert patterns == []

    def test_detect_patterns_with_whitespace(self):
        """Handle whitespace variations in patterns."""
        patterns = detect_jinja_patterns("{{ds}} and {{  ds  }}")

        assert len(patterns) == 2
        assert all(p.pattern_type == JinjaPatternType.DS for p in patterns)

    def test_pattern_positions(self):
        """Track correct start/end positions."""
        text = "prefix {{ ds }} suffix"
        patterns = detect_jinja_patterns(text)

        assert len(patterns) == 1
        assert text[patterns[0].start : patterns[0].end] == "{{ ds }}"


class TestConvertJinjaToFstring:
    """Test conversion of Jinja2 to f-strings."""

    def test_convert_ds(self):
        """Convert {{ ds }} to f-string."""
        converted, imports, warnings = convert_jinja_to_fstring("{{ ds }}")

        assert "scheduled_start_time.strftime('%Y-%m-%d')" in converted
        assert converted.startswith('f"')
        assert "from prefect import runtime" in imports
        assert warnings == []

    def test_convert_ds_nodash(self):
        """Convert {{ ds_nodash }} to f-string."""
        converted, imports, warnings = convert_jinja_to_fstring("{{ ds_nodash }}")

        assert "strftime('%Y%m%d')" in converted
        assert "from prefect import runtime" in imports

    def test_convert_ts(self):
        """Convert {{ ts }} to f-string."""
        converted, imports, warnings = convert_jinja_to_fstring("{{ ts }}")

        assert ".isoformat()" in converted
        assert "from prefect import runtime" in imports

    def test_convert_params(self):
        """Convert {{ params.x }} to parameter reference."""
        converted, imports, warnings = convert_jinja_to_fstring("{{ params.bucket }}")

        assert "{bucket}" in converted
        # params are passed as flow parameters, no special import needed

    def test_convert_macros_ds_add_positive(self):
        """Convert {{ macros.ds_add(ds, N) }} with positive days."""
        converted, imports, warnings = convert_jinja_to_fstring(
            "{{ macros.ds_add(ds, 7) }}"
        )

        assert "timedelta(days=7)" in converted
        assert "strftime('%Y-%m-%d')" in converted
        assert "from datetime import timedelta" in imports
        assert "from prefect import runtime" in imports

    def test_convert_macros_ds_add_negative(self):
        """Convert {{ macros.ds_add(ds, -N) }} with negative days."""
        converted, imports, warnings = convert_jinja_to_fstring(
            "{{ macros.ds_add(ds, -3) }}"
        )

        assert "timedelta(days=3)" in converted
        assert " - timedelta" in converted  # subtraction

    def test_convert_macros_ds_format(self):
        """Convert {{ macros.ds_format(ds, 'format') }}."""
        converted, imports, warnings = convert_jinja_to_fstring(
            "{{ macros.ds_format(ds, '%Y/%m/%d') }}"
        )

        assert "strftime('%Y/%m/%d')" in converted

    def test_convert_prev_ds(self):
        """Convert {{ prev_ds }} with timedelta."""
        converted, imports, warnings = convert_jinja_to_fstring("{{ prev_ds }}")

        assert "timedelta(days=1)" in converted
        assert " - timedelta" in converted
        assert "from datetime import timedelta" in imports

    def test_convert_next_ds(self):
        """Convert {{ next_ds }} with timedelta."""
        converted, imports, warnings = convert_jinja_to_fstring("{{ next_ds }}")

        assert "timedelta(days=1)" in converted
        assert " + timedelta" in converted

    def test_convert_unknown_warns(self):
        """Warn on unrecognized patterns."""
        converted, imports, warnings = convert_jinja_to_fstring(
            "{{ dag_run.conf.key }}"
        )

        assert len(warnings) == 1
        assert "manual conversion required" in warnings[0]
        # Original pattern preserved
        assert "dag_run.conf.key" in converted

    def test_convert_mixed_text_and_patterns(self):
        """Convert string with literal text and patterns."""
        converted, imports, warnings = convert_jinja_to_fstring(
            "s3://bucket/data/{{ ds }}/file.csv"
        )

        assert "s3://bucket/data/" in converted
        assert "/file.csv" in converted
        assert "scheduled_start_time" in converted

    def test_convert_multiple_patterns(self):
        """Convert string with multiple patterns."""
        converted, imports, warnings = convert_jinja_to_fstring(
            "from {{ ds }} to {{ macros.ds_add(ds, 7) }}"
        )

        assert converted.count("{") >= 2  # At least 2 f-string expressions
        assert "strftime('%Y-%m-%d')" in converted
        assert "timedelta(days=7)" in converted

    def test_convert_no_patterns_returns_original(self):
        """Return original string when no patterns found."""
        converted, imports, warnings = convert_jinja_to_fstring("plain string")

        assert converted == "plain string"
        assert imports == []
        assert warnings == []

    def test_convert_execution_date(self):
        """Convert {{ execution_date }} to runtime reference."""
        converted, imports, warnings = convert_jinja_to_fstring("{{ execution_date }}")

        assert "scheduled_start_time" in converted
        # No strftime - returns the datetime object
        assert "strftime" not in converted


class TestHasJinjaPatterns:
    """Test Jinja2 pattern detection helper."""

    def test_has_patterns_true(self):
        """Return True when patterns exist."""
        assert has_jinja_patterns("date: {{ ds }}")

    def test_has_patterns_false(self):
        """Return False when no patterns."""
        assert not has_jinja_patterns("plain string")

    def test_has_patterns_partial_braces(self):
        """Return False for incomplete braces."""
        assert not has_jinja_patterns("{ single brace }")
        assert not has_jinja_patterns("{{ incomplete")


class TestAnalyzeJinjaInCode:
    """Test Jinja2 analysis function."""

    def test_analyze_basic(self):
        """Analyze code with Jinja2 patterns."""
        result = analyze_jinja_in_code('cmd = "echo {{ ds }}"')

        assert result["supported_count"] == 1
        assert result["unsupported_count"] == 0
        assert "from prefect import runtime" in result["imports_needed"]

    def test_analyze_with_params(self):
        """Analyze code with params patterns."""
        result = analyze_jinja_in_code('path = "{{ params.input_path }}"')

        assert result["supported_count"] == 1
        assert any("flow parameters" in note for note in result["conversion_notes"])

    def test_analyze_with_prev_next_ds(self):
        """Analyze code with prev_ds/next_ds."""
        result = analyze_jinja_in_code('range = "{{ prev_ds }} to {{ next_ds }}"')

        assert result["supported_count"] == 2
        assert any("daily schedule" in note for note in result["conversion_notes"])

    def test_analyze_with_unknown(self):
        """Analyze code with unknown patterns."""
        result = analyze_jinja_in_code('custom = "{{ dag_run.conf.x }}"')

        assert result["unsupported_count"] == 1
        assert any("manual conversion" in note for note in result["conversion_notes"])

    def test_analyze_empty(self):
        """Analyze code with no patterns."""
        result = analyze_jinja_in_code("plain code without templates")

        assert result["supported_count"] == 0
        assert result["unsupported_count"] == 0
        assert result["patterns"] == []


class TestRealWorldPatterns:
    """Test with realistic Airflow template strings."""

    def test_s3_path_template(self):
        """Convert S3 path with date partitioning."""
        template = "s3://my-bucket/data/year={{ ds[:4] }}/month={{ ds[5:7] }}/day={{ ds[8:10] }}/file.parquet"
        patterns = detect_jinja_patterns(template)

        # These are slice patterns - will be detected as unknown
        assert len(patterns) == 3
        # All are unknown because they use Python slicing
        assert all(p.pattern_type == JinjaPatternType.UNKNOWN for p in patterns)

    def test_bash_command_template(self):
        """Convert BashOperator command with templates."""
        template = 'aws s3 cp "s3://bucket/{{ ds }}/data.csv" /tmp/ && python process.py --date {{ ds }}'
        converted, imports, warnings = convert_jinja_to_fstring(template)

        assert converted.startswith('f"')
        assert "scheduled_start_time" in converted
        assert "from prefect import runtime" in imports

    def test_sql_template(self):
        """Convert SQL query template."""
        template = """
        SELECT * FROM events
        WHERE event_date >= '{{ ds }}'
        AND event_date < '{{ macros.ds_add(ds, 1) }}'
        """
        converted, imports, warnings = convert_jinja_to_fstring(template)

        assert "strftime('%Y-%m-%d')" in converted
        assert "timedelta(days=1)" in converted
        assert "from datetime import timedelta" in imports

    def test_complex_macro_expression(self):
        """Handle complex macro expressions as unknown."""
        template = "{{ macros.datetime.strptime(ds, '%Y-%m-%d').strftime('%d/%m/%Y') }}"
        patterns = detect_jinja_patterns(template)

        # Complex macro should be detected as unknown
        assert len(patterns) == 1
        assert patterns[0].pattern_type == JinjaPatternType.UNKNOWN

    def test_mixed_known_unknown(self):
        """Handle mix of known and unknown patterns."""
        template = "date: {{ ds }}, custom: {{ dag.owner }}"
        converted, imports, warnings = convert_jinja_to_fstring(template)

        # ds should be converted
        assert "scheduled_start_time" in converted
        # dag.owner should trigger warning
        assert len(warnings) == 1
        assert "manual conversion" in warnings[0]
