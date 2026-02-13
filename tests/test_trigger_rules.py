"""Tests for Trigger Rules converter.

Tests conversion of Airflow trigger_rule parameter to Prefect state-based patterns.
"""

import pytest
from airflow_unfactor.converters.trigger_rules import (
    detect_trigger_rules,
    generate_trigger_rule_code,
    convert_trigger_rules,
    TriggerRuleInfo,
    TRIGGER_RULE_PATTERNS,
)


class TestDetectTriggerRules:
    """Test trigger rule detection."""

    def test_detect_all_done(self):
        code = '''
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

cleanup = PythonOperator(
    task_id="cleanup",
    python_callable=do_cleanup,
    trigger_rule=TriggerRule.ALL_DONE,
)
'''
        rules = detect_trigger_rules(code)

        assert len(rules) == 1
        assert rules[0].task_id == "cleanup"
        assert rules[0].rule == "all_done"

    def test_detect_string_trigger_rule(self):
        code = '''
from airflow.operators.python import PythonOperator

notify = PythonOperator(
    task_id="notify",
    python_callable=send_notification,
    trigger_rule="all_failed",
)
'''
        rules = detect_trigger_rules(code)

        assert len(rules) == 1
        assert rules[0].task_id == "notify"
        assert rules[0].rule == "all_failed"

    def test_detect_one_success(self):
        code = '''
from airflow.operators.python import PythonOperator

proceed = PythonOperator(
    task_id="proceed_if_any_success",
    python_callable=continue_processing,
    trigger_rule="one_success",
)
'''
        rules = detect_trigger_rules(code)

        assert len(rules) == 1
        assert rules[0].rule == "one_success"

    def test_detect_none_failed(self):
        code = '''
from airflow.operators.bash import BashOperator

finalize = BashOperator(
    task_id="finalize",
    bash_command="echo done",
    trigger_rule="none_failed",
)
'''
        rules = detect_trigger_rules(code)

        assert len(rules) == 1
        assert rules[0].rule == "none_failed"

    def test_skip_default_all_success(self):
        """Default all_success should not be reported."""
        code = '''
from airflow.operators.python import PythonOperator

# Explicit all_success
task1 = PythonOperator(
    task_id="task1",
    python_callable=func1,
    trigger_rule="all_success",
)

# No trigger_rule (implicit all_success)
task2 = PythonOperator(
    task_id="task2",
    python_callable=func2,
)
'''
        rules = detect_trigger_rules(code)

        assert len(rules) == 0

    def test_detect_multiple_trigger_rules(self):
        code = '''
from airflow.operators.python import PythonOperator

cleanup = PythonOperator(
    task_id="cleanup",
    python_callable=do_cleanup,
    trigger_rule="all_done",
)

alert = PythonOperator(
    task_id="alert_on_failure",
    python_callable=send_alert,
    trigger_rule="one_failed",
)

report = PythonOperator(
    task_id="report",
    python_callable=generate_report,
    trigger_rule="none_failed",
)
'''
        rules = detect_trigger_rules(code)

        assert len(rules) == 3
        rule_set = {r.rule for r in rules}
        assert rule_set == {"all_done", "one_failed", "none_failed"}

    def test_detect_always_trigger_rule(self):
        code = '''
from airflow.operators.python import PythonOperator

always_run = PythonOperator(
    task_id="always_run",
    python_callable=log_completion,
    trigger_rule="always",
)
'''
        rules = detect_trigger_rules(code)

        assert len(rules) == 1
        assert rules[0].rule == "always"

    def test_detect_trigger_rule_on_sensor(self):
        code = '''
from airflow.sensors.filesystem import FileSensor

wait_for_file = FileSensor(
    task_id="wait_for_file",
    filepath="/data/input.csv",
    trigger_rule="none_failed",
)
'''
        rules = detect_trigger_rules(code)

        assert len(rules) == 1
        assert rules[0].operator_type == "FileSensor"

    def test_handles_syntax_error(self):
        code = "this is not valid python {"
        rules = detect_trigger_rules(code)
        assert rules == []


class TestGenerateTriggerRuleCode:
    """Test code generation for trigger rules."""

    def test_generate_all_done(self):
        info = TriggerRuleInfo(
            task_id="cleanup",
            rule="all_done",
            upstream_tasks=["task1", "task2"],
        )

        code, imports = generate_trigger_rule_code(info)

        assert "cleanup_result = cleanup" in code
        assert "all_done" in code
        assert "return_state=True" in code

    def test_generate_all_failed(self):
        info = TriggerRuleInfo(
            task_id="error_handler",
            rule="all_failed",
            upstream_tasks=["task1", "task2"],
        )

        code, imports = generate_trigger_rule_code(info)

        assert "all(state.is_failed()" in code
        assert "error_handler_result = error_handler" in code

    def test_generate_one_failed(self):
        info = TriggerRuleInfo(
            task_id="alert",
            rule="one_failed",
            upstream_tasks=["step1", "step2"],
        )

        code, imports = generate_trigger_rule_code(info)

        assert "any(state.is_failed()" in code
        assert "# Skip: no upstream task failed" in code

    def test_generate_one_success(self):
        info = TriggerRuleInfo(
            task_id="proceed",
            rule="one_success",
            upstream_tasks=["branch_a", "branch_b"],
        )

        code, imports = generate_trigger_rule_code(info)

        assert "any(state.is_completed()" in code
        assert "# Skip: no upstream task succeeded" in code

    def test_generate_none_failed(self):
        info = TriggerRuleInfo(
            task_id="finalize",
            rule="none_failed",
            upstream_tasks=["step1"],
        )

        code, imports = generate_trigger_rule_code(info)

        assert "not any(state.is_failed()" in code
        assert "finalize_result" in code

    def test_generate_always(self):
        info = TriggerRuleInfo(
            task_id="always_log",
            rule="always",
            upstream_tasks=["may_fail"],
        )

        code, imports = generate_trigger_rule_code(info)

        assert "always_log_result = always_log" in code
        assert "return_state=True" in code

    def test_generate_unknown_rule(self):
        info = TriggerRuleInfo(
            task_id="mystery",
            rule="custom_unknown_rule",
        )

        code, imports = generate_trigger_rule_code(info)

        assert "WARNING" in code
        assert "custom_unknown_rule" in code
        assert "manual" in code.lower()

    def test_no_upstream_tasks(self):
        info = TriggerRuleInfo(
            task_id="entry_task",
            rule="all_done",
            upstream_tasks=[],
        )

        code, imports = generate_trigger_rule_code(info)

        assert "# No upstream tasks" in code

    def test_generate_none_failed_min_one_success(self):
        info = TriggerRuleInfo(
            task_id="conditional",
            rule="none_failed_min_one_success",
            upstream_tasks=["a", "b", "c"],
        )

        code, imports = generate_trigger_rule_code(info)

        assert "not any(s.is_failed()" in code
        assert "any(s.is_completed()" in code


class TestConvertTriggerRules:
    """Test batch trigger rule conversion."""

    def test_convert_dag_with_trigger_rules(self):
        code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

with DAG("my_dag") as dag:
    extract = PythonOperator(
        task_id="extract",
        python_callable=extract_data,
    )

    transform = PythonOperator(
        task_id="transform",
        python_callable=transform_data,
    )

    cleanup = BashOperator(
        task_id="cleanup",
        bash_command="rm -rf /tmp/data",
        trigger_rule="all_done",
    )

    notify_failure = PythonOperator(
        task_id="notify_failure",
        python_callable=send_alert,
        trigger_rule="one_failed",
    )

    [extract, transform] >> cleanup
    [extract, transform] >> notify_failure
'''
        result = convert_trigger_rules(code)

        assert len(result["trigger_rules"]) == 2
        assert "cleanup" in result["conversions"]
        assert "notify_failure" in result["conversions"]
        assert "2 trigger rule(s)" in result["summary"]

    def test_convert_no_trigger_rules(self):
        code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG("simple_dag") as dag:
    task = PythonOperator(
        task_id="task",
        python_callable=do_work,
    )
'''
        result = convert_trigger_rules(code)

        assert result["trigger_rules"] == []
        assert result["conversions"] == {}
        assert "No non-default" in result["summary"]

    def test_warnings_for_failure_rules(self):
        code = '''
from airflow.operators.python import PythonOperator

alert = PythonOperator(
    task_id="alert_on_any_failure",
    python_callable=alert,
    trigger_rule="one_failed",
)
'''
        result = convert_trigger_rules(code)

        assert any("one_failed" in w for w in result["warnings"])

    def test_warnings_for_always_rule(self):
        code = '''
from airflow.operators.python import PythonOperator

always_task = PythonOperator(
    task_id="always_task",
    python_callable=func,
    trigger_rule="always",
)
'''
        result = convert_trigger_rules(code)

        assert any("always" in w.lower() for w in result["warnings"])

    def test_summary_counts_rules(self):
        code = '''
from airflow.operators.python import PythonOperator

t1 = PythonOperator(task_id="t1", python_callable=f, trigger_rule="all_done")
t2 = PythonOperator(task_id="t2", python_callable=f, trigger_rule="all_done")
t3 = PythonOperator(task_id="t3", python_callable=f, trigger_rule="one_failed")
'''
        result = convert_trigger_rules(code)

        assert "3 trigger rule(s)" in result["summary"]
        assert "2 all_done" in result["summary"]
        assert "1 one_failed" in result["summary"]


class TestTriggerRulePatterns:
    """Test that all patterns are properly defined."""

    def test_all_expected_rules_have_patterns(self):
        expected_rules = [
            "all_success",
            "all_done",
            "all_failed",
            "one_failed",
            "one_success",
            "none_failed",
            "none_failed_min_one_success",
            "none_skipped",
            "always",
            "dummy",
        ]

        for rule in expected_rules:
            assert rule in TRIGGER_RULE_PATTERNS, f"Missing pattern for {rule}"

    def test_patterns_contain_trigger_rule_comment(self):
        """Each pattern should document what trigger rule it handles."""
        for rule, pattern in TRIGGER_RULE_PATTERNS.items():
            assert "Trigger rule:" in pattern or "trigger rule:" in pattern.lower(), \
                f"Pattern for {rule} missing trigger rule comment"

    def test_patterns_are_valid_python_templates(self):
        """Patterns should be formattable without errors."""
        placeholders = {
            "task_id": "my_task",
            "upstream_states_code": "# states code",
            "upstream_state_vars": "state_a, state_b",
            "upstream_result_vars": "result_a, result_b",
            "upstream_args": "result_a, result_b",
        }

        for rule, pattern in TRIGGER_RULE_PATTERNS.items():
            try:
                formatted = pattern.format(**placeholders)
                assert formatted  # Should produce non-empty string
            except KeyError as e:
                pytest.fail(f"Pattern for {rule} has missing placeholder: {e}")


class TestIntegration:
    """Integration tests for real-world DAG patterns."""

    def test_etl_with_cleanup(self):
        """Common pattern: cleanup runs regardless of ETL success."""
        code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG("etl_dag") as dag:
    extract = PythonOperator(task_id="extract", python_callable=extract)
    transform = PythonOperator(task_id="transform", python_callable=transform)
    load = PythonOperator(task_id="load", python_callable=load)
    cleanup = PythonOperator(
        task_id="cleanup",
        python_callable=cleanup_temp_files,
        trigger_rule="all_done",
    )

    extract >> transform >> load >> cleanup
'''
        result = convert_trigger_rules(code)

        assert len(result["trigger_rules"]) == 1
        assert result["trigger_rules"][0].task_id == "cleanup"
        code_gen = result["conversions"]["cleanup"][0]
        assert "all_done" in code_gen

    def test_notification_on_failure(self):
        """Common pattern: send alert if any task fails."""
        code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG("monitored_dag") as dag:
    step1 = PythonOperator(task_id="step1", python_callable=step1)
    step2 = PythonOperator(task_id="step2", python_callable=step2)
    step3 = PythonOperator(task_id="step3", python_callable=step3)

    send_failure_alert = PythonOperator(
        task_id="send_failure_alert",
        python_callable=alert_oncall,
        trigger_rule="one_failed",
    )

    [step1, step2, step3] >> send_failure_alert
'''
        result = convert_trigger_rules(code)

        assert len(result["trigger_rules"]) == 1
        code_gen = result["conversions"]["send_failure_alert"][0]
        assert "any(state.is_failed()" in code_gen

    def test_branching_with_join(self):
        """Pattern: join after branches where one success is enough."""
        code = '''
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator

with DAG("branching_dag") as dag:
    branch = BranchPythonOperator(task_id="branch", python_callable=decide)
    path_a = PythonOperator(task_id="path_a", python_callable=do_a)
    path_b = PythonOperator(task_id="path_b", python_callable=do_b)
    join = PythonOperator(
        task_id="join",
        python_callable=merge_results,
        trigger_rule="one_success",
    )

    branch >> [path_a, path_b] >> join
'''
        result = convert_trigger_rules(code)

        assert len(result["trigger_rules"]) == 1
        code_gen = result["conversions"]["join"][0]
        assert "any(state.is_completed()" in code_gen
