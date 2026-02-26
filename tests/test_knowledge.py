"""Tests for knowledge loader."""

import json
from pathlib import Path

import pytest

from airflow_unfactor.knowledge import (
    load_knowledge,
    lookup,
    suggestions,
)


class TestLoadKnowledge:
    """Tests for load_knowledge function."""

    def test_missing_directory_returns_empty(self):
        """Missing Colin output dir returns empty dict."""
        result = load_knowledge("/nonexistent/path")
        assert result == {}

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
