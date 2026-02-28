"""Tests for knowledge loader."""

import json
import logging
from pathlib import Path

import pytest

from airflow_unfactor.knowledge import (
    FALLBACK_KNOWLEDGE,
    _find_knowledge_dir,
    load_knowledge,
    lookup,
    normalize_query,
    suggestions,
)


class TestLoadKnowledge:
    """Tests for load_knowledge function."""

    def test_missing_directory_returns_empty(self):
        """Explicit nonexistent path returns empty dict."""
        result = load_knowledge("/nonexistent/path")
        assert result == {}

    def test_no_knowledge_anywhere_returns_empty(self, monkeypatch):
        """When no bundled data or colin dir is found, returns empty dict."""
        monkeypatch.setattr(
            "airflow_unfactor.knowledge._find_knowledge_dir",
            lambda *a, **kw: None,
        )
        result = load_knowledge()
        assert result == {}

    def test_bundled_data_found(self):
        """Bundled package data is discovered by default."""
        data_dir = _find_knowledge_dir()
        assert data_dir is not None
        assert list(data_dir.glob("*.json"))

    def test_loads_json_files(self, tmp_path):
        """Loads and merges JSON files from Colin output."""
        concepts = {
            "entries": [
                {"name": "DAG", "concept_type": "concept", "description": "workflow"},
                {"name": "XCom", "concept_type": "concept", "description": "data passing"},
            ]
        }
        (tmp_path / "concepts.json").write_text(json.dumps(concepts))

        result = load_knowledge(str(tmp_path))
        assert "DAG" in result
        assert "XCom" in result

    def test_loads_flat_dict(self, tmp_path):
        """Loads flat dict JSON files."""
        data = {
            "PythonOperator": {"concept_type": "operator"},
            "BashOperator": {"concept_type": "operator"},
        }
        (tmp_path / "operators.json").write_text(json.dumps(data))

        result = load_knowledge(str(tmp_path))
        assert "PythonOperator" in result
        assert "BashOperator" in result

    def test_skips_invalid_json(self, tmp_path):
        """Invalid JSON files are skipped."""
        (tmp_path / "bad.json").write_text("not json {{{")
        (tmp_path / "good.json").write_text(json.dumps({"X": {"type": "ok"}}))

        result = load_knowledge(str(tmp_path))
        assert "X" in result


class TestLookup:
    """Tests for lookup function."""

    def test_exact_match(self):
        """Exact match returns the entry with source: colin."""
        knowledge = {"PythonOperator": {"concept_type": "operator"}}
        result = lookup("PythonOperator", knowledge)
        assert result["status"] == "found"
        assert result["source"] == "colin"
        assert result["concept_type"] == "operator"

    def test_case_insensitive_match(self):
        """Case-insensitive match works."""
        knowledge = {"PythonOperator": {"concept_type": "operator"}}
        result = lookup("pythonoperator", knowledge)
        assert result["status"] == "found"

    def test_substring_match(self):
        """Substring match works."""
        knowledge = {"PythonOperator": {"concept_type": "operator"}}
        result = lookup("Python", knowledge)
        assert result["status"] == "found"

    def test_fallback_when_not_in_knowledge(self):
        """Falls back to built-in mappings when not in Colin output."""
        result = lookup("PythonOperator", {})
        assert result["status"] == "found"
        assert result["source"] == "fallback"

    def test_not_found(self):
        """Unrecognized concept returns not_found with suggestions."""
        result = lookup("CompletelyUnknownThing", {})
        assert result["status"] == "not_found"
        assert "suggestions" in result
        assert "fallback_advice" in result


class TestSuggestions:
    """Tests for suggestions function."""

    def test_returns_similar_names(self):
        """Returns suggestions based on character overlap."""
        result = suggestions("Python", {})
        # Should include PythonOperator from fallback
        assert any("Python" in s for s in result)

    def test_empty_query(self):
        """Empty query returns some suggestions."""
        result = suggestions("", {})
        assert isinstance(result, list)

    def test_max_five_suggestions(self):
        """Never returns more than 5 suggestions."""
        knowledge = {f"Concept{i}": {} for i in range(20)}
        result = suggestions("Concept", knowledge)
        assert len(result) <= 5


class TestPhase1Operators:
    """Tests for Phase 1 knowledge expansion operators (KNOW-01 through KNOW-06)."""

    COLIN_OUTPUT_DIR = str(Path(__file__).parent.parent / "colin" / "output")

    @pytest.mark.parametrize("operator_name", [
        "KubernetesPodOperator",       # KNOW-01
        "DatabricksSubmitRunOperator",  # KNOW-02
        "DatabricksRunNowOperator",     # KNOW-03
        "SparkSubmitOperator",          # KNOW-04
        "SimpleHttpOperator",           # KNOW-05
        "SSHOperator",                  # KNOW-06
    ])
    def test_operator_found_in_colin_output(self, operator_name):
        """Each Phase 1 operator is found via lookup with source: colin."""
        knowledge = load_knowledge(self.COLIN_OUTPUT_DIR)
        result = lookup(operator_name, knowledge)
        assert result["status"] == "found", f"{operator_name} not found in Colin output"
        assert result["source"] == "colin", f"{operator_name} found but source is {result['source']}, expected colin"


class TestNormalizeQuery:
    """Tests for normalize_query function (KNOW-09 query normalization)."""

    def test_normalize_jinja_wrapper(self):
        """Strips {{ }} and macros. prefix from Jinja macro syntax."""
        result = normalize_query("{{ macros.ds_add(ds, 5) }}")
        assert result == "ds_add(ds, 5)"

    def test_normalize_var_value(self):
        """Maps var.value.* prefix to canonical var_value key for Variable.get() lookup."""
        result = normalize_query("var.value.my_key")
        assert result == "var_value"

    def test_normalize_plain(self):
        """Plain operator names pass through unchanged."""
        result = normalize_query("PythonOperator")
        assert result == "PythonOperator"

    def test_normalize_jinja_simple_ds(self):
        """Strips {{ }} from simple ds variable."""
        result = normalize_query("{{ ds }}")
        assert result == "ds"

    def test_normalize_macros_no_jinja(self):
        """Strips macros. prefix even without {{ }} wrapping."""
        result = normalize_query("macros.ds_add")
        assert result == "ds_add"

    def test_normalize_whitespace(self):
        """Leading/trailing whitespace is stripped."""
        result = normalize_query("  PythonOperator  ")
        assert result == "PythonOperator"

    def test_normalize_jinja_whitespace_inside(self):
        """Internal whitespace in {{ }} is handled."""
        result = normalize_query("{{  ds  }}")
        assert result == "ds"

    def test_lookup_with_jinja_syntax(self):
        """lookup() resolves Jinja-wrapped concept via normalize_query."""
        knowledge = {"ds_add": {"concept_type": "jinja-macro", "description": "add days"}}
        result = lookup("{{ macros.ds_add(ds, 5) }}", knowledge)
        # After normalization: "ds_add(ds, 5)" — substring match finds "ds_add"
        assert result["status"] == "found"


class TestParseErrorLogging:
    """Tests for SRVR-04: logging when JSON files fail to parse."""

    def test_logs_warning_for_invalid_json(self, tmp_path, caplog):
        """Invalid JSON file triggers a warning with filename."""
        (tmp_path / "bad.json").write_text("not json {{{")
        (tmp_path / "good.json").write_text(json.dumps({"X": {"type": "ok"}}))
        with caplog.at_level(logging.WARNING):
            result = load_knowledge(str(tmp_path))
        assert "bad.json" in caplog.text
        assert "JSONDecodeError" in caplog.text
        assert "X" in result  # good file still loaded

    def test_logs_warning_includes_error_type(self, tmp_path, caplog):
        """Warning message includes the error type name."""
        (tmp_path / "broken.json").write_text("[1, 2, 3")
        with caplog.at_level(logging.WARNING):
            load_knowledge(str(tmp_path))
        assert "broken.json" in caplog.text
        assert "JSONDecodeError" in caplog.text

    def test_continues_loading_after_bad_file(self, tmp_path, caplog):
        """Valid files still load when a corrupt file is present."""
        (tmp_path / "corrupt.json").write_text("NOT JSON AT ALL")
        (tmp_path / "valid.json").write_text(json.dumps({"MyOperator": {"concept_type": "operator"}}))
        with caplog.at_level(logging.WARNING):
            result = load_knowledge(str(tmp_path))
        assert "MyOperator" in result
        assert "corrupt.json" in caplog.text


class TestSuggestionsFuzzy:
    """Tests for difflib-based fuzzy suggestions (SRVR-02)."""

    def test_fuzzy_typo_match(self):
        """Fuzzy match returns KubernetesPodOperator for a close typo."""
        result = suggestions("KubernetesPodOp", {"KubernetesPodOperator": {"concept_type": "operator"}})
        assert "KubernetesPodOperator" in result, f"Expected KubernetesPodOperator in {result}"

    def test_fuzzy_case_insensitive(self):
        """Case-insensitive fuzzy match works despite mixed case query."""
        result = suggestions("kubernetesPodOp", {"KubernetesPodOperator": {"concept_type": "operator"}})
        assert "KubernetesPodOperator" in result, f"Expected KubernetesPodOperator in {result}"

    def test_fuzzy_no_false_positives(self):
        """Completely unknown query returns empty list."""
        result = suggestions("CompletelyUnknownXYZ123", {})
        assert result == [], f"Expected empty list, got {result}"

    def test_fuzzy_returns_original_case(self):
        """Results preserve original casing, not lowercase."""
        result = suggestions("pythonop", {})
        # PythonOperator should appear (from fallback) with correct original casing
        assert any("Python" in r for r in result), (
            f"Expected Python-related result with original casing, got {result}"
        )


class TestPhase3Integration:
    """End-to-end integration tests for Phase 3 knowledge requirements (KNOW-07 through KNOW-12).

    These tests use the real colin/output/ directory (not mocks) to verify that
    Colin models authored in Plans 01 and 02 are compiled to JSON and discoverable
    through the full lookup pipeline.
    """

    COLIN_OUTPUT_DIR = str(Path(__file__).parent.parent / "colin" / "output")

    @pytest.mark.parametrize("operator_name,expected_content", [
        ("AzureDataFactoryRunPipelineOperator", "ARCHITECTURE SHIFT"),  # KNOW-07
        ("WasbOperator", "AzureBlobStorageCredentials"),                # KNOW-07
        ("DbtCloudRunJobOperator", "trigger_dbt_cloud_job_run_and_wait_for_completion"),  # KNOW-08
    ])
    def test_phase3_operator_lookup(self, operator_name, expected_content):
        """Phase 3 operators are findable via lookup with expected content."""
        knowledge = load_knowledge(self.COLIN_OUTPUT_DIR)
        result = lookup(operator_name, knowledge)
        assert result["status"] == "found", f"{operator_name} not found in Colin output"
        result_str = json.dumps(result)
        assert expected_content in result_str, (
            f"Expected '{expected_content}' in {operator_name} result"
        )

    @pytest.mark.parametrize("concept,expected_in_result", [
        ("depends_on_past", "no direct equivalent"),  # KNOW-10
        ("deferrable", "Automations"),                # KNOW-11
    ])
    def test_phase3_concept_lookup(self, concept, expected_in_result):
        """Phase 3 concepts are findable via lookup with expected guidance."""
        knowledge = load_knowledge(self.COLIN_OUTPUT_DIR)
        result = lookup(concept, knowledge)
        assert result["status"] == "found", f"'{concept}' not found in Colin output"
        result_str = json.dumps(result).lower()
        assert expected_in_result.lower() in result_str, (
            f"Expected '{expected_in_result}' in result for '{concept}'"
        )

    @pytest.mark.parametrize("query", [
        "macros.ds_add",                  # KNOW-09: macros prefix stripped
        "{{ macros.ds_add(ds, 5) }}",     # KNOW-09: Jinja wrapper + macros prefix stripped
        "dag_run.conf",                   # KNOW-09: dag_run.conf variable
        "{{ dag_run.conf }}",             # KNOW-09: Jinja-wrapped dag_run.conf
        "var.value.my_key",               # KNOW-09: var.value prefix normalized to var_value
    ])
    def test_phase3_jinja_macro_lookup(self, query):
        """Jinja macro queries are findable after normalization (KNOW-09)."""
        knowledge = load_knowledge(self.COLIN_OUTPUT_DIR)
        result = lookup(query, knowledge)
        assert result["status"] == "found", (
            f"'{query}' returned not_found — normalization or knowledge entry missing"
        )

    def test_azure_adf_is_architecture_shift(self):
        """AzureDataFactoryRunPipelineOperator result explicitly warns of architecture shift."""
        knowledge = load_knowledge(self.COLIN_OUTPUT_DIR)
        result = lookup("AzureDataFactoryRunPipelineOperator", knowledge)
        assert result["status"] == "found"
        result_str = json.dumps(result)
        assert "ARCHITECTURE SHIFT" in result_str, (
            "ADF entry must contain ARCHITECTURE SHIFT warning"
        )
        assert "prefect_azure" in result_str, (
            "ADF entry must mention prefect_azure (to warn against using it)"
        )

    def test_dbt_cloud_operator_uses_wait_for_completion_variant(self):
        """DbtCloudRunJobOperator maps to the _and_wait_for_completion function, not fire-and-forget."""
        knowledge = load_knowledge(self.COLIN_OUTPUT_DIR)
        result = lookup("DbtCloudRunJobOperator", knowledge)
        assert result["status"] == "found"
        result_str = json.dumps(result)
        assert "trigger_dbt_cloud_job_run_and_wait_for_completion" in result_str, (
            "dbt entry must specify the _and_wait_for_completion variant"
        )

    def test_depends_on_past_has_workaround(self):
        """depends_on_past result contains a workaround using get_client()."""
        knowledge = load_knowledge(self.COLIN_OUTPUT_DIR)
        result = lookup("depends_on_past", knowledge)
        assert result["status"] == "found"
        result_str = json.dumps(result)
        assert "get_client" in result_str or "workaround" in result_str, (
            "depends_on_past entry must include workaround guidance"
        )

    def test_deferrable_has_automations_pattern(self):
        """deferrable operator result mentions Automations as the resource-efficient alternative."""
        knowledge = load_knowledge(self.COLIN_OUTPUT_DIR)
        result = lookup("deferrable", knowledge)
        assert result["status"] == "found"
        result_str = json.dumps(result)
        assert "Automation" in result_str or "automation" in result_str, (
            "deferrable entry must reference Prefect Automations as alternative"
        )

    def test_phase3_source_is_colin(self):
        """All Phase 3 entries should be sourced from Colin output, not fallback."""
        knowledge = load_knowledge(self.COLIN_OUTPUT_DIR)
        phase3_operators = [
            "AzureDataFactoryRunPipelineOperator",
            "WasbOperator",
            "DbtCloudRunJobOperator",
        ]
        for name in phase3_operators:
            result = lookup(name, knowledge)
            assert result["status"] == "found", f"{name} not found"
            assert result["source"] == "colin", (
                f"{name} found from {result['source']}, expected colin"
            )


class TestFallbackExpanded:
    """Tests for expanded FALLBACK_KNOWLEDGE entries (SRVR-03)."""

    def test_fallback_count(self):
        """FALLBACK_KNOWLEDGE has at least 15 entries."""
        assert len(FALLBACK_KNOWLEDGE) >= 15, (
            f"Expected >= 15 entries, got {len(FALLBACK_KNOWLEDGE)}"
        )

    def test_shortcircuit_fallback(self):
        """ShortCircuitOperator is found via fallback."""
        result = lookup("ShortCircuitOperator", {})
        assert result["status"] == "found"
        assert result["source"] == "fallback"

    def test_branch_python_fallback(self):
        """BranchPythonOperator is found via fallback."""
        result = lookup("BranchPythonOperator", {})
        assert result["status"] == "found"
        assert result["source"] == "fallback"

    def test_empty_operator_fallback(self):
        """EmptyOperator is found via fallback with guidance to remove placeholder."""
        result = lookup("EmptyOperator", {})
        assert result["status"] == "found"
        assert result["source"] == "fallback"

    def test_trigger_dagrun_fallback(self):
        """TriggerDagRunOperator is found via fallback."""
        result = lookup("TriggerDagRunOperator", {})
        assert result["status"] == "found"
        assert result["source"] == "fallback"

    def test_external_task_sensor_fallback(self):
        """ExternalTaskSensor is found via fallback."""
        result = lookup("ExternalTaskSensor", {})
        assert result["status"] == "found"
        assert result["source"] == "fallback"

    @pytest.mark.parametrize("entry", list(FALLBACK_KNOWLEDGE.values()))
    def test_each_fallback_has_required_fields(self, entry):
        """Every FALLBACK_KNOWLEDGE entry has the required minimum fields."""
        assert "concept_type" in entry, f"Missing concept_type in {entry}"
        assert "airflow" in entry, f"Missing airflow in {entry}"
        assert "prefect_equivalent" in entry, f"Missing prefect_equivalent in {entry}"
        assert "translation_rules" in entry, f"Missing translation_rules in {entry}"
