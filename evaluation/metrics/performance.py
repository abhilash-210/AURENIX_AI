"""
System Performance & Telemetry Aggregator.
"""

from __future__ import annotations

import statistics
from evaluation.models import AggregateMetricSummary


def compute_metric_summary(values: list[float]) -> AggregateMetricSummary:
    """Compute aggregate statistical summary for a list of numeric values."""
    if not values:
        return AggregateMetricSummary(mean=0.0, median=0.0, p95=0.0, min=0.0, max=0.0)

    sorted_vals = sorted(values)
    mean_val = statistics.mean(sorted_vals)
    median_val = statistics.median(sorted_vals)
    min_val = sorted_vals[0]
    max_val = sorted_vals[-1]

    # Calculate 95th percentile index
    p95_idx = int(len(sorted_vals) * 0.95)
    p95_idx = min(p95_idx, len(sorted_vals) - 1)
    p95_val = sorted_vals[p95_idx]

    return AggregateMetricSummary(
        mean=round(mean_val, 4),
        median=round(median_val, 4),
        p95=round(p95_val, 4),
        min=round(min_val, 4),
        max=round(max_val, 4),
    )
