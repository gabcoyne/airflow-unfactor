"""Tests for the metrics module."""

import json
import tempfile
from pathlib import Path

import pytest

from airflow_unfactor.metrics import (
    AggregateStats,
    ConversionMetrics,
    clear_metrics,
    export_all_json,
    export_json,
    export_to_file,
    get_aggregate_stats,
    get_all_metrics,
    metrics_enabled,
    record_conversion,
)


@pytest.fixture(autouse=True)
def clean_metrics():
    """Clear metrics before and after each test."""
    clear_metrics()
    yield
    clear_metrics()


@pytest.fixture
def enable_metrics(monkeypatch):
    """Enable metrics collection for a test."""
    monkeypatch.setenv("AIRFLOW_UNFACTOR_METRICS", "1")
    yield


@pytest.fixture
def disable_metrics(monkeypatch):
    """Disable metrics collection for a test."""
    monkeypatch.delenv("AIRFLOW_UNFACTOR_METRICS", raising=False)
    yield


class TestMetricsEnabled:
    """Tests for metrics_enabled function."""

    def test_disabled_by_default(self, disable_metrics):
        """Metrics should be disabled by default."""
        assert metrics_enabled() is False

    def test_enabled_with_1(self, monkeypatch):
        """Metrics should be enabled with AIRFLOW_UNFACTOR_METRICS=1."""
        monkeypatch.setenv("AIRFLOW_UNFACTOR_METRICS", "1")
        assert metrics_enabled() is True

    def test_enabled_with_true(self, monkeypatch):
        """Metrics should be enabled with AIRFLOW_UNFACTOR_METRICS=true."""
        monkeypatch.setenv("AIRFLOW_UNFACTOR_METRICS", "true")
        assert metrics_enabled() is True

    def test_enabled_with_yes(self, monkeypatch):
        """Metrics should be enabled with AIRFLOW_UNFACTOR_METRICS=yes."""
        monkeypatch.setenv("AIRFLOW_UNFACTOR_METRICS", "yes")
        assert metrics_enabled() is True

    def test_disabled_with_0(self, monkeypatch):
        """Metrics should be disabled with AIRFLOW_UNFACTOR_METRICS=0."""
        monkeypatch.setenv("AIRFLOW_UNFACTOR_METRICS", "0")
        assert metrics_enabled() is False


class TestRecordConversion:
    """Tests for record_conversion function."""

    def test_records_when_enabled(self, enable_metrics):
        """Should record metrics when enabled."""
        result = record_conversion(
            dag_id="test_dag",
            success=True,
            operators_total=5,
            operators_converted=4,
        )

        assert result is not None
        assert result.dag_id == "test_dag"
        assert result.success is True
        assert result.operators_total == 5

    def test_returns_none_when_disabled(self, disable_metrics):
        """Should return None when metrics disabled."""
        result = record_conversion(dag_id="test_dag")
        assert result is None

    def test_stores_in_memory(self, enable_metrics):
        """Should store metrics in memory."""
        record_conversion(dag_id="dag1")
        record_conversion(dag_id="dag2")

        metrics = get_all_metrics()
        assert len(metrics) == 2
        assert metrics[0].dag_id == "dag1"
        assert metrics[1].dag_id == "dag2"

    def test_records_all_fields(self, enable_metrics):
        """Should record all provided fields."""
        result = record_conversion(
            dag_id="test_dag",
            success=False,
            operators_total=10,
            operators_converted=7,
            operators_unknown=3,
            warnings=["Warning 1", "Warning 2"],
            features_detected=["taskflow", "datasets"],
            execution_time_ms=150.5,
            error_message="Test error",
        )

        assert result.success is False
        assert result.operators_total == 10
        assert result.operators_converted == 7
        assert result.operators_unknown == 3
        assert result.warnings == ["Warning 1", "Warning 2"]
        assert result.features_detected == ["taskflow", "datasets"]
        assert result.execution_time_ms == 150.5
        assert result.error_message == "Test error"

    def test_includes_timestamp(self, enable_metrics):
        """Should include a timestamp."""
        result = record_conversion(dag_id="test_dag")
        assert result.timestamp is not None
        assert "T" in result.timestamp  # ISO format


class TestConversionMetrics:
    """Tests for ConversionMetrics dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary."""
        metrics = ConversionMetrics(
            dag_id="test_dag",
            success=True,
            operators_total=5,
        )
        result = metrics.to_dict()

        assert result["dag_id"] == "test_dag"
        assert result["success"] is True
        assert result["operators_total"] == 5

    def test_default_values(self):
        """Should have sensible defaults."""
        metrics = ConversionMetrics(dag_id="test")

        assert metrics.success is True
        assert metrics.operators_total == 0
        assert metrics.warnings == []
        assert metrics.features_detected == []


class TestClearMetrics:
    """Tests for clear_metrics function."""

    def test_clears_all_metrics(self, enable_metrics):
        """Should clear all stored metrics."""
        record_conversion(dag_id="dag1")
        record_conversion(dag_id="dag2")

        clear_metrics()

        assert len(get_all_metrics()) == 0


class TestGetAggregateStats:
    """Tests for get_aggregate_stats function."""

    def test_empty_stats(self):
        """Should return empty stats when no metrics."""
        stats = get_aggregate_stats()

        assert stats.total_conversions == 0
        assert stats.success_rate == 0.0

    def test_calculates_success_rate(self, enable_metrics):
        """Should calculate correct success rate."""
        record_conversion(dag_id="dag1", success=True)
        record_conversion(dag_id="dag2", success=True)
        record_conversion(dag_id="dag3", success=False)

        stats = get_aggregate_stats()

        assert stats.total_conversions == 3
        assert stats.successful_conversions == 2
        assert stats.failed_conversions == 1
        assert abs(stats.success_rate - 0.67) < 0.01

    def test_calculates_operator_coverage(self, enable_metrics):
        """Should calculate correct operator coverage."""
        record_conversion(dag_id="dag1", operators_total=10, operators_converted=8)
        record_conversion(dag_id="dag2", operators_total=5, operators_converted=5)

        stats = get_aggregate_stats()

        assert stats.total_operators == 15
        assert stats.operators_converted == 13
        assert abs(stats.operator_coverage - 0.87) < 0.01

    def test_calculates_warning_frequency(self, enable_metrics):
        """Should calculate warning frequency."""
        record_conversion(dag_id="dag1", warnings=["Unknown operator: X"])
        record_conversion(dag_id="dag2", warnings=["Unknown operator: Y", "Manual review needed"])
        record_conversion(dag_id="dag3", warnings=["Unknown operator: Z"])

        stats = get_aggregate_stats()

        assert stats.total_warnings == 4
        assert stats.warning_frequency["Unknown operator"] == 3

    def test_calculates_feature_frequency(self, enable_metrics):
        """Should calculate feature frequency."""
        record_conversion(dag_id="dag1", features_detected=["taskflow", "datasets"])
        record_conversion(dag_id="dag2", features_detected=["taskflow"])
        record_conversion(dag_id="dag3", features_detected=["datasets"])

        stats = get_aggregate_stats()

        assert stats.features_frequency["taskflow"] == 2
        assert stats.features_frequency["datasets"] == 2

    def test_calculates_avg_execution_time(self, enable_metrics):
        """Should calculate average execution time."""
        record_conversion(dag_id="dag1", execution_time_ms=100.0)
        record_conversion(dag_id="dag2", execution_time_ms=200.0)
        record_conversion(dag_id="dag3")  # No time

        stats = get_aggregate_stats()

        assert stats.avg_execution_time_ms == 150.0


class TestAggregateStats:
    """Tests for AggregateStats dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary."""
        stats = AggregateStats(
            total_conversions=10,
            success_rate=0.8,
        )
        result = stats.to_dict()

        assert result["total_conversions"] == 10
        assert result["success_rate"] == 0.8


class TestExportJson:
    """Tests for export_json function."""

    def test_exports_valid_json(self, enable_metrics):
        """Should export valid JSON."""
        record_conversion(dag_id="test_dag")

        result = export_json()
        data = json.loads(result)

        assert "metrics" in data
        assert "aggregate" in data
        assert "exported_at" in data

    def test_export_all_json_alias(self, enable_metrics):
        """export_all_json should be alias for export_json."""
        record_conversion(dag_id="test_dag")

        result1 = export_json()
        result2 = export_all_json()

        # Both should parse to same structure (timestamps may differ slightly)
        data1 = json.loads(result1)
        data2 = json.loads(result2)
        assert data1["metrics"] == data2["metrics"]


class TestExportToFile:
    """Tests for export_to_file function."""

    def test_writes_file(self, enable_metrics):
        """Should write JSON to file."""
        record_conversion(dag_id="test_dag")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "metrics.json"
            export_to_file(path)

            assert path.exists()
            data = json.loads(path.read_text())
            assert len(data["metrics"]) == 1

    def test_accepts_string_path(self, enable_metrics):
        """Should accept string path."""
        record_conversion(dag_id="test_dag")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/metrics.json"
            export_to_file(path)

            assert Path(path).exists()
