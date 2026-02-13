"""Conversion metrics tracking for airflow-unfactor.

This module provides metrics collection and export for conversion operations.
Metrics are collected in-memory and can be exported to JSON for analysis.

Usage:
    from airflow_unfactor.metrics import record_conversion, get_aggregate_stats

    # Record a conversion
    record_conversion(
        dag_id="my_dag",
        success=True,
        operators_total=5,
        operators_converted=4,
        warnings=["Unknown operator X"],
    )

    # Get aggregate statistics
    stats = get_aggregate_stats()

Metrics are only collected when AIRFLOW_UNFACTOR_METRICS=1 is set.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ConversionMetrics:
    """Metrics for a single conversion operation."""

    dag_id: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    success: bool = True
    operators_total: int = 0
    operators_converted: int = 0
    operators_unknown: int = 0
    warnings: list[str] = field(default_factory=list)
    features_detected: list[str] = field(default_factory=list)
    execution_time_ms: float | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dag_id": self.dag_id,
            "timestamp": self.timestamp,
            "success": self.success,
            "operators_total": self.operators_total,
            "operators_converted": self.operators_converted,
            "operators_unknown": self.operators_unknown,
            "warnings": self.warnings,
            "features_detected": self.features_detected,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
        }


@dataclass
class AggregateStats:
    """Aggregate statistics across all conversions."""

    total_conversions: int = 0
    successful_conversions: int = 0
    failed_conversions: int = 0
    success_rate: float = 0.0
    total_operators: int = 0
    operators_converted: int = 0
    operators_unknown: int = 0
    operator_coverage: float = 0.0
    total_warnings: int = 0
    warning_frequency: dict[str, int] = field(default_factory=dict)
    features_frequency: dict[str, int] = field(default_factory=dict)
    avg_execution_time_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_conversions": self.total_conversions,
            "successful_conversions": self.successful_conversions,
            "failed_conversions": self.failed_conversions,
            "success_rate": round(self.success_rate, 2),
            "total_operators": self.total_operators,
            "operators_converted": self.operators_converted,
            "operators_unknown": self.operators_unknown,
            "operator_coverage": round(self.operator_coverage, 2),
            "total_warnings": self.total_warnings,
            "warning_frequency": self.warning_frequency,
            "features_frequency": self.features_frequency,
            "avg_execution_time_ms": self.avg_execution_time_ms,
        }


# In-memory storage for metrics
_metrics_store: list[ConversionMetrics] = []


def metrics_enabled() -> bool:
    """Check if metrics collection is enabled via environment variable."""
    return os.environ.get("AIRFLOW_UNFACTOR_METRICS", "").lower() in ("1", "true", "yes")


def record_conversion(
    dag_id: str,
    success: bool = True,
    operators_total: int = 0,
    operators_converted: int = 0,
    operators_unknown: int = 0,
    warnings: list[str] | None = None,
    features_detected: list[str] | None = None,
    execution_time_ms: float | None = None,
    error_message: str | None = None,
) -> ConversionMetrics | None:
    """Record metrics for a conversion operation.

    Args:
        dag_id: ID of the DAG being converted
        success: Whether the conversion succeeded
        operators_total: Total number of operators in the DAG
        operators_converted: Number of operators successfully converted
        operators_unknown: Number of unknown operators
        warnings: List of warning messages
        features_detected: List of features detected (e.g., "taskflow", "datasets")
        execution_time_ms: Time taken for conversion in milliseconds
        error_message: Error message if conversion failed

    Returns:
        ConversionMetrics object if metrics are enabled, None otherwise
    """
    if not metrics_enabled():
        return None

    metrics = ConversionMetrics(
        dag_id=dag_id,
        success=success,
        operators_total=operators_total,
        operators_converted=operators_converted,
        operators_unknown=operators_unknown,
        warnings=warnings or [],
        features_detected=features_detected or [],
        execution_time_ms=execution_time_ms,
        error_message=error_message,
    )

    _metrics_store.append(metrics)
    return metrics


def get_all_metrics() -> list[ConversionMetrics]:
    """Get all recorded metrics."""
    return _metrics_store.copy()


def clear_metrics() -> None:
    """Clear all recorded metrics."""
    _metrics_store.clear()


def get_aggregate_stats() -> AggregateStats:
    """Calculate aggregate statistics from all recorded metrics.

    Returns:
        AggregateStats with success rate, coverage, warning frequency, etc.
    """
    if not _metrics_store:
        return AggregateStats()

    total = len(_metrics_store)
    successful = sum(1 for m in _metrics_store if m.success)
    failed = total - successful

    total_ops = sum(m.operators_total for m in _metrics_store)
    converted_ops = sum(m.operators_converted for m in _metrics_store)
    unknown_ops = sum(m.operators_unknown for m in _metrics_store)

    # Calculate warning frequency
    warning_freq: dict[str, int] = {}
    total_warnings = 0
    for m in _metrics_store:
        total_warnings += len(m.warnings)
        for warning in m.warnings:
            # Extract warning category (first few words)
            category = warning.split(":")[0] if ":" in warning else warning[:50]
            warning_freq[category] = warning_freq.get(category, 0) + 1

    # Calculate feature frequency
    feature_freq: dict[str, int] = {}
    for m in _metrics_store:
        for feature in m.features_detected:
            feature_freq[feature] = feature_freq.get(feature, 0) + 1

    # Calculate average execution time
    times = [m.execution_time_ms for m in _metrics_store if m.execution_time_ms is not None]
    avg_time = sum(times) / len(times) if times else None

    return AggregateStats(
        total_conversions=total,
        successful_conversions=successful,
        failed_conversions=failed,
        success_rate=successful / total if total > 0 else 0.0,
        total_operators=total_ops,
        operators_converted=converted_ops,
        operators_unknown=unknown_ops,
        operator_coverage=converted_ops / total_ops if total_ops > 0 else 0.0,
        total_warnings=total_warnings,
        warning_frequency=warning_freq,
        features_frequency=feature_freq,
        avg_execution_time_ms=avg_time,
    )


def export_json() -> str:
    """Export all metrics as JSON string.

    Returns:
        JSON string with all metrics and aggregate stats
    """
    data = {
        "metrics": [m.to_dict() for m in _metrics_store],
        "aggregate": get_aggregate_stats().to_dict(),
        "exported_at": datetime.utcnow().isoformat(),
    }
    return json.dumps(data, indent=2)


def export_all_json() -> str:
    """Export all metrics as JSON string (alias for export_json).

    Returns:
        JSON string with all metrics
    """
    return export_json()


def export_to_file(path: str | Path) -> None:
    """Export metrics to a JSON file.

    Args:
        path: Path to write the JSON file
    """
    path = Path(path)
    path.write_text(export_json())


# Convenience exports
__all__ = [
    "ConversionMetrics",
    "AggregateStats",
    "metrics_enabled",
    "record_conversion",
    "get_all_metrics",
    "clear_metrics",
    "get_aggregate_stats",
    "export_json",
    "export_all_json",
    "export_to_file",
]
