"""Tests for lookup_concept tool."""

import asyncio
import json
from unittest.mock import patch

from airflow_unfactor.tools.lookup import lookup_concept


class TestLookupConcept:
    """Tests for lookup_concept MCP tool wrapper."""

    def test_fallback_lookup(self):
        """With no Colin output, falls back to built-in mappings."""
        with patch("airflow_unfactor.tools.lookup.load_knowledge", return_value={}):
            result = json.loads(asyncio.run(lookup_concept("PythonOperator")))

        assert result["status"] == "found"
        assert result["source"] == "fallback"
        assert result["concept_type"] == "operator"

    def test_colin_lookup(self):
        """With Colin output, returns from compiled knowledge."""
        colin_data = {
            "PythonOperator": {
                "concept_type": "operator",
                "airflow": {"name": "PythonOperator"},
                "prefect_equivalent": {"pattern": "@task"},
            }
        }
        with patch("airflow_unfactor.tools.lookup.load_knowledge", return_value=colin_data):
            result = json.loads(asyncio.run(lookup_concept("PythonOperator")))

        assert result["status"] == "found"
        assert result["source"] == "colin"

    def test_not_found(self):
        """Unknown concept returns not_found with suggestions."""
        with patch("airflow_unfactor.tools.lookup.load_knowledge", return_value={}):
            result = json.loads(asyncio.run(lookup_concept("CompletelyUnknownXYZ")))

        assert result["status"] == "not_found"
        assert isinstance(result["suggestions"], list)

    def test_connection_lookup(self):
        """Connection types are found in fallback."""
        with patch("airflow_unfactor.tools.lookup.load_knowledge", return_value={}):
            result = json.loads(asyncio.run(lookup_concept("postgres_default")))

        assert result["status"] == "found"
        assert result["concept_type"] == "connection"
