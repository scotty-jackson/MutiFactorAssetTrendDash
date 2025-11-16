"""
Trend Engine Module

Core functionality for computing trend scores, classifying trend states,
and calculating trend durations across financial time series.
"""

from .trend_engine import (
    compute_moving_averages,
    compute_slope,
    compute_trend_score,
    classify_trend_state,
    compute_trend_duration,
    compute_all_trend_metrics,
)

__all__ = [
    "compute_moving_averages",
    "compute_slope",
    "compute_trend_score",
    "classify_trend_state",
    "compute_trend_duration",
    "compute_all_trend_metrics",
]
